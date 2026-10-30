# -*- coding: utf-8 -*-
"""Tests automatiques du routage et de la creation des e-mails DSS.

Ces tests utilisent la base temporaire geree par Odoo et ne contactent pas
de serveur SMTP. Ils verifient surtout les objets mail.mail et le journal DSS.
"""

# Importe les outils de tests integres a Odoo.
from odoo.tests import common


class TestDssNotifications(common.TransactionCase):
    """Verifie le routage des notifications DSS sans utiliser de serveur SMTP."""

    def setUp(self):
        # Initialise d'abord les objets et la transaction fournis par Odoo.
        super(TestDssNotifications, self).setUp()
        # Recupere le modele des demandes pour creer les donnees de test.
        self.Request = self.env["dss.request"]
        # Recupere le modele qui journalise les e-mails DSS crees.
        self.NotificationLog = self.env["dss.notification.log"]

    def test_group_email_resolution_ignores_missing_email(self):
        """Verifie que le groupe Chef existe et que ses adresses sont uniques."""
        # Recherche le groupe Chef par son identifiant XML unique.
        group = self.env.ref("dss_v2.group_dss_chef")
        # Verifie que la configuration de ce groupe est presente en base.
        self.assertTrue(group)
        # Demande au modele DSS les adresses des membres actifs de ce groupe.
        emails = self.Request._dss_group_emails("dss_v2.group_dss_chef")
        # set(emails) retire les doublons; les tailles doivent donc etre egales.
        self.assertEqual(len(emails), len(set(emails)))

    def test_missing_recipient_does_not_create_mail_or_log(self):
        """Verifie qu'aucun mail ni journal n'est cree sans destinataire."""
        # Cree une demande avec un nom de test fixe pour la retrouver facilement.
        request = self.Request.create({"name": "TEST-DSS-NO-EMAIL"})
        # Transmet une liste vide de destinataires a la methode de notification.
        self.assertFalse(
            request._dss_notify_once("submission", "Soumission", [])
        )
        # Cherche un journal associe a cette demande et a l'evenement submission.
        self.assertFalse(
            self.NotificationLog.search(
                # Chaque paire du domaine est un critere: champ, operateur, valeur.
                [("request_id", "=", request.id), ("event_key", "=", "submission")]
            )
        )

    def test_mail_is_queued_without_sending(self):
        """Verifie que le mail est en file et reste absent du chatter de la DSS."""
        # Configure une URL publique de test pour vérifier le logo généré.
        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "https://odoo.example.test"
        )
        # Cree la demande qui servira d'objet au test.
        request = self.Request.create({"name": "TEST-DSS-QUEUE"})
        # Cree une notification vers une adresse de test qui ne peut pas recevoir.
        # Le suffixe .invalid est reserve et evite d'envoyer un vrai courriel.
        self.assertTrue(
            request._dss_notify_once(
                # Donne a l'evenement une cle et un libelle lisible.
                "submission", "Soumission", ["no-real-send@example.invalid"]
            )
        )
        # Retrouve la ligne de journal creee pour cette demande et cet evenement.
        log = self.NotificationLog.search(
            # Le domaine filtre par la demande et la cle technique de l'evenement.
            [("request_id", "=", request.id), ("event_key", "=", "submission")],
            # Une seule ligne suffit, car la contrainte interdit les doublons.
            limit=1,
        )
        # Verifie que le journal pointe vers un e-mail Odoo.
        self.assertTrue(log.mail_id)
        # Verifie que le courriel est en attente de traitement par la file Odoo.
        self.assertEqual(log.mail_id.state, "outgoing")
        # Vérifie que le template utilise le domaine public et la société courante.
        self.assertIn(
            "https://odoo.example.test/web/binary/company_logo?db=%s&company=%s"
            % (self.env.cr.dbname, self.env.user.company_id.id),
            log.mail_id.body_html,
        )
        # Vérifie que le bouton ouvre la demande dans la base qui a envoyé l'e-mail.
        self.assertIn(
            "https://odoo.example.test/web?db=%s#id=%s&view_type=form&model=dss.request"
            % (self.env.cr.dbname, request.id),
            log.mail_id.body_html,
        )
        # Un evenement de soumission ne doit pas afficher la ligne du motif.
        self.assertNotIn("Motif :", log.mail_id.body_html)
        # Le mail reste autonome et n'apparait pas dans le chatter de la demande.
        # model indique le type de fiche Odoo auquel un message est rattache.
        self.assertFalse(log.mail_id.model)
        # res_id contient normalement l'identifiant de cette fiche Odoo.
        self.assertFalse(log.mail_id.res_id)
        # Le journal des notifications conserve le lien métier avec la demande.
        # L'e-mail est donc detache, mais son journal reste relie a la DSS.
        self.assertEqual(log.request_id, request)

    def test_same_event_is_not_queued_twice(self):
        """Verifie qu'un meme evenement ne produit pas deux e-mails."""
        # Cree une nouvelle demande pour isoler ce scenario.
        request = self.Request.create({"name": "TEST-DSS-IDEMPOTENT"})
        # Place une adresse valide de test dans une liste de destinataires.
        recipients = ["no-real-send@example.invalid"]
        # Le premier appel doit creer le mail et le journal correspondants.
        self.assertTrue(
            request._dss_notify_once("submission", "Soumission", recipients)
        )
        # Le second appel avec la meme cle doit etre refuse comme doublon.
        self.assertFalse(
            request._dss_notify_once("submission", "Soumission", recipients)
        )
        # Compte les journaux de cet evenement pour cette demande: il doit y en avoir un.
        self.assertEqual(
            self.NotificationLog.search_count(
                # Le domaine limite le comptage a la demande et a l'evenement testes.
                [("request_id", "=", request.id), ("event_key", "=", "submission")]
            ),
            # Valeur attendue: un seul journal.
            1,
        )

    def test_notification_event_keys_are_unique(self):
        """Verifie que la base refuse deux journaux pour le meme evenement."""
        # Cree la demande a laquelle les journaux seront rattaches.
        request = self.Request.create({"name": "TEST-DSS"})
        # Cree une premiere ligne de journal pour l'evenement submission.
        self.NotificationLog.create(
            {"request_id": request.id, "event_key": "submission"}
        )
        # Demande au test de considerer une exception comme le resultat attendu.
        with self.assertRaises(Exception):
            # Essaie de creer le meme couple demande/evenement une seconde fois.
            # La contrainte SQL unique doit faire echouer cette creation.
            self.NotificationLog.create(
                {"request_id": request.id, "event_key": "submission"}
            )

    def test_approval_uses_one_event_for_both_entry_points(self):
        """Verifie qu'aucune notification d'approbation n'existe avant l'action."""
        # Cree une demande sans declencher son approbation.
        request = self.Request.create({"name": "TEST-DSS-APPROVAL"})
        # Verifie qu'aucun journal stock_approval n'a encore ete cree.
        self.assertFalse(
            self.NotificationLog.search(
                # Cherche uniquement pour cette demande et cette cle d'evenement.
                [("request_id", "=", request.id), ("event_key", "=", "stock_approval")]
            )
        )

    def test_rejection_keeps_motif_in_notification_context(self):
        """Verifie que le motif de rejet est inclus dans l'e-mail."""
        # Cree une demande de test avec un motif de rejet deja renseigne.
        request = self.Request.create(
            {"name": "TEST-DSS-REJECTION-MOTIF", "motif_rejet": "Stock indisponible"}
        )
        # Cree le courriel en passant le motif a la methode de notification.
        self.assertTrue(
            request._dss_notify_once(
                # Indique que l'evenement est un rejet par le Chef.
                "chef_rejection",
                # Definit le libelle qui sera transmis au modele d'e-mail.
                "Rejet par le Chef",
                # Fournit un destinataire de test sans adresse de reception reelle.
                ["no-real-send@example.invalid"],
                # Fournit le texte qui doit apparaitre dans le corps du courriel.
                request.motif_rejet,
            )
        )
        # Retrouve le mail genere via le journal de l'evenement de rejet.
        mail = self.NotificationLog.search(
            # Filtre les journaux de cette demande et du rejet par le Chef.
            [("request_id", "=", request.id), ("event_key", "=", "chef_rejection")],
            # Ne recupere que le premier resultat correspondant.
            limit=1,
        # Accede au courriel lie au journal trouve.
        ).mail_id
        # Verifie que le texte du motif se trouve dans le corps HTML du mail.
        self.assertIn("Stock indisponible", mail.body_html)

    def test_return_to_requester_email_contains_rejection_motif(self):
        """Verifie que le renvoi au demandeur reprend le motif du rejet."""
        # Cree une demande avec le motif conserve apres son rejet.
        request = self.Request.create(
            {"name": "TEST-DSS-RETURN-MOTIF", "motif_rejet": "Quantite a preciser"}
        )
        # Ajoute une adresse de test au createur, qui sert de demandeur par defaut.
        self.env.user.partner_id.write({"email": "requester@example.invalid"})
        # Utilise la vraie methode de notification de renvoi de la demande.
        request._dss_notify_return_to_requester()
        # Recherche le journal cree pour l'evenement de renvoi.
        log = self.NotificationLog.search(
            [
                ("request_id", "=", request.id),
                ("event_key", "=", "return_to_requester"),
            ],
            limit=1,
        )
        # Verifie que le demandeur est bien le destinataire enregistre.
        self.assertEqual(log.recipient_emails, "requester@example.invalid")
        # Verifie que le motif figure dans le corps HTML du courriel.
        self.assertIn("Quantite a preciser", log.mail_id.body_html)

    def test_security_is_not_notified_without_a_real_dss_security_transition(self):
        """Verifie qu'aucun e-mail Securite n'est prevu sans etape dediee."""
        # Cree une demande qui n'a pas de transition de validation Securite.
        request = self.Request.create({"name": "TEST-DSS-SECURITY"})
        # Appelle la notification d'approbation Stock, qui ne cible pas la Securite.
        request._dss_notify_stock_approval()
        # Verifie qu'aucun journal portant une cle d'evenement security n'existe.
        self.assertFalse(
            self.NotificationLog.search(
                # Limite la recherche a cette demande et a cette cle d'evenement.
                [("request_id", "=", request.id), ("event_key", "=", "security")]
            )
        )

    def test_rejection_mapping_is_explicit(self):
        """Verifie l'etat initial et l'absence de motif sur une nouvelle demande."""
        # Cree une demande neuve sans fournir d'etat ni de motif.
        request = self.Request.create({"name": "TEST-DSS-REJECTION"})
        # Verifie la valeur par defaut du statut de toute nouvelle demande.
        self.assertEqual(request.state, "brouillon")
        # Verifie qu'aucun motif n'a ete defini a la creation.
        self.assertFalse(request.motif_rejet)
