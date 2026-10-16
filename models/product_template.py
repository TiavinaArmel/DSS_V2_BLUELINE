# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplate(models.Model):
    """Étend la fiche modèle d'article avec une quantité standard propre à DSS."""

    _inherit = 'product.template'

    # Sert de valeur de référence aux contrôles d'écart des mouvements de stock DSS.
    dss_standard_qty = fields.Float(string="Quantite standard DSS", default=0.0)