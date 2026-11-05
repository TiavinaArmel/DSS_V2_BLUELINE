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

    def _approved_request(self):
        """Crée une DSS approuvée appartenant à l'utilisateur courant."""
        return self.Request.create({
            "name": "TEST-DSS-CLOSURE",
            "state": "approuve",
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