# Glossaire DSS V2

## 1. Termes Odoo

| Terme | Définition | Exemple DSS |
|---|---|---|
| Asset | Ressource chargée dans l'interface Web ou dans un rapport. | `views/assets_backend.xml` ajoute le CSS du chatter au bundle Web. |
| Champ calculé | Champ dont la valeur est fournie par une méthode `compute`. | `qty_standard` est calculé depuis `product_id.qty_available`. |
| Chatter | Fil de messages et d'activités associé à un enregistrement via `mail.thread`. | `dss.request` affiche `message_ids` et `message_follower_ids`. |
| Domaine | Liste de critères utilisée par l'ORM pour filtrer des enregistrements. | Le menu « À contrôler » limite la liste à `state = approuve`. |
| Groupe | Ensemble d'utilisateurs référencé notamment par les vues et les ACL. | `dss_v2.group_dss_chef`. |
| Héritage (`_inherit`) | Extension d'un modèle existant sans déclarer un nouveau modèle métier. | `DssRequestWorkflow` étend `dss.request`. |
| Many2one | Relation d'un enregistrement vers au plus un enregistrement d'un autre modèle. | `dss.request.line.request_id` référence une demande. |
| Modèle | Définition ORM des champs et comportements d'un type d'enregistrement. | `dss.request` représente une demande DSS. |
| ORM | Couche d'accès aux enregistrements et modèles Odoo, au-dessus de PostgreSQL. | `self.env['stock.move'].create(...)`. |
| One2many | Relation donnant accès à plusieurs enregistrements liés par un Many2one inverse. | `dss.request.line_ids` regroupe les lignes de la demande. |
| QWeb | Moteur de modèles XML utilisé notamment pour produire des rapports. | `report_bon_livraison_document` compose le BL. |
| Règle d'enregistrement | Filtre de sécurité appliqué aux enregistrements accessibles; distinct des droits CRUD. | Aucun enregistrement `ir.rule` n'est défini dans `dss_security.xml`. |
| TransientModel | Modèle temporaire généralement utilisé pour les assistants et fenêtres modales. | `dss.cloture.wizard` collecte les quantités avant clôture. |
| Vue | Définition XML de l'affichage et des actions disponibles pour un modèle. | `dss_request_views.xml` définit les formulaires et la liste DSS. |
| Wizard | Assistant temporaire qui guide ou confirme une action utilisateur. | Le wizard de rejet recueille un motif avant d'appeler l'action de rejet. |

## 2. Termes métier DSS

| Terme | Définition | Exemple |
|---|---|---|
| BCI | Bon de Commande Interne, référence administrative saisie sur la demande. | Champ `bci` de `dss.request`. |
| BL | Bon de Livraison généré en PDF à partir d'une demande DSS. | Rapport QWeb `dss_v2.report_bon_livraison_document`. |
| Demandeur | Utilisateur enregistré comme ayant soumis la demande. | Champ `signataire_demandeur_id`. |
| DSS | Demande de Sortie de Stock, dossier métier du module. | Modèle `dss.request`. |
| Écart | Différence détectée à la clôture entre quantité sortie et quantité installée. | Le wizard met `has_ecart` à vrai si au moins une ligne diffère. |
| Emplacement destination | Emplacement interne cible, requis pour le type `appro_distant`. | Champ `location_dest_id`. |
| Emplacement source | Emplacement interne sélectionné comme origine d'une sortie ou d'un transfert. | Champ `location_id`. |
| Sens du mouvement | Sens de stock calculé à partir du type d'intervention. | `Sortie`, `Entree`, `Sortie + Entree` ou `Transfert`. |
| Type d'intervention | Catégorie choisie sur la demande et utilisée pour calculer le sens du mouvement. | `nouvelle_installation`, `retour_materiel`. |

## 3. Termes techniques

| Terme | Définition |
|---|---|
| Base64 | Encodage utilisé ici pour placer le contenu binaire du PDF dans `ir.attachment.datas`. |
| CSS | Feuille de style utilisée pour la présentation de l'interface ou du rapport. |
| Identifiant XML | Identifiant stable d'une donnée Odoo, référencé sous la forme `module.identifiant`. |
| PostgreSQL | Système de base de données déclaré dans le cahier des charges du projet. |
| SMTP | Protocole utilisé par Odoo pour transmettre les courriels à un serveur sortant. |
| wkhtmltopdf | Outil externe utilisé par Odoo 10 pour convertir le rendu HTML d'un rapport en PDF. |
| XML | Format de données employé par Odoo pour déclarer vues, menus, groupes et rapports. |

## 4. Acronymes

| Acronyme | Signification |
|---|---|
| ACL | Access Control List, droits d'accès CRUD définis pour un modèle et un groupe. |
| BCI | Bon de Commande Interne. |
| BL | Bon de Livraison. |
| CRUD | Create, Read, Update, Delete : créer, lire, modifier et supprimer. |
| DSS | Demande de Sortie de Stock. |
| ORM | Object-Relational Mapping, couche de mapping objet-relationnel. |
| PDF | Portable Document Format. |
| SMTP | Simple Mail Transfer Protocol. |

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Modèle principal | `dss.request` représente l'en-tête d'une demande. |
| Lignes | `dss.request.line` contient les articles associés à la demande. |
| Assistants | Les wizards du module sont des `TransientModel`. |
| Stock | Les mouvements s'appuient sur les modèles Odoo `stock.picking` et `stock.move`. |
| Sources | Les définitions vérifiées se trouvent dans `models/`, `views/`, `security/` et `report/`. |