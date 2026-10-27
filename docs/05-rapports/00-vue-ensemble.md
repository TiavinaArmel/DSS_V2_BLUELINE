# Vue d'ensemble des rapports

## 1. Rapports déclarés

| Rapport | Identifiant | Modèle | Format |
|---|---|---|---|
| Bon de Livraison | `dss_v2.report_bon_livraison_document` | `dss.request` | QWeb PDF, format papier A5 paysage. |

Le fichier `report/dss_report.xml` ne déclare pas de rapport séparé pour un bon de retour.

## 2. Format papier

| Identifiant XML | Taille | Orientation | DPI |
|---|---|---|---:|
| `dss_v2.paperformat_dss_a5` | A5 | Landscape | 0 |

Les marges déclarées sont 22 mm en haut, 5 mm en bas et sur les côtés; `header_spacing` vaut 10 mm pour espacer l'en-tête du contenu. La marge supérieure réserve la place du logo et des références dans l'en-tête personnalisé. La compatibilité réelle dépend aussi de la version wkhtmltopdf et de l'environnement Odoo.

## 3. Génération PDF

Le rapport utilise `report.html_container` et le layout QWeb dédié `report_bon_livraison_layout`, sans pied de page standard. Ses styles ciblés sont chargés depuis `static/src/css/report_bl_server.css`. La méthode Python de génération place explicitement l'ID du format papier dans le contexte lorsque le format existe.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Rapport existant | Un BL QWeb PDF sur `dss.request`. |
| Bon de retour | Aucun rapport autonome n'est déclaré; voir [la fiche dédiée](02-bon-de-retour.md). |
| Source | [`report/dss_report.xml`](../../report/dss_report.xml). |