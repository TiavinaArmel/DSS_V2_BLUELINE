# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import html_escape


class DssRequest(models.Model):
    _name = "dss.request"
    _description = "Demande de Sortie de Stock"
    _inherit = "mail.thread"

    service_demandeur_id = fields.Many2one(
        "dss.service",
        string="Service Demandeur",
        default=lambda model: model._default_service_demandeur(),
    )
    demandeur_id = fields.Many2one(
        "res.users",
        string="Demandeur",
        required=True,
        readonly=True,
        copy=False,
        default=lambda model: model.env.user,
    )
    is_current_user_chef = fields.Boolean(
        compute="_compute_is_current_user_chef",
        store=False,
    )

    # La contrainte SQL protège aussi contre les doublons créés en parallèle.
    _sql_constraints = [
        (
            "dss_request_bci_unique",
            "unique(bci)",
            u"Le BCI doit être unique. Une demande DSS existe déjà avec ce BCI.",
        ),
    ]

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
    # Indique que le magasinier a confirmé le wizard de modification des
    # quantités. Il distingue une valeur zéro volontaire d'une valeur non
    # encore initialisée avant la validation Stock.
    is_qty_modified = fields.Boolean(
        string="Quantites modifiees",
        default=False,
        readonly=True,
        copy=False,
    )
    # champ de texte contenant le motif du rejet de la demande, rempli via
    # le wizard DssRejetWizard tout en bas de ce fichier
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

    @api.model
    def _default_service_demandeur(self):
        """Retourne le service actif de l'utilisateur lorsqu'il en a un."""
        services = self.env["dss.service"].sudo().search(
            [
                ("active", "=", True),
                ("dss_demandeurs_ids", "in", self.env.user.id),
            ],
            order="id",
            limit=1,
        )
        return services.id or False

    @api.depends("service_demandeur_id.dss_chef_id")
    def _compute_is_current_user_chef(self):
        """Indique si l'utilisateur courant dirige le service de la DSS."""
        for rec in self:
            chef_user = (
                rec.service_demandeur_id.dss_chef_id
                if rec.service_demandeur_id
                else False
            )
            rec.is_current_user_chef = bool(
                chef_user
                and chef_user.active
                and chef_user.has_group("dss_v2.group_dss_chef")
                and chef_user == self.env.user
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
        """
        Surcharge de create() pour attribuer automatiquement un numéro
        à chaque nouvelle demande DSS.

        - Si 'name' est vide ou absent (égal à "/"), on récupère le
          prochain numéro de la séquence 'dss.request'.
        - Sinon, la valeur fournie dans vals est conservée telle quelle
          (en pratique, ce cas n'arrive jamais depuis l'interface,
          puisque le champ est readonly dans la vue).
        """
        vals = dict(vals)
        if "bci" in vals:
            vals["bci"] = (vals["bci"] or "").strip() or False

        if self.env.uid == SUPERUSER_ID:
            target_user_id = self.env.context.get("dss_user_id", self.env.uid)
            target_user = (
                self.env["res.users"].sudo().browse(target_user_id).exists()
            )
            if not target_user:
                raise ValidationError(
                    "L'utilisateur cible de la demande DSS est introuvable."
                )
        else:
            target_user = self.env.user

        # Le propriétaire et son service sont déterminés côté serveur.
        vals["demandeur_id"] = target_user.id
        vals["service_demandeur_id"] = (
            self.env["dss.service"].sudo()
            .search(
                [
                    ("active", "=", True),
                    ("dss_demandeurs_ids", "in", target_user.id),
                ],
                order="id",
                limit=1,
            )
            .id
            or False
        )

        if vals.get("name", "/") == "/":
            vals["name"] = (
                self.env["ir.sequence"].next_by_code("dss.request") or "/"
            )
        return super(DssRequest, self).create(vals)

    @api.multi
    def write(self, vals):
        """Réserve le service aux admins et trace les corrections après soumission."""
        vals = dict(vals)
        if "bci" in vals:
            vals["bci"] = (vals["bci"] or "").strip() or False
        is_admin = (
            self.env.uid == SUPERUSER_ID
            or self.env.user.has_group("base.group_system")
        )
        service_changes = []
        requester_changes = []
        if "demandeur_id" in vals:
            if not is_admin:
                raise AccessError(
                    u"Seul un administrateur peut modifier le demandeur de la DSS."
                )
            new_requester = (
                self.env["res.users"]
                .sudo()
                .browse(vals["demandeur_id"])
                .exists()
                if vals["demandeur_id"]
                else self.env["res.users"]
            )
            new_requester_name = new_requester.name if new_requester else u"Aucun"
            for request in self:
                if request.demandeur_id.id != vals["demandeur_id"]:
                    requester_changes.append(
                        (
                            request,
                            request.demandeur_id.name
                            if request.demandeur_id
                            else u"Aucun",
                            new_requester_name,
                        )
                    )

        if "service_demandeur_id" in vals:
            if not is_admin:
                raise AccessError(
                    u"Seul un administrateur peut modifier le service demandeur."
                )

            new_service = (
                self.env["dss.service"]
                .sudo()
                .browse(vals["service_demandeur_id"])
                .exists()
                if vals["service_demandeur_id"]
                else self.env["dss.service"]
            )
            new_service_name = new_service.name if new_service else u"Aucun"
            for request in self:
                if (
                    request.state != "brouillon"
                    and request.service_demandeur_id.id
                    != vals["service_demandeur_id"]
                ):
                    old_service_name = (
                        request.service_demandeur_id.name
                        if request.service_demandeur_id
                        else u"Aucun"
                    )
                    service_changes.append(
                        (request, old_service_name, new_service_name)
                    )

        result = super(DssRequest, self).write(vals)
        for request, old_name, new_name in service_changes:
            request.message_post(
                body=(
                    u"L'administrateur a modifié le service demandeur : "
                    u"%s -> %s."
                    % (html_escape(old_name), html_escape(new_name))
                )
            )
        for request, old_name, new_name in requester_changes:
            request.message_post(
                body=(
                    u"L'administrateur a modifié le demandeur : %s -> %s."
                    % (html_escape(old_name), html_escape(new_name))
                )
            )
        return result

    @api.constrains("bci")
    def _check_unique_bci(self):
        """Refuse qu'un BCI non vide soit utilisé par une autre demande DSS."""
        for rec in self:
            if not rec.bci:
                continue
            duplicate = self.search(
                [("bci", "=", rec.bci), ("id", "!=", rec.id)],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    u"Le BCI %s est déjà utilisé par une autre demande DSS."
                    % rec.bci
                )
