# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    dss_number = fields.Char(string="Numero DSS", copy=False, readonly=True)
    dss_justification = fields.Text(string="Justification d'ecart")
    dss_movement_type = fields.Selection([
        ('sortie', 'Sortie'),
        ('entree', 'Entree'),
        ('transfert', 'Transfert'),
    ], string="Type de mouvement DSS")
    dss_validation_state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('demandeur', 'Demandeur'),
        ('valide_chef', 'Validation Chef'),
        ('valide_magasin', 'Validation Stock'),
        ('valide_securite', 'Validation Demandeur'),
        ('approuve', 'Approuve'),
    ], string="Statut DSS", default='brouillon')

    @api.model
    def create(self, vals):
        if not vals.get('dss_number'):
            vals['dss_number'] = self.env['ir.sequence'].next_by_code('dss.number') or '/'
        return super(StockPicking, self).create(vals)

    def check_dss_ecart(self):
        for picking in self:
            for move in picking.move_lines:
                standard_qty = move.product_id.dss_standard_qty
                if standard_qty and abs(move.product_uom_qty - standard_qty) > 0.001:
                    if not picking.dss_justification:
                        raise ValidationError(
                            "ECART DETECTE sur '%s' : standard=%s, demande=%s.\n"
                            "Le champ Justification d ecart est obligatoire." % (
                                move.product_id.name,
                                standard_qty,
                                move.product_uom_qty,
                            )
                        )

    @api.multi
    def action_soumettre_dss(self):
        for picking in self:
            picking.dss_validation_state = 'soumis'

    @api.multi
    def action_valider_chef(self):
        for picking in self:
            if picking.dss_validation_state != 'soumis':
                raise ValidationError("La demande doit etre soumise avant validation du Chef.")
            picking.dss_validation_state = 'valide_chef'

    @api.multi
    def action_valider_magasin(self):
        for picking in self:
            if picking.dss_validation_state != 'valide_chef':
                raise ValidationError("La demande doit etre validee par le Chef avant le Magasin.")
            picking.dss_validation_state = 'valide_magasin'

    @api.multi
    def action_valider_securite(self):
        for picking in self:
            if picking.dss_validation_state != 'valide_magasin':
                raise ValidationError("La demande doit etre validee par le Magasin avant la Securite.")
            picking.dss_validation_state = 'valide_securite'

    @api.multi
    def action_approuver(self):
        for picking in self:
            if picking.dss_validation_state != 'valide_securite':
                raise ValidationError("La demande doit etre validee par la Securite avant approbation.")
            picking.dss_validation_state = 'approuve'


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    @api.multi
    def process(self):
        self.pick_id.check_dss_ecart()
        return super(StockImmediateTransfer, self).process()