# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DssRejetWizard(models.TransientModel):
    # models.TransientModel : un modèle "temporaire", utilisé pour les
    # popups/wizards. Ses données ne sont PAS conservées indéfiniment
    # (Odoo les nettoie automatiquement après un certain temps)
    _name = "dss.rejet.wizard"
    _description = "Assistant de rejet de la demande DSS"

    request_id = fields.Many2one(
        "dss.request", string="Demande DSS", required=True, readonly=True
    )
    # le lien vers la demande à rejeter. readonly=True : l'utilisateur ne
    # choisit pas cette demande lui-même dans le wizard, elle est
    # pré-remplie automatiquement par le contexte (default_request_id) vu
    # dans action_open_wizard_rejeter plus haut

    motif = fields.Text(string="Motif du rejet", required=True)
    # le seul champ que l'utilisateur remplit réellement dans ce wizard :
    # obligatoire (required=True), donc impossible de rejeter sans motif

    @api.multi
    def action_confirmer(self):
        self.ensure_one()
        self.request_id.motif_rejet = self.motif
        # on reporte le motif saisi dans le wizard vers le champ
        # motif_rejet de la VRAIE demande DSS (request_id)
        self.request_id.action_rejeter()
        # puis on appelle la méthode de rejet déjà vue plus haut : le
        # wizard ne fait donc que collecter le motif avant de déclencher
        # l'action réelle
        return {"type": "ir.actions.act_window_close"}