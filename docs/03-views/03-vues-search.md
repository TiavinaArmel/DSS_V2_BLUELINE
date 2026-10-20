# Recherche, filtres et regroupements

## 1. Champs de recherche

| Libellé | Champ ou domaine |
|---|---|
| Numéro DSS | `name` |
| BCI | `bci` |
| Client | `partner_id` |
| Lieu d'intervention | `lieu_intervention` |
| Article | `line_ids.product_id.name ilike self` |

## 2. Filtres définis

| Portée | Filtre | Domaine ou critère |
|---|---|---|
| Tous | Aujourd'hui | `date_intervention` de `context_today()` inclus à demain exclu. |
| Tous | Cette semaine | Lundi courant inclus, lundi suivant exclu. |
| Tous | Ce mois | Premier jour du mois courant inclus, premier jour du mois suivant exclu. |
| Tous | Avec écart | `has_ecart = True`. |
| Tous | Transferts inter-sites | `type_intervention = appro_distant`. |
| Chef | À valider | `state = valide_chef`. |
| Chef | Mes validations | `signataire_chef_id = uid`. |
| Chef | À clôturer | `state = approuve`. |
| Chef | Rejetées | `state = rejete`. |
| Magasin | À valider Stock | `state = valide_magasin`. |
| Magasin | Approuvées (à remettre) | `state = approuve`. |
| Magasin | Mes validations Stock | `signataire_magasin_id = uid`. |

Les filtres temporels utilisent `context_today()` et `relativedelta`; `uid` représente l'utilisateur connecté. L'accès aux filtres limités par `groups` ne constitue pas une règle de sécurité des enregistrements.

## 3. Regroupements

| Portée | Libellé | Champ |
|---|---|---|
| Tous | État | `state` |
| Tous | Type d'intervention | `type_intervention` |
| Tous | Client | `partner_id` |
| Chef | Demandeur | `signataire_demandeur_id` |
| Chef | Valideur Chef | `signataire_chef_id` |
| Chef | Date d'intervention (par semaine) | `date_intervention:week` |
| Magasin | Emplacement | `location_id` |
| Magasin | Valideur Stock | `signataire_magasin_id` |
| Magasin | Date d'intervention (par semaine) | `date_intervention:week` |

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Filtres | Ils ajoutent un domaine de recherche, ils ne limitent pas les accès ORM. |
| Groupes | Les filtres Chef et Magasin portent des attributs `groups`. |
| Demandeur/Sécurité | Aucun filtre spécifique à ces groupes n'est déclaré dans cette vue. |
| Source | [`views/dss_request_search_views.xml`](../../views/dss_request_search_views.xml). |