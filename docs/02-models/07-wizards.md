# Wizards DSS

## 1. Liste des assistants

| Assistant | Modèle temporaire | Rôle | Déclencheur |
|---|---|---|---|
| Rejet | `dss.rejet.wizard` | Recueille le motif obligatoire puis appelle le rejet de la demande. | Bouton « Rejeter » du Chef ou du Magasin. |
| Quantités Stock | `dss.qty.sortie.wizard` et lignes | Copie les lignes et permet de modifier sortie/retour. | Bouton « Modifier Qte ». |
| Clôture | `dss.cloture.wizard` et lignes | Copie les lignes, recueille installé/retour, détecte les écarts et clôture. | Bouton Chef « Cloturer ». |
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
| Quantités | `qty_sortie`, `qty_retour`, `motif_ecart` | Exige un motif par article si la sortie diffère de la demande, conserve `qty_demandee`, écrit les quantités et marque la demande comme modifiée. |
| Clôture | `qty_installee`, `qty_retour` | Écrit les lignes, conserve la règle d'écart fondée sur demande/sortie/retour, passe à `cloture`, poste un résumé et notifie. |
| Confirmation Chef | Aucune donnée métier saisie | Appelle `action_valider_chef()`. |
| Confirmation Stock | Aucune donnée métier saisie | Appelle `action_valider_magasin()`. |

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