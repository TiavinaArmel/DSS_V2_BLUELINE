# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DssRequestWorkflow(models.Model):
    _inherit = "dss.request"

    def _detail_articles_html(self):
        """Génère un résumé HTML des articles de la demande."""
        self.ensure_one()
        lignes_detail = []
        for line in self.line_ids:
            parties = []
            if line.qty_demandee:
                parties.append("Qte Demandee %s" % line.qty_demandee)
            if line.qty_sortie:
                parties.append("Qte Sortie %s" % line.qty_sortie)
            if line.qty_installee:
                parties.append("Qte Installee %s" % line.qty_installee)
            if line.qty_retour:
                parties.append("Qte Retour %s" % line.qty_retour)
            if not parties:
                parties.append("Qte Demandee %s" % line.qty_demandee)
            lignes_detail.append("%s : %s" % (line.product_id.name, ", ".join(parties)))
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
        for rec in self:
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
            rec.date_soumission = fields.Datetime.now()
            rec.state = "valide_chef"
            detail = rec._detail_articles_html()
            rec.message_post(
                body="<b>%s</b> a soumis la demande.<br/>%s"
                % (self.env.user.name, detail)
            )

    @api.multi
    def action_valider_chef(self):
        for rec in self:
            if rec.state != "valide_chef":
                raise ValidationError("La demande doit etre en Validation Chef.")
            rec.state = "valide_magasin"
            rec.signataire_chef_id = self.env.user
            rec.date_validation_chef = fields.Datetime.now()
            rec.message_post(
                body="<b>%s</b> a valide la demande en tant que <b>Responsable Chef</b>."
                % self.env.user.name
            )

    @api.multi
    def action_valider_magasin(self):
        for rec in self:
            if rec.state != "valide_magasin":
                raise ValidationError("La demande doit etre en Validation Stock.")

            rec.signataire_magasin_id = self.env.user
            rec.date_validation_magasin = fields.Datetime.now()
            if rec.sens_mouvement == "Sortie":
                rec._generer_mouvement_sortie()
            elif rec.sens_mouvement == "Entree":
                rec._generer_mouvement_entree()
            elif rec.sens_mouvement == "Sortie + Entree":
                rec._generer_mouvement_sortie()
                rec._generer_mouvement_entree()
            elif rec.sens_mouvement == "Transfert":
                rec._generer_mouvement_transfert()

            rec.message_post(
                body="<b>%s</b> a valide la demande en tant que <b>Responsable Stock</b>."
                % self.env.user.name
            )
            rec.state = "approuve"
            rec._generer_bon_livraison()
            rec.message_post(
                body="<b>%s</b> a approuve definitivement la demande."
                % self.env.user.name
            )

    @api.multi
    def action_approuver(self):
        for rec in self:
            if rec.state != "valide_magasin":
                raise ValidationError(
                    "La demande doit etre validee par le Stock avant approbation."
                )
            rec.state = "approuve"
            rec.message_post(
                body="<b>%s</b> a approuve definitivement la demande."
                % self.env.user.name
            )

    @api.multi
    def action_rejeter(self):
        for rec in self:
            rec.state = "rejete"
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
        self.ensure_one()
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
        for rec in self:
            rec.state = "brouillon"
            rec.message_post(
                body="<b>%s</b> a renvoye la demande au demandeur." % self.env.user.name
            )

    @api.multi
    def action_open_modifier_qte_sortie(self):
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