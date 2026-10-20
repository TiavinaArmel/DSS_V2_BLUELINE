# Vue d'ensemble des modèles

## 1. Modèles et extensions

| Modèle | Fichier | Type | Rôle constaté |
|---|---|---|---|
| `dss.request` | [`dss_request.py`](../../models/dss_request.py) | Modèle persistant | En-tête, champs métier, états et numérotation d'une demande. |
| `dss.request.line` | [`dss_request_line.py`](../../models/dss_request_line.py) | Modèle persistant | Article et quantités d'une demande. |
| `dss.request` (extension workflow) | [`dss_request_workflow.py`](../../models/dss_request_workflow.py) | `_inherit` | Soumission, validations, rejet, renvoi et ouverture des wizards. |
| `dss.request` (extension stock) | [`dss_request_stock.py`](../../models/dss_request_stock.py) | `_inherit` | Génération des pickings et mouvements. |
| `dss.request` (extension BL) | [`dss_request_bon_livraison.py`](../../models/dss_request_bon_livraison.py) | `_inherit` | Génération, rattachement et impression du PDF. |
| `dss.request` (extension notification) | [`dss_notification.py`](../../models/dss_notification.py) | `_inherit` | Routage des courriels métier. |
| `dss.notification.log` | [`dss_notification.py`](../../models/dss_notification.py) | Modèle persistant | Journal et déduplication des notifications par demande/événement. |
| `dss.request.line` (extension d'affichage) | [`dss_request_display.py`](../../models/dss_request_display.py) | `_inherit` | Champ calculé `is_magasin_user` utilisé par une vue. |
| `dss.rejet.wizard` | [`dss_rejet_wizard.py`](../../models/dss_rejet_wizard.py) | `TransientModel` | Saisie obligatoire du motif avant rejet. |
| `dss.qty.sortie.wizard` et `.line` | [`dss_qty_sortie_wizard.py`](../../models/dss_qty_sortie_wizard.py) | `TransientModel` | Copie temporaire pour ajuster sortie et retour. |
| `dss.cloture.wizard` et `.line` | [`dss_cloture_wizard.py`](../../models/dss_cloture_wizard.py) | `TransientModel` | Saisie des quantités installées/retournées et clôture. |
| `dss.validation.chef.wizard` et `dss.validation.stock.wizard` | [`dss_validation_wizard.py`](../../models/dss_validation_wizard.py) | `TransientModel` | Confirmation avant les validations Chef et Stock. |
| `product.product` | [`product_product.py`](../../models/product_product.py) | Extension | Filtre les articles proposés si le contexte contient `dss_location_id`. |
| `product.template` | [`product_template.py`](../../models/product_template.py) | Extension | Ajoute `dss_standard_qty`. |
| `stock.picking` | [`stock_picking.py`](../../models/stock_picking.py) | Extension | Ajoute des champs et un workflow DSS distinct. |
| `stock.immediate.transfer` | [`stock_picking.py`](../../models/stock_picking.py) | Extension de `TransientModel` | Vérifie les écarts avant le traitement natif du transfert immédiat. |

## 2. Relations principales

```text
dss.request
|-- line_ids (One2many) -> dss.request.line
|   `-- product_id -> product.product
|-- partner_id -> res.partner
|-- location_id -> stock.location
|-- location_dest_id -> stock.location
|-- picking_id -> stock.picking
`-- signataires -> res.users

Wizards temporaires -> dss.request / dss.request.line
dss.notification.log -> dss.request + mail.mail
```

## 3. Découpage par responsabilité

| Fichier | Responsabilité |
|---|---|
| `dss_request.py` | Déclaration des champs d'en-tête, calcul du sens et numéro de séquence. |
| `dss_request_line.py` | Champs et calculs de ligne. |
| `dss_request_workflow.py` | Transitions, messages chatter et ouverture des assistants. |
| `dss_request_stock.py` | Mouvements sortants, entrants et internes. |
| `dss_request_bon_livraison.py` | Rapport PDF et pièce jointe. |
| `dss_notification.py` | Journal et notifications par e-mail. |
| `dss_request_display.py` | Indicateur utilisateur calculé pour la vue. |

L'ordre des imports est défini dans [`models/__init__.py`](../../models/__init__.py). Les extensions se rattachent aux modèles par leur nom technique Odoo; elles ne créent pas toutes une nouvelle table.

## 4. Convention de nommage

Les modèles propres à DSS utilisent des noms techniques `dss.*`. Les assistants se déclarent avec `models.TransientModel`. Une classe d'extension utilise `_inherit` seul lorsqu'elle ajoute un comportement à un modèle déjà déclaré. Les modèles standards `product.product`, `product.template`, `stock.picking` et `stock.immediate.transfer` sont étendus, pas recréés.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| En-tête et lignes | `dss.request` et `dss.request.line` sont deux modèles persistants liés par One2many/Many2one. |
| Extensions | Le workflow, le stock, le BL et les notifications étendent `dss.request` dans des fichiers distincts. |
| État distinct | L'extension `stock.picking` possède ses propres champs DSS et ne constitue pas le workflow de `dss.request`. |