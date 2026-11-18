# -*- coding: utf-8 -*-
"""Fichier neutralisé — le champ « Quantité standard DSS » a été retiré en 2.16.

CE QU'IL CONTENAIT AVANT
    Une extension du modèle Odoo `product.template` ajoutant le champ
    `dss_standard_qty` (« Quantite standard DSS »), destiné à servir de valeur
    de référence au contrôle d'écart du circuit DSS parallèle.

POURQUOI IL A ÉTÉ RETIRÉ
    Ce champ n'avait qu'un seul lecteur : `check_dss_ecart()`, dans le fichier
    stock_picking.py, lui-même retiré. Il n'était affiché sur aucun écran et
    aucun article de la base ne l'utilisait (0 sur 39 renseigné).

    Le concept de quantité standard faisait par ailleurs doublon avec la
    quantité demandée de la ligne DSS (`qty_demandee`), qui porte déjà la
    référence métier de l'écart.

CE FICHIER N'EST PLUS CHARGÉ
    `models/__init__.py` ne l'importe plus : son contenu n'est jamais exécuté.
    Suppression physique possible depuis un poste :

        Remove-Item C:\\ODOO_10_DEV\\custom-addons\\dss_v2\\models\\product_template.py

    La colonne `dss_standard_qty` subsiste en base, mais plus aucun code ne la lit.
"""
