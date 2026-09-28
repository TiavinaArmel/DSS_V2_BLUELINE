# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DssRequestLineDisplay(models.Model):
    """Heritage additif uniquement : ajoute un indicateur de role
    pour restreindre l'edition de Qte Sortie au Responsable Stock."""
    _inherit = 'dss.request.line'

    is_magasin_user = fields.Boolean(
        string='Utilisateur Magasin',
        compute='_compute_is_magasin_user',
        store=False,
    )

    @api.multi
    def _compute_is_magasin_user(self):
        is_magasin = self.env.user.has_group('dss_v2.group_dss_magasin')
        for rec in self:
            rec.is_magasin_user = is_magasin