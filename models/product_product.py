# -*- coding: utf-8 -*-

from odoo import models, api


class ProductProduct(models.Model):
    _inherit = "product.product"
    # on N'UTILISE PAS _name ici : on utilise _inherit SEUL sur un modèle
    # qui existe déjà (product.product, le modèle standard des articles
    # Odoo). C'est de l'HÉRITAGE PAR EXTENSION : on ne crée pas un nouveau
    # modèle, on ajoute/modifie du comportement sur un modèle existant

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """
        Surcharge de name_search() pour filtrer les articles proposés
        selon l'emplacement passé dans le contexte ('dss_location_id').

        Si ce contexte est présent, seuls les articles ayant un stock
        strictement positif (qty > 0) à cet emplacement sont proposés
        dans les champs Many2one vers product.product.

        Si le contexte est absent, comportement standard d'Odoo
        (tous les articles sont proposés).
        """
        # cette méthode est appelée AUTOMATIQUEMENT par Odoo chaque fois
        # qu'un utilisateur tape du texte dans un champ "Article"
        args = args or []
        # si on ne nous donne aucune liste de filtres, on en crée une
        # vide pour pouvoir la compléter plus loin
        location_id = self._context.get("dss_location_id")
        # on regarde si la vue en cours a précisé un emplacement
        # (context.get("dss_location_id")) — l'emplacement où doit se
        # trouver l'article recherché

        if location_id:
            # si on sait dans quel emplacement on travaille, on demande
            # quels articles sont réellement disponibles à cet endroit :
            # on interroge l'inventaire d'Odoo (stock.quant) pour cet
            # emplacement, en demandant, pour chaque article, combien il
            # y en a en stock
            Quant = self.env["stock.quant"]
            quants = Quant.read_group(
                [("location_id", "=", location_id)],
                ["product_id", "qty"],
                ["product_id"],
            )
            product_ids = []
            for q in quants:
                if q["product_id"] and q["qty"] > 0:
                    product_ids.append(q["product_id"][0])
            args = args + [("id", "in", product_ids)]
        return super(ProductProduct, self).name_search(
            name=name, args=args, operator=operator, limit=limit
        )