# Historique des versions

## 1. Versions vérifiables dans les sources

| Version ou repère | Information vérifiable |
|---|---|
| `2.8` | Version indiquée par le manifeste actuel. |
| `2.7` | Retrait de `hr` des dépendances du module. |
| `2.6` | Version du manifeste précédant le retrait de `hr` en `2.7`. |
| `2.2` | Répertoire de migration contenant le renommage conditionnel de l'identifiant externe du format papier. |

Les fichiers présents ne fournissent pas un journal complet des changements pour les versions `2.0` à `2.8`. Les changements intermédiaires ne sont donc pas détaillés ici sans source vérifiable.

## 2. État actuel du manifeste

| Clé | Valeur |
|---|---|
| Nom | DSS V2 - Demande de Sortie de Stock |
| Version | `2.8` |
| Auteur | Tiavina Armel |
| Dépendances | `web`, `stock`, `mail` |
| Installable | Oui (`installable=True`) |

## 3. Évolutions récentes vérifiées (10-13 novembre 2026)

Les commits présents dans l'historique du module et les sources actuelles confirment les évolutions suivantes :

| Domaine | Changement documenté |
|---|---|
| Quantités | La validation directe reprend la demande en sortie; le wizard Stock peut ajuster les quantités et doit justifier les écarts par article. |
| Chatter Stock | Le message de modification affiche les quantités demandée/sortie et le motif. La puce Unicode est rendue comme `•`, et non comme le texte littéral `\u2022`. |
| BCI | Les espaces extérieurs sont normalisés et un même BCI non vide ne peut pas être utilisé sur plusieurs demandes. |
| Services | Le flux DSS lie la demande à un service, contrôle les demandeurs autorisés et le Chef affecté, et trace les corrections administratives du service. |
| Clôture | Le demandeur peut clôturer une demande approuvée; le Chef possède une clôture exceptionnelle avec motif obligatoire. |
| Courriels | Les événements du workflow disposent de notifications avec destinataires, journal de déduplication et template HTML. L'approbation Stock transmet le motif d'écart par article. |
| Stock local | La disponibilité d'un article est calculée dans l'emplacement source exact, sans agréger ses sous-emplacements. |

Les messages de quantité utilisent des chaînes Unicode explicites pour rester compatibles avec l'environnement Odoo 10/Python 2 lorsque les noms contiennent des accents.

## 4. Amélioration de clôture documentée le 13 novembre 2026

Pour les interventions `nouvelle_installation` et `installation_interne` (sens `Sortie`), la clôture initialise la quantité installée à la quantité sortie et le retour à zéro. L'utilisateur choisit par ligne de saisir l'installation ou le retour; l'autre quantité est calculée, et la quantité saisie ne peut pas dépasser la sortie. Les champs sont verrouillés hors du wizard de clôture. Un retour positif crée un mouvement entrant vers l'emplacement source d'origine, référencé par `picking_retour_cloture_id` et mentionné dans le chatter et l'e-mail. Les autres types d'intervention gardent leur flux de clôture actuel.

## 5. Convention de versioning

La version `2.7` retire `hr` des dépendances du module et supprime le fichier de données vide `data/dss_department_data.xml`. La migration 2.5 est conservée pour transférer les données RH historiques lorsque leurs tables existent. La version `2.8` inclut explicitement `is_sortie_only` dans les valeurs initiales des lignes du wizard Stock, afin que le client Odoo puisse évaluer les règles `attrs` dès l'ouverture.

Le manifeste expose un numéro de version, mais les sources auditées ne documentent pas de règle de versioning complète ni un changelog exhaustif. Ajouter une entrée datée et sourcée lors d'une évolution future permettrait d'établir cet historique sans le reconstruire par supposition.

## 6. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Version actuelle | `2.8`, lue dans `__manifest__.py`. |
| Historique antérieur | Non reconstituable de manière fiable avec les seuls fichiers audités. |
| Migrations | Scripts conservés dans `migrations/2.2/`, `migrations/2.5/` et `migrations/2.6/`. |