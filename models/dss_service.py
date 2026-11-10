# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import AccessError, ValidationError


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

    @api.model
    def create(self, vals):
        """Un Chef ne peut créer qu'un service dont il est lui-même responsable."""
        vals = dict(vals)
        is_admin = (
            self.env.uid == SUPERUSER_ID
            or self.env.user.has_group("base.group_system")
        )
        if not is_admin and vals.get("dss_chef_id") != self.env.uid:
            raise AccessError(
                u"Un Chef DSS ne peut créer qu'un service dont il est le Chef."
            )
        requester_ids = self._requester_ids_from_commands(
            [], vals.get("dss_demandeurs_ids", [])
        )
        self._check_requester_affiliations(requester_ids)
        return super(DssService, self).create(vals)

    @api.multi
    def write(self, vals):
        """Réserve la modification du service à son Chef ou à un administrateur."""
        is_admin = (
            self.env.uid == SUPERUSER_ID
            or self.env.user.has_group("base.group_system")
        )
        if not is_admin:
            for rec in self:
                if rec.dss_chef_id != self.env.user:
                    raise AccessError(
                        u"Seul le Chef DSS de ce service peut le modifier."
                    )
        if "dss_demandeurs_ids" in vals:
            assigned_by_service = {}
            for rec in self:
                requester_ids = self._requester_ids_from_commands(
                    rec.dss_demandeurs_ids.ids,
                    vals["dss_demandeurs_ids"],
                )
                self._check_requester_affiliations(
                    requester_ids,
                    excluded_service_ids=self.ids,
                )
                for user_id in requester_ids:
                    previous_service = assigned_by_service.get(user_id)
                    if previous_service and previous_service != rec:
                        raise ValidationError(
                            u"Un utilisateur ne peut avoir qu'un seul service."
                        )
                    assigned_by_service[user_id] = rec
        return super(DssService, self).write(vals)

    @api.model
    def _requester_ids_from_commands(self, current_ids, commands):
        """Calcule les utilisateurs qui resteront affiliés après les commandes M2M."""
        requester_ids = set(current_ids)
        if not commands:
            return requester_ids
        if (
            isinstance(commands, tuple)
            and len(commands) == 3
            and isinstance(commands[0], int)
        ):
            commands = [commands]
        for command in commands:
            operation = command[0]
            if operation == 6:
                requester_ids = set(command[2])
            elif operation == 5:
                requester_ids.clear()
            elif operation == 4:
                requester_ids.add(command[1])
            elif operation in (2, 3):
                requester_ids.discard(command[1])
        return requester_ids

    @api.model
    def _check_requester_affiliations(
        self, requester_ids, excluded_service_ids=None
    ):
        """Refuse une affiliation déjà utilisée par un autre service."""
        excluded_service_ids = excluded_service_ids or []
        for user_id in requester_ids:
            other_service = self.sudo().search(
                [
                    ("dss_demandeurs_ids", "in", user_id),
                    ("id", "not in", excluded_service_ids),
                ],
                limit=1,
            )
            if other_service:
                user = self.env["res.users"].sudo().browse(user_id)
                raise ValidationError(
                    u"L'utilisateur %s est déjà affilié au service %s. "
                    u"Un utilisateur ne peut avoir qu'un seul service."
                    % (user.name, other_service.name)
                )

    @api.constrains("dss_chef_id")
    def _check_dss_chef(self):
        """Chaque service doit avoir un Chef actif du groupe DSS / Chef."""
        for rec in self:
            chef = rec.dss_chef_id
            if not chef:
                raise ValidationError(
                    u"Un service doit obligatoirement avoir un Chef DSS."
                )
            if not chef.active or not chef.has_group("dss_v2.group_dss_chef"):
                raise ValidationError(
                    u"Le Chef DSS doit être actif et appartenir au groupe DSS / Chef."
                )

    @api.constrains("dss_demandeurs_ids")
    def _check_unique_dss_demandeur(self):
        """Empêche un utilisateur d'être affilié à plusieurs services."""
        for rec in self:
            for user in rec.dss_demandeurs_ids:
                other_service = self.sudo().search(
                    [
                        ("id", "!=", rec.id),
                        ("dss_demandeurs_ids", "in", user.id),
                    ],
                    limit=1,
                )
                if other_service:
                    raise ValidationError(
                        u"L'utilisateur %s est déjà affilié au service %s. "
                        u"Un utilisateur ne peut avoir qu'un seul service."
                        % (user.name, other_service.name)
                    )
