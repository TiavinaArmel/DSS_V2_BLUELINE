# -*- coding: utf-8 -*-

from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    dss_demandeurs_ids = fields.Many2many(
        "res.users",
        string="Demandeurs autorisés",
    )
    dss_chef_id = fields.Many2one(
        "res.users",
        string="Chef DSS",
    )
