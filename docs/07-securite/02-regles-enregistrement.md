# Règles d'enregistrement

## 1. Rôle

Une règle d'enregistrement (`ir.rule`) filtre les enregistrements accessibles selon un domaine. Elle intervient au-delà des permissions CRUD accordées par les ACL.

## 2. Déclarations dans le module

| Fichier audité | Déclaration trouvée |
|---|---|
| `security/dss_security.xml` | Catégorie et groupes `res.groups`; aucune donnée `ir.rule`. |
| `security/ir.model.access.csv` | ACL de modèles, pas des record rules. |
| `views/dss_group_menus.xml` | Domaine de menu Demandeur et domaine fixe du menu Sécurité; filtres de navigation. |

Les domaines de recherche et d'action n'empêchent pas un accès à un enregistrement par un autre chemin si les droits ORM le permettent. Cette documentation ne conclut pas sur les règles fournies par d'autres modules Odoo ou par la base installée.

## 3. Différence avec les ACL

| Mécanisme | Question traitée |
|---|---|
| ACL (`ir.model.access`) | L'utilisateur peut-il lire, écrire, créer ou supprimer ce modèle ? |
| Record rule (`ir.rule`) | Quels enregistrements de ce modèle peut-il lire ou modifier ? |
| `groups` de vue / `attrs` | Quels éléments l'interface affiche-t-elle ou rend-elle éditables ? |
| Domaine d'action | Quels enregistrements sont présentés par cette action de menu ? |

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| État du module | Aucune record rule DSS n'est déclarée dans les fichiers audités. |
| Filtrage | Les filtres et menus ne remplacent pas les record rules. |
| Vérification | Les règles effectives d'une base installée peuvent venir d'autres modules. |