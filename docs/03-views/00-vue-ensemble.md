# Vue d'ensemble des vues

## 1. Inventaire

| Fichier | Type de contenu | Modèle ou cible |
|---|---|---|
| `dss_request_views.xml` | Formulaire, liste, action fenêtre et vue héritée | `dss.request` |
| `dss_request_search_views.xml` | Recherche, filtres et regroupements | `dss.request` |
| `dss_request_display_views.xml` | Vue formulaire héritée pour l'affichage des lignes | `dss.request` / `dss.request.line` |
| `dss_qty_sortie_wizard_views.xml` | Formulaire modal | `dss.qty.sortie.wizard` |
| `dss_cloture_wizard_views.xml` | Formulaire modal | `dss.cloture.wizard` |
| `dss_rejet_wizard_views.xml` | Formulaire modal | `dss.rejet.wizard` |
| `dss_validation_wizard_views.xml` | Deux formulaires modaux | Wizards de validation Chef et Stock |
| `dss_menu.xml` | Menu DSS et action générique | Application DSS |
| `dss_group_menus.xml` | Actions et menus conditionnés par groupe | `dss.request` |
| `assets_backend.xml` | Extension du bundle CSS Web | `web.assets_backend` |

Le module utilise des vues Form, Tree et Search ainsi que des formulaires de wizard. Aucun type Kanban, Calendar ou Gantt n'est déclaré dans ces fichiers.

## 2. Formulaire principal

La vue de demande comprend l'en-tête d'actions, les informations administratives, l'onglet Articles et le chatter. Les boutons sont documentés dans [la fiche formulaire](01-vues-form.md); les champs des lignes utilisent le modèle [`dss.request.line`](../02-models/02-dss-request-line.md).

## 3. Assets

| Asset | Déclaration | Cible |
|---|---|---|
| `dss_chatter.css` | `views/assets_backend.xml` | Bundle `web.assets_backend`. |
| `report_bl.css` | `report/dss_report.xml` | Bundle commun des rapports. |

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Vues principales | `dss_request_views.xml` contient le formulaire et la liste de `dss.request`. |
| Recherche | Les filtres sont dans `dss_request_search_views.xml`; ils ne remplacent pas les ACL. |
| Assistants | Chaque wizard utilisé par un bouton possède une vue XML dédiée, sauf le modèle d'approbation absent non utilisé par la vue. |
| Source | [`views/`](../../views/), [`report/dss_report.xml`](../../report/dss_report.xml). |