# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DssQtySortieWizard(models.TransientModel):
    _name = 'dss.qty.sortie.wizard'
    _description = 'Assistant de saisie des quantites'

    request_id = fields.Many2one(
        'dss.request', string='Demande DSS', required=True, readonly=True)
    line_ids = fields.One2many(
        'dss.qty.sortie.wizard.line', 'wizard_id', string='Articles')

    @api.model
    def default_get(self, fields_list):
        res = super(DssQtySortieWizard, self).default_get(fields_list)
        request_id = self.env.context.get('default_request_id') or self.env.context.get('active_id')
        if request_id:
            request = self.env['dss.request'].browse(request_id)
            lines = []
            for line in request.line_ids:
                lines.append((0, 0, {
                    'request_line_id': line.id,
                    'product_id': line.product_id.id,
                    'qty_demandee': line.qty_demandee,
                    'qty_sortie': line.qty_sortie,
                    'qty_retour': line.qty_retour,
                }))
            res['request_id'] = request_id
            res['line_ids'] = lines
        return res

    @api.multi
    def action_valider(self):
        self.ensure_one()
        changements = []
        for line in self.line_ids:
            parties = []
            ancienne_sortie = line.request_line_id.qty_sortie
            nouvelle_sortie = line.qty_sortie
            if ancienne_sortie != nouvelle_sortie:
                parties.append(
                    u'Qte Sortie %s \u2192 %s' % (ancienne_sortie, nouvelle_sortie)
                )

            ancienne_retour = line.request_line_id.qty_retour
            nouvelle_retour = line.qty_retour
            if ancienne_retour != nouvelle_retour:
                parties.append(
                    u'Qte Retour %s \u2192 %s' % (ancienne_retour, nouvelle_retour)
                )

            if parties:
                changements.append(
                    u'\u2022 %s : %s' % (
                        line.product_id.name,
                        u', '.join(parties),
                    )
                )
                line.request_line_id.write({
                    'qty_sortie': nouvelle_sortie,
                    'qty_retour': nouvelle_retour,
                })

        if changements:
            message = u'Le Responsable Stock %s a modifi\u00e9 les quantit\u00e9s.<br/><br/>%s' % (
                self.env.user.name,
                '<br/>'.join(changements),
            )
            self.request_id.message_post(body=message)

        return {'type': 'ir.actions.act_window_close'}


class DssQtySortieWizardLine(models.TransientModel):
    _name = 'dss.qty.sortie.wizard.line'
    _description = 'Ligne de assistant de saisie des quantites'

    wizard_id = fields.Many2one(
        'dss.qty.sortie.wizard', string='Assistant', ondelete='cascade')
    request_line_id = fields.Many2one(
        'dss.request.line', string='Ligne DSS', readonly=True, required=True)
    product_id = fields.Many2one(
        'product.product', string='Article', readonly=True)
    qty_demandee = fields.Float(string='Qte Demandee', readonly=True)
    qty_sortie = fields.Float(string='Qte Sortie')
    qty_retour = fields.Float(string='Qte Retour')