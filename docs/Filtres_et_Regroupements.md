# Filtres, regroupements et menus par groupe — Sprint 12

Projet : DSS Odoo 10 (module `dss_v2`)
Date : 9 octobre 2026
Source : rapports de l'agent IA collés par Armel (inventaire, filtres communs, commentaires, groupes Chef et Magasin, menus, vérification finale).

---

## 1. Objectif

Faciliter la recherche des DSS par groupe d'utilisateurs : des **filtres rapides** propres à chaque groupe, puis des
**regroupements** pour les recherches plus fines. Ces filtres et menus sont une aide de navigation, **pas une sécurité** :
les droits d'accès restent à traiter à part (voir `Analyse_Cahier_des_Charges.md`, section 5).

## 2. Inventaire initial (agent, lecture seule)

**Vue de recherche existante** : `views/dss_request_search_views.xml`, vue `view_dss_request_search`, modèle `dss.request`.
Au départ, elle contenait seulement cinq champs de recherche : Numéro DSS (`name`), BCI (`bci`), Client (`partner_id`),
Lieu d'intervention (`lieu_intervention`) et Article (recherche sur `line_ids.product_id.name`). Aucun filtre, aucun regroupement.

**Champs utilisés** : tous sont **enregistrés en base** (déduit des définitions Python, la base PostgreSQL n'a pas été interrogée) :
`state`, `name`, `bci`, `partner_id`, `lieu_intervention`, `date_intervention`, `type_intervention`, `location_id`,
`signataire_chef_id`, `signataire_magasin_id`, `has_ecart`, `create_uid`. Le champ calculé `sens_mouvement` est aussi enregistré
(`store=True`) mais n'est pas utilisé ici.

**Clés de `state`** : `brouillon` (Brouillon), `valide_chef` (Validation Chef), `valide_magasin` (Validation Stock),
`approuve` (Approuve), `cloture` (Cloture), `rejete` (Rejete).

**Clés de `type_intervention`** : `nouvelle_installation`, `basculement`, `depannage`, `appro_distant` (approvisionnement de stock
distant), `installation_interne`, `retour_materiel`.

**Groupes** (`security/dss_security.xml`) : `dss_v2.group_dss_demandeur`, `dss_v2.group_dss_chef`, `dss_v2.group_dss_magasin`,
`dss_v2.group_dss_securite`.

**Le demandeur** : champ dédié `signataire_demandeur_id` (« Soumis par »), renseigné **à la soumission** dans
`dss_request_workflow.py`. `create_uid` désigne seulement le créateur de l'enregistrement, qui peut être une autre personne.
Conséquence : une demande **en brouillon n'a pas encore de demandeur** dans ce champ.

## 3. Fichiers

| Fichier | Statut | Lignes |
|---|---|---:|
| `views/dss_request_search_views.xml` | Créé puis étendu | 17 au départ, **169** à la fin |
| `views/dss_group_menus.xml` | Créé (5 actions, 5 menus) | **91** |
| `__manifest__.py` | Modifié : déclaration du fichier de menus après `views/dss_menu.xml` | 60 |

Ordre de chargement dans le manifest : vue de recherche, vues principales, `dss_menu.xml`, `dss_group_menus.xml`, vues d'affichage.
Aucun modèle Python, fichier de sécurité ni fichier du core d'Odoo n'a été modifié . Des commentaires XML détaillés
ont été ajoutés dans la vue de recherche.

## 4. Filtres réalisés

| Groupe | Filtre | Condition | Visibilité |
|---|---|---|---|
| Tous | Aujourd'hui | `date_intervention` entre aujourd'hui et demain | Tous |
| Tous | Cette semaine | du lundi courant au lundi suivant | Tous |
| Tous | Ce mois | du 1er du mois au 1er du mois suivant | Tous |
| Tous | Avec écart | `has_ecart = True` | Tous |
| Tous | Transferts inter-sites | `type_intervention = 'appro_distant'` | Tous |
| Chef | À valider | `state = 'valide_chef'` | `group_dss_chef` |
| Chef | Mes validations | `signataire_chef_id = uid` | `group_dss_chef` |
| Chef | À clôturer | `state = 'approuve'` | `group_dss_chef` |
| Chef | Rejetées | `state = 'rejete'` | `group_dss_chef` |
| Magasin | À valider Stock | `state = 'valide_magasin'` | `group_dss_magasin` |
| Magasin | Approuvées (à remettre) | `state = 'approuve'` | `group_dss_magasin` |
| Magasin | Mes validations Stock | `signataire_magasin_id = uid` | `group_dss_magasin` |

Les filtres de date utilisent `context_today()` et `relativedelta` ; `uid` désigne l'utilisateur connecté.

## 5. Regroupements réalisés

| Groupe | Regroupement | Champ | Visibilité |
|---|---|---|---|
| Tous | État | `state` | Tous |
| Tous | Type d'intervention | `type_intervention` | Tous |
| Tous | Client | `partner_id` | Tous |
| Chef | Demandeur | `signataire_demandeur_id` | `group_dss_chef` |
| Chef | Valideur Chef | `signataire_chef_id` | `group_dss_chef` |
| Chef | Date d'intervention (par semaine) | `date_intervention:week` | `group_dss_chef` |
| Magasin | Emplacement | `location_id` | `group_dss_magasin` |
| Magasin | Valideur Stock | `signataire_magasin_id` | `group_dss_magasin` |
| Magasin | Date d'intervention (par semaine) | `date_intervention:week` | `group_dss_magasin` |

Noms techniques tous distincts. Le libellé « Date d'intervention (par semaine) » apparaît deux fois (Chef et Magasin) sans conflit,
les restrictions de groupe étant différentes.

## 6. Menus d'accès rapide (fichier `dss_group_menus.xml`)

| Menu | Groupe | Condition |
|---|---|---|
| Mes demandes | Demandeur | demandes dont `signataire_demandeur_id` ou `create_uid` est l'utilisateur connecté |
| À valider | Chef | filtre par défaut « À valider » (`valide_chef`) |
| À valider Stock | Magasin | `state = 'valide_magasin'` |
| À remettre | Magasin | `state = 'approuve'` |
| À contrôler | Sécurité | `state = 'approuve'` — **provisoire** (pas d'étape Sécurité dans le workflow) |

Tous réutilisent les vues liste et formulaire existantes (`tree,form`).

## 7. Écarts et points à vérifier

1. **Filtres et regroupements des groupes Demandeur et Sécurité : absents des rapports.** Le tableau final de l'agent ne contient
   que les groupes Tous, Chef et Magasin. Les menus « Mes demandes » et « À contrôler » existent, mais les filtres de la barre de
   recherche pour ces deux groupes n'apparaissent dans aucun rapport. Soit ces deux étapes n'ont pas été faites, soit leur rapport
   n'a pas été transmis.
2. **Demandeur : attention aux brouillons.** `signataire_demandeur_id` n'est rempli qu'à la soumission. Les filtres « Mes demandes »
   et « Mes brouillons » doivent donc aussi s'appuyer sur `create_uid`, comme le fait déjà le menu « Mes demandes ».
3. **Menus : domaine fixe ou filtre par défaut ?** Le menu Chef utilise explicitement un filtre par défaut (que l'utilisateur peut retirer).
   Pour les menus Magasin et Sécurité, le rapport parle à la fois de « filtre activé par défaut » et de « domaine utilisé » : à vérifier,
   car un domaine d'action ne peut pas être retiré par l'utilisateur.

4. **Dépôt Git** : l'agent signale que `C:\ODOO_10_DEV` n'est pas un dépôt Git ; la vérification des fichiers modifiés s'est donc faite
   par les dates de modification. Les commits doivent être faits depuis le dépôt réel du projet, après un contrôle du diff.

6. **Libellés sans accents dans le modèle** : les états s'affichent « Approuve », « Cloture », « Rejete » et certains types
   « Depannage », « Retour de materiel (desinstallation) ». C'est cosmétique, mais cela fait contraste avec les filtres en français
   accentué. Les corriger demande de modifier le modèle Python : sujet à part.
9. **Un utilisateur membre de plusieurs groupes** doit voir les filtres de chacun : à tester.

## 9. Suivi d'avancement
 
- [x] Inventaire de la vue de recherche
- [x] Vue de recherche : champs de recherche
- [x] Filtres et regroupements communs
- [x] Filtres et regroupements du groupe Chef
- [x] Filtres et regroupements du groupe Magasin
- [x] Menus d'accès rapide par groupe (fichier `dss_group_menus.xml`)
- [ ] Filtres et regroupements du groupe Demandeur (non confirmé)
- [ ] Filtres et regroupements du groupe Sécurité (provisoire, non confirmé)
- [ ] Test dans Odoo avec un utilisateur de chaque groupe
- [x] Commits des filtres communs, Chef, Magasin et des menus (5 commits du 9 octobre 2026, section 10)
- [ ] Revue de la partie Sécurité après la réponse de l'encadreur (question 3)
## 10. Commits (dépôt `C:\ODOO_10_DEV\custom-addons\dss_v2`, 9 octobre 2026)
 
| Heure | Hash | Message |
|---|---|---|
| 15:43 | `a5e6589` | `feat(manifest): add search view for DSS requests` |
| 16:10 | `723d980` | `Ajoute filtres et regroupements DSS` |
| 16:19 | `94f0512` | `feat(dss_v2): add advanced filters and groupings for DSS Chef` |
| 16:26 | `d14a844` | `feat(dss_v2): add filters and groupings for DSS / Magasin users` |
| 16:42 | `7f21654` | `feat(dss_v2): add group menus for DSS user roles` |