# Validation Chef

## 1. Acteur

Le bouton « Valider Chef » est placé dans un bloc de vue réservé au groupe `dss_v2.group_dss_chef`.

## 2. Action

Le bouton appelle `action_open_wizard_chef()`, qui ouvre `dss.validation.chef.wizard`. Le bouton de confirmation du wizard délègue à `dss.request.action_valider_chef()`.

## 3. Précondition

| Contrôle | Résultat si non respecté |
|---|---|
| `state == valide_chef` | `ValidationError` indique que la demande doit être en Validation Chef. |

La méthode de validation vérifie l'état, mais ne vérifie pas elle-même l'appartenance au groupe Chef. La restriction du bouton est une condition d'interface.

## 4. Effets

| Donnée | Effet |
|---|---|
| `state` | Passe à `valide_magasin`. |
| `signataire_chef_id` | Prend l'utilisateur courant. |
| `date_validation_chef` | Prend l'heure courante Odoo. |
| Chatter | Ajoute une trace de validation Chef. |
| Notification | Prépare `chef_validation` vers les utilisateurs actifs du groupe Magasin et le demandeur. |

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Confirmation | Le wizard ne porte pas la logique de transition. |
| État cible | `valide_magasin`. |
| Source | [`dss_request_workflow.py`](../../models/dss_request_workflow.py), [`dss_validation_wizard.py`](../../models/dss_validation_wizard.py). |