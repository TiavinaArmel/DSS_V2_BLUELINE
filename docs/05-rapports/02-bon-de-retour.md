# Bon de retour : état de l'implémentation(en cours de validation, pas encore conçue dans cet projet )

## 1. État dans les sources

Le module suit une quantité `qty_retour` sur les lignes et peut créer un mouvement entrant vers `location_id` lorsque le sens calculé est `Entree`. En revanche, les fichiers audités ne déclarent ni un modèle de demande de retour séparé, ni un champ `dss_source_id`, ni un rapport QWeb « Bon de retour » distinct.

## 2. Fonctionnalités présentes et absentes

| Sujet | État constaté |
|---|---|
| Quantité retournée sur une ligne DSS | Présente : `dss.request.line.qty_retour`. |
| Mouvement de stock entrant | Présent dans `_generer_mouvement_entree()`; les lignes avec `qty_retour > 0` sont utilisées. |
| Colonne retour dans le BL | Présente dans le tableau du rapport de livraison. |
| Demande de retour autonome liée à une DSS source clôturée | Non déclarée dans les modèles audités. |
| Rapport PDF autonome de bon de retour | Non déclaré dans `report/dss_report.xml`. |
| Contraintes `_check_dss_source` ou `_check_qty_retour` | Non trouvées dans les modèles audités. |

Le titre « Bon de retour » du cahier de charge est donc un besoin documentaire ou futur, pas une fonction à présenter comme déjà disponible.

## 3. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Retour de matériel | Il existe comme type d'intervention et comme quantité suivie dans le flux DSS. |
| Document distinct | Aucun modèle ou rapport autonome de retour n'est déclaré dans l'état audité. |
| Vérification | Réévaluer cette fiche si un modèle ou rapport de retour est ajouté. |