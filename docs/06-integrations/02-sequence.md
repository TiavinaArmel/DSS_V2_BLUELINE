# Séquences de numérotation

## 1. Séquence des demandes

La séquence `dss.request` est déclarée dans `data/dss_sequence.xml` avec `noupdate="1"`.

| Paramètre | Valeur |
|---|---|
| Identifiant XML | `dss_v2.seq_dss_request` |
| Code | `dss.request` |
| Préfixe | `DSS-` |
| Padding | 5 chiffres |
| Prochain numéro initial | 1 |
| Incrément | 1 |

`DssRequest.create()` appelle `ir.sequence.next_by_code('dss.request')` lorsque le nom fourni vaut `/` ou est absent. Le module ne déclare pas de contrainte SQL d'unicité sur `name`.

## 2. Séquence de `stock.picking` : supprimée en 2.16

Jusqu'à la version `2.15`, `stock.picking.create()` demandait une valeur à `next_by_code('dss.number')` pour alimenter le champ `dss_number`. Aucune séquence de ce code n'a jamais été déclarée : le champ valait donc `/` sur tous les transferts.

Ce mécanisme appartenait au circuit DSS parallèle, retiré en `2.16`. Le code n'appelle plus aucune séquence sur les transferts, et la seule séquence du module reste `dss.request`.

## 3. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Demande | La séquence `dss.request` fournit les numéros `DSS-` suivis d'au moins cinq chiffres. |
| Picking | Aucune séquence DSS n'est plus demandée à la création d'un transfert depuis 2.16. |
| `noupdate` | La déclaration de séquence demande à Odoo de ne pas réinitialiser ses valeurs à chaque mise à jour du module. |
| Sources | [`dss_sequence.xml`](../../data/dss_sequence.xml), [`dss_request.py`](../../models/dss_request.py). |