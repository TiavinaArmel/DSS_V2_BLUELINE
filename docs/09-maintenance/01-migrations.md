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

Le manifeste indique actuellement la version `2.8`. Les scripts `2.5` et `2.6` modifient des données et des contraintes de base; sauvegarder la base et vérifier les journaux d'upgrade avant toute intervention. Leur présence dans le dépôt ne prouve pas qu'ils ont été exécutés sur une instance donnée.

Depuis la version `2.7`, `hr` n'est plus une dépendance d'exécution. Le code de migration `2.5` est conservé pour les bases historiques; il vérifie la présence des tables RH avant de les lire.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Migration trouvée | Renommage d'XML ID, extraction du modèle de service et attribution du propriétaire aux demandes existantes. |
| Prudence | Les scripts ne sont pas une procédure de restauration; sauvegarder la base selon les pratiques d'exploitation avant migration. |
| Source | [`migrations/`](../../migrations/). |