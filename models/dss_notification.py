# -*- coding: utf-8 -*-

# Importe le module standard qui ecrit des informations dans les journaux Odoo.
import logging
# timedelta sert a calculer une date limite « maintenant moins N jours ».
from datetime import timedelta
from xml.sax.saxutils import escape as html_escape

# Importe les outils Odoo pour les modeles, les champs et les API.
from odoo import api, fields, models

# Cree un journal Python nomme pour ce fichier.
_logger = logging.getLogger(__name__)

# Hotes qui designent la machine du destinataire, jamais le serveur Odoo.
# Une adresse privee du reseau interne (192.168.x, 10.x, 172.16.x) reste valide.
_DSS_LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1", "0.0.0.0")

# Duree de conservation des courriels de notification, en jours.
# Le journal dss.notification.log est conserve : seule la copie du message
# est supprimee. 60 jours laissent une fenetre de controle suffisante.
_DSS_MAIL_RETENTION_DAYS = 60


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
        """Retourne l'adresse du propriétaire de la demande DSS."""
        # Cette methode ne traite qu'une seule demande a la fois.
        self.ensure_one()
        user = self.demandeur_id
        # Retourne une liste vide si aucune adresse n'est disponible.
        email = self._dss_user_email(user) if user else ""
        # Le routeur d'e-mails attend une liste, meme pour un seul demandeur.
        return [email] if email else []

    @staticmethod
    def _dss_url_hostname(url):
        """Extrait le nom d'hote d'une URL sans dependre d'urlparse.

        `urlparse` n'existe que sous ce nom en Python 2; un import conditionnel
        pour Python 3 declenche un faux positif dans les analyseurs statiques.
        Le decoupage manuel suffit pour une URL de configuration Odoo.
        """
        if not url:
            return ""
        host = url.strip()
        # Retire le schema (http://, https://).
        if "://" in host:
            host = host.split("://", 1)[1]
        # Retire l'eventuel couple utilisateur:motdepasse@.
        if "@" in host:
            host = host.split("@", 1)[1]
        # Retire le chemin, les parametres et le fragment.
        for separator in ("/", "?", "#"):
            if separator in host:
                host = host.split(separator, 1)[0]
        # Retire le port. Une adresse IPv6 entre crochets garde ses deux-points.
        if host.startswith("["):
            host = host.split("]", 1)[0].lstrip("[")
        elif ":" in host:
            host = host.split(":", 1)[0]
        return host.strip().lower()

    def _dss_base_url(self):
        """Retourne l'adresse du serveur utilisable dans un courriel.

        Une URL de bouclage designe la machine du destinataire, pas le serveur
        Odoo : le logo et le bouton seraient casses chez tous les destinataires.
        Dans ce cas la methode retourne une chaine vide et le modele affiche le
        nom de la societe au lieu d'une image cassee. Une adresse privee du
        reseau interne reste acceptee, car elle est joignable des destinataires
        internes.
        """
        self.ensure_one()
        # Lit l'URL de base dans la configuration Odoo avec les droits admin.
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        # Sans URL de base, aucun lien complet n'est constructible.
        if not base_url:
            return ""
        # Extrait le nom d'hote pour detecter une adresse de bouclage.
        hostname = self._dss_url_hostname(base_url)
        if not hostname or hostname in _DSS_LOOPBACK_HOSTS:
            _logger.warning(
                "DSS courriel : liens desactives car web.base.url vaut %s. "
                "Configurez l'adresse joignable du serveur Odoo.",
                base_url,
            )
            return ""
        # Retire le slash final pour eviter un double slash dans le lien.
        return base_url.rstrip("/")

    def _dss_workflow_url(self):
        """Construit le lien web direct vers la demande DSS."""
        # S'assure que le lien sera construit pour une seule demande.
        self.ensure_one()
        base_url = self._dss_base_url()
        # Sans adresse joignable, le bouton est omis du courriel.
        if not base_url:
            return ""
        # Selectionne la base de cette demande avant d'ouvrir la fiche dans le web client.
        return "%s/web?db=%s#id=%s&view_type=form&model=dss.request" % (
            base_url,
            # Evite que le navigateur ouvre une autre base Odoo sur le meme serveur.
            self.env.cr.dbname,
            # Insere l'identifiant de la demande dans l'URL.
            self.id,
        )

    def _dss_company_logo_url(self):
        """Construit l'URL publique du logo de la société Odoo courante."""
        # S'assure que le logo correspond au contexte d'une seule demande.
        self.ensure_one()
        base_url = self._dss_base_url()
        # Sans adresse joignable, le modele affiche le nom de la societe.
        if not base_url:
            return ""
        # Utilise la société active et la base courante dans l'URL du logo Odoo.
        return "%s/web/binary/company_logo?db=%s&company=%s" % (
            base_url,
            self.env.cr.dbname,
            self.env.user.company_id.id,
        )

    def _dss_selection_label(self, field_name, value):
        """Retourne le libelle lisible d'une valeur de selection du modele."""
        if not value:
            return ""
        # fields_get() expose les choix declares sur le modele.
        definition = self.fields_get([field_name]).get(field_name) or {}
        # selection est une liste de couples (valeur technique, libelle).
        labels = dict(definition.get("selection") or [])
        return labels.get(value) or value

    def _dss_company(self):
        """Retourne la société de l'utilisateur qui déclenche la notification."""
        return self.env.user.company_id

    def _dss_notify_once(
        self,
        event_key,
        action_label,
        recipient_emails,
        motif="",
        quantity_motifs=None,
    ):
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

                # Societe utilisee pour le pied de page et l'adresse de reponse.
                company = self._dss_company()
                # Fournit au modele les informations propres a cette notification.
                values = template.with_context(
                    # Passe le nom de l'action affiche dans le sujet et le corps.
                    dss_action_label=action_label,
                    # Rend la clé technique disponible au template pour adapter le message.
                    dss_event_key=event_key,
                    # Passe le motif, ou une chaine vide s'il n'y en a pas.
                    # Le motif vient d'une saisie libre : il est echappe avant le HTML.
                    dss_motif=html_escape(motif or ""),
                    # Passe les motifs de quantités sous forme de données structurées.
                    dss_quantity_motifs=quantity_motifs or [],
                    # Passe l'etat courant de la demande au modele.
                    dss_status=self.state,
                    # Passe le libelle lisible de l'etat (Validation Chef, Cloture...).
                    dss_status_label=self._dss_selection_label("state", self.state),
                    # Passe le libelle du type d'intervention pour le sujet.
                    dss_intervention_label=self._dss_selection_label(
                        "type_intervention", self.type_intervention
                    ),
                    # Passe le nom de la societe pour l'en-tete et le pied de page.
                    dss_company_name=company.name or "",
                    # Passe l'adresse de reponse de la societe.
                    dss_reply_to=company.email or "",
                    # Passe le lien direct vers la demande au modele.
                    dss_workflow_url=self._dss_workflow_url(),
                    # Donne au template les détails de la clôture lorsqu'ils existent.
                    dss_closure_type=(
                        self.env.context.get("dss_closure_type")
                        or (
                            "exception"
                            if self.env.context.get("dss_closure_is_exception")
                            else ""
                        )
                    ),
                    dss_closure_actor=html_escape(
                        self.env.context.get('dss_closure_actor', '') or ''
                    ),
                    dss_closure_reason=html_escape(
                        self.env.context.get("dss_closure_reason")
                        or self.env.context.get("dss_closure_motif_exception")
                        or ""
                    ),
                    dss_closure_is_exception=(
                        self.env.context.get("dss_closure_is_exception")
                        or self.env.context.get("dss_closure_type") == "exception"
                    ),
                    dss_closure_returns=(
                        self.env.context.get("dss_closure_returns") or []
                    ),
                    # Passe l'URL du logo construite avec la base URL configurée.
                    dss_logo_url=self._dss_company_logo_url(),
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

    def _dss_notify_workflow(
        self,
        event_key,
        action_label,
        recipient_emails,
        motif="",
        quantity_motifs=None,
    ):
        """Ajoute le contexte du workflow puis prepare l'e-mail correspondant."""
        # S'assure que l'appel porte sur une seule demande DSS.
        self.ensure_one()
        # Rend disponibles les informations utilisees par le modele d'e-mail.
        self.with_context(
            # Ajoute l'intitule de l'action au contexte Odoo.
            dss_action_label=action_label,
            # Conserve aussi la clé technique pour le rendu conditionnel du template.
            dss_event_key=event_key,
            # Ajoute le motif au contexte, ou une chaine vide.
            dss_motif=motif or "",
            # Ajoute le statut au contexte pour l'affichage dans le courriel.
            dss_status=self.state,
            # Ajoute le lien web de la demande au contexte.
            dss_workflow_url=self._dss_workflow_url(),
            # Appelle la methode qui verifie les doublons et cree le courriel.
        )._dss_notify_once(
            event_key,
            action_label,
            recipient_emails,
            motif,
            quantity_motifs,
        )

    @api.multi
    def _dss_notify_submission(self):
        # Permet de traiter une ou plusieurs demandes dans un meme appel.
        for rec in self:
            # A la soumission, notifie le Chef DSS configuré pour le service.
            chef_user = rec.service_demandeur_id.dss_chef_id
            chef_email = rec._dss_user_email(chef_user) if chef_user else ""
            rec._dss_notify_workflow(
                # Utilise une cle stable pour reperer une notification de soumission.
                "submission",
                # Libelle transmis au sujet et au corps du courriel.
                "Soumission",
                # Le routeur journalise et ignore l'envoi si l'adresse est absente.
                [chef_email] if chef_email else [],
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
            motifs_ecart = rec._dss_quantity_change_motifs()
            # Notifie le demandeur apres la validation finale du Stock.
            # Aucun e-mail Securite n'est prevu dans le workflow DSS actuel.
            rec._dss_notify_workflow(
                # Identifie l'evenement d'approbation Stock.
                "stock_approval",
                # Libelle affiche dans l'e-mail.
                "Approbation Stock",
                # Le demandeur et le Chef doivent savoir que la DSS peut être clôturée.
                rec._dss_requester_emails()
                + rec._dss_group_emails("dss_v2.group_dss_chef"),
                # Transmet les motifs des modifications de quantités par article.
                quantity_motifs=motifs_ecart,
            )

    def _dss_quantity_change_motifs(self):
        """Retourne les motifs d'écart renseignés, regroupés par article."""
        self.ensure_one()
        motifs = []
        for line in self.line_ids:
            if line.motif_ecart:
                motif = html_escape(
                    line.motif_ecart,
                    {"\"": "&quot;", "'": "&#x27;"},
                )
                if self.type_intervention == "retour_materiel":
                    details = u"quantité retournée validée %s. Motif : %s" % (
                        line.qty_retour,
                        motif,
                    )
                else:
                    details = u"quantité demandée %s, quantité sortie %s. Motif : %s" % (
                        line.qty_demandee,
                        line.qty_sortie,
                        motif,
                    )
                motifs.append(
                    (
                        html_escape(line.product_id.name or ""),
                        details,
                    )
                )
        return motifs

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
                # Accentue et en Unicode explicite : ce libelle termine le sujet
                # du courriel ("DSS xxx - Clôture"), comme les libelles d'etat.
                u"Clôture",
                # Informe le Chef et le Magasin ; le demandeur reste également informé.
                rec._dss_group_emails("dss_v2.group_dss_chef")
                + rec._dss_group_emails("dss_v2.group_dss_magasin")
                + rec._dss_requester_emails(),
            )

    # ------------------------------------------------------------------
    # PURGE DES COURRIELS (version 2.15)
    # ------------------------------------------------------------------
    @api.model
    def _dss_cron_purge_old_mails(self):
        """Supprime les courriels de notification de plus de 60 jours.

        POURQUOI CETTE PURGE
        Le modele d'e-mail fixe auto_delete = False : chaque notification
        laisse un enregistrement mail.mail complet, corps HTML inclus. C'est
        volontaire (on peut controler ce qui a ete envoye), mais sans limite
        la table mail_mail grossit indefiniment et alourdit les sauvegardes.

        CE QUI EST CONSERVE
        Le journal dss.notification.log n'est PAS supprime : il garde la
        demande concernee, la cle d'evenement, les destinataires et sa date
        de creation. Seul le contenu du courriel disparait. Le lien mail_id
        est vide automatiquement par Odoo (comportement par defaut d'un
        Many2one : ondelete = 'set null'), donc aucune erreur de reference.

        CE QUI EST ECARTE
        Seuls les courriels reellement ENVOYES (state = 'sent') sont purges.
        Un courriel encore en file ('outgoing') ou en erreur ('exception')
        est conserve : il sert au diagnostic.

        APPEL
        Cette methode est declenchee par la tache planifiee
        « DSS - Purge des e-mails de notification (60 jours) », declaree dans
        data/dss_cron.xml. @api.model permet de l'appeler sans enregistrement.
        """
        # Odoo 10 : fields.Datetime.now() renvoie une CHAINE, pas un objet
        # datetime. On la convertit avec from_string() pour pouvoir soustraire
        # une duree, puis on repasse en chaine avec to_string() : le format
        # reste exactement celui attendu par la base.
        now = fields.Datetime.from_string(fields.Datetime.now())
        limit_date = fields.Datetime.to_string(
            now - timedelta(days=_DSS_MAIL_RETENTION_DAYS)
        )

        # Recherche des journaux assez anciens qui pointent encore vers un mail.
        # sudo() est necessaire : le cron s'execute en root, mais le modele
        # dss.notification.log est reserve a l'administrateur systeme.
        logs = self.env["dss.notification.log"].sudo().search(
            [
                # create_date est rempli automatiquement par Odoo.
                ("create_date", "<", limit_date),
                ("mail_id", "!=", False),
            ]
        )
        # mapped() transforme les journaux en liste de courriels sans doublon.
        mails = logs.mapped("mail_id")
        # filtered() ne conserve que les courriels deja envoyes.
        mails = mails.filtered(lambda mail: mail.state == "sent")

        purged = 0
        if mails:
            # unlink() supprime les courriels ; le champ mail_id des journaux
            # est remis a vide par Odoo, les journaux restent intacts.
            purged = len(mails)
            mails.unlink()

        # Trace l'operation dans le journal Odoo pour le suivi technique.
        _logger.info(
            "DSS : purge des courriels de notification de plus de %s jours : "
            "%s courriel(s) supprime(s).",
            _DSS_MAIL_RETENTION_DAYS,
            purged,
        )
        # La valeur retournee apparait dans l'historique de la tache planifiee.
        return purged
