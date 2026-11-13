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
        self.admin = self._create_user(
            "DSS Administrator",
            "dss.admin.%s@example.invalid" % self.id(),
            [self.ref("base.group_system")],
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

    def test_requester_cannot_be_assigned_to_multiple_services(self):
        """Un utilisateur déjà affilié ne peut être ajouté à un autre service."""
        with self.assertRaisesRegexp(ValidationError, u"un seul service"):
            self.Service.create(
                {
                    "name": "DSS Secondary Service",
                    "dss_chef_id": self.chef.id,
                    "dss_demandeurs_ids": [(6, 0, [self.requester.id])],
                }
            )

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

    def test_requester_cannot_change_service_even_in_draft(self):
        """Le demandeur ne peut pas modifier le service par appel serveur."""
        request = self._create_request()
        other_service = self.Service.create(
            {
                "name": "DSS Other Service",
                "dss_chef_id": self.chef.id,
                "dss_demandeurs_ids": [(6, 0, [self.outsider.id])],
            }
        )

        with self.assertRaises(AccessError):
            request.with_env(self._env_for(self.requester)).write(
                {"service_demandeur_id": other_service.id}
            )

    def test_service_creation_requires_chef_to_assign_self(self):
        """Un Chef peut créer un service uniquement en s'assignant comme Chef."""
        chef_services = self.Service.with_env(self._env_for(self.chef))

        with self.assertRaises(AccessError):
            chef_services.create(
                {
                    "name": "DSS Unauthorized Service",
                    "dss_chef_id": self.other_chef.id,
                }
            )

        service = chef_services.create(
            {
                "name": "DSS Chef-Owned Service",
                "dss_chef_id": self.chef.id,
            }
        )
        self.assertEqual(service.dss_chef_id, self.chef)

    def test_only_assigned_chef_or_admin_can_modify_service(self):
        """Seul le Chef assigné ou un administrateur peut modifier le service."""
        with self.assertRaises(AccessError):
            self.service.with_env(
                self._env_for(self.other_chef)
            ).write({"name": "DSS Unauthorized Rename"})

        self.service.with_env(self._env_for(self.chef)).write(
            {"name": "DSS Chef Updated Service"}
        )
        self.service.with_env(self._env_for(self.admin)).write(
            {"name": "DSS Admin Updated Service"}
        )
        self.assertEqual(self.service.name, "DSS Admin Updated Service")

    def test_service_requires_active_chef_in_dss_chef_group(self):
        """Un service ne peut pas être créé sans Chef DSS valide."""
        with self.assertRaises(ValidationError):
            self.Service.create({"name": "DSS Service Without Chief"})

        with self.assertRaises(ValidationError):
            self.Service.create(
                {
                    "name": "DSS Service With Invalid Chief",
                    "dss_chef_id": self.outsider.id,
                }
            )

    def test_admin_can_change_submitted_service_and_audit_change(self):
        """Une correction admin après soumission est enregistrée dans le chatter."""
        new_service = self.Service.create(
            {
                "name": "DSS Admin Replacement Service",
                "dss_chef_id": self.chef.id,
            }
        )
        request = self._create_request(
            values={
                "service_demandeur_id": self.service.id,
                "state": "valide_chef",
            }
        )

        request.with_env(self._env_for(self.admin)).write(
            {"service_demandeur_id": new_service.id}
        )

        self.assertEqual(request.service_demandeur_id, new_service)
        audit_message = self.env["mail.message"].search(
            [
                ("model", "=", "dss.request"),
                ("res_id", "=", request.id),
                ("body", "ilike", "L'administrateur a modifié le service"),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(audit_message)
        self.assertIn("DSS Test Service", audit_message.body)
        self.assertIn("DSS Admin Replacement Service", audit_message.body)

    def test_request_creation_forces_owner_and_owner_service(self):
        """La création ignore les propriétaires et services envoyés par le client."""
        other_service = self.Service.create(
            {
                "name": "DSS Outsider Service",
                "dss_chef_id": self.chef.id,
                "dss_demandeurs_ids": [(6, 0, [self.outsider.id])],
            }
        )

        request = self.Request.with_env(self._env_for(self.requester)).create(
            {
                "demandeur_id": self.outsider.id,
                "service_demandeur_id": other_service.id,
            }
        )

        self.assertEqual(request.demandeur_id, self.requester)
        self.assertEqual(request.service_demandeur_id, self.service)

    def test_superuser_can_create_for_target_user_from_context(self):
        """Le contexte dss_user_id est appliqué uniquement aux créations superuser."""
        request = self.Request.sudo().with_context(
            dss_user_id=self.requester.id
        ).create({})

        self.assertEqual(request.demandeur_id, self.requester)
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
            ValidationError, u"contacter votre supérieur de département actuel"
        ):
            request.action_soumettre()

    def test_submission_rejects_service_without_authorized_users(self):
        """Un demandeur absent de la liste du service ne peut pas soumettre."""
        service_without_users = self.Service.create(
            {
                "name": "DSS Service Without Requesters",
                "dss_chef_id": self.chef.id,
            }
        )
        request = self._create_request(
            values={"service_demandeur_id": service_without_users.id}
        )
        request.sudo().write({"service_demandeur_id": service_without_users.id})

        with self.assertRaisesRegexp(
            AccessError, u"liste des demandeurs autorisés"
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
        request.sudo().write({"service_demandeur_id": other_service.id})

        with self.assertRaisesRegexp(
            AccessError, u"liste des demandeurs autorisés"
        ):
            request.action_soumettre()

    def test_only_request_owner_can_submit(self):
        """Un utilisateur ne peut pas soumettre la DSS d'un autre demandeur."""
        request = self._create_request()

        with self.assertRaises(AccessError):
            request.with_env(self._env_for(self.outsider)).action_soumettre()

    def test_submission_requires_dss_chief(self):
        """Un service ne peut pas être enregistré sans Chef DSS."""
        with self.assertRaises(ValidationError):
            self.Service.create({"name": "DSS Service Without Chief"})

    def test_submission_rejects_inactive_or_non_chef_user(self):
        """Le Chef DSS doit être actif et appartenir au groupe Chef."""
        with self.assertRaises(ValidationError):
            self.Service.create(
                {
                    "name": "DSS Service With Invalid Chief",
                    "dss_chef_id": self.outsider.id,
                }
            )

        self.chef.write({"active": False})
        request = self._create_request()
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

    def test_requester_closure_can_create_the_return_picking(self):
        """Le demandeur clôture et crée un retour sans droits Stock."""
        location = self.env["stock.location"].create({
            "name": "DSS Requester Return Location",
            "usage": "internal",
        })
        product = self.env["product.product"].create({
            "name": "DSS Requester Return Product",
            "type": "product",
        })
        request = self._create_request(
            user=self.requester,
            values={
                "state": "approuve",
                "signataire_demandeur_id": self.requester.id,
                "type_intervention": "nouvelle_installation",
                "location_id": location.id,
                "partner_id": self.env.ref("base.res_partner_1").id,
            },
        )
        line = self.env["dss.request.line"].create({
            "request_id": request.id,
            "product_id": product.id,
            "qty_demandee": 10.0,
            "qty_sortie": 10.0,
        })
        wizard = self._create_closure_wizard(request, self.requester)
        wizard.write({
            "line_ids": [(0, 0, {
                "request_line_id": line.id,
                "product_id": product.id,
                "qty_sortie": 10.0,
                "qty_installee": 7.0,
                "qty_retour": 0.0,
                "mode_saisie": "installee",
            })],
        })

        wizard.action_confirmer()

        self.assertEqual(request.state, "cloture")
        self.assertTrue(request.picking_retour_cloture_id)
        self.assertEqual(
            request.picking_retour_cloture_id.location_dest_id,
            location,
        )
        self.assertEqual(
            request.picking_retour_cloture_id.move_lines.product_uom_qty,
            3.0,
        )

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
