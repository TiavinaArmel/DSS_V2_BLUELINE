# Vue liste des demandes

## 1. Structure

La vue `view_dss_request_tree` est une liste du modèle `dss.request`. Elle trie les enregistrements selon `id desc` par défaut.

## 2. Colonnes affichées

| Champ | Type de donnée lié | Rôle dans la liste |
|---|---|---|
| `name` | Numéro DSS | Identifie la demande. |
| `partner_id` | Partenaire | Affiche le client. |
| `type_intervention` | Sélection | Résume la catégorie de l'intervention. |
| `sens_mouvement` | Champ calculé | Indique le sens de stock résultant. |
| `state` | Sélection | Affiche l'état courant. |

## 3. Décorations et widgets

La définition de la vue Tree ne contient pas d'attribut `decoration-*` ni de widget spécifique aux colonnes. Les filtres de recherche et les regroupements sont détaillés dans [la vue Search](03-vues-search.md).

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Modèle | `dss.request`. |
| Ordre | `id desc`. |
| Colonnes | Numéro, client, type, sens et état. |
| Source | [`views/dss_request_views.xml`](../../views/dss_request_views.xml). |