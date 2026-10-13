# -*- coding: utf-8 -*-

from odoo import (
    models,
    fields,
    api,
)


class DssRequestLine(
    models.Model
):  # Nom de la classe Python, représente une ligne d'article à l'intérieur d'une
    # demande DSS (le dss.request)
    _name = "dss.request.line"  # nom technique du modèle utilisé par Odoo == nom de la table dans PostgreSQL
    _description = (
        "Ligne de DSS"  # une DSS Request Line est une ligne qui se trouve dans un DSS
    )
    # une ligne contient un article et ses caractéristiques de demande

    # champ de relation : request_id, clé étrangère qui référence dss.request
    # depuis le modèle dss.request.line (crée la colonne request_id dans la
    # table dss_request_line en base PostgreSQL)
    request_id = fields.Many2one(
        "dss.request",
        string="Demande DSS",
        ondelete="cascade",  # à la suppression du parent dss.request, cette ligne
        # sera supprimée aussi : pas de ligne orpheline
    )
    # champ de relation product_id qui se réfère à un article, dans le modèle
    # standard d'Odoo pour les articles/produits
    product_id = fields.Many2one("product.product", string="Article", required=True)

    # champ de type décimal CALCULÉ (compute=...) : sa valeur n'est pas saisie
    # à la main par l'utilisateur mais calculée automatiquement par la méthode
    # _compute_qty_standard, et le résultat du calcul est sauvegardé en base
    # (store=True)
    qty_standard = fields.Float(
        string="Qte Disponible", compute="_compute_qty_standard", store=True
    )
    # champ de type décimal, pour la saisie de la quantité demandée en sortie/retour
    qty_demandee = fields.Float(string="Qte Demandee")
    # champ de type décimal, pour la quantité réellement sortie du stock
    qty_sortie = fields.Float(string="Qte Sortie")
    # champ de type décimal, pour la quantité réellement installée chez le
    # client, une fois l'intervention terminée
    qty_installee = fields.Float(string="Qte Installee")
    # champ décimal, dédié à la quantité de matériel qui retourne en stock
    # (en cas de retour)
    qty_retour = fields.Float(string="Qte Retour")
    # simple champ de texte libre, pour une remarque sur la ligne de DSS
    observation = fields.Char(string="Observation")
    # champ booléen qui sert uniquement à piloter l'affichage du champ
    # qty_demandee dans la vue (le rendre modifiable ou non)
    qty_demandee_readonly = fields.Boolean(
        string="Qte Demandee lecture seule", default=False
    )

    # Décorateur @api.depends('product_id') : dit à Odoo "recalcule ce
    # champ automatiquement à chaque fois que product_id change".
    # C'est ce qui relie ce compute à sa déclaration plus haut.
    @api.depends("product_id")
    def _compute_qty_standard(self):
        for line in self:
            # self peut contenir plusieurs lignes à la fois, alors on boucle
            # sur chacune
            if line.product_id:
                # si un article est choisi sur cette ligne
                line.qty_standard = line.product_id.qty_available
                # on récupère sa quantité disponible ("qty_available") en
                # stock, un champ déjà fourni nativement par le modèle
                # product.product
            else:  # sinon
                line.qty_standard = 0.0
                # si aucun article n'est encore choisi, pas de quantité à
                # afficher : on met 0 plutôt que de laisser une valeur vide

    # @api.onchange (différent de @api.depends) : s'exécute UNIQUEMENT
    # côté interface, en direct pendant que l'utilisateur remplit le
    # formulaire, AVANT toute sauvegarde en base. Sert à ajuster
    # dynamiquement l'écran (ici, verrouiller ou non un champ).
    @api.onchange("product_id")
    def _onchange_product_id_qty_demandee_readonly(self):
        if self.request_id:
            # on vérifie que la ligne est bien rattachée à une demande
            # (sécurité : au tout début de la saisie, ça peut ne pas
            # encore être le cas)

            # Logique métier : si le type d'intervention de la demande
            # parente est "Retour de materiel", alors qty_demandee devient
            # en lecture seule sur cette ligne (dans ce cas, c'est plutôt
            # qty_retour qui a du sens à remplir, pas une nouvelle demande)
            self.qty_demandee_readonly = (
                self.request_id.type_intervention == "retour_materiel"
            )