# -*- coding: utf-8 -*-
"""Tests de sécurité du module DSS.

Ce fichier vérifie le « lot A » de sécurisation :
    1. l'accès au modèle est réservé aux groupes DSS ;
    2. le demandeur ne voit que ses propres demandes ;
    3. le Chef ne voit que les demandes de son service ;
    4. l'état ne peut pas être écrit en dehors du workflow ;
    5. la validation Stock exige le groupe Magasin ;
    6. l'assistant de quantités refuse une demande hors étape Stock ;
    7. un Chef ne peut pas valider sa propre demande ;
    8. les assistants de confirmation sont accessibles à leur groupe.

Odoo 10 : les tests s'exécutent en superutilisateur (uid = 1). Pour tester un
rôle, il faut donc fabriquer un environnement avec api.Environment(cr, uid,
context) — c'est le rôle du raccourci _env_for() ci-dessous.
"""

# api permet de construire un environnement Odoo pour un autre utilisateur.
from odoo import api
# AccessError : droit refusé. ValidationError : règle métier non respectée.
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import common


class TestDssSecurity(common.TransactionCase):
    """Vérifie les ACL, les règles d'enregistrement et les garde-fous serveur."""

    def setUp(self):
        super(TestDssSecurity, self).setUp()
        # Raccourcis vers les modèles utilisés dans tous les tests.
        self.Request = self.env["dss.request"]
        self.Service = self.env["dss.service"]
        self.Product = self.env["product.product"]

        # Identifiants des groupes DSS, récupérés par leur nom XML externe.
        self.group_chef = self.ref("dss_v2.group_dss_chef")
        self.group_magasin = self.ref("dss_v2.group_dss_magasin")
        self.group_demandeur = self.ref("dss_v2.group_dss_demandeur")

        # Quatre utilisateurs, chacun avec un rôle bien distinct.
        self.requester_a = self._create_user(
            "DSS Securite Demandeur A", [self.group_demandeur]
        )
        self.requester_b = self._create_user(
            "DSS Securite Demandeur B", [self.group_demandeur]
        )
        self.chef_a = self._create_user(
            "DSS Securite Chef A", [self.group_chef]
        )
        self.chef_b = self._create_user(
            "DSS Securite Chef B", [self.group_chef]
        )
        self.magasinier = self._create_user(
            "DSS Securite Magasin", [self.group_magasin]
        )
        # Cet utilisateur n'a AUCUN groupe DSS : il ne doit rien voir.
        self.outsider = self._create_user("DSS Securite Externe", [])

        # Deux services indépendants, chacun avec son Chef et son demandeur.
        self.service_a = self.Service.create({
            "name": "DSS Securite Service A",
            "dss_chef_id": self.chef_a.id,
            "dss_demandeurs_ids": [(6, 0, [self.requester_a.id])],
        })
        self.service_b = self.Service.create({
            "name": "DSS Securite Service B",
            "dss_chef_id": self.chef_b.id,
            "dss_demandeurs_ids": [(6, 0, [self.requester_b.id])],
        })

    # ------------------------------------------------------------------
    # Outils de test
    # ------------------------------------------------------------------

    def _create_user(self, name, dss_groups=None):
        """Crée un utilisateur interne, avec un partenaire et une adresse uniques.

        Un utilisateur Odoo est toujours lié à un partenaire : on le crée
        d'abord pour pouvoir y placer le nom et l'e-mail.
        """
        login = "%s@example.invalid" % name.lower().replace(" ", ".")
        partner = self.env["res.partner"].create({
            "name": name,
            "email": login,
        })
        return self.env["res.users"].create({
            "name": name,
            "login": login,
            "partner_id": partner.id,
            # base.group_user = « Utilisateur interne », obligatoire pour se
            # connecter. On y ajoute les groupes DSS demandés par le test.
            "groups_id": [
                (6, 0, [self.ref("base.group_user")] + list(dss_groups or [])),
            ],
        })

    def _env_for(self, user):
        """Retourne un environnement Odoo 10 agissant en tant qu'utilisateur.

        api.Environment(cr, uid, context) est la seule façon de changer
        d'utilisateur dans un test : les droits (ACL + règles) sont alors
        réellement évalués comme en production.
        """
        return api.Environment(self.cr, user.id, dict(self.env.context))

    def _request_as(self, user, values=None):
        """Crée une demande avec l'environnement d'un utilisateur donné."""
        return self.Request.with_env(self._env_for(user)).create(values or {})

    # ------------------------------------------------------------------
    # 1. Contrôle d'accès au modèle (ACL)
    # ------------------------------------------------------------------

    def test_outsider_has_no_access_to_requests(self):
        """Un utilisateur sans groupe DSS ne peut pas lire les demandes."""
        # La demande existe bel et bien dans la base.
        request = self._request_as(self.requester_a)
        self.assertTrue(request.id)

        # search([]) déclenche le contrôle de droit de lecture sur le modèle.
        with self.assertRaises(AccessError):
            self.Request.with_env(self._env_for(self.outsider)).search([])

    # ------------------------------------------------------------------
    # 2 et 3. Périmètre de visibilité (règles d'enregistrement)
    # ------------------------------------------------------------------

    def test_requester_cannot_read_request_of_another_service(self):
        """Un demandeur accède à ses demandes, pas à celles d'un autre service."""
        request_a = self._request_as(self.requester_a)
        request_b = self._request_as(self.requester_b)
        env_b = self._env_for(self.requester_b)

        # Sa propre demande est lisible.
        self.assertEqual(request_b.with_env(env_b).name, request_b.name)

        # Lire une demande d'un autre service doit échouer : c'est la règle
        # d'enregistrement qui ajoute le filtre demandeur_id = utilisateur.
        with self.assertRaises(AccessError):
            request_a.with_env(env_b).read(["name"])

    def test_chef_sees_only_his_service(self):
        """Un Chef ne voit que les demandes du service qu'il dirige."""
        request_a = self._request_as(self.requester_a)
        request_b = self._request_as(self.requester_b)

        # search([]) applique la règle : service dont dss_chef_id = ce Chef.
        visible = self.Request.with_env(self._env_for(self.chef_a)).search([])

        self.assertIn(request_a, visible)
        self.assertNotIn(request_b, visible)

    def test_magasin_sees_all_requests(self):
        """Le Magasin doit voir toutes les demandes pour préparer les sorties."""
        request_a = self._request_as(self.requester_a)
        request_b = self._request_as(self.requester_b)

        visible = self.Request.with_env(
            self._env_for(self.magasinier)
        ).search([])

        self.assertIn(request_a, visible)
        self.assertIn(request_b, visible)

    # ------------------------------------------------------------------
    # 4. Garde-fou sur le champ state
    # ------------------------------------------------------------------

    def test_state_cannot_be_written_directly(self):
        """Un write({'state': ...}) hors workflow est refusé."""
        request = self._request_as(self.requester_a)

        # Le demandeur a bien le droit d'écrire sur le modèle (ACL), mais le
        # changement d'état est réservé aux actions du circuit.
        with self.assertRaises(AccessError):
            request.with_env(self._env_for(self.requester_a)).write({
                "state": "cloture",
            })

    def test_workflow_still_changes_state(self):
        """Les actions du workflow, elles, modifient bien l'état."""
        request = self._request_as(self.requester_a)

        # _dss_set_state() est le chemin autorisé : il pose une clé de contexte
        # que write() reconnaît. On vérifie donc que le mécanisme fonctionne.
        request.sudo()._dss_set_state("valide_chef")

        self.assertEqual(request.state, "valide_chef")

    # ------------------------------------------------------------------
    # 5. Contrôle du rôle à la validation Stock
    # ------------------------------------------------------------------

    def test_stock_validation_requires_magasin_group(self):
        """Un non-magasinier est refusé sur son rôle, avant même l'étape."""
        request = self._request_as(self.requester_a)

        # La demande est encore en brouillon. Pour un utilisateur sans le
        # groupe Magasin, c'est bien le contrôle de RÔLE qui doit parler en
        # premier : le message mentionne donc « DSS / Magasin ».
        with self.assertRaisesRegexp(AccessError, "DSS / Magasin"):
            request.with_env(
                self._env_for(self.requester_a)
            ).action_valider_magasin()

    def test_magasinier_passes_the_role_check(self):
        """Le magasinier franchit le contrôle de rôle, puis bute sur l'étape."""
        request = self._request_as(self.requester_a)

        # Même demande en brouillon, mais avec le bon groupe : le contrôle de
        # rôle laisse passer et c'est le contrôle d'ÉTAPE qui refuse.
        # L'exception attendue est donc ValidationError et non AccessError,
        # ce qui prouve que les deux garde-fous sont bien distincts.
        with self.assertRaises(ValidationError):
            request.with_env(
                self._env_for(self.magasinier)
            ).action_valider_magasin()

    # ------------------------------------------------------------------
    # 6. Contrôle de l'étape dans l'assistant de quantités
    # ------------------------------------------------------------------

    def test_quantity_wizard_requires_stock_stage(self):
        """L'ajustement des quantités est refusé hors de l'étape Stock."""
        product = self.Product.create({
            "name": "DSS Securite Produit",
            "type": "product",
        })
        # Demande déjà approuvée : les mouvements sont enregistrés.
        request = self.Request.create({"state": "approuve"})
        line = self.env["dss.request.line"].create({
            "request_id": request.id,
            "product_id": product.id,
            "qty_demandee": 5.0,
            "qty_sortie": 5.0,
        })
        wizard = self.env["dss.qty.sortie.wizard"].create({
            "request_id": request.id,
            "line_ids": [(0, 0, {
                "request_line_id": line.id,
                "product_id": product.id,
                "qty_sortie": 3.0,
                "motif_ecart": "Test securite",
            })],
        })

        # Le test s'exécute en superutilisateur : le contrôle de rôle passe,
        # c'est donc bien le contrôle d'étape qui doit refuser.
        with self.assertRaises(ValidationError):
            wizard.action_valider()

    # ------------------------------------------------------------------
    # 7. Séparation des tâches (Chef demandeur)
    # ------------------------------------------------------------------

    def test_chef_cannot_validate_his_own_request(self):
        """Un Chef qui est aussi le demandeur ne valide pas sa propre demande."""
        # Utilisateur cumulant les deux rôles.
        auto_chef = self._create_user(
            "DSS Securite Chef Demandeur",
            [self.group_chef, self.group_demandeur],
        )
        # Service dont ce même utilisateur est Chef ET demandeur autorisé.
        self.Service.create({
            "name": "DSS Securite Service Auto",
            "dss_chef_id": auto_chef.id,
            "dss_demandeurs_ids": [(6, 0, [auto_chef.id])],
        })

        # La demande lui appartient : demandeur_id est posé automatiquement.
        request = self.Request.with_env(
            self._env_for(auto_chef)
        ).create({})
        request.sudo().write({"state": "valide_chef"})

        with self.assertRaises(AccessError):
            request.with_env(
                self._env_for(auto_chef)
            ).action_valider_chef()

    # ------------------------------------------------------------------
    # 8. Assistants de confirmation
    # ------------------------------------------------------------------

    def test_validation_wizards_are_open_to_their_groups(self):
        """Chaque assistant de confirmation est accessible à son groupe métier."""
        request = self._request_as(self.requester_a)
        request.sudo().write({"state": "valide_chef"})

        # Le Chef peut ouvrir l'assistant de confirmation Chef.
        chef_wizard = self.env["dss.validation.chef.wizard"].with_env(
            self._env_for(self.chef_a)
        ).create({"request_id": request.id})
        self.assertTrue(chef_wizard.id)

        # Le Magasin peut ouvrir l'assistant de confirmation Stock.
        stock_wizard = self.env["dss.validation.stock.wizard"].with_env(
            self._env_for(self.magasinier)
        ).create({"request_id": request.id})
        self.assertTrue(stock_wizard.id)
