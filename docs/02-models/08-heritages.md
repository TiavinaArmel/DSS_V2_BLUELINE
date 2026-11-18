# Extensions des modèles Odoo

## 1. Modèles étendus (version 2.16)

| Modèle standard | Fichier | Modification déclarée |
|---|---|---|
| `product.product` | [`product_product.py`](../../models/product_product.py) | Surcharge `name_search()` pour filtrer les articles par `dss_location_id` lorsqu'il est fourni. |
| `dss.request.line` | [`dss_request_display.py`](../../models/dss_request_display.py) | Ajoute `is_magasin_user`, calculé et non stocké. |
| `dss.request` | `dss_request_workflow.py`, `dss_request_stock.py`, `dss_request_bon_livraison.py`, `dss_notification.py` | Répartit les actions de workflow, stock, PDF et notifications. |

**Il n'y a plus aucune extension de `stock.picking`, `stock.immediate.transfer` ni `product.template`.** Le module ne touche donc plus au fonctionnement de l'application Stock en dehors des transferts qu'il crée lui-même.

## 2. Suppression du circuit DSS parallèle (version 2.16)

| Fichier | Contenu retiré | Raison |
|---|---|---|
| `stock_picking.py` | Champs `dss_number`, `dss_validation_state`, `dss_justification`, `dss_movement_type`, les cinq méthodes de validation et `check_dss_ecart()` | Second circuit DSS jamais utilisé : aucune vue, aucun menu, aucune séquence, 53 transferts sur 53 restés en brouillon |
| `product_template.py` | Champ `dss_standard_qty` | N'avait qu'un seul lecteur, `check_dss_ecart()`, lui-même retiré ; faisait doublon avec `qty_demandee` |

Le point sensible était `check_dss_ecart()`, branché sur la popup Odoo **« Transfert immédiat ? »** (`stock.immediate.transfer.process()`). Dès qu'une quantité standard aurait été renseignée, il aurait bloqué la validation de n'importe quel transfert de stock, en exigeant un champ visible sur aucun écran.

Les deux fichiers restent sur le disque, **vidés de leur code** et documentés, mais ne sont plus importés par `models/__init__.py` : leur contenu n'est jamais chargé. Les colonnes correspondantes subsistent en base ; plus aucun code ne les lit.

Un test de garde-fou vérifie l'absence de ces champs : [`tests/test_dss_no_parallel_circuit.py`](../../tests/test_dss_no_parallel_circuit.py).

## 3. Différence entre `_inherit` et `_name`

Les extensions indiquées utilisent `_inherit` sans déclarer un nouveau `_name`: elles modifient le modèle existant. Les modèles comme `dss.request` et `dss.request.line` sont, eux, déclarés avec leur propre `_name` dans leurs fichiers de base.

## 4. Surcharges et particularités constatées

| Méthode ou champ | Comportement |
|---|---|
| `product.product.name_search()` | Ajoute un domaine `id in product_ids` si `dss_location_id` existe dans le contexte; sans ce contexte, délègue le filtrage standard. |
| `dss.request.line.is_magasin_user` | Calcule l'appartenance de l'utilisateur courant au groupe Magasin; champ non stocké. |

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Extension | `_inherit` seul étend un modèle existant. |
| Pas de nouvelle entité | Les extensions ne créent pas un nouveau modèle métier simplement parce qu'elles sont dans un fichier séparé. |
| Stock | Le module ne modifie plus `stock.picking` : il crée des transferts standard et les valide. |
| Garde-fou | Un test échoue si les champs du circuit parallèle sont réintroduits. |
