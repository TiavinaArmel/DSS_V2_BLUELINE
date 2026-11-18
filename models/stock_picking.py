# -*- coding: utf-8 -*-
"""Fichier neutralisé — le circuit DSS parallèle a été retiré en version 2.16.

CE QU'IL CONTENAIT AVANT
    Une extension du modèle Odoo `stock.picking` qui ajoutait :
      - des champs DSS propres au transfert : dss_number, dss_validation_state,
        dss_justification, dss_movement_type ;
      - une seconde machine à états (brouillon -> soumis -> valide_chef ->
        valide_magasin -> valide_securite -> approuve) avec ses méthodes de
        validation ;
      - un contrôle d'écart `check_dss_ecart()` branché sur la popup Odoo
        « Transfert immédiat ? » (stock.immediate.transfer).

POURQUOI IL A ÉTÉ RETIRÉ
    Ce circuit n'a jamais été utilisé, ce que la base a confirmé :
      - aucune vue, aucun menu, aucun bouton ne l'exposait ;
      - la séquence `dss.number` n'a jamais existé : tous les numéros valent « / » ;
      - 53 pickings sur 53 sont restés à l'état `brouillon` ;
      - aucune justification d'écart n'a jamais été saisie.

    Un élément restait néanmoins actif : le contrôle branché sur la popup
    « Transfert immédiat ? ». Il pouvait bloquer la validation de n'importe quel
    transfert de stock de l'entreprise dès qu'une « quantité standard » aurait
    été renseignée, en exigeant un champ invisible dans l'interface.

CE FICHIER N'EST PLUS CHARGÉ
    `models/__init__.py` ne l'importe plus : son contenu n'est donc jamais
    exécuté par Odoo. Il ne reste que pour permettre la suppression physique
    depuis un poste, sans risque :

        Remove-Item C:\\ODOO_10_DEV\\custom-addons\\dss_v2\\models\\stock_picking.py

    Les colonnes correspondantes subsistent en base (Odoo ne les supprime pas
    automatiquement), mais plus aucun code ne les lit.
"""
