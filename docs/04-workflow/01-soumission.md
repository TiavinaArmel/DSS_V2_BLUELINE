# Soumission d'une demande

## 1. Acteur et déclencheur

Le formulaire présente le bouton « Soumettre » à l'état `brouillon`. Il appelle `action_soumettre()` sur le modèle `dss.request`.

## 2. Préconditions contrôlées

| Champ ou relation | Contrôle |
|---|---|
| `bci` | Valeur non vide. |
| `partner_id` | Client défini. |
| `lieu_intervention` | Valeur non vide. |
| `date_intervention` | Date définie. |
| `type_intervention` | Type défini. |
| `location_id` | Emplacement source défini. |
| `location_dest_id` | Requis uniquement pour `appro_distant`. |
| `line_ids` | Au moins une ligne. |

Les champs ne sont pas tous déclarés `required=True` dans le modèle; ces contrôles sont exécutés dans l'action. Elle ne vérifie pas que la demande est encore en brouillon au niveau Python.

## 3. Effets

```text
Contrôles réussis
  |-- signataire_demandeur_id = utilisateur courant
  |-- date_soumission = fields.Datetime.now()
  |-- state = valide_chef
  |-- message chatter avec le détail des articles et quantités renseignées
  `-- notification submission vers les adresses du groupe Chef
```

La notification est créée dans la file Odoo, elle n'est pas envoyée directement par `action_soumettre()`.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| État cible | `valide_chef`. |
| Traçabilité | Demandeur et date sont enregistrés à la soumission. |
| Échec | Une donnée requise manquante lève `ValidationError` avant la transition. |
| Source | [`models/dss_request_workflow.py`](../../models/dss_request_workflow.py). |