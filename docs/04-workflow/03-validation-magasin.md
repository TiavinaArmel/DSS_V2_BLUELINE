# Validation Stock

## 1. Acteur et déclencheur

Le bouton « Valider Stock » porte directement l'attribut `groups="dss_v2.group_dss_magasin"` dans le `<header>` et est conditionné par l'état `valide_magasin`. Il ouvre un wizard de confirmation, qui appelle `action_valider_magasin()`.

## 2. Précondition

| Contrôle | Résultat si non respecté |
|---|---|
| `state == valide_magasin` | `ValidationError`; le traitement des mouvements ne démarre pas. |

La méthode ne vérifie pas directement le groupe de l'utilisateur. Elle enregistre d'abord le signataire Stock et la date, puis choisit les méthodes de mouvement selon `sens_mouvement`.

## 3. Routeur des mouvements

| `sens_mouvement` | Traitement appelé |
|---|---|
| `Sortie` | `_generer_mouvement_sortie()` |
| `Entree` | `_generer_mouvement_entree()` |
| `Sortie + Entree` | Sortie puis entrée |
| `Transfert` | `_generer_mouvement_transfert()` |

Pour les interventions `nouvelle_installation` et `installation_interne` (sens `Sortie`), le wizard Stock ne permet pas de renseigner `qty_retour`; cette valeur est remise à zéro côté serveur. Les quantités installée et retournée sont déterminées seulement lors de la clôture. Les autres sens suivent le routeur ci-dessus sans changement.

Pour `retour_materiel` (sens `Entree`), la demande de retour est préremplie dans le wizard Stock et peut être corrigée. Toute variation, à la hausse ou à la baisse, exige un motif; une quantité négative est refusée côté serveur. Si Stock confirme sans modifier, la quantité demandée est conservée. Les quantités demandée, sortie et installée restent à zéro; le mouvement entrant est généré selon la quantité retournée validée. La clôture ne modifie ensuite plus cette quantité.

Les contrôles de stock, les emplacements et le cycle des pickings sont décrits dans [l'intégration Stock](../06-integrations/00-stock.md).

## 4. Effets après le routeur

Si le code de génération ne lève pas d'exception, l'action poste un message de validation Stock, passe l'état à `approuve`, génère ou met à jour le PDF du BL, poste un message d'approbation définitive et prépare `stock_approval` pour le demandeur.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| État source | `valide_magasin`. |
| État cible | `approuve`, après les méthodes de mouvement. |
| PDF | Généré automatiquement après l'approbation. |
| Sécurité | Aucune transition DSS vers un groupe Sécurité n'est exécutée par cette action. |