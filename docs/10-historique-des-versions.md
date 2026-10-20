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

## 3. Convention de versioning

Le manifeste expose un numéro de version, mais les sources auditées ne documentent pas de règle de versioning complète ni de changelog historique. Ajouter une entrée datée et sourcée lors d'une évolution future permettrait d'établir cet historique sans le reconstruire par supposition.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Version actuelle | `2.4`, lue dans `__manifest__.py`. |
| Historique antérieur | Non reconstituable de manière fiable avec les seuls fichiers audités. |
| Migration | Le script disponible se trouve dans `migrations/2.2/`. |