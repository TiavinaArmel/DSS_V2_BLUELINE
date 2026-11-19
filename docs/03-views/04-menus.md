# Menus et actions DSS

## 1. Structure des menus

| Menu | Parent | Groupe requis | Action et filtre |
|---|---|---|---|
| DSS | Racine | Aucun groupe indiqué | Menu racine. |
| Demandes | DSS | Aucun groupe indiqué | Action générique `action_dss_request`, vues `tree,form`. |
| Mes demandes | DSS | Demandeur | Domaine OR : `demandeur_id = uid` ou `create_uid = uid`. |
| À valider | DSS | Chef | Active par défaut le filtre `chef_filter_a_valider`. |
| À valider Stock | DSS | Magasin | Active par défaut le filtre `magasin_filter_a_valider_stock`. |
| À remettre | DSS | Magasin | Active par défaut le filtre `magasin_filter_approuvees_a_remettre`. |
| Demandes approuvées | DSS | Sécurité | Domaine fixe `state = approuve`. |

## 2. Menu par groupe

Les actions Chef et Magasin définissent `search_default_*` dans leur contexte : elles préactivent un filtre de recherche retirable depuis l'interface. À l'inverse, l'action Sécurité définit un `domain`; ce domaine fait partie de l'action et sert de filtre de liste.

Le menu « Demandes approuvées » est un **raccourci de consultation** : le modèle `dss.request` ne définit ni état ni action de validation Sécurité. Il s'appelait « À contrôler » jusqu'à la version `2.17`, ce qui laissait croire à une validation attendue ; le libellé a été corrigé en `2.18`.

## 3. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Menus | Les déclarations se trouvent dans `dss_menu.xml` et `dss_group_menus.xml`. |
| Actions | Les menus réutilisent l'action et les vues de `dss.request`. |
| Sécurité | Un menu ou un domaine d'action n'est pas un substitut aux ACL et record rules. |
| Source | [`views/dss_menu.xml`](../../views/dss_menu.xml), [`views/dss_group_menus.xml`](../../views/dss_group_menus.xml). |