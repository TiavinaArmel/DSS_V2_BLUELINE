# Rejet, renvoi et clôture

## 1. Rejet

Les boutons « Rejeter » apparaissent au Chef à l'état `valide_chef` et au Magasin à l'état `valide_magasin`. Ils ouvrent `dss.rejet.wizard`.

| Étape | Comportement |
|---|---|
| Saisie | Le champ `motif` du wizard est requis. |
| Confirmation | Copie `motif` vers `dss.request.motif_rejet`, puis appelle `action_rejeter()`. |
| Transition | `state` devient `rejete`; un message chatter est ajouté. |
| Notification | Le destinataire et la clé dépendent de l'état précédent. |

`action_rejeter()` n'applique pas de contrôle serveur de l'état de départ. La visibilité des boutons ne suffit pas à empêcher un appel direct de cette méthode dans un autre contexte.

## 2. Renvoi au demandeur

Le renvoi est affiché au Chef quand l'état vaut `rejete`. Le code vérifie également côté serveur l'appartenance au groupe Chef et l'état rejeté. L'état passe à `brouillon`, le chatter est mis à jour et une notification `return_to_requester` est préparée à l'adresse du signataire ou, à défaut, du créateur. Le motif précédent est conservé et transmis au template.

## 3. Clôture

Le bouton Chef ouvre `dss.cloture.wizard` à l'état `approuve`. Le wizard préremplit une copie des lignes et permet de saisir `qty_installee` et `qty_retour`.

| Opération lors de la confirmation | Détail |
|---|---|
| Écriture | Écrit `qty_installee` et `qty_retour` sur les lignes DSS. |
| Écart | Compare `qty_installee` à `qty_sortie`; `has_ecart` devient vrai si une ligne diffère. |
| État | Passe la demande à `cloture`. |
| Chatter | Ajoute un récapitulatif et les écarts éventuels. |
| Notification | Appelle `_dss_notify_closure()` pour le demandeur et le groupe Magasin. |

Le wizard n'effectue pas de contrôle explicite de l'état avant de clôturer; le bouton de la vue limite l'accès normal à l'état approuvé.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Rejet | Motif obligatoire dans le wizard; garde-fou d'état absent dans `action_rejeter()`. |
| Renvoi | Chef seulement, état `rejete` vérifié côté serveur. |
| Clôture | Écart calculé sur installé versus sorti; la quantité retournée n'entre pas dans cette comparaison. |
| Sources | [`dss_rejet_wizard.py`](../../models/dss_rejet_wizard.py), [`dss_cloture_wizard.py`](../../models/dss_cloture_wizard.py), [`dss_request_workflow.py`](../../models/dss_request_workflow.py). |