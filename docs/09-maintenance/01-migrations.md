# Migrations de données

## 1. Rôle du dossier

Le module contient des scripts de migration dans `migrations/2.2/`, `migrations/2.5/` et `migrations/2.6/`.

## 2. Script présent

| Chemin | Fonction constatée |
|---|---|
| `migrations/2.2/pre-rename-paperformat-xmlid.py` | Renomme dans `ir_model_data` l'identifiant externe `dss_v2.paperformat_dss_a4` en `dss_v2.paperformat_dss_a5` si le nouvel identifiant n'existe pas déjà. |
| `migrations/2.5/pre-migration.py` | Prépare le modèle `dss.service`, transfère conditionnellement les départements et affiliations demandeurs depuis les anciennes tables RH si elles existent, et archive les anciennes vues de département. Les demandeurs déjà liés à un service ne sont pas affectés à un second service. |
| `migrations/2.6/pre-migration.py` | Supprime les affiliations multiples en conservant le service au plus petit identifiant, ajoute l'unicité de `user_id` et renseigne `demandeur_id` depuis le signataire historique ou le créateur. La migration interrompt l'upgrade si le propriétaire ne peut pas être retrouvé. |

La requête SQL cible le module `dss_v2` et le modèle `report.paperformat`. Elle ne crée pas un deuxième format papier; elle modifie le nom de l'identifiant externe existant. Si l'identifiant cible existe déjà, la condition `NOT EXISTS` empêche le renommage.

## 3. Version et exécution

Le manifeste indique actuellement la version `2.18`. Les scripts `2.5`, `2.6` et `2.18` modifient des données et des contraintes de base; sauvegarder la base et vérifier les journaux d'upgrade avant toute intervention. Leur présence dans le dépôt ne prouve pas qu'ils ont été exécutés sur une instance donnée.

Depuis la version `2.7`, `hr` n'est plus une dépendance d'exécution. Le code de migration `2.5` est conservé pour les bases historiques; il vérifie la présence des tables RH avant de les lire.

### 3 bis. Script `2.18` — unicité du BCI

`migrations/2.18/pre-migration.py` prépare la contrainte d'unicité sur le champ `bci` de `dss.request`. Il s'exécute **avant** la création de la contrainte par Odoo, et fait trois choses :

| Étape | Action |
|---|---|
| 1 | Retire les espaces autour des BCI existants (`btrim`), comme le fait déjà `write()` à l'enregistrement |
| 2 | Convertit les BCI vides en `NULL`, pour qu'ils ne comptent pas comme une valeur répétée |
| 3 | Liste les doublons restants et **interrompt la migration** avec un message nommant les demandes concernées |

**Le script ne supprime aucune donnée.** Choisir quelle demande conserve un BCI est une décision métier : un administrateur corrige les fiches signalées, puis relance la mise à jour. Sans cette étape, PostgreSQL refuserait la création de l'index unique avec une erreur technique difficile à interpréter.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Migration trouvée | Renommage d'XML ID (2.2), extraction du modèle de service (2.5), attribution du propriétaire (2.6), normalisation et contrôle des BCI (2.18). |
| Prudence | Les scripts ne sont pas une procédure de restauration; sauvegarder la base selon les pratiques d'exploitation avant migration. |
| BCI | Le script 2.18 bloque volontairement en cas de doublon, plutôt que de laisser échouer la contrainte SQL. |
| Source | [`migrations/`](../../migrations/). |