# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DssRequestLineDisplay(models.Model):
    # Héritage ADDITIF de dss.request.line.
    # On ne crée pas un nouveau modèle : on étend l'existant
    # en lui ajoutant un champ calculé non stocké.
    #
    # Objectif : exposer un indicateur is_magasin_user dans les vues
    # pour restreindre l'édition de qty_sortie au Responsable Stock.
    _inherit = 'dss.request.line'
    # ⚠️ Pas de _name : c'est un héritage additif.

    # Indicateur calculé : True si l'utilisateur connecté
    # appartient au groupe DSS / Magasin.
    # store=False : non stocké en base (dépend de l'utilisateur connecté).
    is_magasin_user = fields.Boolean(
        string='Utilisateur Magasin',
        compute='_compute_is_magasin_user',
        store=False,
    )

    @api.multi
    def _compute_is_magasin_user(self):
        # Calcul unique : has_group ne dépend pas de rec.
        is_magasin = self.env.user.has_group('dss_v2.group_dss_magasin')
        for rec in self:
            rec.is_magasin_user = is_magasin