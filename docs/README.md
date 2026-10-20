# Documentation du module DSS V2

## 1. Présentation rapide

DSS V2 est un module Odoo de gestion des demandes de sortie de stock : saisie d'articles, validations Chef et Stock, mouvements Odoo, suivi dans le chatter et génération d'un bon de livraison PDF. Le manifeste indique la version `2.4`; le `README.md` du module cible Odoo 10 Community. Le cahier de projet mentionne Python 2.7 et PostgreSQL, mais le manifeste ne fixe pas la version de Python.

## 2. Prérequis

| Élément | État selon les fichiers du module |
|---|---|
| Odoo | Odoo 10 indiqué dans le README du module. |
| Python | Version non déclarée dans le manifeste; vérifier l'interpréteur de l'instance Odoo 10 déployée. |
| PostgreSQL | Base utilisée par Odoo; aucune version n'est fixée par le module. |
| wkhtmltopdf | Nécessaire au rendu PDF Odoo; aucune version n'est imposée par le manifeste. |
| Less | Aucun fichier Less propre à `dss_v2` n'a été recensé; le module livre des fichiers CSS. |

Les dépendances Odoo déclarées sont `web`, `stock` et `mail`.

## 3. Installation rapide

1. Placer le dossier `dss_v2` dans un chemin d'addons reconnu par l'instance Odoo.
2. Vérifier que ce chemin figure dans `addons_path` de la configuration Odoo.
3. Redémarrer Odoo et actualiser la liste des applications en mode développeur.
4. Rechercher « DSS V2 - Demande de Sortie de Stock » puis installer le module.
5. Pour mettre à jour une installation existante, utiliser la commande Odoo adaptée à l'environnement et à la base cible.

Exemple de mise à jour, à adapter au chemin réel de l'exécutable et à la base :

```bash
python odoo-bin -c odoo.conf -d NOM_DE_LA_BASE -u dss_v2
```

## 4. Sommaire complet

| Catégorie | Documentation |
|---|---|
| Général | [Glossaire](00-glossaire.md), [architecture et sécurité](01-architecture-et-securite.md) |
| Modèles | [Vue d'ensemble](02-models/00-vue-ensemble.md), [`dss.request`](02-models/01-dss-request.md), [lignes](02-models/02-dss-request-line.md), [workflow](02-models/03-dss-request-workflow.md), [stock](02-models/04-dss-request-stock.md), [bon de livraison](02-models/05-dss-request-bon-de-livraison.md), [notifications](02-models/06-dss-notifications.md), [wizards](02-models/07-wizards.md), [héritages](02-models/08-heritages.md) |
| Vues | [Vue d'ensemble](03-views/00-vue-ensemble.md), [formulaire](03-views/01-vues-form.md), [liste](03-views/02-vues-tree.md), [recherche](03-views/03-vues-search.md), [menus](03-views/04-menus.md) |
| Workflow | [Cycle de vie](04-workflow/00-cycle-de-vie.md), [soumission](04-workflow/01-soumission.md), [validation Chef](04-workflow/02-validation-chef.md), [validation Stock](04-workflow/03-validation-magasin.md), [rejet et clôture](04-workflow/04-rejet-et-cloture.md) |
| Rapports | [Vue d'ensemble](05-rapports/00-vue-ensemble.md), [bon de livraison](05-rapports/01-bon-de-livraison.md), [bon de retour](05-rapports/02-bon-de-retour.md) |
| Intégrations | [Stock](06-integrations/00-stock.md), [courriels et SMTP](06-integrations/01-email-smtp.md), [séquence](06-integrations/02-sequence.md) |
| Sécurité | [Groupes](07-securite/00-groupes.md), [droits CRUD](07-securite/01-droits-crud.md), [règles d'enregistrement](07-securite/02-regles-enregistrement.md) |
| Tests | [Notifications](08-tests/00-tests-notifications.md) |
| Maintenance | [Dépannage](09-maintenance/00-depannage.md), [migrations](09-maintenance/01-migrations.md), [organisation du code](09-maintenance/02-refactorisation.md) |
| Historique | [Versions](10-historique-des-versions.md) |

## 5. Conventions

| Sujet | Convention documentée |
|---|---|
| Fichiers de documentation | Préfixe numérique, sujet en minuscules et tirets; pas d'accent dans le nom du fichier. |
| Titres | Un titre H1, sections H2 numérotées et fiche de mémorisation finale. |
| Faits techniques | Décrire le code réellement présent; signaler explicitement une fonction absente ou non vérifiée. |
| Liens | Employer des chemins Markdown relatifs. |
| Git | Le README racine propose des branches `feature/` et un exemple de commit `feat:`; ces exemples ne sont pas imposés par le code. |

## 6. Contacts

| Rôle | Information disponible |
|---|---|
| Auteur du module | Tiavina Armel, selon `__manifest__.py`. |
| Encadreur | Non indiqué dans les fichiers du module audités. |
| Mise à jour de cet index | 2026-10-16. |

## 7. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Entrée de lecture | Commencer par cette page, puis suivre la catégorie recherchée. |
| Code | Les liens vers les sources permettent de vérifier chaque comportement décrit. |
| Limites | « Prévu », « présent » et « testé » sont des statuts différents dans ces documents. |