# Règles d'enregistrement

## 1. Rôle

Une règle d'enregistrement (`ir.rule`) filtre **quels enregistrements** un utilisateur peut atteindre. Elle complète les ACL : l'ACL dit « ce rôle peut lire le modèle », la règle dit « sur quelles lignes ».

Sans règle, un utilisateur qui possède le droit de lecture peut ouvrir n'importe quelle demande en connaissant son identifiant, même si le menu ne lui en montre qu'une partie.

## 2. Déclarations dans le module

| Fichier | Contenu |
|---|---|
| [`security/dss_security.xml`](../../security/dss_security.xml) | Catégorie DSS et quatre groupes `res.groups`. |
| [`security/ir.model.access.csv`](../../security/ir.model.access.csv) | ACL par modèle et par rôle. |
| [`security/dss_record_rules.xml`](../../security/dss_record_rules.xml) | **Dix règles d'enregistrement** depuis la version `2.14` : cinq sur `dss.request`, cinq sur `dss.request.line`. |

Le fichier de règles est déclaré dans le manifeste **après** les ACL, car il référence les groupes créés par `dss_security.xml`.

## 3. Périmètre par rôle

| Rôle | Domaine appliqué sur `dss.request` | Conséquence |
|---|---|---|
| DSS / Demandeur | `['|', ('demandeur_id', '=', user.id), ('create_uid', '=', user.id)]` | Ne voit que ses propres demandes |
| DSS / Chef | `[('service_demandeur_id.dss_chef_id', '=', user.id)]` | Ne voit que les demandes des services qu'il dirige |
| DSS / Magasin | `[(1, '=', 1)]` | Voit toutes les demandes, car il prépare toutes les sorties |
| DSS / Securite | `[(1, '=', 1)]` | Voit tout, mais ne peut pas écrire (ACL en lecture seule) |
| Administrateur système | `[(1, '=', 1)]` | Accès complet, y compris aux demandes orphelines |

Les mêmes règles existent sur `dss.request.line`, avec le préfixe `request_id.` : le périmètre d'une ligne est celui de sa demande.

**Combinaison :** Odoo applique un **OU** entre les règles des groupes d'un même utilisateur. Un collaborateur à la fois Demandeur et Chef voit donc l'union de ses demandes et des demandes de son service.

**Exceptions :** le superutilisateur (identifiant 1) et le mode `sudo()` ignorent les règles. C'est ce qui permet aux scripts de maintenance, aux notifications et aux tests de fonctionner.

## 4. Différence avec les autres mécanismes

| Mécanisme | Question traitée |
|---|---|
| ACL (`ir.model.access`) | Ce rôle peut-il lire, écrire, créer ou supprimer dans ce modèle ? |
| Record rule (`ir.rule`) | Quels enregistrements de ce modèle peut-il lire ou modifier ? |
| `groups` de vue / `attrs` | Quels éléments l'interface affiche-t-elle ou rend-elle éditables ? |
| Domaine d'action | Quels enregistrements sont présentés par cette action de menu ? |
| Contrôle dans une méthode Python | Cette action précise est-elle autorisée pour cet utilisateur et cet état ? |

Les quatre premiers mécanismes ne remplacent pas le cinquième : un appel RPC contourne l'interface, donc les méthodes sensibles revérifient le rôle et l'état côté serveur.

## 5. Vérification

| Contrôle | Méthode |
|---|---|
| Un utilisateur hors groupe DSS ne voit rien | `test_outsider_has_no_access_to_requests` |
| Un demandeur ne voit pas la demande d'un autre service | `test_requester_cannot_read_request_of_another_service` |
| Un Chef ne voit que son service | `test_chef_sees_only_his_service` |
| Le Magasin voit toutes les demandes | `test_magasin_sees_all_requests` |

Ces tests se trouvent dans [`tests/test_dss_security.py`](../../tests/test_dss_security.py).

## 6. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| État du module | Dix règles déclarées dans `security/dss_record_rules.xml` depuis 2.14. |
| Principe | Un demandeur voit ses demandes, un Chef son service, le Magasin tout. |
| Combinaison | OU entre les groupes d'un même utilisateur. |
| Limite | Une règle ne remplace pas un contrôle dans la méthode pour une action précise. |
| Rigidité | Si un Chef change de service, il perd l'accès aux demandes de l'ancien service. |
