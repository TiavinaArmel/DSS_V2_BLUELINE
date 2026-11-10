# Modèle `dss.request`

## 1. Rôle

`dss.request` est le modèle persistant de l'en-tête d'une demande. Il porte les références métier, les emplacements, le type d'intervention, les états, les signataires et la relation vers les lignes. Les actions de workflow et les traitements associés sont ajoutés dans des extensions séparées.

## 2. Champs

| Champ | Type Odoo | Attributs visibles dans le code | Description |
|---|---|---|---|
| `name` | `Char` | `copy=False`, `readonly=True`, défaut `/` | Numéro produit par la séquence `dss.request` dans `create()`. |
| `state` | `Selection` | Défaut `brouillon` | État du workflow; clés listées ci-dessous. |
| `bci` | `Char` | Aucun `required=True` | Référence administrative, contrôlée à la soumission. |
| `partner_id` | `Many2one(res.partner)` | Aucun `required=True` | Client de l'intervention. |
| `lieu_intervention` | `Char` | Aucun `required=True` | Lieu saisi pour l'intervention. |
| `date_intervention` | `Date` | Défaut `fields.Date.today` | Date prévue/renseignée pour l'intervention. |
| `demandeur_id` | `Many2one(res.users)` | `required=True`, `readonly=True`, `copy=False` | Propriétaire de la DSS, déterminé à la création depuis l'utilisateur cible ou `dss_user_id`. |
| `service_demandeur_id` | `Many2one(dss.service)` | Défaut depuis le service actif du demandeur; `readonly` dans la vue | Service DSS affecté automatiquement; les corrections par un administrateur après soumission sont tracées dans le chatter. |
| `is_current_user_chef` | `Boolean` | Calculé, non stocké | Indicateur d'affichage; vrai lorsque l'utilisateur courant est le Chef DSS configuré sur le service. L'autorisation est revérifiée par le workflow. |
| `location_id` | `Many2one(stock.location)` | Domaine `usage = internal` | Emplacement source. |
| `location_dest_id` | `Many2one(stock.location)` | Domaine `usage = internal` | Destination interne, notamment pour `appro_distant`. |
| `type_intervention` | `Selection` | Six valeurs | Catégorie métier qui détermine le sens calculé. |
| `sens_mouvement` | `Char` | `compute`, `store=True`, `readonly=True` | Sens de stock dérivé du type d'intervention. |
| `picking_id` | `Many2one(stock.picking)` | `readonly=True` | Lien vers le dernier picking affecté par les méthodes DSS. |
| `has_ecart` | `Boolean` | `readonly=True` | Indicateur calculé à la validation Stock et à la clôture lorsque `qty_sortie + qty_retour` diffère de `qty_demandee` à deux décimales près. |
| `is_qty_modified` | `Boolean` | Défaut `False`, `readonly=True`, `copy=False` | Indique que le wizard de modification des quantités a été confirmé. |
| `motif_rejet` | `Text` | Aucun | Motif reporté depuis le wizard de rejet. |
| `line_ids` | `One2many(dss.request.line)` | Relation inverse `request_id` | Lignes de la demande. |
| `signataire_demandeur_id` | `Many2one(res.users)` | `readonly=True`, `copy=False` | Acteur ayant soumis la demande; distinct du propriétaire `demandeur_id`. |
| `date_soumission` | `Datetime` | `readonly=True`, `copy=False` | Horodatage de soumission. |
| `signataire_chef_id` | `Many2one(res.users)` | `readonly=True` | Utilisateur ayant validé l'étape Chef. |
| `date_validation_chef` | `Datetime` | `readonly=True` | Horodatage de validation Chef. |
| `signataire_magasin_id` | `Many2one(res.users)` | `readonly=True` | Utilisateur ayant validé l'étape Stock. |
| `date_validation_magasin` | `Datetime` | `readonly=True` | Horodatage de validation Stock. |

Les champs métiers de soumission ne portent pas `required=True` dans le modèle; l'action de soumission les vérifie au moment du changement d'état.

## 3. Méthodes du fichier de base

| Méthode | Décorateur | Rôle |
|---|---|---|
| `_compute_sens_mouvement` | `@api.depends('type_intervention')` | Associe chaque type au sens correspondant. |
| `_onchange_type_intervention_lines` | `@api.onchange('type_intervention')` | Met à jour `qty_demandee_readonly` des lignes pour un retour matériel. |
| `create` | `@api.model` | Détermine le demandeur cible, affecte son service actif et génère le numéro DSS si `name` vaut `/`. |
| `_default_service_demandeur` | `@api.model` | Préremplit le service actif du demandeur, s'il en a un. |
| `write` | `@api.multi` | Réserve la modification du service au superuser/administrateur et trace les changements après soumission. |
| `_onchange_location_id_qty_standard` | `@api.onchange('location_id')` | Recalcule la disponibilité des articles pour l'emplacement sélectionné. |

Les méthodes de transition sont documentées dans [le workflow](03-dss-request-workflow.md).

La validation Stock utilise `is_qty_modified` pour distinguer une validation directe d'une validation confirmée par le wizard de quantités. En validation directe, `qty_sortie` reprend `qty_demandee` et `qty_retour` est remis à zéro.

## 4. Machine à états

```text
brouillon --soumettre--> valide_chef --valider Chef--> valide_magasin
valide_magasin --valider Stock--> approuve --cloturer--> cloture
valide_chef --rejeter--> rejete
valide_magasin --rejeter--> rejete
rejete --renvoi par un Chef--> brouillon
```

Le code ne déclare pas de transition Sécurité pour `dss.request`.

## 5. Valeurs de `state`

| Clé | Libellé défini dans le modèle | Acteur/action observé(e) |
|---|---|---|
| `brouillon` | Brouillon | État initial; soumission depuis le formulaire. |
| `valide_chef` | Validation Chef | Étape présentée au groupe Chef. |
| `valide_magasin` | Validation Stock | Étape présentée au groupe Magasin. |
| `approuve` | Approuve | Après génération des mouvements par l'action Stock. |
| `cloture` | Cloture | État défini par le wizard de clôture. |
| `rejete` | Rejete | État défini par l'action de rejet. |

Les libellés sans accents ci-dessus sont ceux du code source; la vue peut présenter d'autres textes pour les boutons.

## 6. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Numérotation | `create()` utilise le code de séquence `dss.request`. |
| Sens | `sens_mouvement` est stocké et recalculé selon `type_intervention`. |
| Contrôles | Les champs requis de soumission sont validés par l'action, pas par `required=True` sur tous les champs. |
| Source | [`models/dss_request.py`](../../models/dss_request.py). |