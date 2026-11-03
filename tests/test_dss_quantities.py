# -*- coding: utf-8 -*-
"""Tests de la logique métier des quantités DSS."""

from odoo.exceptions import ValidationError
from odoo.tests import common


class TestDssQuantities(common.TransactionCase):
    """Vérifie la copie par défaut, les modifications et les écarts."""

    def setUp(self):
        super(TestDssQuantities, self).setUp()
        self.Request = self.env["dss.request"]
        self.Line = self.env["dss.request.line"]
        self.Product = self.env["product.product"]
        self.product = self.Product.create({
            "name": "DSS Quantity Test Product",
            "type": "product",
        })

    def _request_with_line(self, demand=10.0):
        request = self.Request.create({})
        line = self.Line.create({
            "request_id": request.id,
            "product_id": self.product.id,
            "qty_demandee": demand,
        })
        return request, line

    def test_default_quantity_is_copied_at_stock_validation(self):
        """Sans wizard, la sortie reprend la demande et aucun retour n'est créé."""
        request, line = self._request_with_line()
        request.is_qty_modified = False
        line.qty_sortie = 0.0
        line.qty_retour = 4.0

        request._prepare_quantities_before_stock_validation()

        self.assertEqual(line.qty_sortie, 10.0)
        self.assertEqual(line.qty_retour, 0.0)
        self.assertFalse(request.has_ecart)

    def test_modified_quantity_requires_motif(self):
        """Une sortie différente de la demande exige un motif dans le wizard."""
        request, line = self._request_with_line()
        wizard = self.env["dss.qty.sortie.wizard"].create({
            "request_id": request.id,
            "line_ids": [(0, 0, {
                "request_line_id": line.id,
                "product_id": self.product.id,
                "qty_demandee": 10.0,
                "qty_sortie": 7.0,
                "qty_retour": 0.0,
            })],
        })

        with self.assertRaises(ValidationError):
            wizard.action_valider()

    def test_modified_quantity_keeps_demand_and_writes_motif(self):
        """Le wizard conserve la demande et reporte le motif sur la ligne DSS."""
        request, line = self._request_with_line()
        wizard = self.env["dss.qty.sortie.wizard"].create({
            "request_id": request.id,
            "line_ids": [(0, 0, {
                "request_line_id": line.id,
                "product_id": self.product.id,
                "qty_demandee": 10.0,
                "qty_sortie": 7.0,
                "qty_retour": 0.0,
                "motif_ecart": "Stock insuffisant",
            })],
        })

        wizard.action_valider()

        self.assertEqual(line.qty_demandee, 10.0)
        self.assertEqual(line.qty_sortie, 7.0)
        self.assertEqual(line.motif_ecart, "Stock insuffisant")
        self.assertTrue(request.is_qty_modified)

    def test_ecart_uses_two_decimal_precision(self):
        """Une différence inférieure au centième n'est pas un écart."""
        request, line = self._request_with_line()
        request.is_qty_modified = True
        line.qty_sortie = 10.004
        line.qty_retour = 0.0

        request._prepare_quantities_before_stock_validation()

        self.assertFalse(request.has_ecart)
