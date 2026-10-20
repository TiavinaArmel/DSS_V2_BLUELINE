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

## 2. Séquence de `stock.picking`

L'extension `stock.picking.create()` demande aussi une valeur à `next_by_code('dss.number')` si `dss_number` n'est pas fourni. Aucune séquence avec le code `dss.number` n'apparaît dans les fichiers de données de `dss_v2`; sa définition doit donc provenir d'une autre donnée ou installation si ce chemin est utilisé.

## 3. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Demande | La séquence `dss.request` fournit les numéros `DSS-` suivis d'au moins cinq chiffres. |
| Picking | Le code attend le code de séquence distinct `dss.number`. |
| `noupdate` | La déclaration de séquence demande à Odoo de ne pas réinitialiser ses valeurs à chaque mise à jour du module. |
| Sources | [`dss_sequence.xml`](../../data/dss_sequence.xml), [`dss_request.py`](../../models/dss_request.py), [`stock_picking.py`](../../models/stock_picking.py). |