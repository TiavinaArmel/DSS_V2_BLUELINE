# Vue formulaire de la demande

## 1. Structure

La vue `view_dss_request_form` déclare un formulaire de `dss.request` avec quatre zones : en-tête, informations générales, onglet Articles et chatter. Les boutons `type="object"` appellent des méthodes Python du modèle.

## 2. Boutons d'en-tête

| Bouton | Groupe de vue | Condition d'affichage | Méthode appelée |
|---|---|---|---|
| Soumettre | Aucun groupe explicite | `state == brouillon` | `action_soumettre` |
| Valider Chef | DSS / Chef | `state == valide_chef` | `action_open_wizard_chef` |
| Rejeter | DSS / Chef | `state == valide_chef` | `action_open_wizard_rejeter` |
| Cloturer | DSS / Chef | `state == approuve` | `action_open_wizard_cloture` |
| Valider Stock | DSS / Magasin | `state == valide_magasin` | `action_open_wizard_stock` |
| Rejeter | DSS / Magasin | `state == valide_magasin` | `action_open_wizard_rejeter` |
| Modifier Qte | DSS / Magasin | Masqué seulement si `state == approuve` | `action_open_modifier_qte_sortie` |
| Bon de Livraison | DSS / Magasin | `state == approuve` | `action_imprimer_bon_livraison` |
| Renvoyer au demandeur | DSS / Chef | `state == rejete` | `action_renvoyer_demandeur` |

Le champ `state` est rendu avec le widget `statusbar` et expose les étapes visibles `brouillon`, `valide_chef`, `valide_magasin`, `approuve`, `cloture`. L'état `rejete` n'est pas dans `statusbar_visible`.

## 3. Champs et lignes

| Zone | Champs et comportement |
|---|---|
| Général | BCI, client, lieu, date, emplacement source, destination et type d'intervention. |
| Destination | Invisible hors `appro_distant`, marquée obligatoire pour `appro_distant`. |
| Sens et écart | `sens_mouvement` et `has_ecart` en lecture seule. |
| Articles | `line_ids` devient readonly hors brouillon; article reçoit `dss_location_id` depuis `parent.location_id`. |
| Quantité demandée | Lecture seule selon `qty_demandee_readonly`. |
| Quantité sortie | Vue héritée : readonly si `is_magasin_user` est faux; le groupe Magasin est calculé côté Python. |
| Chatter | Affiche `message_follower_ids` et `message_ids`. |

Une vue héritée réservée aux groupes Chef, Magasin et Sécurité désactive `create`, `edit`, `delete` et retire le bouton Soumettre. Ces paramètres d'interface ne remplacent pas les ACL serveur.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Bouton | `type="object"` délègue à une méthode Python; les boutons de validation ouvrent d'abord un wizard. |
| Visibilité | `groups` et `attrs` pilotent l'affichage côté interface. |
| Restrictions | La vue « readonly » ne constitue pas une règle d'enregistrement. |
| Source | [`views/dss_request_views.xml`](../../views/dss_request_views.xml), [`views/dss_request_display_views.xml`](../../views/dss_request_display_views.xml). |