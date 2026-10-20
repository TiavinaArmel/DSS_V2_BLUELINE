# Extension workflow de `dss.request`

## 1. Actions et transitions

| Méthode | État contrôlé | État affecté | Effets constatés |
|---|---|---|---|
| `action_soumettre` | Aucun contrôle d'état explicite | `valide_chef` | Valide les champs requis et les lignes, renseigne demandeur/date, poste un message et prépare une notification. |
| `action_valider_chef` | Exige `valide_chef` | `valide_magasin` | Enregistre signataire/date Chef, poste un message et prépare une notification. |
| `action_valider_magasin` | Exige `valide_magasin` | `approuve` après génération stock | Enregistre signataire/date Stock, appelle le routeur stock, génère le BL, poste des messages et prépare une notification. |
| `action_rejeter` | Aucun contrôle d'état explicite | `rejete` | Conserve l'état précédent pour le routage, poste le motif s'il existe et prépare une notification si l'état précédent est reconnu. |
| `action_renvoyer_demandeur` | Exige groupe Chef et état `rejete` | `brouillon` | Poste le nom du demandeur et prépare un courriel de renvoi. |

Les actions métier et leur ordre réel sont implémentés dans [`dss_request_workflow.py`](../../models/dss_request_workflow.py). Les contrôles d'accès visuels et les contrôles serveur ne sont pas équivalents.

## 2. Validations de soumission

| Donnée contrôlée | Règle dans `action_soumettre()` |
|---|---|
| `bci` | Doit être renseigné. |
| `partner_id` | Doit être renseigné. |
| `lieu_intervention` | Doit être renseigné. |
| `date_intervention` | Doit être renseignée. |
| `type_intervention` | Doit être renseigné. |
| `location_id` | Doit être renseigné. |
| `location_dest_id` | Requis si `type_intervention == 'appro_distant'`. |
| `line_ids` | Au moins une ligne est requise. |

Chaque échec lève `ValidationError` avant l'enregistrement de la soumission. Le code ne vérifie pas explicitement que l'état initial est `brouillon`.

## 3. Traçabilité

| Champ | Renseigné par | Moment |
|---|---|---|
| `signataire_demandeur_id` | `action_soumettre()` | Utilisateur courant à la soumission. |
| `date_soumission` | `action_soumettre()` | `fields.Datetime.now()`. |
| `signataire_chef_id` / `date_validation_chef` | `action_valider_chef()` | Validation Chef. |
| `signataire_magasin_id` / `date_validation_magasin` | `action_valider_magasin()` | Avant la génération des mouvements. |

Les actions de validation Chef et Stock contrôlent l'état attendu, mais leur méthode Python ne vérifie pas directement l'appartenance au groupe; les boutons de la vue sont limités par `groups`.

## 4. Actions d'ouverture des wizards

| Méthode | Modèle modal référencé |
|---|---|
| `action_open_wizard_rejeter` | `dss.rejet.wizard` |
| `action_open_modifier_qte_sortie` | `dss.qty.sortie.wizard` |
| `action_open_wizard_cloture` | `dss.cloture.wizard` |
| `action_open_wizard_chef` | `dss.validation.chef.wizard` |
| `action_open_wizard_stock` | `dss.validation.stock.wizard` |
| `action_open_wizard_approuver` | `dss.validation.approuver.wizard` |

Le dernier modèle référencé n'est pas déclaré dans les fichiers Python recensés et aucun bouton correspondant n'est défini dans la vue principale. Ne pas le confondre avec le wizard de validation Stock.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Transitions | Chef puis Stock; l'approbation suit la réussite du routeur de mouvements. |
| Rejet | Le wizard exige un motif; la méthode `action_rejeter()` ne vérifie pas l'état de départ. |
| Renvoi | Contrôles serveur explicites du groupe Chef et de l'état rejeté. |
| Source | [`models/dss_request_workflow.py`](../../models/dss_request_workflow.py). |