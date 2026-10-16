# -*- coding: utf-8 -*-

from odoo import models
from odoo.exceptions import ValidationError


class DssRequestStock(models.Model):
    """Ajoute à une demande DSS la création de ses mouvements de stock."""

    _inherit = "dss.request"

    def _generer_mouvement_sortie(self):
        """Transfère les quantités sorties de l'emplacement vers le client."""
        # Cette méthode traite une seule demande, condition nécessaire à ensure_one().
        self.ensure_one()
        # env donne accès aux modèles Odoo ; ces variables sont des modèles ORM, pas des lignes.
        StockQuant = self.env["stock.quant"]
        StockMove = self.env["stock.move"]
        StockPicking = self.env["stock.picking"]

        # filtered() garde les lignes dont la quantité à sortir est strictement positive.
        # La fonction lambda reçoit chaque ligne et fournit le critère de filtrage.
        lignes_a_traiter = self.line_ids.filtered(lambda l: l.qty_sortie > 0)
        if not lignes_a_traiter:
            # Aucun mouvement n'est nécessaire si aucune ligne n'a de quantité à sortir.
            return

        # Vérifie toutes les quantités avant de créer le transfert, afin d'éviter une sortie partielle.
        for ligne in lignes_a_traiter:
            # read_group regroupe les quantités par article et emplacement selon ce domaine.
            quants = StockQuant.read_group(
                [
                    ("location_id", "=", self.location_id.id),
                    ("product_id", "=", ligne.product_id.id),
                ],
                ["qty"],
                [],
            )
            # Une recherche vide signifie qu'aucun stock disponible n'a été trouvé.
            qty_disponible = quants[0]["qty"] if quants else 0.0
            if ligne.qty_sortie > qty_disponible:
                # ValidationError annule l'action Odoo et affiche ce message à l'utilisateur.
                raise ValidationError(
                    "Quantite insuffisante pour l article %s dans l emplacement %s : "
                    "demande %s, disponible %s."
                    % (
                        ligne.product_id.name,
                        self.location_id.name,
                        ligne.qty_sortie,
                        qty_disponible,
                    )
                )
        # Odoo peut définir un emplacement client propre au partenaire.
        emplacement_destination = self.partner_id.property_stock_customer
        if not emplacement_destination:
            # ref() charge l'emplacement client standard à partir de son identifiant XML externe.
            emplacement_destination = self.env.ref("stock.stock_location_customers")
        # Recherche le type de transfert sortant ; limit=1 évite de retourner plusieurs résultats.
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "outgoing")], limit=1
        )
        # create() crée l'en-tête du transfert et renvoie l'enregistrement obtenu.
        picking = StockPicking.create(
            {
                "partner_id": self.partner_id.id,
                "picking_type_id": picking_type.id,
                "location_id": self.location_id.id,
                "location_dest_id": emplacement_destination.id,
                "origin": self.name,
            }
        )
        # Chaque ligne DSS devient un mouvement de stock lié à l'en-tête créé plus haut.
        for ligne in lignes_a_traiter:
            # Les valeurs du dictionnaire correspondent aux champs du modèle stock.move.
            StockMove.create(
                {
                    "name": ligne.product_id.name,
                    "product_id": ligne.product_id.id,
                    "product_uom_qty": ligne.qty_sortie,
                    "product_uom": ligne.product_id.uom_id.id,
                    "location_id": self.location_id.id,
                    "location_dest_id": emplacement_destination.id,
                    "picking_id": picking.id,
                }
            )
        # Ces actions Odoo confirment, réservent puis terminent réellement le transfert.
        picking.action_confirm()
        picking.action_assign()
        picking.action_done()
        # Conserve le lien vers le transfert pour le retrouver depuis la demande DSS.
        self.picking_id = picking.id

    def _generer_mouvement_entree(self):
        """Réintègre dans le stock les quantités retournées par le client."""
        # Un seul dossier est traité à la fois ; les lignes sont filtrées sur la quantité retournée.
        self.ensure_one()
        StockMove = self.env["stock.move"]
        StockPicking = self.env["stock.picking"]

        # filtered() conserve uniquement les lignes dont le retour est supérieur à zéro.
        lignes_a_traiter = self.line_ids.filtered(lambda l: l.qty_retour > 0)
        if not lignes_a_traiter:
            # Rien à réintégrer : la méthode se termine sans créer de transfert vide.
            return

        # Le client est la source du retour ; le stock interne de la demande en est la destination.
        emplacement_source = self.partner_id.property_stock_customer
        if not emplacement_source:
            # En l'absence de configuration partenaire, utilise l'emplacement client standard d'Odoo.
            emplacement_source = self.env.ref("stock.stock_location_customers")
        # Le code incoming désigne un transfert entrant dans la configuration de stock Odoo.
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )
        # Crée le transfert entrant avec ses emplacements et l'origine de la demande.
        picking = StockPicking.create(
            {
                "partner_id": self.partner_id.id,
                "picking_type_id": picking_type.id,
                "location_id": emplacement_source.id,
                "location_dest_id": self.location_id.id,
                "origin": self.name,
            }
        )
        # Crée un mouvement par article retourné, avec son unité de mesure d'origine.
        for ligne in lignes_a_traiter:
            StockMove.create(
                {
                    "name": ligne.product_id.name,
                    "product_id": ligne.product_id.id,
                    "product_uom_qty": ligne.qty_retour,
                    "product_uom": ligne.product_id.uom_id.id,
                    "location_id": emplacement_source.id,
                    "location_dest_id": self.location_id.id,
                    "picking_id": picking.id,
                }
            )
        # Confirme, réserve puis valide le transfert selon le cycle standard d'Odoo 10.
        picking.action_confirm()
        picking.action_assign()
        picking.action_done()
        # Le champ permet de consulter le transfert depuis la demande.
        self.picking_id = picking.id

    def _generer_mouvement_transfert(self):
        """Déplace les quantités entre deux emplacements internes de stock."""
        # Un seul dossier est traité à la fois ; l'ORM fournit ensuite ses lignes et ses emplacements.
        self.ensure_one()
        StockQuant = self.env["stock.quant"]
        StockMove = self.env["stock.move"]
        StockPicking = self.env["stock.picking"]

        # Pour un transfert interne, la quantité déplacée est portée par qty_sortie.
        lignes_a_traiter = self.line_ids.filtered(lambda l: l.qty_sortie > 0)
        if not lignes_a_traiter:
            # Aucun article à transférer : ne crée pas d'opération vide.
            return
        if not self.location_dest_id:
            # La destination doit être définie avant de pouvoir construire un mouvement interne.
            raise ValidationError(
                "L emplacement destination est obligatoire pour un Transfert."
            )
        # Contrôle le stock source pour chaque article avant toute création de transfert.
        for ligne in lignes_a_traiter:
            # read_group agrège ici la quantité de l'article dans l'emplacement source.
            quants = StockQuant.read_group(
                [
                    ("location_id", "=", self.location_id.id),
                    ("product_id", "=", ligne.product_id.id),
                ],
                ["qty"],
                [],
            )
            # Si aucun résultat n'existe, la quantité disponible est considérée comme nulle.
            qty_disponible = quants[0]["qty"] if quants else 0.0
            if ligne.qty_sortie > qty_disponible:
                # L'exception interrompt la validation et empêche un transfert incomplet.
                raise ValidationError(
                    "Quantite insuffisante pour l article %s dans l emplacement %s : "
                    "demande %s, disponible %s."
                    % (
                        ligne.product_id.name,
                        self.location_id.name,
                        ligne.qty_sortie,
                        qty_disponible,
                    )
                )
        # Le code internal demande à Odoo un type de transfert entre emplacements internes.
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "internal")], limit=1
        )
        # L'en-tête du transfert relie l'emplacement source à l'emplacement destination.
        picking = StockPicking.create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.location_id.id,
                "location_dest_id": self.location_dest_id.id,
                "origin": self.name,
            }
        )
        # Chaque article devient un mouvement rattaché à ce transfert interne.
        for ligne in lignes_a_traiter:
            StockMove.create(
                {
                    "name": ligne.product_id.name,
                    "product_id": ligne.product_id.id,
                    "product_uom_qty": ligne.qty_sortie,
                    "product_uom": ligne.product_id.uom_id.id,
                    "location_id": self.location_id.id,
                    "location_dest_id": self.location_dest_id.id,
                    "picking_id": picking.id,
                }
            )
        # Termine le cycle standard : confirmation, réservation, puis validation du transfert.
        picking.action_confirm()
        picking.action_assign()
        picking.action_done()
        # Enregistre le transfert créé sur la demande DSS.
        self.picking_id = picking.id