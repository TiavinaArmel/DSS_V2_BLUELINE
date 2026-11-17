# Validation Chef

## 1. Acteur

Le bouton « Valider Chef » porte directement l'attribut `groups="dss_v2.group_dss_chef"` dans le `<header>`; il est également conditionné par l'état `valide_chef`.

## 2. Action

Le bouton appelle `action_open_wizard_chef()`, qui ouvre `dss.validation.chef.wizard`. Le bouton de confirmation du wizard délègue à `dss.request.action_valider_chef()`.

## 3. Précondition

| Contrôle | Résultat si non respecté |
|---|---|
| `state == valide_chef` | `ValidationError` indique que la demande doit être en Validation Chef. |
| Utilisateur = Chef du service de la demande | `AccessError` sinon. |
| Utilisateur ≠ demandeur de la demande | `AccessError` depuis la version `2.14` : un Chef qui serait aussi le demandeur ne peut pas valider sa propre demande (séparation des tâches). |

La méthode vérifie l'état, l'identité du Chef du service et l'absence d'auto-validation. La restriction du bouton dans la vue est une condition d'interface qui ne remplace pas ces contrôles.

## 4. Effets

| Donnée | Effet |
|---|---|
| `state` | Passe à `valide_magasin`. |
| `signataire_chef_id` | Prend l'utilisateur courant. |
| `date_validation_chef` | Prend l'heure courante Odoo. |
| Chatter | Note interne (`subtype="mail.mt_note"`) : `<b>{utilisateur}</b> a validé la demande en tant que <b>Responsable Chef</b>.` Le nom est échappé par `html_escape()`. |
| Notification | Prépare `chef_validation` vers les utilisateurs actifs du groupe Magasin et le demandeur. |

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Confirmation | Le wizard ne porte pas la logique de transition. |
| État cible | `valide_magasin`. |
| Source | [`dss_request_workflow.py`](../../models/dss_request_workflow.py), [`dss_validation_wizard.py`](../../models/dss_validation_wizard.py). |