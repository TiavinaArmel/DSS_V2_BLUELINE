# -*- coding: utf-8 -*-
"""Tests du routage DSS par service RH et chef de département."""

from odoo import api
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import common


class TestDssServiceDepartment(common.TransactionCase):
    """Vérifie l'affectation RH, les droits du chef et les notifications."""

    def setUp(self):
        super(TestDssServiceDepartment, self).setUp()
        self.Request = self.env["dss.request"]
        self.Employee = self.env["hr.employee"]
        self.Department = self.env["hr.department"]
        self.NotificationLog = self.env["dss.notification.log"]

        self.requester = self._create_user(
            "DSS Requester", "dss.requester.%s@example.invalid" % self.id()
        )
        self.chef = self._create_user(
            "DSS Department Chief", "dss.chef.%s@example.invalid" % self.id()
        )
        self.outsider = self._create_user(
            "DSS Outsider", "dss.outsider.%s@example.invalid" % self.id()
        )
        self.department = self.Department.create({"name": "DSS Test Department"})
        self.requester_employee = self.Employee.create(
            {
                "name": self.requester.name,
                "user_id": self.requester.id,
                "department_id": self.department.id,
            }
        )
        self.chef_employee = self.Employee.create(
            {
                "name": self.chef.name,
                "user_id": self.chef.id,
                "department_id": self.department.id,
            }
        )
        self.department.write({"manager_id": self.chef_employee.id})

    def _create_user(self, name, email):
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
                    (6, 0, [self.ref("base.group_user")]),
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

    def test_submission_requires_department_manager_and_user(self):
        """La soumission exige un chef avec un compte Odoo associé."""
        self.department.write({"manager_id": False})
        request = self._create_request()

        with self.assertRaises(ValidationError):
            request.action_soumettre()

        manager_without_user = self.Employee.create(
            {
                "name": "DSS Manager Without User",
                "department_id": self.department.id,
            }
        )
        self.department.write({"manager_id": manager_without_user.id})
        request = self._create_request()

        with self.assertRaises(ValidationError):
            request.action_soumettre()

    def test_only_current_department_manager_can_validate(self):
        """Le chef actuel peut valider, les autres utilisateurs sont refusés."""
        request = self._create_request(values={"state": "valide_chef"})

        with self.assertRaises(AccessError):
            request.with_env(self._env_for(self.outsider)).action_valider_chef()

        request.with_env(self._env_for(self.chef)).action_valider_chef()
        self.assertEqual(request.state, "valide_magasin")
        self.assertEqual(request.signataire_chef_id, self.chef)

    def test_submission_email_is_sent_to_department_manager(self):
        """La soumission cible l'adresse résolue du chef du service."""
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
