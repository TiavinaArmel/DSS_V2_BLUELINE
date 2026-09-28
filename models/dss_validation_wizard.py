# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DssValidationChefWizard(models.TransientModel):
    _name = 'dss.validation.chef.wizard'
    _description = 'Wizard de confirmation Validation Chef'

    request_id = fields.Many2one('dss.request', string='Demande DSS', required=True)

    @api.multi
    def action_confirmer(self):
        self.ensure_one()
        self.request_id.action_valider_chef()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_annuler(self):
        return {'type': 'ir.actions.act_window_close'}


class DssValidationStockWizard(models.TransientModel):
    _name = 'dss.validation.stock.wizard'
    _description = 'Wizard de confirmation Validation Stock'

    request_id = fields.Many2one('dss.request', string='Demande DSS', required=True)

    @api.multi
    def action_confirmer(self):
        self.ensure_one()
        self.request_id.action_valider_magasin()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_annuler(self):
        return {'type': 'ir.actions.act_window_close'}


class DssValidationApprouverWizard(models.TransientModel):
    _name = 'dss.validation.approuver.wizard'
    _description = 'Wizard de confirmation Approbation'

    request_id = fields.Many2one('dss.request', string='Demande DSS', required=True)

    @api.multi
    def action_confirmer(self):
        self.ensure_one()
        self.request_id.action_approuver()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_annuler(self):
        return {'type': 'ir.actions.act_window_close'}