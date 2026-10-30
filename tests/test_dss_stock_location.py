# -*- coding: utf-8 -*-
"""Tests de la disponibilité des articles par emplacement DSS."""

from odoo.tests import common


class TestDssStockLocation(common.TransactionCase):
    """Vérifie que DSS utilise uniquement l'emplacement sélectionné."""

    def setUp(self):
        super(TestDssStockLocation, self).setUp()
        self.Location = self.env["stock.location"]
        self.Product = self.env["product.product"]
        self.Quant = self.env["stock.quant"]
        self.Request = self.env["dss.request"]
        self.Line = self.env["dss.request.line"]

        self.source = self.Location.create({
            "name": "DSS Test Source",
            "usage": "internal",
        })
        self.child = self.Location.create({
            "name": "DSS Test Child",
            "usage": "internal",
            "location_id": self.source.id,
        })
        self.product = self.Product.create({
            "name": "DSS Test Product",
            "type": "product",
        })

    def test_qty_standard_uses_exact_location_only(self):
        """La quantité directe est utilisée sans inclure l'enfant."""
        self.Quant.create({
            "product_id": self.product.id,
            "location_id": self.source.id,
            "qty": 7.0,
        })
        self.Quant.create({
            "product_id": self.product.id,
            "location_id": self.child.id,
            "qty": 13.0,
        })
        request = self.Request.create({"location_id": self.source.id})
        line = self.Line.create({
            "request_id": request.id,
            "product_id": self.product.id,
        })

        self.assertEqual(line.qty_standard, 7.0)

    def test_qty_standard_is_zero_without_location(self):
        """Sans emplacement source, aucune quantité globale n'est affichée."""
        request = self.Request.create({})
        line = self.Line.create({
            "request_id": request.id,
            "product_id": self.product.id,
        })

        self.assertEqual(line.qty_standard, 0.0)

    def test_name_search_returns_no_product_without_dss_location(self):
        """Le contexte DSS sans emplacement ne propose aucun article."""
        result = self.Product.with_context(dss_location_id=False).name_search(
            name="DSS Test Product"
        )

        self.assertFalse(result)