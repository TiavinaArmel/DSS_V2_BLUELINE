# Intégration avec Stock

## 1. Modèles Odoo utilisés

| Modèle | Rôle dans le code DSS |
|---|---|
| `product.product` | Article de la ligne DSS et unité de mesure du mouvement. |
| `stock.quant` | Quantité `qty` agrégée pour le contrôle de sortie et de transfert. |
| `stock.location` | Emplacement source, destination interne ou emplacement client. |
| `stock.picking.type` | Type de picking recherché par code. |
| `stock.picking` | En-tête du transfert créé. |
| `stock.move` | Mouvement associé à chaque ligne traitée. |

## 2. Types de picking dans le workflow principal

| Code Odoo recherché | Sens DSS | Emplacements |
|---|---|---|
| `outgoing` | Sortie | `location_id` vers l'emplacement client du partenaire ou le repli standard. |
| `incoming` | Entrée | Emplacement client vers `location_id`. |
| `internal` | Transfert | `location_id` vers `location_dest_id`. |

Le code effectue une recherche `limit=1` par code de picking; il ne filtre pas la recherche sur un entrepôt ou une société dans les méthodes présentées.

Pour les interventions `nouvelle_installation`, `installation_interne`, `depannage` **et `appro_distant`**, la quantité retournée est déterminée à la clôture, et non au wizard de quantités Stock. Un picking est alors créé uniquement pour les articles dont `qty_retour > 0` : depuis l'emplacement client du partenaire (ou l'emplacement client standard) vers l'emplacement source original `request.location_id` pour les sorties et le dépannage, et de l'emplacement destination `location_dest_id` vers `request.location_id` pour un approvisionnement distant, avec un type de picking `internal`. Son lien est enregistré dans `picking_retour_cloture_id`; les articles et leur emplacement d'origine sont aussi inscrits dans le chatter et l'e-mail de clôture. Le `basculement` conserve le routeur Stock existant et sa saisie manuelle.

## 3. Contrôle de stock et cycle

Les méthodes de sortie et de transfert agrègent `stock.quant.qty` par produit et emplacement, puis lèvent `ValidationError` si `qty_sortie` dépasse la valeur obtenue. Le mouvement entrant utilise `qty_retour` et ne fait pas ce contrôle de disponibilité.

```text
DSS line_ids
  `-- lignes dont la quantité correspondante est positive
        `-- stock.picking + stock.move par ligne
              `-- action_confirm()
                    `-- action_assign()
                          `-- action_done()
```

## 4. Circuit DSS parallèle : retiré en 2.16

Jusqu'à la version `2.15`, `models/stock_picking.py` ajoutait au transfert de stock ses propres champs DSS, une seconde machine à états (`brouillon` → `soumis` → `valide_chef` → `valide_magasin` → `valide_securite` → `approuve`) et un contrôle d'écart branché sur la popup Odoo « Transfert immédiat ? ».

Ce circuit n'a jamais été utilisé, ce que la base a confirmé : aucune vue ni aucun menu ne l'exposait, la séquence `dss.number` n'existait pas (tous les numéros valaient `/`) et les 53 transferts étaient restés à l'état `brouillon`. Un seul élément restait actif : le contrôle d'écart, qui pouvait bloquer la validation de n'importe quel transfert de stock dès qu'une « quantité standard » aurait été renseignée, en exigeant un champ visible sur aucun écran.

Le circuit a donc été retiré en `2.16` : les fichiers sont neutralisés et ne sont plus importés, aucune extension de `stock.picking` ni de `product.template` ne subsiste, et un test de garde-fou empêche leur réintroduction. Les colonnes restent en base mais plus aucun code ne les lit.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Flux principal | Les méthodes de `dss.request` créent et terminent les pickings. |
| Retour de clôture | Les sorties seules, les approvisionnements distants et le dépannage réintègrent les quantités retournées à l'emplacement source après l'intervention. |
| Contrôle de quantité | Présent avant sortie et transfert; pas dans la méthode d'entrée. |
| Circuit secondaire | Retiré en 2.16 : le module ne modifie plus le comportement de l'application Stock. |
| Sources | [`dss_request_stock.py`](../../models/dss_request_stock.py). |