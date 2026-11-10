# Historique des versions

## 1. Versions vérifiables dans les sources

| Version ou repère | Information vérifiable |
|---|---|
| `2.4` | Version indiquée par le manifeste actuel. |
| `2.2` | Répertoire de migration contenant le renommage conditionnel de l'identifiant externe du format papier. |

Les fichiers présents ne fournissent pas un journal complet des changements pour les versions `2.0` à `2.4`. Les changements intermédiaires ne sont donc pas détaillés ici sans source vérifiable.

## 2. État actuel du manifeste

| Clé | Valeur |
|---|---|
| Nom | DSS V2 - Demande de Sortie de Stock |
| Version | `2.4` |
| Auteur | Tiavina Armel |
| Dépendances | `web`, `stock`, `mail` |
| Installable | Oui (`installable=True`) |

## 3. Évolution documentée du 3 novembre 2026

La branche `feature/logique-quantites` corrige la préparation des quantités DSS avant la validation Stock. La validation directe initialise `qty_sortie` à partir de `qty_demandee` et remet `qty_retour` à zéro. Le wizard conserve la quantité demandée, permet une sortie et un retour distincts, exige un motif d'écart par article si nécessaire et marque la demande comme modifiée. L'indicateur `has_ecart` utilise une comparaison à deux décimales.

Un correctif complémentaire a été appliqué au wizard de quantités après l'apparition d'un `UnicodeDecodeError` sous Odoo 10/Python 2. Les textes construits dans `action_valider()` utilisent désormais des chaînes Unicode explicites afin de supporter les noms d'articles, noms d'utilisateurs et motifs contenant des caractères accentués.

La notification `stock_approval` transmet également le motif de modification des quantités par article dans l'e-mail envoyé après la validation Stock. Le contenu est construit depuis `motif_ecart` et reste absent lorsqu'aucune ligne n'a été modifiée.

Le comportement multi-lignes a ensuite été corrigé : le motif n'est requis que pour une ligne effectivement modifiée, les autres lignes reçoivent automatiquement leur quantité demandée en sortie et les motifs transmis par e-mail sont rendus sous forme de liste HTML non ordonnée.

## 4. Convention de versioning

Le manifeste expose un numéro de version, mais les sources auditées ne documentent pas de règle de versioning complète ni de changelog historique. Ajouter une entrée datée et sourcée lors d'une évolution future permettrait d'établir cet historique sans le reconstruire par supposition.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Version actuelle | `2.4`, lue dans `__manifest__.py`. |
| Historique antérieur | Non reconstituable de manière fiable avec les seuls fichiers audités. |
| Migration | Le script disponible se trouve dans `migrations/2.2/`. |