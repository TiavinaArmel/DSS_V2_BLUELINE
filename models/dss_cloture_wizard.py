# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DssClotureWizard(models.TransientModel):
    _name = 'dss.cloture.wizard'
    _description = 'Assistant de cloture de la demande DSS'

    request_id = fields.Many2one(
        'dss.request', string='Demande DSS', required=True, readonly=True)
    line_ids = fields.One2many(
        'dss.cloture.wizard.line', 'wizard_id', string='Articles')

    @api.model
    def default_get(self, fields_list):
        res = super(DssClotureWizard, self).default_get(fields_list)
        request_id = self.env.context.get('default_request_id') or self.env.context.get('active_id')
        if request_id:
            request = self.env['dss.request'].browse(request_id)
            lines = []
            for line in request.line_ids:
                lines.append((0, 0, {
                    'request_line_id': line.id,
                    'product_id': line.product_id.id,
                    'qty_sortie': line.qty_sortie,
                    'qty_installee': line.qty_installee,
                    'qty_retour': line.qty_retour,
                }))
            res['request_id'] = request_id
            res['line_ids'] = lines
        return res

    @api.multi
    def action_confirmer(self):
        self.ensure_one()
        ecarts = []
        recap = []
        for line in self.line_ids:
            line.request_line_id.write({
                'qty_installee': line.qty_installee,
                'qty_retour': line.qty_retour,
            })
            recap.append(
                u'\u2022 %s : Qte Installee %s, Qte Retour %s' % (
                    line.product_id.name, line.qty_installee, line.qty_retour)
            )
            if line.qty_installee != line.qty_sortie:
                ecarts.append(
                    u'%s : sorti %s, installe %s' % (
                        line.product_id.name, line.qty_sortie, line.qty_installee)
                )

        self.request_id.has_ecart = bool(ecarts)
        self.request_id.state = 'cloture'

        message = u'<b>%s</b> a cloture la demande.<br/>%s' % (
            self.env.user.name, u'<br/>'.join(recap))
        if ecarts:
            message += u'<br/><br/><b>Ecarts detectes :</b><br/>' + u'<br/>'.join(ecarts)
        self.request_id.message_post(body=message)

        return {'type': 'ir.actions.act_window_close'}


class DssClotureWizardLine(models.TransientModel):
    _name = 'dss.cloture.wizard.line'
    _description = 'Ligne de assistant de cloture'

    wizard_id = fields.Many2one(
        'dss.cloture.wizard', string='Assistant', ondelete='cascade')
    request_line_id = fields.Many2one(
        'dss.request.line', string='Ligne DSS', readonly=True, required=True)
    product_id = fields.Many2one(
        'product.product', string='Article', readonly=True)
    qty_sortie = fields.Float(string='Qte Sortie', readonly=True)
    qty_installee = fields.Float(string='Qte Installee')
    qty_retour = fields.Float(string='Qte Retour')