# -*- coding: utf-8 -*-

from odoo import (
    models,
    fields,
    api,
)
# ValidationError : erreur métier affichée à l'utilisateur, qui annule l'action.
from odoo.exceptions import ValidationError
# float_compare : compare deux décimaux en respectant une précision donnée.
# Indispensable ici, car comparer des flottants avec < 0 peut refuser -0.001
# à cause des arrondis internes de Python.
from odoo.tools.float_utils import float_compare


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
    # Motif saisi lorsque les quantités validées ne correspondent pas à la
    # quantité initialement demandée.
    motif_ecart = fields.Text(string="Motif de l'écart")
    # simple champ de texte libre, pour une remarque sur la ligne de DSS
    observation = fields.Char(string="Observation")
    # champ booléen qui sert uniquement à piloter l'affichage du champ
    # qty_demandee dans la vue (le rendre modifiable ou non)
    qty_demandee_readonly = fields.Boolean(
        string="Qte Demandee lecture seule", default=False
    )
    is_sortie_only = fields.Boolean(
        string="Intervention avec mouvement sortie uniquement",
        compute="_compute_is_sortie_only",
    )
    is_retour_materiel = fields.Boolean(
        string="Intervention de retour de matériel",
        compute="_compute_is_retour_materiel",
    )

    # Décorateur @api.depends : recalcule la disponibilité quand l'article ou
    # l'emplacement source de la demande change.
    # C'est ce qui relie ce compute à sa déclaration plus haut.
    @api.depends("product_id", "request_id.location_id")
    def _compute_qty_standard(self):
        StockQuant = self.env["stock.quant"]

        for line in self:
            # Sans article ou sans emplacement source, aucune quantité locale
            # ne peut être déterminée de manière fiable.
            if not line.product_id or not line.request_id.location_id:
                line.qty_standard = 0.0
                continue

            # Le domaine utilise '=' volontairement : les sous-emplacements
            # ne doivent pas être consolidés dans cette disponibilité.
            quants = StockQuant.search(
                [
                    ("location_id", "=", line.request_id.location_id.id),
                    ("product_id", "=", line.product_id.id),
                ]
            )
            line.qty_standard = sum(quant.qty for quant in quants)

    @api.depends("request_id.sens_mouvement", "request_id.type_intervention")
    def _compute_is_sortie_only(self):
        # Une intervention concernée ne produit pas de retour au moment de la
        # validation Stock : le retour éventuel se décide à la clôture.
        # La règle métier est centralisée sur la demande concernée.
        for line in self:
            request = line.request_id
            line.is_sortie_only = bool(
                request and request._closure_uses_complement_quantities()
            )

    @api.depends("request_id.type_intervention")
    def _compute_is_retour_materiel(self):
        for line in self:
            line.is_retour_materiel = (
                line.request_id.type_intervention == "retour_materiel"
            )

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

    # ------------------------------------------------------------------
    # CONTRÔLE DES QUANTITÉS (version 2.15)
    # @api.constrains : méthode appelée automatiquement par Odoo après chaque
    # create() et après chaque write() sur les champs listés. Si elle lève une
    # exception, l'écriture est annulée : rien n'est enregistré en base.
    # Elle s'exécute côté serveur : impossible de la contourner par un import
    # ou un appel RPC, contrairement à un attribut de vue.
    # ------------------------------------------------------------------
    @api.constrains("qty_demandee", "qty_sortie", "qty_installee", "qty_retour")
    def _check_quantities_are_not_negative(self):
        """Refuse toute quantité négative sur une ligne de demande.

        POURQUOI CETTE RÈGLE EXISTE
        Une quantité négative n'a aucun sens métier et provoque deux effets
        graves, tous deux constatés dans le code :

          1. Les mouvements de stock sont filtrés sur « quantité > 0 » :
             une sortie négative ne crée donc AUCUN mouvement, mais la
             demande peut tout de même être validée puis clôturée. On obtient
             une DSS officiellement approuvée qui n'a jamais bougé de stock.

          2. La clôture impose « 0 <= quantité saisie <= quantité sortie ».
             Si la quantité sortie est négative, aucune valeur ne peut
             satisfaire cette condition : la demande devient impossible à
             clôturer et exige une correction manuelle en base.

        CHOIX DE CONCEPTION : >= 0 ET NON > 0
        On se limite ici au SIGNE. Exiger « > 0 » empêcherait l'utilisateur
        d'ajouter une ligne vide puis de la remplir, puisque la contrainte
        s'exécute dès la création de la ligne. L'exigence d'une quantité
        réellement exploitable est vérifiée plus tard, à la soumission, par
        dss.request._check_lines_have_positive_quantity(), qui connaît le
        type d'intervention et peut donc choisir le bon champ.

        PRÉCISION
        float_compare(..., precision_digits=2) compare avec deux décimales,
        comme partout dans le module : -0.001 est ainsi traité comme zéro
        et ne bloque pas la saisie pour un simple arrondi.
        """
        # On parcourt chaque ligne pour identifier précisément la fautive.
        for line in self:
            # Les quatre quantités métier suivent la même règle de signe.
            for field_name in (
                "qty_demandee",
                "qty_sortie",
                "qty_installee",
                "qty_retour",
            ):
                # line[champ] lit la valeur courante, y compris non stockée.
                value = line[field_name]
                # Une valeur inférieure à zéro est refusée.
                if float_compare(value, 0.0, precision_digits=2) < 0:
                    # _fields[...].string renvoie le libellé du champ
                    # (« Qte Demandee », etc.) : le message reste lisible.
                    raise ValidationError(
                        u"La quantité « %s » ne peut pas être négative "
                        u"pour l'article %s (valeur saisie : %s)."
                        % (
                            line._fields[field_name].string,
                            line.product_id.name or u"sans article",
                            value,
                        )
                    )