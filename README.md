# DSS V2 — Demande de Sortie de Stock

Module Odoo permettant de digitaliser et de suivre les demandes de sortie de stock au sein de l’entreprise.

> **Compatibilité actuelle : Odoo 10 Community**

## 1. Présentation

Le module **DSS V2** permet de créer, valider, rejeter, clôturer et suivre les demandes de sortie de stock.

Il prend en charge le workflow complet d’une demande, depuis sa création jusqu’à la sortie effective des articles du magasin.

## 2. Fonctionnalités principales

- Création d’une demande de sortie de stock ;
- Attribution automatique d’un numéro DSS ;
- Ajout de plusieurs articles dans une demande ;
- Gestion des quantités demandées et des quantités sorties ;
- Validation par le responsable et par le magasin ;
- Rejet d’une demande avec indication du motif ;
- Clôture d’une demande ;
- Suivi de l’état d’avancement de la demande ;
- Historique des échanges dans le chatter Odoo ;
- Suivi des activités et notifications internes ;
- Création et gestion du bon de livraison ;
- Génération d’un bon de livraison au format PDF ;
- Recherche, filtres et regroupements avancés ;
- Gestion des droits d’accès selon le rôle de l’utilisateur.

## 3. Workflow

Le modèle `dss.request` définit le parcours suivant :

```text
brouillon -> valide_chef -> valide_magasin -> approuve -> cloture
valide_chef -> rejete
valide_magasin -> rejete
rejete -> brouillon (renvoi par le groupe Chef)
```

Le rejet passe par un wizard qui exige un motif. Le code ne définit pas d'état de sortie partielle.

## 4. Rôles utilisateurs

- **Demandeur** : crée et consulte ses demandes ;
- **Chef** : vérifie et valide les demandes ;
- **Magasin** : prépare et effectue la sortie des articles ;
- **Sécurité** : consulte et contrôle les opérations selon les droits accordés.

Les groupes et les droits d’accès sont configurés dans le dossier `security/`.

## 5. Compatibilité et dépendances

| Élément | Valeur |
|---|---|
| Nom technique | `dss_v2` |
| Nom affiché | DSS V2 - Demande de Sortie de Stock |
| Version du module | 2.4 |
| Version Odoo supportée actuellement | Odoo 10 Community |
| Catégorie | Inventory |
| Auteur | Tiavina Armel |
| Dépendances Odoo | `web`, `stock`, `mail` |

Le README annonce Odoo 10 Community. Le manifeste ne fixe pas de version Python; le cahier de projet mentionne Python 2.7. Vérifier l'interpréteur réellement utilisé par l'instance.

## 6. Installation

### 1. Copier le module

Copier le dossier `dss_v2` dans le répertoire des modules personnalisés Odoo :

```text
C:\ODOO_10_DEV\custom-addons\dss_v2
```

### 2. Vérifier le chemin des modules

Vérifier que le fichier de configuration Odoo contient le chemin du dossier `custom-addons` :

```ini
addons_path = C:\chemin\vers\odoo\addons,C:\ODOO_10_DEV\custom-addons
```

### 3. Installer le module

1. Redémarrer le serveur Odoo ;
2. Activer le mode développeur ;
3. Aller dans **Applications** ;
4. Cliquer sur **Mettre à jour la liste des applications** ;
5. Rechercher `DSS V2` ;
6. Installer le module.

### Mise à jour depuis la ligne de commande

```bash
python odoo-bin -c odoo.conf -d NOM_DE_LA_BASE -u dss_v2
```

Remplacer `NOM_DE_LA_BASE` par le nom réel de la base de données.

## 7. Structure du module

```text
dss_v2/
├── __init__.py
├── __manifest__.py
├── data/                 # Séquences DSS
├── docs/                 # Documentation technique et fonctionnelle
├── migrations/           # Scripts de migration
├── models/               # Modèles et assistants Python
├── report/               # Rapport PDF
├── security/             # Groupes et droits d’accès
├── static/               # Feuilles de style CSS
└── views/                # Vues, menus et actions XML
```

## 8. Tests à effectuer après l’installation

- Créer une demande DSS ;
- Ajouter et modifier les lignes d’articles ;
- Valider la demande en tant que chef ;
- Valider et traiter la demande en tant que magasin ;
- Rejeter une demande avec un motif ;
- Gérer les quantités sorties ;
- Créer le bon de livraison ;
- Générer le bon de livraison PDF ;
- Vérifier le chatter et les notifications ;
- Tester les recherches, filtres et regroupements ;
- Vérifier l’affichage des menus selon les rôles ;
- Vérifier le respect des droits d’accès ;
- Clôturer une demande terminée.

## 9. Documentation

L'index de la documentation technique et fonctionnelle se trouve dans [`docs/README.md`](docs/README.md). Il présente l'architecture, les modèles, les vues, le workflow, les rapports, les intégrations, la sécurité, les tests et la maintenance.

## 10. Développement

Avant toute modification :

```bash
git status
git pull
```

Créer une branche dédiée pour chaque évolution :

```bash
git checkout -b feature/nom-de-la-fonctionnalite
```

Après les modifications :

```bash
git add .
git commit -m "feat: description de la modification"
git push origin feature/nom-de-la-fonctionnalite
```

## 11. Dépôt

Le projet est hébergé sur GitHub :

```text
https://github.com/TiavinaArmel/DSS_V2_BLUELINE.git
```

## 12. Auteur

**Tiavina Armel**

Module développé pour la gestion des demandes de sortie de stock dans Odoo 10 Community.

## 13. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Version | `2.4`, selon le manifeste. |
| Workflow | Chef puis Stock; le workflow principal n'a pas d'étape Sécurité. |
| Documentation détaillée | [`docs/README.md`](docs/README.md). |