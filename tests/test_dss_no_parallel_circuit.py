# -*- coding: utf-8 -*-
"""Garde-fous contre le code retiré du module.

Ce fichier protège deux nettoyages successifs. Il échoue si quelqu'un
réintroduit les éléments correspondants, ce qui réactiverait les problèmes
en silence.

1) LE CIRCUIT DSS PARALLÈLE (retiré en 2.16)
Le module a longtemps étendu deux modèles standards d'Odoo pour un second
circuit DSS, distinct de la fiche dss.request :
    - stock.picking          : dss_number, dss_validation_state,
                               dss_justification, dss_movement_type ;
    - product.template       : dss_standard_qty.

Ce circuit n'a jamais été utilisé : aucune vue, aucun menu, aucune séquence de
numérotation, et 53 transferts sur 53 restés à l'état brouillon en base. Un de
ses contrôles, branché sur la popup Odoo « Transfert immédiat ? », pouvait en
plus bloquer la validation de n'importe quel transfert de stock.

2) LA MÉTHODE FANTÔME (retirée en 2.17)
`action_open_wizard_approuver()` ouvrait une fenêtre sur le modèle
`dss.validation.approuver.wizard`, qui n'a jamais été écrit. Aucun bouton ne
l'appelait ; un appel aurait produit une erreur serveur « Model not found ».
"""

from odoo.tests import common


class TestDssNoParallelCircuit(common.TransactionCase):
    """Vérifie que les extensions du circuit parallèle restent absentes."""

    def test_stock_picking_has_no_dss_fields(self):
        """Le modèle stock.picking ne porte plus aucun champ DSS."""
        # _fields est le dictionnaire des champs réellement enregistrés par
        # l'ORM pour ce modèle : c'est la source de vérité, pas la vue.
        fields = self.env["stock.picking"]._fields
        for field_name in (
            "dss_number",
            "dss_validation_state",
            "dss_justification",
            "dss_movement_type",
        ):
            self.assertNotIn(
                field_name,
                fields,
                u"Le champ %s a été réintroduit sur stock.picking : "
                u"le circuit DSS parallèle retiré en 2.16 revient." % field_name,
            )

    def test_product_template_has_no_standard_quantity(self):
        """Le modèle product.template ne porte plus la quantité standard DSS."""
        self.assertNotIn(
            "dss_standard_qty",
            self.env["product.template"]._fields,
            u"Le champ dss_standard_qty a été réintroduit : il n'avait de sens "
            u"que pour le circuit parallèle retiré en 2.16.",
        )

    def test_stock_picking_keeps_eccart_method_removed(self):
        """La méthode de contrôle d'écart du circuit parallèle a disparu."""
        # dir() liste les attributs accessibles du modèle ; la méthode retirée
        # ne doit plus y figurer. On évite hasattr(), dont le comportement est
        # particulier sur les modèles Odoo (__getattr__ personnalisé).
        self.assertNotIn("check_dss_ecart", dir(self.env["stock.picking"]))


class TestDssNoPhantomWizardMethod(common.TransactionCase):
    """Vérifie la suppression de la méthode d'ouverture sans modèle (2.17)."""

    def test_approval_wizard_method_is_removed(self):
        """action_open_wizard_approuver() ne doit plus exister sur dss.request."""
        # Cette méthode renvoyait une action pointant vers le modèle
        # `dss.validation.approuver.wizard`, qui n'a jamais été écrit.
        # Elle aurait provoqué une erreur « Model not found » si un bouton
        # avait un jour été branché dessus.
        self.assertNotIn(
            "action_open_wizard_approuver",
            dir(self.env["dss.request"]),
            u"La méthode fantôme action_open_wizard_approuver() a été "
            u"réintroduite : elle vise un modèle inexistant.",
        )

    def test_approval_wizard_model_is_still_absent(self):
        """Le modèle visé ne doit pas être réapparu non plus."""
        # Garde-fou symétrique : si quelqu'un crée un jour ce modèle pour
        # « réparer » la méthode, il devra aussi rétablir un vrai bouton et
        # une étape de validation, ce qui est une décision métier explicite.
        self.assertNotIn(
            "dss.validation.approuver.wizard",
            self.env.registry.models,
            u"Le modèle dss.validation.approuver.wizard est apparu : vérifiez "
            u"qu'une étape de validation a réellement été conçue pour lui.",
        )
