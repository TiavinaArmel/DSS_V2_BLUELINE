# -*- coding: utf-8 -*-
"""Tests transactionnels du workflow de clôture DSS."""

from odoo.exceptions import ValidationError
from odoo.tests import common


class TestDssClosure(common.TransactionCase):
    """Vérifie les clôtures normale et exceptionnelle."""

    def setUp(self):
        super(TestDssClosure, self).setUp()
        self.Request = self.env["dss.request"]
        self.Wizard = self.env["dss.cloture.wizard"]
        self.chef_group = self.env.ref("dss_v2.group_dss_chef")
        self.Product = self.env["product.product"]
        self.Location = self.env["stock.location"]

    def _approved_request(self):
        """Crée une DSS approuvée appartenant à l'utilisateur courant."""
        return self.Request.create({
            "name": "TEST-DSS-CLOSURE",
            "state": "approuve",
        })

    def _sortie_request(self, type_intervention="nouvelle_installation"):
        location = self.Location.create({
            "name": "DSS Closure Return Location",
            "usage": "internal",
        })
        product = self.Product.create({
            "name": "DSS Closure Return Product",
            "type": "product",
        })
        request = self.Request.create({
            "name": "TEST-DSS-CLOSURE-RETURN",
            "state": "approuve",
            "type_intervention": type_intervention,
            "location_id": location.id,
            "partner_id": self.env.ref("base.res_partner_1").id,
        })
        line = self.env["dss.request.line"].create({
            "request_id": request.id,
            "product_id": product.id,
            "qty_demandee": 10.0,
            "qty_sortie": 10.0,
            "qty_installee": 3.0,
            "qty_retour": 7.0,
        })
        return request, line

    def _create_sortie_wizard(self, request, line, mode, installed, returned):
        return self.Wizard.create({
            "request_id": request.id,
            "line_ids": [(0, 0, {
                "request_line_id": line.id,
                "product_id": line.product_id.id,
                "qty_sortie": line.qty_sortie,
                "qty_installee": installed,
                "qty_retour": returned,
                "mode_saisie": mode,
            })],
        })

    def test_requester_can_open_normal_closure_with_create_uid_fallback(self):
        """Le créateur peut clôturer si le signataire historique est vide."""
        request = self._approved_request()
        self.assertFalse(request.signataire_demandeur_id)

        action = request.action_open_wizard_cloture()

        self.assertEqual(action["res_model"], "dss.cloture.wizard")
        self.assertFalse(action["context"]["default_is_exception"])
        self.assertEqual(action["context"]["default_request_id"], request.id)

    def test_exception_closure_requires_a_reason(self):
        """Une clôture exceptionnelle sans motif est refusée côté serveur."""
        self.env.user.write({"groups_id": [(4, self.chef_group.id)]})
        request = self._approved_request()
        wizard = self.Wizard.create({
            "request_id": request.id,
            "is_exception": True,
        })

        with self.assertRaises(ValidationError):
            wizard.action_confirmer()

    def test_exception_closure_records_actor_and_reason(self):
        """La clôture exceptionnelle passe l'état et trace son motif."""
        self.env.user.write({"groups_id": [(4, self.chef_group.id)]})
        request = self._approved_request()
        wizard = self.Wizard.create({
            "request_id": request.id,
            "is_exception": True,
            "motif_exception": "Demandeur indisponible",
        })

        wizard.action_confirmer()

        self.assertEqual(request.state, "cloture")
        self.assertTrue(
            any(
                "clôture exceptionnelle" in (message.body or "")
                and "Demandeur indisponible" in (message.body or "")
                for message in request.message_ids
            )
        )

    def test_exception_closure_action_sets_exception_context(self):
        """Le bouton Chef ouvre le même wizard avec le contexte exceptionnel."""
        self.env.user.write({"groups_id": [(4, self.chef_group.id)]})
        request = self._approved_request()

        action = request.action_open_wizard_cloture_exception()

        self.assertEqual(action["res_model"], "dss.cloture.wizard")
        self.assertTrue(action["context"]["default_is_exception"])

    def test_sortie_closure_defaults_to_all_installed(self):
        """Une sortie laissée intacte est considérée entièrement installée."""
        request, line = self._sortie_request()
        defaults = self.Wizard.with_context(
            default_request_id=request.id
        ).default_get(["request_id", "line_ids"])
        default_line = defaults["line_ids"][0][2]

        self.assertTrue(default_line["is_sortie_only"])
        self.assertEqual(default_line["qty_installee"], 10.0)
        self.assertEqual(default_line["qty_retour"], 0.0)
        self.assertEqual(default_line["mode_saisie"], "installee")

        wizard = self._create_sortie_wizard(request, line, "installee", 10.0, 0.0)
        wizard.action_confirmer()

        self.assertEqual(line.qty_installee, 10.0)
        self.assertEqual(line.qty_retour, 0.0)
        self.assertFalse(request.picking_retour_cloture_id)

    def test_sortie_closure_calculates_return_and_replenishes_origin(self):
        """La quantité installée saisie calcule le retour et le transfère à la source."""
        request, line = self._sortie_request()
        self.env.user.partner_id.write({
            "email": "dss-closure-return@example.invalid",
        })
        wizard = self._create_sortie_wizard(request, line, "installee", 7.0, 0.0)

        wizard.action_confirmer()

        self.assertEqual(line.qty_installee, 7.0)
        self.assertEqual(line.qty_retour, 3.0)
        picking = request.picking_retour_cloture_id
        self.assertTrue(picking)
        self.assertEqual(picking.state, "done")
        self.assertEqual(picking.location_dest_id, request.location_id)
        self.assertEqual(picking.move_lines.product_uom_qty, 3.0)
        self.assertTrue(
            any(
                "Retours à l’emplacement d’origine" in (message.body or "")
                and "Une quantité 3.0 de l’article %s" % line.product_id.name
                in (message.body or "")
                and request.location_id.name in (message.body or "")
                for message in request.message_ids
            )
        )
        notification = self.env["dss.notification.log"].search([
            ("request_id", "=", request.id),
            ("event_key", "=", "closure"),
        ], limit=1)
        self.assertTrue(notification)
        self.assertIn("Une quantité 3.0", notification.mail_id.body_html)
        self.assertIn(request.location_id.name, notification.mail_id.body_html)

    def test_sortie_closure_can_use_return_as_the_input(self):
        """La saisie du retour calcule automatiquement la quantité installée."""
        request, line = self._sortie_request("installation_interne")
        wizard = self._create_sortie_wizard(request, line, "retour", 10.0, 2.0)

        wizard.action_confirmer()

        self.assertEqual(line.qty_installee, 8.0)
        self.assertEqual(line.qty_retour, 2.0)
        self.assertEqual(
            request.picking_retour_cloture_id.move_lines.product_uom_qty,
            2.0,
        )

    def test_sortie_closure_onchange_updates_the_complementary_quantity(self):
        """Le changement du mode ou du nombre recalcule l'autre champ dans le wizard."""
        request, line = self._sortie_request()
        wizard_line = self.env["dss.cloture.wizard.line"].new({
            "request_line_id": line.id,
            "qty_sortie": 10.0,
            "qty_installee": 7.0,
            "qty_retour": 0.0,
            "mode_saisie": "installee",
        })

        wizard_line._onchange_quantites_sortie()

        self.assertEqual(wizard_line.qty_retour, 3.0)

        wizard_line.mode_saisie = "retour"
        wizard_line.qty_retour = 2.0
        wizard_line._onchange_quantites_sortie()

        self.assertEqual(wizard_line.qty_installee, 8.0)

    def test_sortie_closure_rejects_quantity_above_stock_output(self):
        """Le serveur interdit une quantité installée supérieure à la sortie."""
        request, line = self._sortie_request()
        wizard = self._create_sortie_wizard(request, line, "installee", 11.0, 0.0)
        wizard.line_ids.qty_sortie = 100.0

        with self.assertRaises(ValidationError):
            wizard.action_confirmer()

        self.assertEqual(request.state, "approuve")
        self.assertFalse(request.picking_retour_cloture_id)

    def test_sortie_closure_rejects_negative_return(self):
        """Le serveur refuse une quantité retournée négative."""
        request, line = self._sortie_request()
        wizard = self._create_sortie_wizard(request, line, "retour", 10.0, -1.0)

        with self.assertRaises(ValidationError):
            wizard.action_confirmer()

        self.assertEqual(request.state, "approuve")
        self.assertFalse(request.picking_retour_cloture_id)

    def test_other_movement_types_keep_manual_closure_quantities(self):
        """Les autres sens de mouvement conservent la saisie existante."""
        request, line = self._sortie_request("basculement")
        wizard = self._create_sortie_wizard(request, line, "installee", 6.0, 4.0)

        wizard.action_confirmer()

        self.assertEqual(line.qty_installee, 6.0)
        self.assertEqual(line.qty_retour, 4.0)
        self.assertFalse(request.picking_retour_cloture_id)

    def test_exception_closure_email_contains_actor_and_reason(self):
        """Le contexte exceptionnel enrichit le courriel de clôture."""
        request = self._approved_request()
        request.with_context(
            dss_closure_type="exception",
            dss_closure_actor="Chef de test",
            dss_closure_reason="Motif de test",
        )._dss_notify_workflow(
            "closure",
            "Clôture",
            ["closure-exception@example.invalid"],
        )
        log = self.env["dss.notification.log"].search(
            [("request_id", "=", request.id), ("event_key", "=", "closure")],
            limit=1,
        )

        self.assertIn("Clôture exceptionnelle", log.mail_id.body_html)
        self.assertIn("Chef de test", log.mail_id.body_html)
        self.assertIn("Motif de test", log.mail_id.body_html)