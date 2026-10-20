# Cycle de vie d'une demande DSS

## 1. Schéma général

```text
brouillon --Soumettre--> valide_chef --Validation Chef--> valide_magasin
valide_chef --Rejet--> rejete
valide_magasin --Rejet--> rejete
rejete --Renvoi par un Chef--> brouillon
valide_magasin --Validation Stock + mouvements + BL--> approuve
approuve --Cloture--> cloture
```

Le groupe Sécurité ne forme pas une étape du circuit de `dss.request`. Le parcours DSS séparé ajouté à `stock.picking` est décrit dans [l'intégration Stock](../06-integrations/00-stock.md).

## 2. États

| État technique | Libellé de sélection | Description constatée |
|---|---|---|
| `brouillon` | Brouillon | État par défaut et destination du renvoi par un Chef. |
| `valide_chef` | Validation Chef | Attente de l'action Chef. |
| `valide_magasin` | Validation Stock | Attente de l'action Magasin. |
| `approuve` | Approuve | État après le routeur de mouvements et avant clôture. |
| `cloture` | Cloture | État assigné par le wizard de clôture. |
| `rejete` | Rejete | État assigné par l'action de rejet. |

## 3. Transitions

| De | Vers | Action | Contrôle explicite dans le code |
|---|---|---|---|
| `brouillon` | `valide_chef` | `action_soumettre()` | Champs de soumission et au moins une ligne; pas de contrôle explicite de l'état initial. |
| `valide_chef` | `valide_magasin` | `action_valider_chef()` | Vérifie l'état `valide_chef`. |
| `valide_magasin` | `approuve` | `action_valider_magasin()` | Vérifie l'état et exécute les mouvements avant d'approuver. |
| Tout état en cas d'appel direct | `rejete` | `action_rejeter()` | Pas de contrôle serveur de l'état initial; les boutons sont conditionnés par la vue. |
| `rejete` | `brouillon` | `action_renvoyer_demandeur()` | Vérifie l'état et le groupe Chef. |
| `approuve` | `cloture` | `DssClotureWizard.action_confirmer()` | Le bouton est visible au Chef à l'état approuvé; le wizard ne contrôle pas lui-même cet état. |

## 4. Cas particuliers

Le rejet conserve son motif dans `motif_rejet`. Le renvoi retourne l'état à `brouillon`; le code de cette action ne vide pas les signataires, dates ou le motif existants. La clôture calcule l'écart à partir de `qty_installee != qty_sortie`.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Parcours nominal | Brouillon -> Chef -> Stock -> approuvé -> clôturé. |
| Rejet | Depuis les boutons Chef ou Magasin, puis renvoi éventuel au brouillon par un Chef. |
| Étape sécurité | Absente du workflow `dss.request`. |
| Sources | [`dss_request.py`](../../models/dss_request.py), [`dss_request_workflow.py`](../../models/dss_request_workflow.py), wizards dans `models/`. |