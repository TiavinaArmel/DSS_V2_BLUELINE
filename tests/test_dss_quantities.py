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
        # Le magasinier n'intervient qu'à l'étape Stock : la demande est créée
        # dans cet état pour respecter le contrôle serveur du wizard
        # (action_valider refuse tout autre état depuis la version 2.14).
        request = self.Request.create({"state": "valide_magasin"})
        line = self.Line.create({
            "request_id": request.id,
            "product_id": self.product.id,
            "qty_demandee": demand,
        })
        return request, line

    def _return_material_request(self, qty_retour=4.0):
        request, line = self._request_with_line()
        request.type_intervention = "retour_materiel"
        line.qty_retour = qty_retour
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

    def test_quantity_change_chatter_renders_bullet(self):
        """Le chatter affiche le caractère puce et non sa séquence d'échappement."""
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

        audit_message = self.env["mail.message"].search(
            [
                ("model", "=", "dss.request"),
                ("res_id", "=", request.id),
                ("body", "ilike", "Le Responsable Stock"),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(audit_message)
        self.assertIn(u"\u2022", audit_message.body)
        self.assertNotIn(u"\\u2022", audit_message.body)
        self.assertIn(u"Article DSS Quantity Test Product", audit_message.body)
        self.assertIn(u"Quantité demandée : 10.0", audit_message.body)
        self.assertIn(u"Quantité sortie : 7.0", audit_message.body)
        self.assertIn(u"Motif de modification : Stock insuffisant", audit_message.body)

    def test_sortie_only_return_is_deferred_to_closure(self):
        """Le wizard Stock ne peut pas enregistrer un retour pour une sortie seule."""
        request, line = self._request_with_line()
        request.type_intervention = "nouvelle_installation"
        line.qty_sortie = 10.0
        wizard = self.env["dss.qty.sortie.wizard"].create({
            "request_id": request.id,
            "line_ids": [(0, 0, {
                "request_line_id": line.id,
                "product_id": self.product.id,
                "qty_demandee": 10.0,
                "qty_sortie": 10.0,
                "qty_retour": 4.0,
                "qty_sortie_initiale": 10.0,
                "qty_retour_initiale": 0.0,
            })],
        })

        wizard.action_valider()

        self.assertEqual(line.qty_sortie, 10.0)
        self.assertEqual(line.qty_retour, 0.0)

    def test_stock_wizard_defaults_include_sortie_only_flag(self):
        """Le tableau du wizard reçoit le booléen utilisé par son attrs."""
        request, line = self._request_with_line()
        request.type_intervention = "nouvelle_installation"
        self.assertTrue(line.is_sortie_only)

        defaults = self.env["dss.qty.sortie.wizard"].with_context(
            default_request_id=request.id
        ).default_get(["request_id", "line_ids"])

        self.assertTrue(defaults["line_ids"][0][2]["is_sortie_only"])

    def test_return_material_defaults_preserve_return_quantity(self):
        """Le wizard Stock reprend le retour demandé et conserve les lignes intactes."""
        request, line = self._return_material_request(4.0)
        defaults = self.env["dss.qty.sortie.wizard"].with_context(
            default_request_id=request.id
        ).default_get(["request_id", "line_ids"])
        default_line = defaults["line_ids"][0][2]

        self.assertTrue(default_line["is_retour_materiel"])
        self.assertEqual(default_line["qty_retour"], 4.0)
        self.assertEqual(default_line["qty_retour_initiale"], 4.0)

        wizard = self.env["dss.qty.sortie.wizard"].create(defaults)
        wizard.action_valider()
        request._prepare_quantities_before_stock_validation()

        self.assertEqual(line.qty_retour, 4.0)
        self.assertEqual(line.qty_demandee, 0.0)
        self.assertEqual(line.qty_sortie, 0.0)
        self.assertEqual(line.qty_installee, 0.0)
        self.assertFalse(request.is_qty_modified)
        self.assertFalse(request.has_ecart)

    def test_return_material_quantity_change_requires_motif(self):
        """Toute variation de la quantité retournée exige un motif au Stock."""
        request, line = self._return_material_request(4.0)
        wizard = self.env["dss.qty.sortie.wizard"].create({
            "request_id": request.id,
            "line_ids": [(0, 0, {
                "request_line_id": line.id,
                "product_id": self.product.id,
                "qty_retour": 2.0,
                "qty_retour_initiale": 4.0,
            })],
        })

        with self.assertRaises(ValidationError):
            wizard.action_valider()

        self.assertEqual(line.qty_retour, 4.0)
        self.assertFalse(request.is_qty_modified)

    def test_return_material_quantity_change_is_saved_and_traced(self):
        """Le motif et la quantité corrigée sont conservés sans utiliser les autres quantités."""
        request, line = self._return_material_request(4.0)
        wizard = self.env["dss.qty.sortie.wizard"].create({
            "request_id": request.id,
            "line_ids": [(0, 0, {
                "request_line_id": line.id,
                "product_id": self.product.id,
                "qty_retour": 2.0,
                "qty_retour_initiale": 4.0,
                "motif_ecart": u"Quantité réellement reçue",
            })],
        })

        wizard.action_valider()
        request._prepare_quantities_before_stock_validation()

        self.assertEqual(line.qty_retour, 2.0)
        self.assertEqual(line.qty_demandee, 0.0)
        self.assertEqual(line.qty_sortie, 0.0)
        self.assertEqual(line.qty_installee, 0.0)
        self.assertEqual(line.motif_ecart, u"Quantité réellement reçue")
        self.assertTrue(request.is_qty_modified)
        self.assertTrue(request.has_ecart)

        audit_message = self.env["mail.message"].search(
            [
                ("model", "=", "dss.request"),
                ("res_id", "=", request.id),
                ("body", "ilike", "Le Responsable Stock"),
            ],
            order="id desc",
            limit=1,
        )
        self.assertIn(u"Quantité retour demandée : 4.0", audit_message.body)
        self.assertIn(u"Quantité retour validée : 2.0", audit_message.body)
        self.assertIn(u"Quantité réellement reçue", audit_message.body)

    def test_return_material_rejects_negative_quantity(self):
        """La quantité retournée négative est refusée côté serveur."""
        request, line = self._return_material_request(4.0)
        wizard = self.env["dss.qty.sortie.wizard"].create({
            "request_id": request.id,
            "line_ids": [(0, 0, {
                "request_line_id": line.id,
                "product_id": self.product.id,
                "qty_retour": -1.0,
                "qty_retour_initiale": 4.0,
                "motif_ecart": "Test",
            })],
        })

        with self.assertRaises(ValidationError):
            wizard.action_valider()

        self.assertEqual(line.qty_retour, 4.0)

    def test_ecart_uses_two_decimal_precision(self):
        """Une différence inférieure au centième n'est pas un écart."""
        request, line = self._request_with_line()
        request.is_qty_modified = True
        line.qty_sortie = 10.004
        line.qty_retour = 0.0

        request._prepare_quantities_before_stock_validation()

        self.assertFalse(request.has_ecart)

    def test_unmodified_lines_use_requested_quantity_without_motif(self):
        """Une seule ligne modifiée ne force pas de motif sur les autres lignes."""
        request = self.Request.create({})
        second_product = self.Product.create({
            "name": "DSS Quantity Test Product 2",
            "type": "product",
        })
        first = self.Line.create({
            "request_id": request.id,
            "product_id": self.product.id,
            "qty_demandee": 10.0,
        })
        second = self.Line.create({
            "request_id": request.id,
            "product_id": second_product.id,
            "qty_demandee": 5.0,
        })
        wizard = self.env["dss.qty.sortie.wizard"].create({
            "request_id": request.id,
            "line_ids": [
                (0, 0, {
                    "request_line_id": first.id,
                    "product_id": self.product.id,
                    "qty_demandee": 10.0,
                    "qty_sortie": 7.0,
                    "qty_retour": 0.0,
                    "qty_sortie_initiale": 0.0,
                    "qty_retour_initiale": 0.0,
                    "motif_ecart": "Stock insuffisant",
                }),
                (0, 0, {
                    "request_line_id": second.id,
                    "product_id": second_product.id,
                    "qty_demandee": 5.0,
                    "qty_sortie": 0.0,
                    "qty_retour": 0.0,
                    "qty_sortie_initiale": 0.0,
                    "qty_retour_initiale": 0.0,
                }),
            ],
        })

        wizard.action_valider()

        self.assertEqual(first.qty_sortie, 7.0)
        self.assertEqual(first.motif_ecart, "Stock insuffisant")
        self.assertEqual(second.qty_sortie, 5.0)
        self.assertFalse(second.motif_ecart)

        request._prepare_quantities_before_stock_validation()
        self.assertTrue(request.has_ecart)

    def test_appro_distant_stock_wizard_defers_return_to_closure(self):
        """Un approvisionnement distant ne porte aucun retour à la validation Stock."""
        request, line = self._request_with_line()
        request.type_intervention = "appro_distant"
        line.qty_retour = 4.0

        defaults = self.env["dss.qty.sortie.wizard"].with_context(
            default_request_id=request.id
        ).default_get(["request_id", "line_ids"])
        default_line = defaults["line_ids"][0][2]

        self.assertTrue(default_line["is_sortie_only"])
        self.assertEqual(default_line["qty_retour"], 0.0)
        self.assertEqual(default_line["qty_retour_initiale"], 0.0)

    def test_depannage_stock_wizard_defers_return_to_closure(self):
        """Un dépannage reporte le retour à la clôture, pas à la validation Stock."""
        request, line = self._request_with_line()
        request.type_intervention = "depannage"
        line.qty_retour = 4.0

        defaults = self.env["dss.qty.sortie.wizard"].with_context(
            default_request_id=request.id
        ).default_get(["request_id", "line_ids"])
        default_line = defaults["line_ids"][0][2]

        self.assertTrue(default_line["is_sortie_only"])
        self.assertEqual(default_line["qty_retour"], 0.0)
        self.assertEqual(default_line["qty_retour_initiale"], 0.0)

    def test_basculement_keeps_manual_quantities_at_stock(self):
        """Le basculement conserve la saisie manuelle des quantités au Stock."""
        request, line = self._request_with_line()
        request.type_intervention = "basculement"
        line.qty_retour = 4.0

        defaults = self.env["dss.qty.sortie.wizard"].with_context(
            default_request_id=request.id
        ).default_get(["request_id", "line_ids"])
        default_line = defaults["line_ids"][0][2]

        self.assertFalse(default_line["is_sortie_only"])
        self.assertEqual(default_line["qty_retour"], 4.0)
