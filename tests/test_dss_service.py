# -*- coding: utf-8 -*-
"""Tests des services DSS et des droits du workflow."""

from odoo import api
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import common


class TestDssServiceWorkflow(common.TransactionCase):
    """Vérifie les services DSS, les contrôles d'accès et les notifications."""

    def setUp(self):
        super(TestDssServiceWorkflow, self).setUp()
        self.Request = self.env["dss.request"]
        self.Service = self.env["dss.service"]
        self.NotificationLog = self.env["dss.notification.log"]

        self.requester = self._create_user(
            "DSS Requester",
            "dss.requester.%s@example.invalid" % self.id(),
            [self.ref("dss_v2.group_dss_demandeur")],
        )
        self.chef = self._create_user(
            "DSS Service Chief",
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
        self.service = self.Service.create(
            {
                "name": "DSS Test Service",
                "dss_chef_id": self.chef.id,
                "dss_demandeurs_ids": [(6, 0, [self.requester.id])],
            }
        )

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

    def test_request_service_defaults_when_user_matches_one_service(self):
        """Le service est prérempli quand un seul service autorise le demandeur."""
        request = self._create_request()

        self.assertEqual(request.service_demandeur_id, self.service)

    def test_request_service_is_empty_when_user_matches_multiple_services(self):
        """Le service reste vide si plusieurs services autorisent le demandeur."""
        self.Service.create(
            {
                "name": "DSS Secondary Service",
                "dss_chef_id": self.chef.id,
                "dss_demandeurs_ids": [(6, 0, [self.requester.id])],
            }
        )

        request = self._create_request()

        self.assertFalse(request.service_demandeur_id)

    def test_request_service_is_empty_when_user_matches_no_service(self):
        """Le service reste vide si aucun service n'autorise le demandeur."""
        user_without_service = self._create_user(
            "DSS No Service User",
            "dss.no.service.%s@example.invalid" % self.id(),
        )

        request = self._create_request(user_without_service)

        self.assertFalse(request.service_demandeur_id)

    def test_request_service_ignores_inactive_service(self):
        """Un service inactif ne peut pas être choisi par défaut."""
        self.service.write({"active": False})

        request = self._create_request()

        self.assertFalse(request.service_demandeur_id)

    def test_request_service_can_change_only_in_draft(self):
        """Le demandeur peut choisir le service au brouillon, mais pas ensuite."""
        request = self._create_request()
        other_service = self.Service.create(
            {
                "name": "DSS Other Service",
                "dss_chef_id": self.chef.id,
                "dss_demandeurs_ids": [(6, 0, [self.requester.id])],
            }
        )

        request.write({"service_demandeur_id": other_service.id})
        self.assertEqual(request.service_demandeur_id, other_service)
        request.write({"state": "valide_chef"})
        with self.assertRaises(AccessError):
            request.write({"service_demandeur_id": self.service.id})

    def test_superuser_can_create_for_target_user_from_context(self):
        """Le contexte dss_user_id est appliqué uniquement aux créations superuser."""
        request = self.Request.sudo().with_context(
            dss_user_id=self.requester.id
        ).create({})

        self.assertEqual(request.service_demandeur_id, self.service)

    def test_superuser_rejects_nonexistent_target_user(self):
        """Une création superuser refuse un utilisateur cible inexistant."""
        with self.assertRaises(ValidationError):
            self.Request.sudo().with_context(dss_user_id=999999999).create({})

    def test_submission_requires_selected_service(self):
        """La soumission est refusée si aucun service n'a été sélectionné."""
        user_without_service = self._create_user(
            "DSS No Service User",
            "dss.no.service.%s@example.invalid" % self.id(),
        )
        request = self._create_request(user_without_service)

        with self.assertRaisesRegexp(
            ValidationError, u"Veuillez sélectionner un service demandeur"
        ):
            request.action_soumettre()

    def test_submission_rejects_service_without_authorized_users(self):
        """La soumission est refusée si le service n'a aucun demandeur configuré."""
        service_without_users = self.Service.create(
            {
                "name": "DSS Service Without Requesters",
                "dss_chef_id": self.chef.id,
            }
        )
        request = self._create_request(
            values={"service_demandeur_id": service_without_users.id}
        )

        with self.assertRaisesRegexp(
            ValidationError, u"aucun demandeur autorisé configuré"
        ):
            request.action_soumettre()

    def test_submission_rejects_user_not_authorized_for_selected_service(self):
        """La soumission est refusée si le demandeur n'est pas autorisé."""
        other_service = self.Service.create(
            {
                "name": "DSS Other Service",
                "dss_chef_id": self.chef.id,
                "dss_demandeurs_ids": [(6, 0, [self.outsider.id])],
            }
        )
        request = self._create_request(
            values={"service_demandeur_id": other_service.id}
        )

        with self.assertRaisesRegexp(
            AccessError, u"pas autorisé à effectuer des demandes"
        ):
            request.action_soumettre()

    def test_submission_requires_dss_chief(self):
        """La soumission exige un Chef DSS configuré sur le service."""
        self.service.write({"dss_chef_id": False})
        request = self._create_request()

        with self.assertRaises(ValidationError):
            request.action_soumettre()

    def test_submission_rejects_inactive_or_non_chef_user(self):
        """Le Chef DSS doit être actif et appartenir au groupe Chef."""
        self.service.write({"dss_chef_id": self.outsider.id})
        request = self._create_request()

        with self.assertRaises(ValidationError):
            request.action_soumettre()

        self.service.write({"dss_chef_id": self.chef.id})
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
