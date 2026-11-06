# -*- coding: utf-8 -*-

from odoo import fields, models


class DssService(models.Model):
    """Service de référence utilisé par le workflow DSS."""

    _name = "dss.service"
    _description = "Service DSS"
    _order = "name, id"

    name = fields.Char(
        string="Nom du service",
        required=True,
    )
    dss_chef_id = fields.Many2one(
        "res.users",
        string="Chef DSS",
    )
    dss_demandeurs_ids = fields.Many2many(
        "res.users",
        "dss_service_demandeur_rel",
        "service_id",
        "user_id",
        string="Demandeurs autorisés",
    )
    active = fields.Boolean(
        string="Actif",
        default=True,
    )
