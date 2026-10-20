# Génération des mouvements de stock

## 1. Rôle

L'extension `DssRequestStock` crée les transferts Odoo lors de la validation Stock de `dss.request`. Elle travaille avec `stock.picking`, `stock.move`, `stock.quant`, `stock.location` et `stock.picking.type`.

## 2. Routeur et quantités

| Sens calculé | Méthode | Lignes retenues | Type de picking |
|---|---|---|---|
| `Sortie` | `_generer_mouvement_sortie()` | `qty_sortie > 0` | `outgoing` |
| `Entree` | `_generer_mouvement_entree()` | `qty_retour > 0` | `incoming` |
| `Sortie + Entree` | Sortie puis entrée | Selon chaque méthode | Deux pickings possibles |
| `Transfert` | `_generer_mouvement_transfert()` | `qty_sortie > 0` | `internal` |

Le routeur est dans `action_valider_magasin()`; les types d'intervention et leur sens sont décrits dans [le modèle principal](01-dss-request.md).

## 3. Emplacements et contrôle de quantité

| Mouvement | Source | Destination | Vérification dans le code DSS |
|---|---|---|---|
| Sortie | `location_id` | `partner_id.property_stock_customer`, sinon emplacement client standard | `stock.quant.read_group()` sur `location_id` et `product_id`; compare `qty_sortie` au champ agrégé `qty`. |
| Entrée | Emplacement client du partenaire, sinon emplacement client standard | `location_id` | Pas de contrôle de disponibilité de stock source dans cette méthode. |
| Transfert interne | `location_id` | `location_dest_id` | Destination obligatoire et contrôle `stock.quant.read_group()` de la quantité source. |

La destination du transfert interne est également contrôlée dans la méthode, même si la soumission exige déjà une destination pour `appro_distant`.

## 4. Modèles Odoo utilisés

| Modèle | Utilisation dans le traitement |
|---|---|
| `stock.quant` | Agrège le champ `qty` par emplacement et article avant sortie/transfert. |
| `stock.picking.type` | Recherche un type par code `outgoing`, `incoming` ou `internal`. |
| `stock.picking` | Porte l'en-tête du transfert et ses emplacements. |
| `stock.move` | Un mouvement est créé pour chaque ligne retenue. |
| `stock.location` | Définit les emplacements source et destination. |

## 5. Cycle d'un picking

```text
Créer stock.picking
       |
Créer un stock.move par ligne retenue
       |
action_confirm() -> action_assign() -> action_done()
       |
Mettre à jour dss.request.picking_id
```

Le picking est confirmé, affecté, puis terminé dans chacune des trois méthodes de génération.

## 6. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Sortie/transfert | Utilisent `qty_sortie` et contrôlent la quantité agrégée du stock source. |
| Entrée | Utilise `qty_retour`; aucun contrôle de disponibilité source n'est effectué par cette méthode. |
| Sortie + entrée | Deux appels successifs peuvent créer deux pickings; `picking_id` est réaffecté à chaque appel et ne conserve donc que le dernier lien. |
| Source | [`models/dss_request_stock.py`](../../models/dss_request_stock.py). |