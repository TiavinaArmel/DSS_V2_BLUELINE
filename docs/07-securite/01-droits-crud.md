# Droits CRUD

## 1. Colonnes de l'ACL CSV

| Colonne | Signification |
|---|---|
| `id` | Identifiant externe de la ligne ACL. |
| `name` | Libellé technique. |
| `model_id:id` | Référence au modèle Odoo. |
| `group_id:id` | Groupe concerné; vide signifie qu'aucun groupe n'est spécifié. |
| `perm_read` | Lecture. |
| `perm_write` | Modification. |
| `perm_create` | Création. |
| `perm_unlink` | Suppression. |

## 2. Droits déclarés par le module

| Modèle | Groupe | Lire | Écrire | Créer | Supprimer |
|---|---|---:|---:|---:|---:|
| `dss.request` | Aucun | 1 | 1 | 1 | 1 |
| `dss.request.line` | Aucun | 1 | 1 | 1 | 1 |
| `dss.qty.sortie.wizard` | DSS / Magasin | 1 | 1 | 1 | 1 |
| `dss.qty.sortie.wizard.line` | DSS / Magasin | 1 | 1 | 1 | 1 |
| `dss.rejet.wizard` | Aucun | 1 | 1 | 1 | 1 |
| `dss.cloture.wizard` | DSS / Chef | 1 | 1 | 1 | 1 |
| `dss.cloture.wizard.line` | DSS / Chef | 1 | 1 | 1 | 1 |
| `dss.notification.log` | Aucun | 1 | 1 | 1 | 0 |

Dans l'ACL, un `group_id` vide n'est pas un groupe DSS implicite : la ligne s'applique aux utilisateurs internes selon la sémantique ACL Odoo. Les droits combinés des autres modules et groupes peuvent s'ajouter.

## 3. Points d'attention

Les demandes et lignes ont les quatre permissions activées sans groupe DSS spécifié. Le wizard de rejet et le journal ont également une ACL sans groupe explicite. Les restrictions de boutons et de vues ne réduisent pas ces permissions du modèle. Les ACL de `product.product`, `product.template`, `stock.picking` et des modèles Odoo standards relèvent également des autres modules.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| CRUD | R = lecture, W = écriture, C = création, U dans l'usage courant = suppression (`perm_unlink`). |
| Groupe vide | Aucun `group_id` DSS n'est associé à la ligne; ne pas interpréter cela comme une règle par rôle. |
| Vue | Masquer un bouton n'est pas une restriction ACL serveur. |
| Source | [`security/ir.model.access.csv`](../../security/ir.model.access.csv). |