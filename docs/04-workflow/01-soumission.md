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
  |-- demandeur_id = propriétaire défini à la création
  |-- signataire_demandeur_id = utilisateur courant qui soumet
  |-- date_soumission = fields.Datetime.now()
  |-- state = valide_chef
  |-- message chatter avec le détail des articles et quantités renseignées
  `-- notification submission vers les adresses du groupe Chef
```

La notification est créée dans la file Odoo, elle n'est pas envoyée directement par `action_soumettre()`.

Le message de chatter est posté comme note interne (`subtype="mail.mt_note"`). Son corps vaut `<b>{utilisateur}</b> a soumis la demande.<br/>` suivi d'une ligne par article. Les libellés sont accentués : `Qté demandée`, `Qté sortie`, `Qté installée`, `Qté retour`; seules les quantités non nulles sont affichées, et une intervention de retour de matériel n'affiche que `Qté retour`. Le nom de l'utilisateur et le nom de chaque article passent par `html_escape()` avant l'injection HTML, et les lignes sont séparées par `<br/>`.

Depuis la version `2.15`, la soumission vérifie aussi que chaque ligne porte une **quantité strictement positive** : `qty_retour` pour un retour de matériel, `qty_demandee` pour tous les autres types (`_check_lines_have_positive_quantity()`). Une demande à quantité nulle serait sinon validée par le Chef puis par le Magasin sans créer le moindre mouvement de stock.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| État cible | `valide_chef`. |
| Traçabilité | Demandeur et date sont enregistrés à la soumission. |
| Échec | Une donnée requise manquante lève `ValidationError` avant la transition. |
| Source | [`models/dss_request_workflow.py`](../../models/dss_request_workflow.py). |