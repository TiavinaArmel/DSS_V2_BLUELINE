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
| `qty_standard` | `Float` | Oui, stocké | Copie `product_id.qty_available`; vaut `0.0` sans article. |
| `qty_demandee` | `Float` | Non | Quantité demandée. |
| `qty_sortie` | `Float` | Non | Quantité effectivement sortie ou déplacée par le flux DSS. |
| `qty_installee` | `Float` | Non | Quantité déclarée installée lors de la clôture. |
| `qty_retour` | `Float` | Non | Quantité de retour utilisée par le mouvement entrant. |
| `observation` | `Char` | Non | Texte d'observation affiché notamment sur le BL. |
| `qty_demandee_readonly` | `Boolean` | Non | Indicateur lu par la vue pour verrouiller la quantité demandée. |

## 4. Méthodes de calcul et onchange

| Méthode | Déclencheur | Effet |
|---|---|---|
| `_compute_qty_standard` | `@api.depends('product_id')` | Affecte `product_id.qty_available` ou `0.0`. Le champ est déclaré `store=True`. |
| `_onchange_product_id_qty_demandee_readonly` | `@api.onchange('product_id')` | Si la ligne a une demande parente, reflète le type `retour_materiel` dans `qty_demandee_readonly`. |

Le modèle parent met également à jour cet indicateur lors du changement du type d'intervention. L'`onchange` agit sur le formulaire; il ne constitue pas à lui seul une contrainte de sécurité serveur.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Relation | Une demande possède plusieurs lignes; chaque ligne pointe vers un seul article. |
| Stock standard | `qty_standard` vient de `product.product.qty_available`, pas de `dss_standard_qty`. |
| Quantités | Sortie, installation et retour sont des champs distincts utilisés à des étapes différentes. |
| Source | [`models/dss_request_line.py`](../../models/dss_request_line.py). |