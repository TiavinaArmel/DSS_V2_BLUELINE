# Historique des versions

## 1. Versions vérifiables dans les sources

| Version ou repère | Information vérifiable |
|---|---|
| `2.17` | Suppression de la méthode fantôme `action_open_wizard_approuver()`, qui ouvrait une fenêtre sur le modèle inexistant `dss.validation.approuver.wizard`. Aucun bouton ne l'appelait. |
| `2.16` | Retrait du circuit DSS parallèle porté par `stock.picking` et `product.template` : jamais utilisé, il pouvait bloquer la validation de n'importe quel transfert de stock. Le module ne modifie plus le comportement de l'application Stock. |
| `2.15` | Fiabilité : contrainte serveur interdisant les quantités négatives, exigence d'une quantité strictement positive à la soumission, fusion des deux conditions d'affichage de la quantité sortie, purge quotidienne des courriels de plus de 60 jours. |
| `2.14` | Sécurisation : ACL rattachées à chaque rôle, dix règles d'enregistrement, interdiction d'écrire l'état hors workflow, contrôles serveur du rôle Magasin et de l'étape d'ajustement, blocage de l'auto-validation par le Chef, ACL des assistants de confirmation. |
| `2.13` | Courriels : détection des adresses de bouclage pour ne plus envoyer de logo ni de lien cassés, statut affiché sous forme de libellé, texte d'action propre à chaque événement, motifs échappés, sujet enrichi du type d'intervention, adresse de réponse de la société et pied de page dynamique. |
| `2.12` | Le `depannage` suit le parcours de clôture calculé de la nouvelle installation : `qty_installee` préremplie à `qty_sortie`, retour saisi à la clôture et entrée de stock générée à ce moment. Le `basculement` reste en saisie manuelle. |
| `2.11` | L'approvisionnement distant (`appro_distant`) suit le parcours de clôture de la nouvelle installation : `qty_installee` préremplie à `qty_sortie`, retour éventuel saisi à la clôture et transféré par un picking interne de `location_dest_id` vers `location_id`. |
| `2.10` | Harmonisation des messages du chatter : libellés accentués, échappement HTML des noms et des motifs, fusion des deux messages de validation Stock et sous-type `mail.mt_note` explicite. |
| `2.9` | Parcours dédié de retour de matériel : correction motivée à Stock et clôture de confirmation en lecture seule. |
| `2.8` | Version précédant le parcours dédié de retour de matériel. |
| `2.7` | Retrait de `hr` des dépendances du module. |
| `2.6` | Version du manifeste précédant le retrait de `hr` en `2.7`. |
| `2.2` | Répertoire de migration contenant le renommage conditionnel de l'identifiant externe du format papier. |

Les fichiers présents ne fournissent pas un journal complet des changements pour les versions `2.0` à `2.17`. Les changements intermédiaires ne sont donc pas détaillés ici sans source vérifiable.

## 2. État actuel du manifeste

| Clé | Valeur |
|---|---|
| Nom | DSS V2 - Demande de Sortie de Stock |
| Version | `2.17` |
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
| Retour de matériel | La quantité retournée est préremplie à Stock; toute correction nécessite un motif. La clôture confirme sans réécrire les quantités ni générer un second mouvement. |

Les messages de quantité utilisent des chaînes Unicode explicites pour rester compatibles avec l'environnement Odoo 10/Python 2 lorsque les noms contiennent des accents.

## 4. Amélioration de clôture documentée le 13 novembre 2026

Pour les interventions `nouvelle_installation` et `installation_interne` (sens `Sortie`), la clôture initialise la quantité installée à la quantité sortie et le retour à zéro. L'utilisateur choisit par ligne de saisir l'installation ou le retour; l'autre quantité est calculée, et la quantité saisie ne peut pas dépasser la sortie. Les champs sont verrouillés hors du wizard de clôture. Un retour positif crée un mouvement entrant vers l'emplacement source d'origine, référencé par `picking_retour_cloture_id` et mentionné dans le chatter et l'e-mail. Les autres types d'intervention gardent leur flux de clôture actuel.

## 5. Convention de versioning

La version `2.7` retire `hr` des dépendances du module et supprime le fichier de données vide `data/dss_department_data.xml`. La migration 2.5 est conservée pour transférer les données RH historiques lorsque leurs tables existent. La version `2.8` inclut explicitement `is_sortie_only` dans les valeurs initiales des lignes du wizard Stock, afin que le client Odoo puisse évaluer les règles `attrs` dès l'ouverture. La version `2.9` ajoute les contrôles de quantité et de motif au parcours « Retour de matériel », ainsi qu'une clôture de confirmation en lecture seule. La version `2.10` ne modifie aucune donnée ni aucun état du workflow : elle uniformise le rendu des messages de chatter et déclare explicitement leur sous-type, sans migration de base nécessaire. La version `2.11` étend le parcours de clôture des interventions de sens `Sortie` au transfert interne `appro_distant`, et adapte le mouvement de retour à la source réelle du matériel (`location_dest_id`). La version `2.12` applique le même parcours au `depannage`, dont l'entrée de stock est désormais créée à la clôture à partir de la quantité retournée, et laisse le `basculement` en saisie manuelle. La version `2.13` ne modifie ni le workflow ni les quantités : elle corrige les liens des courriels et rend leur contenu explicite, sans migration de base. La version `2.14` ne change aucune règle métier du circuit : elle ajoute uniquement des contrôles d'accès et des garde-fous serveur, donc aucune migration de données n'est nécessaire. La version `2.15` ajoute des contraintes de quantité et une tâche planifiée de purge : aucun changement de schéma, mais un upgrade du module est nécessaire pour créer la tâche planifiée. La version `2.16` retire un circuit parallèle inutilisé : aucun changement de comportement visible, mais un upgrade est nécessaire pour que Odoo cesse de charger les extensions de `stock.picking` et `product.template`. La version `2.17` supprime une méthode qui visait un modèle inexistant : aucun changement fonctionnel, uniquement de la propreté de code.

Le manifeste expose un numéro de version, mais les sources auditées ne documentent pas de règle de versioning complète ni un changelog exhaustif. Ajouter une entrée datée et sourcée lors d'une évolution future permettrait d'établir cet historique sans le reconstruire par supposition.

## 6. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Version actuelle | `2.17`, lue dans `__manifest__.py`. |
| Historique antérieur | Non reconstituable de manière fiable avec les seuls fichiers audités. |
| Migrations | Scripts conservés dans `migrations/2.2/`, `migrations/2.5/` et `migrations/2.6/`. |