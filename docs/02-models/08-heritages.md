# Extensions des modèles Odoo

## 1. Modèles étendus

| Modèle standard | Fichier | Modification déclarée |
|---|---|---|
| `product.product` | [`product_product.py`](../../models/product_product.py) | Surcharge `name_search()` pour filtrer les articles par `dss_location_id` lorsqu'il est fourni. |
| `product.template` | [`product_template.py`](../../models/product_template.py) | Ajoute `dss_standard_qty`, flottant avec défaut `0.0`. |
| `stock.picking` | [`stock_picking.py`](../../models/stock_picking.py) | Ajoute des champs DSS, un second workflow et `check_dss_ecart()`. |
| `stock.immediate.transfer` | [`stock_picking.py`](../../models/stock_picking.py) | Surcharge `process()` pour contrôler les écarts avant le `super()`. |
| `dss.request.line` | [`dss_request_display.py`](../../models/dss_request_display.py) | Ajoute `is_magasin_user`, calculé et non stocké. |
| `dss.request` | `dss_request_workflow.py`, `dss_request_stock.py`, `dss_request_bon_livraison.py`, `dss_notification.py` | Répartit les actions de workflow, stock, PDF et notifications. |

## 2. Différence entre `_inherit` et `_name`

Les extensions indiquées utilisent `_inherit` sans déclarer un nouveau `_name`: elles modifient le modèle existant. Les modèles comme `dss.request` et `dss.request.line` sont, eux, déclarés avec leur propre `_name` dans leurs fichiers de base.

## 3. Surcharges et particularités constatées

| Méthode ou champ | Comportement |
|---|---|
| `product.product.name_search()` | Ajoute un domaine `id in product_ids` si `dss_location_id` existe dans le contexte; sans ce contexte, délègue le filtrage standard. |
| `stock.picking.create()` | Attribue la séquence `dss.number` si `dss_number` n'est pas fourni. |
| `stock.immediate.transfer.process()` | Appelle `self.pick_id.check_dss_ecart()` avant le traitement standard. |
| `dss.request.line.is_magasin_user` | Calcule l'appartenance de l'utilisateur courant au groupe Magasin; champ non stocké. |

Le workflow de `stock.picking` est distinct du workflow principal `dss.request`; ses limites sont relevées dans [l'intégration Stock](../06-integrations/00-stock.md).

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Extension | `_inherit` seul étend un modèle existant. |
| Pas de nouvelle entité | Les extensions ne créent pas un nouveau modèle métier simplement parce qu'elles sont dans un fichier séparé. |
| `stock.picking` | Son circuit DSS parallèle ne doit pas être confondu avec la validation Stock de `dss.request`. |