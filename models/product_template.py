# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    dss_standard_qty = fields.Float(string="Quantite standard DSS", default=0.0)