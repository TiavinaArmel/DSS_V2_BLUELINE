# -*- coding: utf-8 -*-

from odoo import models
from odoo.exceptions import ValidationError


class DssRequestStock(models.Model):
    _inherit = "dss.request"

    def _generer_mouvement_sortie(self):
        self.ensure_one()
        StockQuant = self.env["stock.quant"]
        StockMove = self.env["stock.move"]
        StockPicking = self.env["stock.picking"]

        lignes_a_traiter = self.line_ids.filtered(lambda l: l.qty_sortie > 0)
        if not lignes_a_traiter:
            return

        for ligne in lignes_a_traiter:
            quants = StockQuant.read_group(
                [
                    ("location_id", "=", self.location_id.id),
                    ("product_id", "=", ligne.product_id.id),
                ],
                ["qty"],
                [],
            )
            qty_disponible = quants[0]["qty"] if quants else 0.0
            if ligne.qty_sortie > qty_disponible:
                raise ValidationError(
                    "Quantite insuffisante pour l article %s dans l emplacement %s : "
                    "demande %s, disponible %s."
                    % (
                        ligne.product_id.name,
                        self.location_id.name,
                        ligne.qty_sortie,
                        qty_disponible,
                    )
                )
        emplacement_destination = self.partner_id.property_stock_customer
        if not emplacement_destination:
            emplacement_destination = self.env.ref("stock.stock_location_customers")
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "outgoing")], limit=1
        )
        picking = StockPicking.create(
            {
                "partner_id": self.partner_id.id,
                "picking_type_id": picking_type.id,
                "location_id": self.location_id.id,
                "location_dest_id": emplacement_destination.id,
                "origin": self.name,
            }
        )
        for ligne in lignes_a_traiter:
            StockMove.create(
                {
                    "name": ligne.product_id.name,
                    "product_id": ligne.product_id.id,
                    "product_uom_qty": ligne.qty_sortie,
                    "product_uom": ligne.product_id.uom_id.id,
                    "location_id": self.location_id.id,
                    "location_dest_id": emplacement_destination.id,
                    "picking_id": picking.id,
                }
            )
        picking.action_confirm()
        picking.action_assign()
        picking.action_done()
        self.picking_id = picking.id

    def _generer_mouvement_entree(self):
        self.ensure_one()
        StockMove = self.env["stock.move"]
        StockPicking = self.env["stock.picking"]

        lignes_a_traiter = self.line_ids.filtered(lambda l: l.qty_retour > 0)
        if not lignes_a_traiter:
            return

        emplacement_source = self.partner_id.property_stock_customer
        if not emplacement_source:
            emplacement_source = self.env.ref("stock.stock_location_customers")
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )
        picking = StockPicking.create(
            {
                "partner_id": self.partner_id.id,
                "picking_type_id": picking_type.id,
                "location_id": emplacement_source.id,
                "location_dest_id": self.location_id.id,
                "origin": self.name,
            }
        )
        for ligne in lignes_a_traiter:
            StockMove.create(
                {
                    "name": ligne.product_id.name,
                    "product_id": ligne.product_id.id,
                    "product_uom_qty": ligne.qty_retour,
                    "product_uom": ligne.product_id.uom_id.id,
                    "location_id": emplacement_source.id,
                    "location_dest_id": self.location_id.id,
                    "picking_id": picking.id,
                }
            )
        picking.action_confirm()
        picking.action_assign()
        picking.action_done()
        self.picking_id = picking.id

    def _generer_mouvement_transfert(self):
        self.ensure_one()
        StockQuant = self.env["stock.quant"]
        StockMove = self.env["stock.move"]
        StockPicking = self.env["stock.picking"]

        lignes_a_traiter = self.line_ids.filtered(lambda l: l.qty_sortie > 0)
        if not lignes_a_traiter:
            return
        if not self.location_dest_id:
            raise ValidationError(
                "L emplacement destination est obligatoire pour un Transfert."
            )
        for ligne in lignes_a_traiter:
            quants = StockQuant.read_group(
                [
                    ("location_id", "=", self.location_id.id),
                    ("product_id", "=", ligne.product_id.id),
                ],
                ["qty"],
                [],
            )
            qty_disponible = quants[0]["qty"] if quants else 0.0
            if ligne.qty_sortie > qty_disponible:
                raise ValidationError(
                    "Quantite insuffisante pour l article %s dans l emplacement %s : "
                    "demande %s, disponible %s."
                    % (
                        ligne.product_id.name,
                        self.location_id.name,
                        ligne.qty_sortie,
                        qty_disponible,
                    )
                )
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "internal")], limit=1
        )
        picking = StockPicking.create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.location_id.id,
                "location_dest_id": self.location_dest_id.id,
                "origin": self.name,
            }
        )
        for ligne in lignes_a_traiter:
            StockMove.create(
                {
                    "name": ligne.product_id.name,
                    "product_id": ligne.product_id.id,
                    "product_uom_qty": ligne.qty_sortie,
                    "product_uom": ligne.product_id.uom_id.id,
                    "location_id": self.location_id.id,
                    "location_dest_id": self.location_dest_id.id,
                    "picking_id": picking.id,
                }
            )
        picking.action_confirm()
        picking.action_assign()
        picking.action_done()
        self.picking_id = picking.id