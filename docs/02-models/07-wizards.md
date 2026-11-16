# Wizards DSS

## 1. Liste des assistants

| Assistant | Modèle temporaire | Rôle | Déclencheur |
|---|---|---|---|
| Rejet | `dss.rejet.wizard` | Recueille le motif obligatoire puis appelle le rejet de la demande. | Bouton « Rejeter » du Chef ou du Magasin. |
| Quantités Stock | `dss.qty.sortie.wizard` et lignes | Copie les lignes et permet de modifier sortie/retour. | Bouton « Modifier Qte ». |
| Clôture | `dss.cloture.wizard` et lignes | Copie les lignes, calcule installé/retour pour les sorties seules, crée le transfert de retour et clôture. | Bouton du demandeur ou clôture exceptionnelle du Chef. |
| Confirmation Chef | `dss.validation.chef.wizard` | Confirme puis délègue à `action_valider_chef()`. | Bouton « Valider Chef ». |
| Confirmation Stock | `dss.validation.stock.wizard` | Confirme puis délègue à `action_valider_magasin()`. | Bouton « Valider Stock ». |

## 2. `Model` et `TransientModel`

`dss.request` et ses lignes sont des modèles persistants. Les modèles de wizard héritent de `models.TransientModel`; leurs enregistrements servent à une interaction temporaire. Une ligne de wizard est une copie de travail liée à l'enregistrement réel via `request_line_id`.

## 3. Préremplissage et validation

Les wizards de quantité et de clôture utilisent `default_get()` pour lire `default_request_id`, avec `active_id` en repli, puis construisent des lignes One2many temporaires. La confirmation écrit ensuite les valeurs autorisées sur les lignes DSS réelles. Les wizards Chef et Stock ne portent pas la logique métier de transition; ils délèguent à l'action du modèle principal.

Pour le wizard de quantités, le motif est porté par `dss.qty.sortie.wizard.line` afin de permettre un motif différent pour chaque article. Le champ est recopié depuis `dss.request.line` à l'ouverture.

### Compatibilité Unicode avec Odoo 10

Le serveur Odoo 10 fonctionne avec Python 2. Les messages construits dans `action_valider()` utilisent donc des chaînes Unicode préfixées par `u` lorsqu'ils incorporent des valeurs Odoo comme `product_id.name` ou `env.user.name`. Cette précaution évite une conversion ASCII implicite et l'erreur `UnicodeDecodeError` lorsqu'un article, un utilisateur ou un motif contient des caractères accentués.

| Wizard | Valeurs modifiables dans l'assistant | Effets à la confirmation |
|---|---|---|
| Rejet | `motif` requis | Copie dans `motif_rejet`, puis appelle `action_rejeter()`. |
| Quantités | `qty_sortie`, `qty_retour`, `motif_ecart` | Compare chaque ligne à ses valeurs initiales, exige un motif uniquement pour une ligne réellement modifiée, initialise les autres lignes avec `qty_demandee` et conserve `qty_demandee`. Pour `retour_materiel`, la quantité retournée est préremplie; toute variation exige un motif et les autres quantités restent à zéro. |
| Clôture | `qty_installee`, `qty_retour`, `mode_saisie`, `is_exception`, `motif_exception` | Pour `sens_mouvement == "Sortie"` et `sens_mouvement == "Transfert"` (`appro_distant`), installe = sortie et retour = 0 par défaut; le demandeur choisit une quantité à saisir, l'autre est calculée et contrôlée entre 0 et la sortie. Un retour positif est transféré à l'emplacement source (picking entrant pour une sortie, transfert interne depuis `location_dest_id` pour un approvisionnement distant). Pour `retour_materiel`, l'assistant affiche la quantité validée au Stock en lecture seule et ne réécrit pas la ligne ni ne crée de mouvement. Le Chef doit toujours fournir le motif de clôture exceptionnelle. |
| Confirmation Chef | Aucune donnée métier saisie | Appelle `action_valider_chef()`. |
| Confirmation Stock | Aucune donnée métier saisie | Appelle `action_valider_magasin()`. |

Chaque ligne du wizard mémorise ses valeurs initiales (`qty_sortie_initiale`, `qty_retour_initiale`, `motif_ecart_initial`). Une ligne non modifiée reçoit automatiquement `qty_sortie = qty_demandee` et `qty_retour = 0.0`.

Pour les deux interventions dont le sens est uniquement `Sortie` (« Nouvelle installation client » et « Installation interne ») et pour l'approvisionnement distant (`appro_distant`, sens `Transfert`), `qty_installee` et `qty_retour` ne sont pas modifiables sur la demande ni dans le wizard Stock; ils le sont uniquement dans le wizard de clôture. Par ligne, `mode_saisie` choisit le champ actif. Le serveur recalcule la valeur complémentaire et rejette une quantité saisie négative ou supérieure à `qty_sortie`, même si l'on contourne l'interface.

Pour `retour_materiel`, le wizard Stock compare `qty_retour` à sa valeur initiale et exige un motif si elle diffère, quelle que soit la direction du changement. La clôture est une confirmation seule; les valeurs transmises par le wizard ne peuvent pas remplacer la quantité déjà validée au Stock.

À la clôture, les retours positifs de ces interventions créent un picking entrant depuis l'emplacement client vers `request.location_id`. Le lien de ce transfert est conservé dans `picking_retour_cloture_id`; le chatter et la notification de clôture mentionnent chaque article, sa quantité retournée et son emplacement d'origine.

Le chatter du wizard Stock regroupe les lignes modifiées dans un seul message à puces. Chaque article affiche son nom, sa quantité demandée, sa nouvelle quantité sortie et le motif; la puce est un caractère Unicode et non la séquence littérale `\u2022`. Le message est posté en note interne (`subtype="mail.mt_note"`), avec l'en-tête `Le Responsable Stock {utilisateur} a modifié les quantités.` et des libellés accentués (`Quantité demandée`, `Quantité sortie`, `Motif de modification`, `Quantité retournée`).

## 4. Cycle de vie d'un wizard

```text
Bouton de la demande -> action window modal + default_request_id
        `-> default_get() (si assistant de copie)
                `-> saisie temporaire
                        |-> Confirmer : appliquer l'action métier
                        `-> Annuler : fermer sans confirmation
```

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Données temporaires | Le wizard collecte des valeurs; les méthodes `action_*` déterminent les effets persistants. |
| Délégation | Les confirmations Chef/Stock appellent les méthodes de `dss.request`. |
| Modèle absent | `dss.validation.approuver.wizard` est référencé par une méthode, mais n'est pas déclaré dans les sources auditées. |
| Sources | [`models/`](../../models/), [`views/`](../../views/). |