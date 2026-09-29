.
# Jour 1 — Architecture générale et sécurité

**Auteur :** Tiavina Armel
**Contexte :** Odoo 10 Community — Python 2.7 — XML
**Module :** DSS V2 – Demande de Sortie de Stock

## Objectifs du jour

- Expliquer le rôle du manifest
- Expliquer le rôle du `__init__.py`
- Distinguer groupe de sécurité et droit CRUD
- Lire et interpréter un fichier `ir.model.access.csv`
- Repérer les points fragiles de la sécurité

---

## 1. Architecture générale du module

```
dss/
│
├── __init__.py              → point d'entrée Python du module
├── __manifest__.py          → fiche d'identité du module Odoo
├── .gitignore                → config Git (pas Odoo)
│
├── data/
│   └── dss_sequence.xml     → séquence de numérotation des DSS
│
├── models/                   → logique métier Python (ORM Odoo)
│   ├── __init__.py
│   ├── dss_request.py
│   ├── dss_request_display.py
│   ├── dss_cloture_wizard.py
│   ├── dss_qty_sortie_wizard.py
│   ├── dss_validation_wizard.py
│   ├── product_template.py
│   └── stock_picking.py
│
├── views/                    → interface XML (form, tree, menu…)
│   ├── dss_request_views.xml
│   ├── dss_request_display_views.xml
│   ├── dss_cloture_wizard_views.xml
│   ├── dss_qty_sortie_wizard_views.xml
│   ├── dss_validation_wizard_views.xml
│   ├── dss_rejet_wizard_views.xml
│   └── dss_menu.xml
│
├── security/                 → droits d'accès
│   ├── dss_security.xml
│   └── ir.model.access.csv
│
└── report/
    └── dss_report.xml        → rapport PDF
```

> Les fichiers `.pyc` sont des fichiers compilés par Python 2.7 — on ne les édite jamais.

---

## 2. `__manifest__.py`

### Rôle

Le manifest est la carte d'identité du module Odoo. Odoo le lit en premier pour installer ou mettre à jour le module. Il contient le nom du module, sa version, ses dépendances, la liste des fichiers XML/CSV à charger, et les options d'installation.

### Contenu analysé

```python
{
    "name": "DSS V2 - Demande de Sortie de Stock",
    "version": "2.1",
    "depends": ["stock", "mail"],
    "author": "Tiavina Armel",
    "category": "Inventory",
    "description": "Digitalisation des Demandes de Sortie de Stock (DSS) selon cahier des charges",
    "data": [
        "security/dss_security.xml",
        "security/ir.model.access.csv",
        "data/dss_sequence.xml",
        "views/dss_qty_sortie_wizard_views.xml",
        "views/dss_rejet_wizard_views.xml",
        "views/dss_cloture_wizard_views.xml",
        "views/dss_validation_wizard_views.xml",
        "views/dss_request_views.xml",
        "views/dss_menu.xml",
        "views/dss_request_display_views.xml",
        "report/dss_report.xml",
    ],
    "application": True,
    "installable": True,
}
```

### Explication ligne par ligne

| Clé | Rôle |
|---|---|
| `name` | Nom lisible du module dans la liste des applications Odoo |
| `version` | Version du module (ici `2.1`) |
| `depends` | Modules Odoo obligatoires — `stock` pour les mouvements de stock, `mail` pour le chatter et les notifications |
| `author` | Auteur du module |
| `category` | Catégorie Odoo (`Inventory`) |
| `description` | Description fonctionnelle rapide |
| `data` | Liste **ordonnée** des fichiers XML/CSV chargés — ordre : sécurité → données → vues → menus → rapport |
| `application` | Le module apparaît comme une application |
| `installable` | Le module peut être installé |

### Points importants

- Les modèles Python ne sont **pas** chargés par le manifest — ils sont chargés par `__init__.py`.
- Un `"""..."""` au milieu d'un dictionnaire Python n'est **pas** un commentaire, c'est une chaîne de caractères : cela provoque une erreur de syntaxe.
- Les commentaires `#` sont autorisés en Python, y compris en fin de ligne. En CSV, aucun commentaire n'est autorisé.

---

## 3. `__init__.py` (racine)

### Rôle

Transforme un dossier Python en package importable. Celui de la racine du module DSS importe uniquement le dossier `models`.

```python
from . import models
```

### Explication

- `from` : mot-clé Python d'importation
- `.` : désigne le dossier courant (racine du module DSS)
- `import models` : importe le package `models/`

### Conséquence

Sans ce fichier, aucun modèle Python n'est chargé : pas de `dss.request`, pas de `dss.request.line`, pas de wizard, pas de logique métier.

### Chaîne de chargement

```
__manifest__.py     → charge XML + CSV
__init__.py          → charge models/
models/__init__.py   → charge les fichiers .py un par un
```

---

## 4. `security/dss_security.xml`

### Rôle

Définit la catégorie DSS et les 4 groupes de sécurité du module.

> **Important :** ce fichier ne donne **aucun** droit. Il crée seulement des groupes (des étiquettes).

### Contenu analysé

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="module_category_dss" model="ir.module.category">
        <field name="name">DSS</field>
    </record>

    <record id="group_dss_demandeur" model="res.groups">
        <field name="name">DSS / Demandeur</field>
        <field name="category_id" ref="module_category_dss"/>
    </record>

    <record id="group_dss_chef" model="res.groups">
        <field name="name">DSS / Chef</field>
        <field name="category_id" ref="module_category_dss"/>
    </record>

    <record id="group_dss_magasin" model="res.groups">
        <field name="name">DSS / Magasin</field>
        <field name="category_id" ref="module_category_dss"/>
    </record>

    <record id="group_dss_securite" model="res.groups">
        <field name="name">DSS / Securite</field>
        <field name="category_id" ref="module_category_dss"/>
    </record>
</odoo>
```

### Explication ligne par ligne

| Élément | Rôle |
|---|---|
| `<?xml version="1.0" encoding="utf-8"?>` | Déclaration XML standard |
| `<odoo>` | Balise racine des fichiers Odoo 10 |
| `ir.module.category` | Catégorie affichée dans la page Utilisateurs |
| `res.groups` | Modèle Odoo représentant un groupe de sécurité |
| `ref="module_category_dss"` | Référence à un autre `record` XML |

### Les 4 groupes du DSS

| Groupe | Rôle métier |
|---|---|
| `group_dss_demandeur` | Crée et soumet une DSS |
| `group_dss_chef` | Valide et clôture une DSS |
| `group_dss_magasin` | Prépare la sortie physique du stock |
| `group_dss_securite` | Contrôle la sortie du stock |

### Lien avec les autres fichiers

```
security/dss_security.xml     → crée les groupes
security/ir.model.access.csv  → donne les droits CRUD
views/*.xml                   → affiche/masque boutons selon groups="..."
models/*.py                   → applique la logique métier selon le groupe
```

---

## 5. `security/ir.model.access.csv`

### Rôle

Accorde les droits CRUD aux groupes de sécurité, sur chaque modèle Odoo.

### Rappel CRUD

| Lettre | Signification | Champ CSV |
|---|---|---|
| C | Create — créer | `perm_create` |
| R | Read — lire | `perm_read` |
| U | Update — modifier (`write`) | `perm_write` |
| D | Delete — supprimer (`unlink`) | `perm_unlink` |

### Colonnes du fichier

`id, name, model_id:id, group_id:id, perm_read, perm_write, perm_create, perm_unlink`

### Règles importantes

- `group_id:id` **vide** → la règle s'applique à **tous** les utilisateurs Odoo connectés.
- `group_id:id` **rempli** → la règle s'applique uniquement à ce groupe.
- **Aucune ligne pour un modèle** → seul l'administrateur y a accès (pas d'ouverture par défaut).
- `model_id:id` = nom technique du modèle, points remplacés par des underscores, préfixé par `model_`. Exemple : `dss.request` → `model_dss_request`.

### Contenu analysé

| Ligne | Modèle | Groupe | Statut |
|---|---|---|---|
| 1 | `dss.request` | *(vide)* | ⚠️ ouvert à tous |
| 2 | `dss.request.line` | *(vide)* | ⚠️ ouvert à tous |
| 3 | `dss.qty.sortie.wizard` | `DSS / Magasin` | ✅ correct |
| 4 | `dss.qty.sortie.wizard.line` | `DSS / Magasin` | ✅ correct |
| 5 | `dss.rejet.wizard` | *(vide)* | ⚠️ ouvert à tous |
| 6 | `dss.cloture.wizard` | `DSS / Chef` | ✅ correct |
| 7 | `dss.cloture.wizard.line` | `DSS / Chef` | ✅ correct |

### Points fragiles identifiés

1. `dss.request` et `dss.request.line` sont ouverts à tout utilisateur connecté → faille de sécurité métier potentielle.
2. `dss.rejet.wizard` est ouvert à tous → un utilisateur quelconque pourrait rejeter une DSS.
3. `perm_unlink = 1` sur les wizards est souvent superflu.
4. Aucune ligne pour `dss.request.display`, `dss.validation.wizard`, `product.template` (hérité), `stock.picking` (hérité) → **à vérifier en pratique** : sans règle, ces modèles ne sont accessibles qu'à l'administrateur. Pour `product.template` et `stock.picking`, qui existent déjà dans le module `stock`, leurs droits d'accès existent probablement déjà là-bas — donc ce n'est pas forcément un bug ici.

---

## 6. Exercices — corrigé

**Q1. Différence entre `dss_security.xml` et `ir.model.access.csv` ?**
`dss_security.xml` crée les groupes. `ir.model.access.csv` accorde les droits CRUD à ces groupes.

**Q2. Pourquoi un groupe seul ne donne aucun droit ?**
Un groupe est une étiquette. Il ne donne de droits que si `ir.model.access.csv` lui en accorde explicitement.

**Q3. Que se passe-t-il si un utilisateur n'appartient à aucun groupe DSS ?**
Il n'a aucun droit sur les modèles DSS protégés par un groupe ; les modèles à `group_id:id` vide restent en revanche accessibles.

**Q4. Pourquoi `module_category_dss` est-elle utile ?**
Elle regroupe les 4 groupes DSS dans la page Utilisateurs, pour les retrouver facilement.

**Q5. Pourquoi les lignes 1, 2 et 5 sont-elles anormales ?**
`group_id:id` vide → tous les utilisateurs ont les droits CRUD sur `dss.request`, `dss.request.line` et `dss.rejet.wizard`.

**Q6. Pourquoi les lignes 6 et 7 sont-elles correctes ?**
Elles limitent les droits au groupe `dss_v2.group_dss_chef` : seuls les utilisateurs DSS / Chef peuvent clôturer une DSS.

---

## Points à revoir

- Ne pas confondre : vue ≠ rapport · modèle ≠ wizard · groupe ≠ droit · `write` ≠ `create`
- Toujours écrire les droits dans l'ordre : `perm_read, perm_write, perm_create, perm_unlink`
- `model_id:id` doit être **exactement** : nom du modèle → `.` remplacés par `_` → préfixé par `model_`
- Un fichier CSV ne supporte pas les commentaires `#`