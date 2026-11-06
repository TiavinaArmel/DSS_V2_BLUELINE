# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, models, fields, api
from odoo.exceptions import AccessError, ValidationError


class DssRequestWorkflow(models.Model):
    """Regroupe les actions qui font avancer une demande DSS dans son workflow."""

    _inherit = "dss.request"

    def _detail_articles_html(self):
        """Construit le résumé HTML des quantités de chaque article pour le chatter."""
        # Cette méthode produit un texte unique et doit donc recevoir une seule demande.
        self.ensure_one()
        lignes_detail = []
        # Parcourt les articles liés et construit pour chacun une liste d'informations à afficher.
        for line in self.line_ids:
            parties = []
            # append() ajoute le texte à la fin de la liste sans remplacer les valeurs existantes.
            if line.qty_demandee:
                parties.append("Qte Demandee %s" % line.qty_demandee)
            if line.qty_sortie:
                parties.append("Qte Sortie %s" % line.qty_sortie)
            if line.qty_installee:
                parties.append("Qte Installee %s" % line.qty_installee)
            if line.qty_retour:
                parties.append("Qte Retour %s" % line.qty_retour)
            if not parties:
                # Si aucune quantité n'est renseignée, conserve malgré tout la quantité demandée dans le résumé.
                parties.append("Qte Demandee %s" % line.qty_demandee)
            lignes_detail.append("%s : %s" % (line.product_id.name, ", ".join(parties)))
        # join() assemble les articles avec une balise de saut de ligne HTML comme séparateur.
        return "<br/>".join(lignes_detail)

    @api.multi
    def action_soumettre(self):
        """
        Action déclenchée par le bouton "Soumettre".

        Étapes :
            1. Vérifie les champs obligatoires :
                - bci, partner_id, lieu_intervention, date_intervention,
                  type_intervention, location_id
            2. Vérifie la règle conditionnelle :
                - si type_intervention == "appro_distant", alors
                  location_dest_id est obligatoire
            3. Vérifie qu'au moins une ligne d'article existe (line_ids)
            4. Change le statut en 'valide_chef'
            5. Poste un message dans le chatter avec le résumé HTML
               des articles (_detail_articles_html)

        :raises ValidationError: si un champ obligatoire est manquant
                                 ou si aucun article n'est renseigné.
        """
        # @api.multi autorise l'appel sur plusieurs demandes ; chacune est contrôlée dans cette boucle.
        for rec in self:
            if not rec.service_demandeur_id:
                raise ValidationError(
                    u"Veuillez sélectionner un service demandeur."
                )
            if not rec.service_demandeur_id.dss_demandeurs_ids:
                raise ValidationError(
                    u"Ce service n'a aucun demandeur autorisé configuré. "
                    u"Contactez l'administrateur."
                )
            if self.env.user not in rec.service_demandeur_id.dss_demandeurs_ids:
                raise AccessError(
                    u"Vous n'êtes pas autorisé à effectuer des demandes pour ce service."
                )
            if not rec.service_demandeur_id.dss_chef_id:
                raise ValidationError(
                    u"Le service %s n'a pas de Chef DSS configuré, impossible de soumettre."
                    % rec.service_demandeur_id.name
                )
            if (
                not rec.service_demandeur_id.dss_chef_id.active
                or not rec.service_demandeur_id.dss_chef_id.has_group(
                    "dss_v2.group_dss_chef"
                )
            ):
                raise ValidationError(
                    u"Le Chef DSS du service %s doit être actif et appartenir au groupe DSS / Chef."
                    % rec.service_demandeur_id.name
                )

            # Chaque champ obligatoire est vérifié avant de changer l'état du dossier.
            if not rec.bci:
                raise ValidationError("Le champ BCI est obligatoire avant de soumettre.")
            if not rec.partner_id:
                raise ValidationError("Le champ Client est obligatoire avant de soumettre.")
            if not rec.lieu_intervention:
                raise ValidationError("Le champ Lieu d intervention est obligatoire avant de soumettre.")
            if not rec.date_intervention:
                raise ValidationError("Le champ Date d intervention est obligatoire avant de soumettre.")
            if not rec.type_intervention:
                raise ValidationError("Le champ Type d intervention est obligatoire avant de soumettre.")
            if not rec.location_id:
                raise ValidationError("Le champ Emplacement est obligatoire avant de soumettre.")
            if rec.type_intervention == "appro_distant" and not rec.location_dest_id:
                raise ValidationError("Le champ Emplacement destination est obligatoire pour un Transfert.")
            if not rec.line_ids:
                raise ValidationError("Vous devez ajouter au moins un article avant de soumettre.")
            rec.signataire_demandeur_id = self.env.user
            # Enregistre l'heure serveur Odoo de la soumission.
            rec.date_soumission = fields.Datetime.now()
            rec.state = "valide_chef"
            detail = rec._detail_articles_html()
            # message_post() ajoute au chatter un message dont body peut contenir du HTML.
            rec.message_post(
                body="<b>%s</b> a soumis la demande.<br/>%s"
                % (self.env.user.name, detail)
            )
            rec._dss_notify_submission()

    @api.multi
    def action_valider_chef(self):
        """Enregistre la validation du Chef et transmet le dossier à l'étape Stock."""
        for rec in self:
            # Refuse la transition si l'état actuel ne correspond pas à l'étape attendue.
            if rec.state != "valide_chef":
                raise ValidationError("La demande doit etre en Validation Chef.")
            if not rec.service_demandeur_id:
                raise AccessError(
                    u"Aucun service DSS n'est défini pour cette demande."
                )
            chef_service = rec.service_demandeur_id.dss_chef_id
            if (
                not chef_service
                or not chef_service.active
                or not chef_service.has_group("dss_v2.group_dss_chef")
                or self.env.user != chef_service
            ):
                raise AccessError(
                    u"Seul le Chef DSS actif et assigné à ce service peut valider cette demande."
                )
            # Mémorise le nouvel état, le signataire et la date de validation.
            rec.state = "valide_magasin"
            rec.signataire_chef_id = self.env.user
            rec.date_validation_chef = fields.Datetime.now()
            # Le chatter garde une trace lisible de l'utilisateur ayant validé la demande.
            rec.message_post(
                body="<b>%s</b> a valide la demande en tant que <b>Responsable Chef</b>."
                % self.env.user.name
            )
            rec._dss_notify_chef_validation()

    @api.multi
    def action_valider_magasin(self):
        """Crée les mouvements de stock correspondants puis approuve la demande."""
        for rec in self:
            # Le responsable Stock ne peut agir qu'après la validation du Chef.
            if rec.state != "valide_magasin":
                raise ValidationError("La demande doit etre en Validation Stock.")

            rec.signataire_magasin_id = self.env.user
            rec.date_validation_magasin = fields.Datetime.now()
            # Le sens du mouvement sélectionne le traitement de sortie, entrée ou transfert.
            if rec.sens_mouvement == "Sortie":
                rec._generer_mouvement_sortie()
            elif rec.sens_mouvement == "Entree":
                rec._generer_mouvement_entree()
            elif rec.sens_mouvement == "Sortie + Entree":
                rec._generer_mouvement_sortie()
                rec._generer_mouvement_entree()
            elif rec.sens_mouvement == "Transfert":
                rec._generer_mouvement_transfert()

            # Le premier message identifie la validation effectuée par le magasinier.
            rec.message_post(
                body="<b>%s</b> a valide la demande en tant que <b>Responsable Stock</b>."
                % self.env.user.name
            )
            rec.state = "approuve"
            # Produit le PDF du bon de livraison après la validation du stock.
            rec._generer_bon_livraison()
            # Ajoute une trace distincte de l'approbation finale au chatter.
            rec.message_post(
                body="<b>%s</b> a approuve definitivement la demande."
                % self.env.user.name
            )
            # Notifie les destinataires de l'approbation finale du stock.
            rec._dss_notify_stock_approval()

    @api.multi
    def action_rejeter(self):
        """Rejette la demande et ajoute le motif au chatter s'il a été saisi."""
        for rec in self:
            rec._check_rejet_access()
            previous_state = rec.state
            rec.state = "rejete"
            # Le motif est facultatif ; les deux branches produisent un message adapté.
            if rec.motif_rejet:
                rec.message_post(
                    body="<b>%s</b> a rejete la demande.<br/>Motif : %s"
                    % (self.env.user.name, rec.motif_rejet)
                )
            else:
                rec.message_post(
                    body="<b>%s</b> a rejete la demande." % self.env.user.name
                )
            rec._dss_notify_rejection(previous_state)

    @api.multi
    def _check_rejet_access(self):
        """Vérifie le droit de rejet selon l'étape du workflow."""
        self.ensure_one()
        if self.state == "valide_chef":
            if (
                self.env.uid != SUPERUSER_ID
                and self.env.user != self.service_demandeur_id.dss_chef_id
            ):
                raise AccessError(
                    u"Seul le Chef DSS assigné à ce service peut rejeter cette demande."
                )
        elif self.state == "valide_magasin":
            if (
                self.env.uid != SUPERUSER_ID
                and not self.env.user.has_group("dss_v2.group_dss_magasin")
            ):
                raise AccessError(
                    u"Seul un utilisateur du groupe DSS / Magasin peut rejeter cette demande."
                )
        else:
            raise AccessError(
                u"La demande ne peut pas être rejetée dans cet état."
            )

    @api.multi
    def action_open_wizard_rejeter(self):
        """Ouvre le wizard temporaire utilisé pour saisir le motif de rejet."""
        # Une action fenêtre Odoo doit ici être liée à une seule demande.
        self.ensure_one()
        self._check_rejet_access()
        # Le dictionnaire retourné décrit au client Web le formulaire modal à ouvrir.
        return {
            "type": "ir.actions.act_window",
            "name": "Motif du rejet",
            "res_model": "dss.rejet.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    @api.multi
    def action_renvoyer_demandeur(self):
        """Autorise le Chef à remettre au demandeur une demande précédemment rejetée."""
        # Le contrôle serveur protège aussi les appels qui ne viennent pas du bouton de l'interface.
        if not self.env.user.has_group("dss_v2.group_dss_chef"):
            raise AccessError(
                "Seul un utilisateur du groupe DSS / Chef peut renvoyer une demande."
            )
        for rec in self:
            # Seule une demande rejetée peut revenir au demandeur pour correction.
            if rec.state != "rejete":
                raise ValidationError(
                    "Seule une demande rejetee peut etre renvoyee au demandeur."
                )
            # Le signataire est privilégié ; create_uid sert de repli si aucun signataire n'existe.
            demandeur = rec.signataire_demandeur_id or rec.create_uid
            nom_demandeur = demandeur.name if demandeur else "demandeur"
            # Remet la demande en brouillon avant d'ajouter la trace du renvoi au chatter.
            rec.state = "brouillon"
            rec.message_post(
                body="<b>%s</b> a renvoye la demande au demandeur <b>%s</b>."
                % (self.env.user.name, nom_demandeur)
            )
            rec._dss_notify_return_to_requester()

    @api.multi
    def action_open_modifier_qte_sortie(self):
        """Ouvre le wizard temporaire de modification des quantités de stock."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Modifier Qte",
            "res_model": "dss.qty.sortie.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    @api.multi
    def action_open_wizard_cloture(self):
        """Ouvre le formulaire de clôture lié à la demande courante."""
        self.ensure_one()
        if self.state != "approuve":
            raise AccessError(
                u"Seule une demande approuvée peut être clôturée."
            )
        is_requester = self.env.user == self.signataire_demandeur_id
        is_chef_exception = (
            not is_requester
            and self.env.user.has_group("dss_v2.group_dss_chef")
        )
        if not is_requester and not is_chef_exception:
            raise AccessError(
                u"Seul le demandeur d'origine ou un Chef DSS en clôture exceptionnelle peut clôturer cette demande."
            )
        return {
            "type": "ir.actions.act_window",
            "name": "Cloturer la demande",
            "res_model": "dss.cloture.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_request_id": self.id,
                "default_is_exception": is_chef_exception,
            },
        }

    @api.multi
    def action_open_wizard_chef(self):
        """Ouvre le wizard de confirmation de la validation Chef."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Confirmation de validation",
            "res_model": "dss.validation.chef.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    @api.multi
    def action_open_wizard_stock(self):
        """Ouvre le wizard de confirmation de la validation Stock."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Confirmation de validation",
            "res_model": "dss.validation.stock.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    @api.multi
    def action_open_wizard_approuver(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Confirmation d approbation",
            "res_model": "dss.validation.approuver.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }