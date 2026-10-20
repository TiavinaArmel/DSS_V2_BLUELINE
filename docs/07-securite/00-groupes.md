# Groupes DSS

## 1. Catégorie

`security/dss_security.xml` crée la catégorie Odoo `DSS`, puis y rattache les groupes du module. Ce fichier ne déclare pas de relation hiérarchique ni de droits CRUD.

## 2. Groupes déclarés

| XML ID | Nom affiché | Usage déclaré ou visible |
|---|---|---|
| `dss_v2.group_dss_demandeur` | DSS / Demandeur | Accès au menu « Mes demandes ». |
| `dss_v2.group_dss_chef` | DSS / Chef | Validations Chef, rejet au niveau Chef, renvoi et clôture. |
| `dss_v2.group_dss_magasin` | DSS / Magasin | Validation Stock, rejet au niveau Stock, modification des quantités et impression du BL. |
| `dss_v2.group_dss_securite` | DSS / Securite | Vue de demande en lecture seule et menu provisoire « À contrôler ». |

Le groupe Sécurité n'a pas de transition dans le workflow principal `dss.request`; le libellé du groupe ne prouve donc pas qu'une étape d'approbation est implémentée.

## 3. Attribution des groupes

Les groupes sont des enregistrements `res.groups` rangés sous la catégorie DSS. Leur attribution aux utilisateurs se fait dans la configuration Odoo; aucun utilisateur nominatif n'est déclaré par les sources du module.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Définition | Groupes et catégorie dans `dss_security.xml`. |
| Permissions | Les droits d'accès sont séparés dans `ir.model.access.csv`. |
| Sécurité | La présence d'un groupe n'implique ni ACL restreinte ni record rule. |
| Source | [`security/dss_security.xml`](../../security/dss_security.xml). |