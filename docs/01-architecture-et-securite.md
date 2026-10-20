# Architecture et sécurité

## 1. Arborescence du module

```text
dss_v2/
|-- __init__.py                 # Charge le package models
|-- __manifest__.py             # Métadonnées, dépendances et données XML/CSV
|-- data/                       # Séquence et modèle de courriel
|-- docs/                       # Documentation du module
|-- migrations/2.2/             # Migration de l'identifiant du format PDF
|-- models/                     # Modèles, extensions, workflow et assistants
|-- report/                     # Rapport QWeb et format papier
|-- security/                   # Groupes et droits d'accès aux modèles
|-- static/src/css/             # Styles de l'interface et du rapport
|-- tests/                      # Tests Odoo du routage des notifications
`-- views/                      # Formulaires, listes, recherche, menus et wizards
```

Les fichiers compilés Python (`.pyc`) présents localement ne sont pas des sources du module. Le dossier `.git/` relève du dépôt et n'est pas détaillé ici.

## 2. Couches du module

| Couche | Dossier ou fichier | Rôle vérifié |
|---|---|---|
| Métadonnées | `__manifest__.py` | Déclare la version `2.4`, les dépendances et les fichiers de données chargés. |
| Modèles | `models/` | Définit la demande, ses lignes, les extensions Odoo et les traitements métier. |
| Interface | `views/` | Déclare les vues, filtres, menus et fenêtres modales. |
| Sécurité | `security/` | Crée quatre groupes et déclare les ACL CSV; aucune règle d'enregistrement n'est définie dans le XML fourni. |
| Données | `data/` | Déclare la séquence DSS et le template de courriel. |
| Rapport | `report/` | Déclare le rapport QWeb du bon de livraison et son format A5 paysage. |
| Assets | `static/`, `views/assets_backend.xml` | Fournit les CSS du chatter et du rapport. |
| Tests | `tests/` | Vérifie principalement la création et le routage des courriels sans SMTP. |

## 3. Chargement et flux de données

```text
Chargement du module
__manifest__.py -> fichiers XML/CSV déclarés dans data
__init__.py -> models/__init__.py -> extensions et modèles Python

Traitement d'une demande
Utilisateur -> vue XML -> methode du modele -> ORM Odoo -> PostgreSQL
                                      |-> stock.picking / stock.move
                                      |-> chatter et file mail.mail
                                      `-> rapport QWeb -> PDF / ir.attachment
```

L'ordre exact des imports Python est défini dans [`models/__init__.py`](../models/__init__.py). L'ordre des fichiers XML/CSV est défini dans [`__manifest__.py`](../__manifest__.py).

## 4. Groupes de sécurité

| Identifiant XML | Libellé | Usage visible dans le module |
|---|---|---|
| `dss_v2.group_dss_demandeur` | DSS / Demandeur | Menu « Mes demandes ». |
| `dss_v2.group_dss_chef` | DSS / Chef | Boutons Chef, filtres et menu de validation. |
| `dss_v2.group_dss_magasin` | DSS / Magasin | Boutons Stock, modification des quantités et menus Magasin. |
| `dss_v2.group_dss_securite` | DSS / Securite | Vue en lecture seule et menu « À contrôler » provisoire. |

Le groupe Sécurité n'ajoute pas d'étape au workflow `dss.request`. Les états et transitions de cette demande sont décrits dans [le cycle de vie](04-workflow/00-cycle-de-vie.md). Un circuit différent existe sur `stock.picking`; voir [les héritages](02-models/08-heritages.md).

## 5. Droits CRUD

| Modèle | Groupe dans l'ACL | Lire | Écrire | Créer | Supprimer |
|---|---|---:|---:|---:|---:|
| `dss.request` | Aucun (`group_id` vide) | Oui | Oui | Oui | Oui |
| `dss.request.line` | Aucun (`group_id` vide) | Oui | Oui | Oui | Oui |
| `dss.qty.sortie.wizard` et sa ligne | DSS / Magasin | Oui | Oui | Oui | Oui |
| `dss.rejet.wizard` | Aucun (`group_id` vide) | Oui | Oui | Oui | Oui |
| `dss.cloture.wizard` et sa ligne | DSS / Chef | Oui | Oui | Oui | Oui |
| `dss.notification.log` | Aucun (`group_id` vide) | Oui | Oui | Oui | Non |

Les droits effectifs peuvent aussi dépendre des ACL des autres modules et des groupes hérités de l'utilisateur. Les restrictions `groups`, `attrs` et les vues en lecture seule ne remplacent pas les contrôles serveur.

## 6. Règles d'enregistrement

`security/dss_security.xml` crée la catégorie et les groupes; il ne contient pas de record rule (`ir.rule`). Les domaines des actions de menus servent à filtrer des listes, pas à isoler les enregistrements pour des accès directs à l'ORM.

À noter dans le code actuel : `action_renvoyer_demandeur()` vérifie le groupe Chef côté serveur; les actions de soumission, rejet et validation reposent principalement sur les boutons de vue et, pour les validations Chef/Stock, sur l'état attendu. `action_rejeter()` ne vérifie pas l'état de départ. Voir [les droits détaillés](07-securite/01-droits-crud.md).

## 7. Dépendances

| Dépendance | Utilisation dans le module |
|---|---|
| `web` | Interface Web et bundle d'assets backend. |
| `stock` | Articles, emplacements, quantités, pickings et mouvements. |
| `mail` | Chatter, templates et file de courriels. |

## 8. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Source de vérité | Le manifeste, les modèles Python et les XML définissent le comportement réel. |
| Sécurité | Groupes, ACL, restrictions de vue et règles d'enregistrement sont des mécanismes distincts. |
| Workflow principal | `dss.request` n'a pas d'étape de validation Sécurité. |
| Versions | Le manifeste indique `2.4`; il ne déclare pas de version Python. |