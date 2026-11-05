# -*- coding: utf-8 -*-

from odoo import api, fields, models


class DssRequest(models.Model):
    _name = "dss.request"
    _description = "Demande de Sortie de Stock"
    _inherit = "mail.thread"

    name = fields.Char(
        string="Numero DSS",
        copy=False,
        readonly=True,
        default="/",
    )
    state = fields.Selection(
        [
            ("brouillon", "Brouillon"),
            ("valide_chef", "Validation Chef"),
            ("valide_magasin", "Validation Stock"),
            ("approuve", "Approuve"),
            ("cloture", "Cloture"),
            ("rejete", "Rejete"),
        ],
        string="Statut",
        default="brouillon",
    )
    bci = fields.Char(string="BCI")
    partner_id = fields.Many2one("res.partner", string="Client")
    lieu_intervention = fields.Char(string="Lieu d intervention")
    date_intervention = fields.Date(
        string="Date d intervention",
        default=fields.Date.today,
    )
    location_id = fields.Many2one(
        "stock.location",
        string="Emplacement",
        domain=[("usage", "=", "internal")],
    )
    location_dest_id = fields.Many2one(
        "stock.location",
        string="Emplacement destination",
        domain=[("usage", "=", "internal")],
    )
    type_intervention = fields.Selection(
        [
            ("nouvelle_installation", "Nouvelle installation client"),
            ("basculement", "Basculement client"),
            ("depannage", "Depannage"),
            ("appro_distant", "Approvisionnement de stock distant"),
            ("installation_interne", "Installation interne (relais, infrastructure)"),
            ("retour_materiel", "Retour de materiel (desinstallation)"),
        ],
        string="Type d intervention",
    )
    sens_mouvement = fields.Char(
        string="Sens du mouvement",
        compute="_compute_sens_mouvement",
        store=True,
        readonly=True,
    )
    picking_id = fields.Many2one(
        "stock.picking",
        string="Mouvement de stock Odoo",
        readonly=True,
    )
    has_ecart = fields.Boolean(string="Ecart detecte", readonly=True)
    is_qty_modified = fields.Boolean(
        string="Quantites modifiees",
        default=False,
        readonly=True,
        copy=False,
    )
    motif_rejet = fields.Text(string="Motif de rejet")
    line_ids = fields.One2many(
        "dss.request.line",
        "request_id",
        string="Lignes",
    )
    signataire_demandeur_id = fields.Many2one(
        "res.users",
        string="Soumis par",
        readonly=True,
        copy=False,
    )
    date_soumission = fields.Datetime(
        string="Date de soumission",
        readonly=True,
        copy=False,
    )
    signataire_chef_id = fields.Many2one(
        "res.users",
        string="Valide par Chef",
        readonly=True,
    )
    date_validation_chef = fields.Datetime(
        string="Date validation Chef",
        readonly=True,
    )
    signataire_magasin_id = fields.Many2one(
        "res.users",
        string="Valide par Stock",
        readonly=True,
    )
    date_validation_magasin = fields.Datetime(
        string="Date validation Stock",
        readonly=True,
    )

    @api.depends("type_intervention")
    def _compute_sens_mouvement(self):
        mapping = {
            "nouvelle_installation": "Sortie",
            "basculement": "Sortie + Entree",
            "depannage": "Sortie + Entree",
            "appro_distant": "Transfert",
            "installation_interne": "Sortie",
            "retour_materiel": "Entree",
        }
        for rec in self:
            rec.sens_mouvement = mapping.get(rec.type_intervention, "")

    @api.onchange("type_intervention")
    def _onchange_type_intervention_lines(self):
        for line in self.line_ids:
            line.qty_demandee_readonly = (
                self.type_intervention == "retour_materiel"
            )

    @api.onchange("location_id")
    def _onchange_location_id_qty_standard(self):
        for line in self.line_ids:
            line._compute_qty_standard()

    @api.model
    def create(self, vals):
        if vals.get("name", "/") == "/":
            vals["name"] = (
                self.env["ir.sequence"].next_by_code("dss.request") or "/"
            )
        return super(DssRequest, self).create(vals)
