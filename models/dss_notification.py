# -*- coding: utf-8 -*-

# Importe le module standard qui ecrit des informations dans les journaux Odoo.
import logging

# Importe les outils Odoo pour les modeles, les champs et les API.
from odoo import api, fields, models

# Cree un journal Python nomme pour ce fichier.
_logger = logging.getLogger(__name__)


class DssNotificationLog(models.Model):
    """Journal technique qui evite les doublons de notification DSS."""

    # Declare le nom technique du modele stocke dans la base Odoo.
    _name = "dss.notification.log"
    # Definit le libelle descriptif du modele dans l'administration Odoo.
    _description = "Journal des notifications DSS"
    # Affiche les journaux du plus recent au plus ancien.
    _order = "id desc"

    # Relie chaque journal a la demande DSS concernee.
    # Supprime le journal si sa demande est supprimee.
    request_id = fields.Many2one(
        "dss.request", string="Demande DSS", required=True, ondelete="cascade"
    )
    # Stocke le nom technique de l'evenement, par exemple submission.
    event_key = fields.Char(string="Evenement", required=True)
    # Relie le journal au courriel cree par Odoo.
    # readonly empeche la modification manuelle depuis les formulaires.
    mail_id = fields.Many2one("mail.mail", string="Email Odoo", readonly=True)
    # Conserve les adresses auxquelles le courriel a ete adresse.
    # Ce champ est en lecture seule dans l'interface.
    recipient_emails = fields.Text(string="Destinataires", readonly=True)

    # Declare les contraintes SQL appliquees directement par la base de donnees.
    _sql_constraints = [
        (
            # Donne un nom unique a la contrainte pour Odoo et PostgreSQL.
            "dss_notification_once",
            # Interdit deux journaux avec la meme demande et le meme evenement.
            "unique(request_id, event_key)",
            # Texte affiche si la contrainte unique est violee.
            "Une notification DSS ne peut etre creee qu une seule fois par evenement.",
        ),
    ]


class DssRequestNotification(models.Model):
    """Gestion des e-mails lies au workflow des demandes DSS."""

    # Etend le modele DSS existant sans creer un nouveau modele de demande.
    _inherit = "dss.request"

    # Identifiant externe du modele d'e-mail declare dans le fichier XML.
    _dss_template_xmlid = "dss_v2.mail_template_dss_workflow"

    def _dss_user_email(self, user):
        """Retourne l'adresse du contact, ou celle de l'utilisateur en repli."""
        # Recupere le contact Odoo lie au compte utilisateur.
        partner = user.partner_id
        # Prefere l'adresse du contact, puis utilise celle du compte en repli.
        # strip() retire les espaces au debut et a la fin, pas ceux au milieu.
        return (partner.email or user.email or "").strip()

    def _dss_group_emails(self, group_xmlid):
        """Retourne les adresses uniques des utilisateurs actifs d'un groupe."""
        # Charge le groupe demande sans provoquer d'erreur s'il n'existe pas.
        group = self.env.ref(group_xmlid, raise_if_not_found=False)
        # Un groupe absent est represente par une valeur vide.
        if not group:
            # Retourne une liste vide car aucun destinataire n'a ete trouve.
            return []
        # Prepare une liste vide pour les adresses a notifier.
        emails = []
        # Parcourt uniquement les utilisateurs actifs du groupe.
        for user in group.users.filtered(lambda u: u.active):
            # Recupere l'adresse disponible pour l'utilisateur courant.
            email = self._dss_user_email(user)
            # Garde les adresses renseignees sans ajouter de doublon.
            if email and email not in emails:
                # Ajoute l'adresse a la liste des destinataires.
                emails.append(email)
        # Renvoie toutes les adresses valides trouvees dans le groupe.
        return emails

    def _dss_requester_emails(self):
        """Retourne l'adresse du signataire, ou celle du createur de la DSS."""
        # Cette methode ne traite qu'une seule demande a la fois.
        self.ensure_one()
        # Utilise le signataire de soumission lorsqu'il est renseigne.
        user = self.signataire_demandeur_id
        # Teste si le signataire est absent ou non renseigne.
        if not user:
            # Sinon, prend l'utilisateur qui a cree la demande.
            user = self.create_uid
        # Retourne une liste vide si aucune adresse n'est disponible.
        email = self._dss_user_email(user) if user else ""
        # Le routeur d'e-mails attend une liste, meme pour un seul demandeur.
        return [email] if email else []

    def _dss_workflow_url(self):
        """Construit le lien web direct vers la demande DSS."""
        # S'assure que le lien sera construit pour une seule demande.
        self.ensure_one()
        # Lit l'URL de base dans la configuration Odoo avec les droits admin.
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        # Sans URL de base, il est impossible de construire un lien complet.
        if not base_url:
            return ""
        # Assemble l'URL avec le modele et l'identifiant de cette demande.
        return "%s/web#id=%s&view_type=form&model=dss.request" % (
            # Retire le slash final pour eviter un double slash dans le lien.
            base_url.rstrip("/"),
            # Insere l'identifiant de la demande dans l'URL.
            self.id,
        )

    def _dss_notify_once(self, event_key, action_label, recipient_emails, motif=""):
        """Met un e-mail en file apres une transition metier reussie.

        L'envoi reel sera effectue ensuite par la file de courriels Odoo.
        """
        # S'assure que le traitement concerne une seule demande DSS.
        self.ensure_one()
        # Prepare les adresses en retirant les espaces et les doublons.
        emails = []
        # Traite chaque adresse fournie par la regle de destinataires.
        for email in recipient_emails:
            # Si la valeur est vide, utilise une chaine vide avant strip().
            email = (email or "").strip()
            # Ignore les valeurs vides et les adresses deja ajoutees.
            if email and email not in emails:
                # Ajoute l'adresse nettoyee a la liste finale.
                emails.append(email)
        # N'enregistre rien si aucun destinataire n'a d'adresse valide.
        if not emails:
            # Ecrit un avertissement utile au diagnostic dans le journal Odoo.
            _logger.warning(
                # Indique l'evenement, la demande et la cause de l'abandon.
                "DSS notification %s skipped for %s: no recipient email.",
                # Remplace le premier %s par la cle de l'evenement.
                event_key,
                # Remplace le second %s par le numero de la demande.
                self.name,
            )
            # Signale que le courriel n'a pas ete cree.
            return False

        # Utilise le journal technique avec les droits administrateur.
        Log = self.env["dss.notification.log"].sudo()
        try:
            # Isole les erreurs de notification sans annuler la transition DSS.
            with self.env.cr.savepoint():
                # Verifie si cet evenement a deja ete traite pour cette demande.
                existing = Log.search(
                    # Cherche une ligne correspondant a la demande et a l'evenement.
                    [("request_id", "=", self.id), ("event_key", "=", event_key)],
                    # Arrete la recherche au premier resultat trouve.
                    limit=1,
                )
                # Une ligne trouvee signifie que l'evenement a deja ete notifie.
                if existing:
                    # Evite de creer un second courriel pour le meme evenement.
                    return False

                # Recupere le modele d'e-mail configure dans les donnees XML.
                template = self.env.ref(
                    # Utilise l'identifiant externe declare dans ce fichier.
                    self._dss_template_xmlid,
                    raise_if_not_found=False,
                )
                # Le modele peut etre absent si les donnees XML ne sont pas chargees.
                if not template:
                    # Signale la configuration manquante sans bloquer le workflow.
                    _logger.error(
                        "Missing DSS email template %s", self._dss_template_xmlid
                    )
                    # Interrompt la notification sans creer de courriel.
                    return False

                # Fournit au modele les informations propres a cette notification.
                values = template.with_context(
                    # Passe le nom de l'action affiche dans le sujet et le corps.
                    dss_action_label=action_label,
                    # Passe la cle technique utilisee pour afficher ou non le motif.
                    dss_event_key=event_key,
                    # Passe le motif, ou une chaine vide s'il n'y en a pas.
                    dss_motif=motif or "",
                    # Passe l'etat courant de la demande au modele.
                    dss_status=self.state,
                    # Passe le lien direct vers la demande au modele.
                    dss_workflow_url=self._dss_workflow_url(),
                ).generate_email(
                    # Demande le rendu du modele pour l'enregistrement courant.
                    self.id,
                    fields=[
                        # Recupere le sujet rendu de l'e-mail.
                        "subject",
                        # Recupere le corps HTML rendu de l'e-mail.
                        "body_html",
                        # Recupere l'adresse d'expedition configuree.
                        "email_from",
                        # Recupere l'adresse de reponse configuree.
                        "reply_to",
                        # Recupere le choix de conservation apres l'envoi.
                        "auto_delete",
                    ],
                )
                # Definit les adresses de destination de l'e-mail.
                # join() assemble les adresses avec une virgule entre elles.
                values["email_to"] = ",".join(emails)
                # Detache le message de l'e-mail du modele de demande DSS.
                # False signifie qu'aucun modele metier ne sera associe au mail.
                values["model"] = False
                # Evite ainsi d'afficher le contenu du modele dans le chatter DSS.
                # Sans identifiant de demande, le mail n'est pas rattache a sa fiche.
                values["res_id"] = False
                # Conserve l'e-mail apres son envoi pour le suivi technique.
                values["auto_delete"] = False
                # Cree l'e-mail en file sans lancer son envoi immediat.
                mail = self.env["mail.mail"].sudo().create(values)
                # Enregistre l'evenement et le lien vers la demande pour audit.
                Log.create(
                    {
                        # Relie le journal a la demande d'origine.
                        "request_id": self.id,
                        # Stocke la cle qui empechera un doublon ulterieur.
                        "event_key": event_key,
                        # Relie le journal au courriel mis en file.
                        "mail_id": mail.id,
                        # Conserve les destinataires sous forme de texte.
                        "recipient_emails": ",".join(emails),
                    }
                )
                # Signale que le courriel et son journal ont ete crees.
                return True
        except Exception:
            # Journalise l'erreur sans bloquer le traitement principal de la DSS.
            _logger.exception(
                # Ajoute l'evenement et le numero DSS au detail de l'erreur.
                "Could not queue DSS notification %s for %s.",
                event_key,
                self.name,
            )
            # Signale l'echec de notification au code appelant.
            return False

    def _dss_notify_workflow(self, event_key, action_label, recipient_emails, motif=""):
        """Ajoute le contexte du workflow puis prepare l'e-mail correspondant."""
        # S'assure que l'appel porte sur une seule demande DSS.
        self.ensure_one()
        # Rend disponibles les informations utilisees par le modele d'e-mail.
        self.with_context(
            # Ajoute l'intitule de l'action au contexte Odoo.
            dss_action_label=action_label,
            # Ajoute le motif au contexte, ou une chaine vide.
            dss_motif=motif or "",
            # Ajoute le statut au contexte pour l'affichage dans le courriel.
            dss_status=self.state,
            # Ajoute le lien web de la demande au contexte.
            dss_workflow_url=self._dss_workflow_url(),
            # Appelle la methode qui verifie les doublons et cree le courriel.
        )._dss_notify_once(event_key, action_label, recipient_emails, motif)

    @api.multi
    def _dss_notify_submission(self):
        # Permet de traiter une ou plusieurs demandes dans un meme appel.
        for rec in self:
            # A la soumission, notifie les utilisateurs du groupe Chef.
            rec._dss_notify_workflow(
                # Utilise une cle stable pour reperer une notification de soumission.
                "submission",
                # Libelle transmis au sujet et au corps du courriel.
                "Soumission",
                # Recupere les adresses des utilisateurs du groupe Chef.
                rec._dss_group_emails("dss_v2.group_dss_chef"),
            )

    @api.multi
    def _dss_notify_chef_validation(self):
        # Parcourt chaque demande du recordset Odoo.
        for rec in self:
            # A la validation du Chef, notifie le Magasin et le demandeur.
            rec._dss_notify_workflow(
                # Identifie cet evenement pour eviter les doublons.
                "chef_validation",
                # Fournit un libelle lisible dans le message.
                "Validation Chef",
                # Combine les adresses du Magasin avec celle du demandeur.
                rec._dss_group_emails("dss_v2.group_dss_magasin")
                + rec._dss_requester_emails(),
            )

    @api.multi
    def _dss_notify_rejection(self, previous_state):
        # Traite chaque demande rejetee du recordset.
        for rec in self:
            # Choisit les destinataires selon l'etape ou le rejet a eu lieu.
            if previous_state == "valide_chef":
                # Cree une cle distincte pour un rejet fait par le Chef.
                event_key = "chef_rejection"
                # Le demandeur est le destinataire de ce rejet.
                recipients = rec._dss_requester_emails()
                # Indique dans l'e-mail que le rejet vient du Chef.
                label = "Rejet par le Chef"
            elif previous_state == "valide_magasin":
                # Cree une cle distincte pour un rejet fait par le Magasin.
                event_key = "stock_rejection"
                # Notifie le demandeur et les utilisateurs du groupe Chef.
                recipients = rec._dss_requester_emails() + rec._dss_group_emails(
                    "dss_v2.group_dss_chef"
                )
                # Indique dans l'e-mail que le rejet vient du Stock.
                label = "Rejet par le Stock"
            else:
                # Ignore les rejets hors des deux etapes prevues par le workflow.
                _logger.warning(
                    # Consigne l'etat sans regle de notification pour diagnostic.
                    "No DSS rejection notification mapping for state %s on %s.",
                    previous_state,
                    rec.name,
                )
                # Passe a la prochaine demande sans envoyer cet e-mail.
                continue
            # Envoie le motif de rejet au modele et cree la notification.
            rec._dss_notify_workflow(event_key, label, recipients, rec.motif_rejet)

    @api.multi
    def _dss_notify_stock_approval(self):
        # Parcourt chaque demande dont l'approbation Stock vient d'aboutir.
        for rec in self:
            # Notifie le demandeur apres la validation finale du Stock.
            # Aucun e-mail Securite n'est prevu dans le workflow DSS actuel.
            rec._dss_notify_workflow(
                # Identifie l'evenement d'approbation Stock.
                "stock_approval",
                # Libelle affiche dans l'e-mail.
                "Approbation Stock",
                # L'approbation Stock est communiquee au demandeur.
                rec._dss_requester_emails(),
            )

    @api.multi
    def _dss_notify_return_to_requester(self):
        # Parcourt chaque demande renvoyee au demandeur.
        for rec in self:
            # Au renvoi, adresse la notification au demandeur de la DSS.
            rec._dss_notify_workflow(
                # Identifie l'evenement de retour pour eviter les doublons.
                "return_to_requester",
                # Libelle affiche dans l'e-mail.
                "Renvoi au demandeur",
                # Recupere l'adresse du signataire ou, a defaut, du createur.
                rec._dss_requester_emails(),
                # Reprend dans l'e-mail le motif conserve apres le rejet.
                rec.motif_rejet,
            )

    @api.multi
    def _dss_notify_closure(self):
        # Parcourt chaque demande qui vient d'etre cloturee.
        for rec in self:
            # A la cloture, notifie le demandeur et le groupe Magasin.
            rec._dss_notify_workflow(
                # Identifie l'evenement de cloture pour eviter les doublons.
                "closure",
                # Libelle affiche dans l'e-mail.
                "Cloture",
                # Combine le demandeur et les utilisateurs du groupe Magasin.
                rec._dss_requester_emails()
                + rec._dss_group_emails("dss_v2.group_dss_magasin"),
            )
