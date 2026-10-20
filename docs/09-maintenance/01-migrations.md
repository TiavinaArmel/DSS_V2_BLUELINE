# Migrations de données

## 1. Rôle du dossier

Le module contient un script de migration dans `migrations/2.2/`. L'audit des fichiers ne recense pas d'autres scripts de migration dans ce dossier.

## 2. Script présent

| Chemin | Fonction constatée |
|---|---|
| `migrations/2.2/pre-rename-paperformat-xmlid.py` | Renomme dans `ir_model_data` l'identifiant externe `dss_v2.paperformat_dss_a4` en `dss_v2.paperformat_dss_a5` si le nouvel identifiant n'existe pas déjà. |

La requête SQL cible le module `dss_v2` et le modèle `report.paperformat`. Elle ne crée pas un deuxième format papier; elle modifie le nom de l'identifiant externe existant. Si l'identifiant cible existe déjà, la condition `NOT EXISTS` empêche le renommage.

## 3. Version et exécution

Le répertoire porte le nom `2.2`, tandis que le manifeste actuel indique la version `2.4`. Le contenu du script seul ne permet pas de conclure sur les bases où il a effectivement été exécuté ni sur l'historique complet des migrations. Vérifier les conventions de migration de l'instance Odoo et l'état des `ir.model.data` avant toute intervention sur une base.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Migration trouvée | Renommage conditionnel de l'XML ID du paperformat. |
| Prudence | Le script n'est pas une procédure de restauration; sauvegarder la base selon les pratiques d'exploitation avant migration. |
| Source | [`migrations/2.2/pre-rename-paperformat-xmlid.py`](../../migrations/2.2/pre-rename-paperformat-xmlid.py). |