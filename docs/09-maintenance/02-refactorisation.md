# Organisation du code

## 1. Répartition actuelle

| Responsabilité | Fichier |
|---|---|
| Champs d'en-tête, calcul du sens et création numérotée | `models/dss_request.py` |
| Lignes d'articles et quantité standard | `models/dss_request_line.py` |
| Actions du workflow principal | `models/dss_request_workflow.py` |
| Mouvements stock de sortie, entrée et transfert | `models/dss_request_stock.py` |
| Rapport PDF et pièce jointe | `models/dss_request_bon_livraison.py` |
| Notifications et journal | `models/dss_notification.py` |
| Wizards | `models/dss_*_wizard.py` |
| Extensions des modèles standard | `models/product_product.py`, `product_template.py`, `stock_picking.py` |

## 2. Chargement des extensions

`models/__init__.py` importe les modules Python. L'ordre actuel charge notamment les modèles standards étendus, puis `dss.request`, sa ligne et ses extensions stock, BL, workflow et notification, avant les assistants et le modèle d'affichage.

Les relations entre modèles utilisent leurs noms techniques Odoo; les classes d'extension de `dss.request` déclarent `_inherit = 'dss.request'`. Toute modification de l'ordre d'import ou d'un nom technique doit être vérifiée contre le manifeste, les vues, les wizards, le rapport et les ACL.

## 3. Vérifications lors d'une modification

| Zone touchée | Vérifications de régression utiles |
|---|---|
| Workflow | États et boutons visibles, rôles, messages chatter, destinataires et erreurs d'état. |
| Stock | Sens de mouvement, emplacements, unités, quantités, pickings et état final. |
| Lignes | Champs affichés, onchange, quantités copiées dans les wizards et le rapport. |
| Rapport | XML QWeb, paperformat, CSS, pièce jointe et impression manuelle. |
| Notifications | Template, clé d'événement, déduplication et tests de routage. |

Cette page décrit l'organisation actuellement observée; elle ne certifie pas les étapes historiques de la refactorisation.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Modules Python | L'ordre effectif de chargement est `models/__init__.py`. |
| API exposée | Les noms de modèles, champs et méthodes référencés par les vues/XML forment des dépendances à préserver. |
| Vérification | Un test ciblé et un démarrage/mise à jour sur l'environnement Odoo sont nécessaires pour valider un changement de comportement. |