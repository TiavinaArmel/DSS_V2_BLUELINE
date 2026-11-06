# -*- coding: utf-8 -*-
"""Tests du routage DSS par service RH et Chef DSS."""

from odoo import api
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import common


class TestDssServiceDepartment(common.TransactionCase):
    """Vérifie l'affectation RH, les droits du Chef DSS et les notifications."""

    def setUp(self):
        super(TestDssServiceDepartment, self).setUp()
        self.Request = self.env["dss.request"]
        self.Employee = self.env["hr.employee"]
        self.Department = self.env["hr.department"]
        self.NotificationLog = self.env["dss.notification.log"]

        self.requester = self._create_user(
            "DSS Requester",
            "dss.requester.%s@example.invalid" % self.id(),
            [self.ref("dss_v2.group_dss_demandeur")],
        )
        self.chef = self._create_user(
            "DSS Department Chief",
            "dss.chef.%s@example.invalid" % self.id(),
            [self.ref("dss_v2.group_dss_chef")],
        )
        self.outsider = self._create_user(
            "DSS Outsider", "dss.outsider.%s@example.invalid" % self.id()
        )
        self.other_chef = self._create_user(
            "DSS Other Chief",
            "dss.other.chef.%s@example.invalid" % self.id(),
            [self.ref("dss_v2.group_dss_chef")],
        )
        self.magasinier = self._create_user(
            "DSS Store User",
            "dss.store.%s@example.invalid" % self.id(),
            [self.ref("dss_v2.group_dss_magasin")],
        )
        self.department = self.Department.create({"name": "DSS Test Department"})
        self.requester_employee = self.Employee.create(
            {
                "name": self.requester.name,
                "user_id": self.requester.id,
                "department_id": self.department.id,
            }
        )
        self.department.write({"dss_chef_id": self.chef.id})

    def _create_user(self, name, email, additional_groups=None):
        """Crée un utilisateur interne de test avec une adresse distincte."""
        partner = self.env["res.partner"].create(
            {"name": name, "email": email}
        )
        return self.env["res.users"].create(
            {
                "name": name,
                "login": email,
                "partner_id": partner.id,
                "groups_id": [
                    (
                        6,
                        0,
                        [self.ref("base.group_user")] + (additional_groups or []),
                    ),
                ],
            }
        )

    def _env_for(self, user):
        """Construit un environnement Odoo 10 pour l'utilisateur fourni."""
        return api.Environment(self.cr, user.id, dict(self.env.context))

    def _create_request(self, user=None, values=None):
        """Crée une DSS avec l'environnement du demandeur de test."""
        user = user or self.requester
        return self.Request.with_env(self._env_for(user)).create(values or {})

    def test_request_service_defaults_from_active_employee(self):
        """Le service vient de la fiche employé du demandeur."""
        request = self._create_request()

        self.assertEqual(request.service_demandeur_id, self.department)

    def test_request_service_uses_lowest_id_active_employee(self):
        """Les utilisateurs multi-employés reçoivent le service du premier ID."""
        other_department = self.Department.create(
            {"name": "DSS Secondary Department"}
        )
        self.Employee.create(
            {
                "name": "DSS Secondary Employee",
                "user_id": self.requester.id,
                "department_id": other_department.id,
            }
        )

        request = self._create_request()

        self.assertEqual(request.service_demandeur_id, self.department)

    def test_create_ignores_service_supplied_by_caller(self):
        """Même une valeur fournie par l'appelant est remplacée par le service RH."""
        another_department = self.Department.create(
            {"name": "DSS Other Department"}
        )
        request = self._create_request(
            values={"service_demandeur_id": another_department.id}
        )

        self.assertEqual(request.service_demandeur_id, self.department)

    def test_regular_user_cannot_change_request_service(self):
        """Le service d'une DSS ne peut pas être modifié après sa création."""
        request = self._create_request()
        another_department = self.Department.create(
            {"name": "DSS Other Department"}
        )

        with self.assertRaises(AccessError):
            request.write({"service_demandeur_id": another_department.id})

    def test_superuser_can_create_for_target_user_from_context(self):
        """Le contexte dss_user_id est appliqué uniquement aux créations superuser."""
        request = self.Request.sudo().with_context(
            dss_user_id=self.requester.id
        ).create({})

        self.assertEqual(request.service_demandeur_id, self.department)

    def test_superuser_rejects_nonexistent_target_user(self):
        """Une création superuser refuse un utilisateur cible inexistant."""
        with self.assertRaises(ValidationError):
            self.Request.sudo().with_context(dss_user_id=999999999).create({})

    def test_submission_requires_rh_department(self):
        """La soumission d'un demandeur sans service RH est refusée."""
        user_without_department = self._create_user(
            "DSS No Department", "dss.no.department.%s@example.invalid" % self.id()
        )
        request = self._create_request(user_without_department)

        with self.assertRaises(ValidationError):
            request.action_soumettre()

    def test_submission_requires_dss_chief(self):
        """La soumission exige un Chef DSS configuré sur le service."""
        self.department.write({"dss_chef_id": False})
        request = self._create_request()

        with self.assertRaises(ValidationError):
            request.action_soumettre()

    def test_submission_rejects_inactive_or_non_chef_user(self):
        """Le Chef DSS doit être actif et appartenir au groupe Chef."""
        self.department.write({"dss_chef_id": self.outsider.id})
        request = self._create_request()

        with self.assertRaises(ValidationError):
            request.action_soumettre()

        self.department.write({"dss_chef_id": self.chef.id})
        self.chef.write({"active": False})
        with self.assertRaises(ValidationError):
            request.action_soumettre()

    def test_only_configured_dss_chief_can_validate(self):
        """Seul le Chef DSS configuré peut valider."""
        request = self._create_request(values={"state": "valide_chef"})

        with self.assertRaises(AccessError):
            request.with_env(self._env_for(self.outsider)).action_valider_chef()

        request.with_env(self._env_for(self.chef)).action_valider_chef()
        self.assertEqual(request.state, "valide_magasin")
        self.assertEqual(request.signataire_chef_id, self.chef)

    def test_submission_email_is_sent_to_dss_chief(self):
        """La soumission cible l'adresse résolue du Chef DSS."""
        partner = self.env["res.partner"].create(
            {"name": "DSS Test Customer"}
        )
        location = self.env["stock.location"].create(
            {"name": "DSS Test Location", "usage": "internal"}
        )
        product = self.env["product.product"].create(
            {"name": "DSS Test Product", "type": "product"}
        )
        request = self._create_request(
            values={
                "bci": "DSS-TEST-BCI",
                "partner_id": partner.id,
                "lieu_intervention": "DSS Test Site",
                "date_intervention": "2026-11-05",
                "type_intervention": "nouvelle_installation",
                "location_id": location.id,
                "line_ids": [
                    (0, 0, {"product_id": product.id, "qty_demandee": 1.0}),
                ],
            }
        )

        request.action_soumettre()

        log = self.NotificationLog.search(
            [
                ("request_id", "=", request.id),
                ("event_key", "=", "submission"),
            ],
            limit=1,
        )
        self.assertTrue(log)
        self.assertEqual(log.recipient_emails, self.chef.partner_id.email)

    def test_only_assigned_chief_can_reject_at_chief_stage(self):
        """Au stade Chef, seul le Chef DSS assigné peut ouvrir ou confirmer le rejet."""
        request = self._create_request(values={"state": "valide_chef"})

        with self.assertRaises(AccessError):
            request.with_env(self._env_for(self.other_chef)).action_open_wizard_rejeter()
        with self.assertRaises(AccessError):
            request.with_env(self._env_for(self.other_chef)).action_rejeter()

        request.with_env(self._env_for(self.chef)).action_rejeter()
        self.assertEqual(request.state, "rejete")

    def test_only_store_group_can_reject_at_store_stage(self):
        """Au stade Stock, le rejet est réservé au groupe Magasin."""
        request = self._create_request(values={"state": "valide_magasin"})

        with self.assertRaises(AccessError):
            request.with_env(self._env_for(self.outsider)).action_rejeter()

        request.with_env(self._env_for(self.magasinier)).action_rejeter()
        self.assertEqual(request.state, "rejete")

    def test_rejection_is_refused_outside_allowed_stages(self):
        """Une demande ne peut pas être rejetée depuis un autre état."""
        request = self._create_request(values={"state": "brouillon"})

        with self.assertRaises(AccessError):
            request.with_env(self._env_for(self.chef)).action_open_wizard_rejeter()
        with self.assertRaises(AccessError):
            request.with_env(self._env_for(self.chef)).action_rejeter()

    def _create_closure_wizard(self, request, user, is_exception=False):
        """Crée le wizard de clôture avec l'environnement de l'utilisateur."""
        env = self._env_for(user)
        return env["dss.cloture.wizard"].with_context(
            default_is_exception=is_exception
        ).create({"request_id": request.id})

    def test_requester_can_close_approved_request(self):
        """Le demandeur d'origine peut clôturer sa demande approuvée."""
        request = self._create_request(
            values={
                "state": "approuve",
                "signataire_demandeur_id": self.requester.id,
            }
        )
        wizard = self._create_closure_wizard(request, self.requester)

        wizard.action_confirmer()

        self.assertEqual(request.state, "cloture")

    def test_closure_wizard_marks_chef_exception(self):
        """L'ouverture du wizard marque explicitement la clôture du Chef."""
        request = self._create_request(
            values={
                "state": "approuve",
                "signataire_demandeur_id": self.requester.id,
            }
        )

        requester_action = request.action_open_wizard_cloture()
        chef_action = request.with_env(self._env_for(self.chef)).action_open_wizard_cloture()
        with self.assertRaises(AccessError):
            request.with_env(self._env_for(self.outsider)).action_open_wizard_cloture()

        self.assertFalse(requester_action["context"]["default_is_exception"])
        self.assertTrue(chef_action["context"]["default_is_exception"])

    def test_chef_can_close_only_as_exception(self):
        """Un Chef peut clôturer comme exception, pas comme demandeur ordinaire."""
        request = self._create_request(
            values={
                "state": "approuve",
                "signataire_demandeur_id": self.requester.id,
            }
        )
        regular_wizard = self._create_closure_wizard(request, self.chef)

        with self.assertRaises(AccessError):
            regular_wizard.action_confirmer()

        exception_wizard = self._create_closure_wizard(
            request, self.chef, is_exception=True
        )
        exception_wizard.action_confirmer()

        self.assertEqual(request.state, "cloture")

    def test_unrelated_user_cannot_close_request(self):
        """Un utilisateur qui n'est ni demandeur ni Chef ne peut clôturer."""
        request = self._create_request(
            values={
                "state": "approuve",
                "signataire_demandeur_id": self.requester.id,
            }
        )

        with self.assertRaises(AccessError):
            request.with_env(self._env_for(self.outsider)).action_open_wizard_cloture()

    def test_closure_requires_approved_state(self):
        """Même un utilisateur autorisé ne peut clôturer un autre état."""
        request = self._create_request(
            values={
                "state": "valide_chef",
                "signataire_demandeur_id": self.requester.id,
            }
        )
        wizard = self._create_closure_wizard(request, self.requester)

        with self.assertRaises(ValidationError):
            wizard.action_confirmer()
