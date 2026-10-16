# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


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

    @api.multi
    def action_valider_chef(self):
        """Enregistre la validation du Chef et transmet le dossier à l'étape Stock."""
        for rec in self:
            # Refuse la transition si l'état actuel ne correspond pas à l'étape attendue.
            if rec.state != "valide_chef":
                raise ValidationError("La demande doit etre en Validation Chef.")
            # Mémorise le nouvel état, le signataire et la date de validation.
            rec.state = "valide_magasin"
            rec.signataire_chef_id = self.env.user
            rec.date_validation_chef = fields.Datetime.now()
            # Le chatter garde une trace lisible de l'utilisateur ayant validé la demande.
            rec.message_post(
                body="<b>%s</b> a valide la demande en tant que <b>Responsable Chef</b>."
                % self.env.user.name
            )

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

    @api.multi
    def action_approuver(self):
        """Approuve définitivement la demande après le contrôle de l'état attendu."""
        for rec in self:
            if rec.state != "valide_magasin":
                raise ValidationError(
                    "La demande doit etre validee par le Stock avant approbation."
                )
            # Met à jour l'état puis consigne l'approbation dans l'historique du dossier.
            rec.state = "approuve"
            rec.message_post(
                body="<b>%s</b> a approuve definitivement la demande."
                % self.env.user.name
            )

    @api.multi
    def action_rejeter(self):
        """Rejette la demande et ajoute le motif au chatter s'il a été saisi."""
        for rec in self:
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

    @api.multi
    def action_open_wizard_rejeter(self):
        """Ouvre le wizard temporaire utilisé pour saisir le motif de rejet."""
        # Une action fenêtre Odoo doit ici être liée à une seule demande.
        self.ensure_one()
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
        """Remet la demande rejetée en brouillon afin qu'elle puisse être corrigée."""
        for rec in self:
            # Réinitialise l'étape, puis conserve au chatter la trace du renvoi.
            rec.state = "brouillon"
            rec.message_post(
                body="<b>%s</b> a renvoye la demande au demandeur." % self.env.user.name
            )

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
        return {
            "type": "ir.actions.act_window",
            "name": "Cloturer la demande",
            "res_model": "dss.cloture.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
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
        """Ouvre le wizard de confirmation de l'approbation finale."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Confirmation d approbation",
            "res_model": "dss.validation.approuver.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }