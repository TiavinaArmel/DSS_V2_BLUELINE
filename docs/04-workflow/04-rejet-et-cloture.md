# Rejet, renvoi et clôture

## 1. Rejet

Les boutons « Rejeter » apparaissent au Chef à l'état `valide_chef` et au Magasin à l'état `valide_magasin`. Ils ouvrent `dss.rejet.wizard`.

| Étape | Comportement |
|---|---|
| Saisie | Le champ `motif` du wizard est requis. |
| Confirmation | Copie `motif` vers `dss.request.motif_rejet`, puis appelle `action_rejeter()`. |
| Transition | `state` devient `rejete`; une note interne (`subtype="mail.mt_note"`) est ajoutée au chatter : `<b>{utilisateur}</b> a rejeté la demande.<br/><b>Motif :</b> {motif}`, ou sans motif `<b>{utilisateur}</b> a rejeté la demande.` |
| Notification | Le destinataire et la clé dépendent de l'état précédent. |

Le motif de rejet provient d'une saisie libre : il passe par `html_escape()` avant l'injection HTML, puis ses retours à la ligne sont convertis en `<br/>`. Le nom de l'utilisateur est échappé de la même manière. Sans ce traitement, un motif contenant `<`, `>` ou `&` cassait l'affichage du message.

`action_rejeter()` n'applique pas de contrôle serveur de l'état de départ. La visibilité des boutons ne suffit pas à empêcher un appel direct de cette méthode dans un autre contexte.

## 2. Renvoi au demandeur

Le renvoi est affiché au Chef quand l'état vaut `rejete`. Le code vérifie également côté serveur l'appartenance au groupe Chef et l'état rejeté. L'état passe à `brouillon`, le chatter est mis à jour et une notification `return_to_requester` est préparée à l'adresse du signataire ou, à défaut, du créateur. Le motif précédent est conservé et transmis au template.

## 3. Clôture

Le demandeur d'origine ouvre `dss.cloture.wizard` à l'état `approuve` pour une clôture normale. Le Chef dispose d'une action de clôture exceptionnelle utilisant le même wizard et exigeant un motif, vérifié aussi côté serveur.

Pour les interventions **Nouvelle installation client** et **Installation interne** (`sens_mouvement == "Sortie"`), l'ouverture du wizard initialise chaque ligne avec `qty_installee = qty_sortie` et `qty_retour = 0`. Le choix « Quantité à saisir » rend un seul champ modifiable par ligne :

- saisir la quantité installée calcule `qty_retour = qty_sortie - qty_installee` ;
- saisir la quantité retournée calcule `qty_installee = qty_sortie - qty_retour`.

La quantité saisie doit être comprise entre zéro et `qty_sortie`; le contrôle est répété côté serveur à la confirmation. Les lignes laissées intactes sont donc considérées entièrement installées. À la clôture, chaque retour positif crée un picking entrant du stock client vers l'emplacement source `location_id`. Le picking est accessible depuis `picking_retour_cloture_id`; le chatter et l'e-mail de clôture indiquent l'article, la quantité retournée et son emplacement d'origine.

Pour les autres types d'intervention, les valeurs installée/retour conservent le comportement antérieur. L'indicateur d'écart des interventions de sortie seule compare le total installé + retourné à la quantité demandée.

### Retour de matériel

Pour `retour_materiel`, le demandeur renseigne en brouillon l'article, la quantité retournée et l'observation. À la validation Stock, la quantité retournée est préremplie et modifiable; toute différence par rapport à la quantité demandée impose un motif. Une confirmation sans modification conserve la valeur initiale. Les quantités demandée, sortie et installée sont ignorées et ramenées à zéro. À la clôture normale ou exceptionnelle, la quantité retournée validée est affichée en lecture seule : confirmer ne réécrit pas les quantités et ne crée pas un second mouvement. Le motif reste obligatoire pour toute clôture exceptionnelle.

| Opération lors de la confirmation | Détail |
|---|---|
| Écriture | Écrit `qty_installee` et `qty_retour` sur les lignes DSS. |
| Quantités sortie seule | Le total installé + retourné correspond à `qty_sortie`; une seule quantité est saisie et l'autre est calculée. |
| Retour stock | Chaque quantité retournée positive est transférée à la clôture vers l'emplacement source de la demande. |
| Écart | Pour une sortie seule, compare le total installé + retourné à `qty_demandee`; `has_ecart` devient vrai si une ligne diffère. |
| État | Passe la demande à `cloture`. |
| Chatter | Note interne (`subtype="mail.mt_note"`) avec récapitulatif par article (`Qté installée`, `Qté retour`; `Qté retour confirmée` pour un retour de matériel), les retours à l'emplacement d'origine et, s'il y en a, la section `Écarts détectés`. |
| Notification | Appelle `_dss_notify_closure()` pour le Chef, le Magasin et le demandeur; le contexte conserve le type et le motif d'une clôture exceptionnelle. |

Le wizard vérifie côté serveur que la demande est encore à l'état `approuve` avant toute écriture. Les boutons XML ajoutent une protection d'interface, mais ne remplacent pas ce contrôle serveur.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Rejet | Motif obligatoire dans le wizard; garde-fou d'état absent dans `action_rejeter()`. |
| Renvoi | Chef seulement, état `rejete` vérifié côté serveur. |
| Clôture sortie seule | `qty_installee + qty_retour = qty_sortie`; un retour positif crée un transfert entrant à la clôture. |
| Clôture retour matériel | Confirmation uniquement; conserve la quantité validée au Stock, sans réécriture ni nouveau mouvement. |
| Sources | [`dss_rejet_wizard.py`](../../models/dss_rejet_wizard.py), [`dss_cloture_wizard.py`](../../models/dss_cloture_wizard.py), [`dss_request_workflow.py`](../../models/dss_request_workflow.py). |