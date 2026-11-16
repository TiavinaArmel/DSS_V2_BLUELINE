# Modèle `dss.request.line`

## 1. Rôle

Chaque enregistrement `dss.request.line` décrit un article et les quantités suivies dans une demande. Le modèle est défini dans `models/dss_request_line.py`.

## 2. Relation avec `dss.request`

```text
dss.request.line.request_id (Many2one) -> dss.request
dss.request.line_ids (One2many) -> dss.request.line
```

`request_id` porte `ondelete='cascade'`; la relation est inverse de `line_ids` sur la demande.

## 3. Champs

| Champ | Type | Calculé | Description |
|---|---|---|---|
| `request_id` | `Many2one` | Non | Demande parente; suppression en cascade. |
| `product_id` | `Many2one(product.product)` | Non | Article; `required=True`. |
| `qty_standard` | `Float` | Oui, stocké | Somme des `stock.quant.qty` de l'article dans l'emplacement exact de la demande; vaut `0.0` sans article ou sans emplacement. |
| `qty_demandee` | `Float` | Non | Quantité demandée. |
| `qty_sortie` | `Float` | Non | Quantité effectivement sortie ou déplacée par le flux DSS. |
| `qty_installee` | `Float` | Non | Quantité déclarée installée lors de la clôture. |
| `qty_retour` | `Float` | Non | Quantité retournée; utilisée à la clôture pour une sortie seule et au mouvement Stock selon les autres sens. |
| `is_sortie_only` | `Boolean` | Oui, non stocké | Vrai pour les interventions dont la clôture calcule une quantité à partir de l'autre : sens `Sortie`, sens `Transfert` et `depannage`. Verrouille l'installation et le retour hors wizard de clôture. |
| `is_retour_materiel` | `Boolean` | Oui, non stocké | Vrai pour l'intervention « Retour de matériel »; distingue la quantité retournée des champs de sortie/installation. |
| `motif_ecart` | `Text` | Non | Motif de l'écart saisi par article lorsque la quantité sortie diffère de la quantité demandée. |
| `observation` | `Char` | Non | Texte d'observation affiché notamment sur le BL. |
| `qty_demandee_readonly` | `Boolean` | Non | Indicateur lu par la vue pour verrouiller la quantité demandée. |

## 4. Méthodes de calcul et onchange

| Méthode | Déclencheur | Effet |
|---|---|---|
| `_compute_qty_standard` | `@api.depends('product_id', 'request_id.location_id')` | Somme le stock de l'article dans l'emplacement exact, sans inclure les sous-emplacements; vaut `0.0` si l'article ou l'emplacement manque. Le champ est déclaré `store=True`. |
| `_compute_is_sortie_only` | `@api.depends('request_id.sens_mouvement', 'request_id.type_intervention')` | Active les règles de clôture calculée : sens `Sortie`, sens `Transfert` et `depannage`. La règle est centralisée dans `dss.request._closure_uses_complement_quantities()`. |
| `_onchange_product_id_qty_demandee_readonly` | `@api.onchange('product_id')` | Si la ligne a une demande parente, reflète le type `retour_materiel` dans `qty_demandee_readonly`. |

Le modèle parent met également à jour cet indicateur lors du changement du type d'intervention. L'`onchange` agit sur le formulaire; il ne constitue pas à lui seul une contrainte de sécurité serveur.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Relation | Une demande possède plusieurs lignes; chaque ligne pointe vers un seul article. |
| Disponibilité locale | `qty_standard` est calculé depuis `stock.quant` avec `location_id = request_id.location_id`; les sous-emplacements sont exclus. |
| Quantités | Pour les sorties seules, l'approvisionnement distant et le dépannage, installation et retour sont saisis à la clôture, l'un étant calculé à partir de l'autre; un retour positif est remis à l'emplacement source. Le basculement conserve sa saisie manuelle. La demande initiale n'est pas écrasée par le wizard. |
| Retour de matériel | `qty_retour` est la seule quantité métier; les quantités demandée, sortie et installée sont normalisées à zéro à la soumission et à la validation Stock. |
| Source | [`models/dss_request_line.py`](../../models/dss_request_line.py). |