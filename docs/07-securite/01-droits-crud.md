# Droits CRUD

## 1. Colonnes de l'ACL CSV

| Colonne | Signification |
|---|---|
| `id` | Identifiant externe de la ligne ACL. |
| `name` | Libellé technique. |
| `model_id:id` | Référence au modèle Odoo. |
| `group_id:id` | Groupe concerné. Depuis la version `2.14`, **aucune ligne DSS n'est laissée sans groupe**. |
| `perm_read` | Lecture. |
| `perm_write` | Modification. |
| `perm_create` | Création. |
| `perm_unlink` | Suppression. |

Un CSV ne supporte pas les commentaires : toute ligne commençant par `#` serait interprétée comme un droit. La documentation joue donc ce rôle.

## 2. Droits déclarés par le module (version 2.14)

### Demandes et lignes d'articles

| Modèle | Groupe | Lire | Écrire | Créer | Supprimer |
|---|---|---:|---:|---:|---:|
| `dss.request` | DSS / Demandeur | 1 | 1 | 1 | 0 |
| `dss.request` | DSS / Chef | 1 | 1 | 0 | 0 |
| `dss.request` | DSS / Magasin | 1 | 1 | 0 | 0 |
| `dss.request` | DSS / Securite | 1 | 0 | 0 | 0 |
| `dss.request` | Administrateur système | 1 | 1 | 1 | 1 |
| `dss.request.line` | DSS / Demandeur | 1 | 1 | 1 | 0 |
| `dss.request.line` | DSS / Chef | 1 | 1 | 0 | 0 |
| `dss.request.line` | DSS / Magasin | 1 | 1 | 0 | 0 |
| `dss.request.line` | DSS / Securite | 1 | 0 | 0 | 0 |
| `dss.request.line` | Administrateur système | 1 | 1 | 1 | 1 |

**Aucun rôle DSS ne peut supprimer une demande.** La suppression est réservée à l'administrateur système, ce qui protège l'historique et les mouvements de stock déjà générés.

### Configuration et assistants

| Modèle | Groupe | Lire | Écrire | Créer | Supprimer |
|---|---|---:|---:|---:|---:|
| `dss.service` | Utilisateur interne (`base.group_user`) | 1 | 0 | 0 | 0 |
| `dss.service` | DSS / Chef | 1 | 1 | 1 | 1 |
| `dss.service` | Administrateur système | 1 | 1 | 1 | 1 |
| `dss.validation.chef.wizard` | DSS / Chef | 1 | 1 | 1 | 1 |
| `dss.validation.stock.wizard` | DSS / Magasin | 1 | 1 | 1 | 1 |
| `dss.qty.sortie.wizard` et sa ligne | DSS / Magasin | 1 | 1 | 1 | 1 |
| `dss.rejet.wizard` | DSS / Chef **et** DSS / Magasin | 1 | 1 | 1 | 1 |
| `dss.cloture.wizard` et sa ligne | DSS / Chef | 1 | 1 | 1 | 1 |
| `dss.cloture.wizard` et sa ligne | DSS / Demandeur | 1 | 1 | 1 | 1 |
| `dss.notification.log` | Administrateur système | 1 | 1 | 1 | 0 |

La lecture de `dss.service` reste ouverte à tout utilisateur interne : ce modèle ne contient aucune donnée sensible et son nom est affiché sur la fiche de demande.

## 3. Corrections apportées en 2.14

| Problème corrigé | Détail |
|---|---|
| ACL sans groupe sur `dss.request` et `dss.request.line` | Les quatre permissions étaient accordées à tout utilisateur interne. Chaque rôle dispose désormais de sa propre ligne, et la suppression n'est plus accordée aux rôles métier. |
| ACL sans groupe sur `dss.rejet.wizard` | Restreinte aux groupes Chef et Magasin. |
| ACL sans groupe sur `dss.notification.log` | Restreinte à l'administrateur système; le module y écrit en mode `sudo()`. |
| **Assistants de validation sans aucune ACL** | `dss.validation.chef.wizard` et `dss.validation.stock.wizard` n'avaient **aucune ligne ACL** : seul le superutilisateur pouvait ouvrir les popups de confirmation Chef et Stock. Ils disposent maintenant de leur ligne. |

## 4. Points d'attention

- Une ACL autorise un rôle sur un **modèle** ; elle ne filtre pas **quels enregistrements** sont accessibles. Ce filtrage est assuré par les règles d'enregistrement décrites dans [les règles d'enregistrement](02-regles-enregistrement.md).
- Les droits des modèles standards (`product.product`, `stock.picking`, `mail.*`) relèvent des autres modules Odoo et ne sont pas modifiés ici.
- Modifier les ACL exige une montée de version du module (`-u dss_v2`) : les droits sont stockés en base.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| CRUD | R = lecture, W = écriture, C = création, U dans l'usage courant = suppression (`perm_unlink`). |
| Groupe vide | Interdit depuis 2.14 sur les modèles du module. |
| Suppression | Réservée à l'administrateur système. |
| Vue | Masquer un bouton n'est pas une restriction ACL serveur. |
| Source | [`security/ir.model.access.csv`](../../security/ir.model.access.csv). |
