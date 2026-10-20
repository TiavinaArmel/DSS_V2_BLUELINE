# Validation Stock

## 1. Acteur et déclencheur

Le bouton « Valider Stock » est limité dans la vue au groupe `dss_v2.group_dss_magasin` et à l'état `valide_magasin`. Il ouvre un wizard de confirmation, qui appelle `action_valider_magasin()`.

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