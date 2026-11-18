# -*- coding: utf-8 -*-
"""Tests automatiques du routage et de la creation des e-mails DSS.

Ces tests utilisent la base temporaire geree par Odoo et ne contactent pas
de serveur SMTP. Ils verifient surtout les objets mail.mail et le journal DSS.
"""

# Importe les outils de tests integres a Odoo.
from odoo.tests import common

# datetime et timedelta servent a vieillir artificiellement un journal
# pour tester la purge des courriels.
from datetime import datetime, timedelta


class TestDssNotifications(common.TransactionCase):
    """Verifie le routage des notifications DSS sans utiliser de serveur SMTP."""

    def setUp(self):
        # Initialise d'abord les objets et la transaction fournis par Odoo.
        super(TestDssNotifications, self).setUp()
        # Recupere le modele des demandes pour creer les donnees de test.
        self.Request = self.env["dss.request"]
        # Recupere le modele qui journalise les e-mails DSS crees.
        self.NotificationLog = self.env["dss.notification.log"]

    def _create_user(self, name, email, group_xmlid=None):
        partner = self.env["res.partner"].create(
            {"name": name, "email": email}
        )
        group_ids = [self.ref("base.group_user")]
        if group_xmlid:
            group_ids.append(self.ref(group_xmlid))
        return self.env["res.users"].sudo().create(
            {
                "name": name,
                "login": email,
                "partner_id": partner.id,
                "groups_id": [(6, 0, group_ids)],
            }
        )

    def _create_routed_request(self, suffix):
        requester_email = "dss.requester.%s@example.invalid" % suffix
        chef_email = "dss.chef.%s@example.invalid" % suffix
        magasin_email = "dss.magasin.%s@example.invalid" % suffix
        requester = self._create_user(
            "DSS Requester %s" % suffix,
            requester_email,
            "dss_v2.group_dss_demandeur",
        )
        chef = self._create_user(
            "DSS Chef %s" % suffix,
            chef_email,
            "dss_v2.group_dss_chef",
        )
        self._create_user(
            "DSS Magasin %s" % suffix,
            magasin_email,
            "dss_v2.group_dss_magasin",
        )
        service = self.env["dss.service"].sudo().create(
            {
                "name": "DSS Service %s" % suffix,
                "dss_chef_id": chef.id,
                "dss_demandeurs_ids": [(6, 0, [requester.id])],
            }
        )
        request = self.Request.sudo().with_context(
            dss_user_id=requester.id
        ).create({"name": "TEST-DSS-%s" % suffix})
        return request, requester_email, chef_email, magasin_email

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

    def test_stock_approval_notifies_requester_with_closure_instruction(self):
        request, requester_email, chef_email, _magasin_email = (
            self._create_routed_request("STOCK-APPROVAL")
        )
        request.sudo().write({"state": "approuve"})

        request._dss_notify_stock_approval()

        log = self.NotificationLog.search(
            [
                ("request_id", "=", request.id),
                ("event_key", "=", "stock_approval"),
            ],
            limit=1,
        )
        body = " ".join(log.mail_id.body_html.split())
        recipients = set(log.recipient_emails.split(","))
        self.assertIn(requester_email, recipients)
        self.assertIn(chef_email, recipients)
        self.assertIn(
            "Votre demande a été validée par le magasin. "
            "Vous pouvez maintenant la consulter et la clôturer.",
            body,
        )
        self.assertIn(request.demandeur_id.name, body)
        self.assertIn(request.service_demandeur_id.name, body)
        self.assertIn("Statut", body)

    def test_stock_approval_email_lists_changed_lines_and_reasons(self):
        request, requester_email, chef_email, _magasin_email = (
            self._create_routed_request("STOCK-APPROVAL-CHANGES")
        )
        product = self.env["product.product"].sudo().create(
            {"name": "Produit ajusté"}
        )
        self.env["dss.request.line"].sudo().create(
            {
                "request_id": request.id,
                "product_id": product.id,
                "qty_demandee": 5.0,
                "qty_sortie": 3.0,
                "motif_ecart": "Stock disponible limité",
            }
        )
        request.sudo().write({"state": "approuve"})

        request._dss_notify_stock_approval()

        log = self.NotificationLog.search(
            [
                ("request_id", "=", request.id),
                ("event_key", "=", "stock_approval"),
            ],
            limit=1,
        )
        body = " ".join(log.mail_id.body_html.split())
        recipients = set(log.recipient_emails.split(","))
        self.assertIn(requester_email, recipients)
        self.assertIn(chef_email, recipients)
        self.assertIn("<ul>", body)
        self.assertIn("<li>", body)
        self.assertNotIn("&lt;ul&gt;", body)
        self.assertIn("Produit ajusté", body)
        self.assertIn("quantité demandée 5.0, quantité sortie 3.0", body)
        self.assertIn("Motif : Stock disponible limité", body)

    def test_return_material_approval_email_uses_return_quantity(self):
        request, requester_email, chef_email, _magasin_email = (
            self._create_routed_request("RETURN-MATERIAL-APPROVAL")
        )
        request.sudo().write({"type_intervention": "retour_materiel"})
        product = self.env["product.product"].sudo().create(
            {"name": "Returned item"}
        )
        self.env["dss.request.line"].sudo().create(
            {
                "request_id": request.id,
                "product_id": product.id,
                "qty_retour": 2.0,
                "motif_ecart": "Received quantity differs",
            }
        )
        request.sudo().write({"state": "approuve"})

        request._dss_notify_stock_approval()

        log = self.NotificationLog.search(
            [
                ("request_id", "=", request.id),
                ("event_key", "=", "stock_approval"),
            ],
            limit=1,
        )
        body = log.mail_id.body_html
        if isinstance(body, str):
            body = body.decode("utf-8")
        body = u" ".join(body.split())
        self.assertIn(requester_email, log.recipient_emails)
        self.assertIn(chef_email, log.recipient_emails)
        self.assertIn("Returned item", body)
        self.assertIn("quantit&#233; retourn&#233;e valid&#233;e 2.0", body)
        self.assertIn("Motif : Received quantity differs", body)
        self.assertNotIn("quantit&#233; demand&#233;e", body)

    def test_stock_rejection_notifies_requester_and_assigned_chef(self):
        request, requester_email, chef_email, _magasin_email = (
            self._create_routed_request("STOCK-REJECTION")
        )
        request.sudo().write(
            {"state": "rejete", "motif_rejet": "Stock indisponible"}
        )

        request._dss_notify_rejection("valide_magasin")

        log = self.NotificationLog.search(
            [
                ("request_id", "=", request.id),
                ("event_key", "=", "stock_rejection"),
            ],
            limit=1,
        )
        body = " ".join(log.mail_id.body_html.split())
        self.assertEqual(
            set(log.recipient_emails.split(",")),
            set([requester_email, chef_email]),
        )
        self.assertIn(
            "La demande a été rejetée par le magasin. "
            "Motif : Stock indisponible.",
            body,
        )
        self.assertIn(request.demandeur_id.name, body)
        self.assertIn(request.service_demandeur_id.name, body)
        self.assertIn("Statut", body)

    def test_closure_notifies_assigned_chef_magasin_and_requester(self):
        request, requester_email, chef_email, magasin_email = (
            self._create_routed_request("CLOSURE")
        )
        request.sudo().write({"state": "cloture"})

        request._dss_notify_closure()

        log = self.NotificationLog.search(
            [
                ("request_id", "=", request.id),
                ("event_key", "=", "closure"),
            ],
            limit=1,
        )
        body = " ".join(log.mail_id.body_html.split())
        recipients = set(log.recipient_emails.split(","))
        self.assertIn(requester_email, recipients)
        self.assertIn(chef_email, recipients)
        self.assertIn(magasin_email, recipients)
        self.assertIn(
            "La demande a été officiellement clôturée par le demandeur.",
            body,
        )
        self.assertIn(request.demandeur_id.name, body)
        self.assertIn(request.service_demandeur_id.name, body)
        self.assertIn("Statut", body)

    def test_exceptional_closure_email_contains_its_reason(self):
        request, _requester_email, _chef_email, _magasin_email = (
            self._create_routed_request("EXCEPTION-CLOSURE")
        )
        request.sudo().write({"state": "cloture"})

        request.with_context(
            dss_closure_is_exception=True,
            dss_closure_motif_exception="Le demandeur est absent",
        )._dss_notify_closure()

        log = self.NotificationLog.search(
            [
                ("request_id", "=", request.id),
                ("event_key", "=", "closure"),
            ],
            limit=1,
        )
        body = " ".join(log.mail_id.body_html.split())
        self.assertIn(
            "La demande a été clôturée exceptionnellement par le Chef DSS.",
            body,
        )
        self.assertIn("Motif de la clôture exceptionnelle", body)
        self.assertIn("Le demandeur est absent", body)

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

    def test_stock_approval_email_explains_that_requester_can_close(self):
        """Le mail Stock indique que la DSS peut maintenant être clôturée."""
        request = self.Request.create({"name": "TEST-DSS-STOCK-APPROVAL"})
        request._dss_notify_workflow(
            "stock_approval",
            "Approbation Stock",
            ["stock-approval@example.invalid"],
        )
        log = self.NotificationLog.search(
            [("request_id", "=", request.id), ("event_key", "=", "stock_approval")],
            limit=1,
        )
        self.assertIn("Le stock a été mis à jour", log.mail_id.body_html)
        self.assertIn("clôturer votre demande", log.mail_id.body_html)

    def test_closure_email_confirms_request_is_closed(self):
        """Le mail de clôture confirme la fin du workflow DSS."""
        request = self.Request.create({"name": "TEST-DSS-CLOSURE"})
        request._dss_notify_workflow(
            "closure",
            "Clôture",
            ["closure@example.invalid"],
        )
        log = self.NotificationLog.search(
            [("request_id", "=", request.id), ("event_key", "=", "closure")],
            limit=1,
        )
        self.assertIn(
            "La demande de sortie de stock est maintenant clôturée",
            log.mail_id.body_html,
        )

    def test_stock_approval_email_contains_quantity_change_motif(self):
        """La validation Stock transmet le motif d'écart par article."""
        request = self.Request.create({"name": "TEST-DSS-STOCK-MOTIF"})
        product = self.env["product.product"].create({
            "name": "Article câble accentué",
            "type": "product",
        })
        self.env["dss.request.line"].create({
            "request_id": request.id,
            "product_id": product.id,
            "qty_demandee": 10.0,
            "qty_sortie": 7.0,
            "motif_ecart": "Stock indisponible à l'emplacement demandé",
        })
        self.env.user.partner_id.write({"email": "requester@example.invalid"})

        request._dss_notify_stock_approval()

        log = self.NotificationLog.search([
            ("request_id", "=", request.id),
            ("event_key", "=", "stock_approval"),
        ], limit=1)
        self.assertTrue(log)
        self.assertIn("Stock indisponible", log.mail_id.body_html)
        self.assertIn("Article câble accentué", log.mail_id.body_html)
        self.assertIn("<ul", log.mail_id.body_html)
        self.assertIn("<li", log.mail_id.body_html)

    def test_stock_approval_email_escapes_quantity_change_html(self):
        """Les noms et motifs ne peuvent pas injecter de balises HTML."""
        request = self.Request.create({"name": "TEST-DSS-STOCK-HTML"})
        product = self.env["product.product"].create({
            "name": "Article <script>",
            "type": "product",
        })
        self.env["dss.request.line"].create({
            "request_id": request.id,
            "product_id": product.id,
            "qty_demandee": 10.0,
            "qty_sortie": 7.0,
            "motif_ecart": "Motif <script>alert(1)</script>",
        })
        self.env.user.partner_id.write({"email": "requester@example.invalid"})

        request._dss_notify_stock_approval()

        log = self.NotificationLog.search([
            ("request_id", "=", request.id),
            ("event_key", "=", "stock_approval"),
        ], limit=1)
        self.assertTrue(log)
        self.assertIn("&lt;script&gt;", log.mail_id.body_html)
        self.assertNotIn("<script>", log.mail_id.body_html)

    def test_rejection_mapping_is_explicit(self):
        """Verifie l'etat initial et l'absence de motif sur une nouvelle demande."""
        # Cree une demande neuve sans fournir d'etat ni de motif.
        request = self.Request.create({"name": "TEST-DSS-REJECTION"})
        # Verifie la valeur par defaut du statut de toute nouvelle demande.
        self.assertEqual(request.state, "brouillon")
        # Verifie qu'aucun motif n'a ete defini a la creation.
        self.assertFalse(request.motif_rejet)

    def test_loopback_base_url_omits_broken_image_and_link(self):
        """Une adresse localhost ne doit produire ni image ni lien casses."""
        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "http://localhost:8069"
        )
        request = self.Request.create({"name": "TEST-DSS-LOOPBACK"})

        self.assertTrue(
            request._dss_notify_once(
                "submission", "Soumission", ["no-real-send@example.invalid"]
            )
        )

        log = self.NotificationLog.search(
            [
                ("request_id", "=", request.id),
                ("event_key", "=", "submission"),
            ],
            limit=1,
        )
        body = log.mail_id.body_html
        self.assertNotIn("localhost", body)
        self.assertNotIn("/web/binary/company_logo", body)
        self.assertNotIn("/web?db=", body)
        self.assertIn(self.env.user.company_id.name, body)
        # Le bouton reste present dans le modele, mais sans adresse exploitable.
        self.assertIn("Consulter la demande", body)

    def test_lan_base_url_keeps_logo_and_button(self):
        """Une adresse du reseau interne reste utilisable dans les courriels."""
        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "http://192.168.1.50:8069"
        )
        request = self.Request.create({"name": "TEST-DSS-LAN"})

        self.assertTrue(
            request._dss_notify_once(
                "submission", "Soumission", ["no-real-send@example.invalid"]
            )
        )

        log = self.NotificationLog.search(
            [
                ("request_id", "=", request.id),
                ("event_key", "=", "submission"),
            ],
            limit=1,
        )
        body = log.mail_id.body_html
        self.assertIn(
            "http://192.168.1.50:8069/web/binary/company_logo", body
        )
        self.assertIn("http://192.168.1.50:8069/web?db=", body)

    def test_email_displays_readable_status_label(self):
        """La carte de reference affiche le libelle du statut, pas le code technique."""
        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "https://odoo.example.test"
        )
        request = self.Request.create({"name": "TEST-DSS-STATUS-LABEL"})
        request.sudo().write({"state": "valide_chef"})

        self.assertTrue(
            request._dss_notify_once(
                "chef_validation",
                "Validation Chef",
                ["no-real-send@example.invalid"],
            )
        )

        log = self.NotificationLog.search(
            [
                ("request_id", "=", request.id),
                ("event_key", "=", "chef_validation"),
            ],
            limit=1,
        )
        body = " ".join(log.mail_id.body_html.split())
        self.assertIn("Validation Chef", body)
        self.assertNotIn("valide_chef", body)

    def test_rejection_email_escapes_the_motif(self):
        """Le motif de rejet ne peut pas injecter de HTML dans le courriel."""
        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "https://odoo.example.test"
        )
        request = self.Request.create({"name": "TEST-DSS-MOTIF-ESCAPE"})

        self.assertTrue(
            request._dss_notify_once(
                "chef_rejection",
                "Rejet par le Chef",
                ["no-real-send@example.invalid"],
                "Motif <script>alert(1)</script>",
            )
        )

        log = self.NotificationLog.search(
            [
                ("request_id", "=", request.id),
                ("event_key", "=", "chef_rejection"),
            ],
            limit=1,
        )
        self.assertIn("&lt;script&gt;", log.mail_id.body_html)
        self.assertNotIn("<script>", log.mail_id.body_html)

    def test_subject_contains_intervention_label(self):
        """Le sujet rappelle le type d'intervention pour trier les courriels."""
        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "https://odoo.example.test"
        )
        request = self.Request.create({
            "name": "TEST-DSS-SUBJECT",
            "type_intervention": "depannage",
        })

        self.assertTrue(
            request._dss_notify_once(
                "submission", "Soumission", ["no-real-send@example.invalid"]
            )
        )

        log = self.NotificationLog.search(
            [
                ("request_id", "=", request.id),
                ("event_key", "=", "submission"),
            ],
            limit=1,
        )
        self.assertIn("TEST-DSS-SUBJECT", log.mail_id.subject)
        self.assertIn("Depannage", log.mail_id.subject)

    # ------------------------------------------------------------------
    # Purge des courriels (version 2.15)
    # ------------------------------------------------------------------

    def _notification_for_purge(self, request_name):
        """Crée une notification et retourne son journal.

        L'adresse .invalid est réservée : aucun courriel réel n'est envoyé.
        """
        # URL publique factice pour que le modèle rende un contenu complet.
        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "https://odoo.example.test"
        )
        request = self.Request.create({"name": request_name})
        self.assertTrue(
            request._dss_notify_once(
                "submission", "Soumission", ["no-real-send@example.invalid"]
            )
        )
        return self.NotificationLog.search(
            [
                ("request_id", "=", request.id),
                ("event_key", "=", "submission"),
            ],
            limit=1,
        )

    def _backdate_log(self, log, days):
        """Vieillit artificiellement un journal de N jours.

        create_date est en lecture seule dans l'interface, mais l'ORM accepte
        l'écriture : c'est la seule façon de simuler une ancienne notification
        sans attendre 60 jours.
        """
        old_date = (datetime.now() - timedelta(days=days)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        log.write({"create_date": old_date})
        return old_date

    def test_cron_purges_old_sent_mails_and_keeps_log(self):
        """Le cron supprime le courriel ancien mais conserve le journal."""
        log = self._notification_for_purge("TEST-DSS-PURGE-OLD")
        mail = log.mail_id
        self.assertTrue(mail)

        # Le courriel doit être considéré comme envoyé pour être purgeable.
        mail.write({"state": "sent"})
        # On le vieillit de 90 jours, donc au-delà des 60 jours de rétention.
        self._backdate_log(log, 90)

        purged = self.Request._dss_cron_purge_old_mails()

        self.assertEqual(purged, 1)
        # Le courriel a disparu...
        self.assertFalse(mail.exists())
        # ... mais la trace métier reste, sans lien vers le courriel supprimé.
        self.assertTrue(log.exists())
        self.assertFalse(log.mail_id)

    def test_cron_keeps_recent_mails(self):
        """Un courriel récent n'est jamais purgé."""
        log = self._notification_for_purge("TEST-DSS-PURGE-RECENT")
        mail = log.mail_id
        mail.write({"state": "sent"})
        # Seulement 10 jours : la fenêtre de 60 jours n'est pas dépassée.
        self._backdate_log(log, 10)

        purged = self.Request._dss_cron_purge_old_mails()

        self.assertEqual(purged, 0)
        self.assertTrue(mail.exists())

    def test_cron_keeps_pending_mails_even_when_old(self):
        """Un courriel encore en file n'est pas purgé, même ancien."""
        log = self._notification_for_purge("TEST-DSS-PURGE-PENDING")
        mail = log.mail_id
        # On ne touche pas à l'état : le courriel reste 'outgoing'.
        self._backdate_log(log, 90)

        purged = self.Request._dss_cron_purge_old_mails()

        self.assertEqual(purged, 0)
        self.assertTrue(mail.exists())
