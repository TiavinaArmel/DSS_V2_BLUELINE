# Refactorisation de `dss_request.py` — Sprint 11

Projet : DSS Odoo 10 (module `dss_v2`)
Début : 8 octobre 2026
Sources : mesure des fichiers faite par Armel, analyse en lecture seule faite par l'agent IA de l'IDE, relecture par Claude.

---

## 1. Objectif

Réduire la taille des fichiers du module, avec **environ 250 lignes par fichier** comme repère
(à adapter quand un fichier cohérent ne peut pas être découpé sans nuire à la lisibilité).

Règles de la refactorisation :

- **aucun changement de comportement** : on réorganise, on n'ajoute aucune fonctionnalité ;
- **aucune modification du core d'Odoo** (consigne de l'encadreur) ;
- aucun renommage de champ ni de méthode appelés par les vues XML, les wizards ou le reste du module ;
- un bloc à la fois : extraire, relancer Odoo, refaire le test manuel, puis un commit ;
- pas de refactorisation mélangée à une nouvelle fonctionnalité dans le même commit.

## 2. État initial (mesure du 8 octobre 2026)

| Lignes | Fichier |
|---|---|
| **1031** | `models\dss_request.py` |
| 221 | `report\dss_report.xml` |
| 169 | `static\src\css\report_bl.css` |
| 168 | `models\dss_cloture_wizard.py` |
| 165 | `models\dss_qty_sortie_wizard.py` |
| 129 | `views\dss_request_views.xml` |
| 85 | `models\stock_picking.py` |
| 85 | `models\dss_validation_wizard.py` |
| 62 | `views\dss_validation_wizard_views.xml` |
| 58 | `__manifest__.py` |
| 41 | `security\dss_security.xml` |
| 29 | `models\dss_request_display.py` |
| 24 | `views\dss_cloture_wizard_views.xml` |
| 24 | `views\dss_qty_sortie_wizard_views.xml` |
| 19 | `views\dss_request_display_views.xml` |

**Constat : `dss_request.py` est le seul fichier qui dépasse nettement la cible** (plus de quatre fois).
Tous les autres sont sous 250 lignes et ne sont pas concernés par le Sprint 11.

## 3. Préparation

| Élément | État |
|---|---|
| Sauvegarde de la base `DSS_V2_DB` | **Faite** (selon l'agent) : `C:\backup\DSS_V2_DB_avant_refactor.backup`, 3 349 934 octets, vérifiée |
| Branche Git de travail (`refactor/decoupage-dss-request` proposée) | À confirmer |
| Test de référence manuel (voir section 7) | À faire avant le premier découpage |
| Fichiers du projet modifiés à ce stade | Aucun (selon l'agent) |

Détail de la sauvegarde : le premier essai a échoué parce que le chemin de `pg_dump.exe` proposé
(dossier `PostgreSQL` de l'installation d'Odoo) n'existe pas sur cette machine. L'agent a trouvé
`pg_dump.exe` dans `C:\Program Files\PostgreSQL\9.5\bin`, et la sauvegarde a réussi avec cet exécutable.
Le mot de passe de la base, lu dans `odoo.conf`, n'est pas reproduit dans cette documentation.

## 4. Contenu réel de `dss_request.py` (cartographie de l'agent, étape 2A)

Mesure faite **après** l'extraction de `DssRequestLine` : le fichier compte **944 lignes**.
`DssRequest` occupe **847 lignes**, suivies du wizard de rejet et de l'extension produit.
Les tailles comptent aussi les lignes vides et les commentaires.

| Bloc | Lignes | Qui l'utilise |
|---|---:|---|
| Déclaration de `DssRequest` et ses champs (dont les sélections `state` et `type_intervention`) | 128 | Le modèle ; le formulaire et le rapport lisent ces champs ; les wizards lisent ou modifient certaines valeurs |
| Calcul du sens du mouvement et onchange | 28 | Déclenchés par Odoo ; les méthodes du modèle consomment `sens_mouvement` |
| `create()` et attribution du numéro par séquence | 19 | Mécanisme ORM ; la séquence `dss.request` est déclarée dans les données XML |
| `_detail_articles_html()` | 42 | `action_soumettre()` seulement (résultat publié dans le chatter) |
| Soumission et validations Chef / Stock | 142 | Bouton Soumettre ; les wizards de validation appellent les actions Chef et Stock ; la validation Stock appelle aussi les générateurs de mouvements et le PDF |
| Générateurs de mouvements (sortie, entrée, transfert) | 276 | Routeur interne de la validation Stock ; aucun appel direct depuis une vue ou un wizard |
| Génération et pièce jointe du Bon de Livraison | 57 | Validation Stock et action d'impression |
| Impression, approbation, rejet, renvoi, ouverture des wizards | 155 | Boutons du formulaire ; les wizards de validation et de rejet appellent aussi certaines actions |
| `DssRejetWizard` | 32 | Sa vue XML, les droits d'accès et l'action d'ouverture (par nom de modèle) |
| `ProductProduct.name_search()` | 50 | Recherche Many2one d'Odoo ; le formulaire fournit le contexte d'emplacement |

Le reste (environ 15 lignes) correspond à l'en-tête et aux imports. Total des blocs : 847 + 32 + 50 + en-tête = 944.

Points complémentaires relevés par l'agent :

- **Aucune constante globale** dans le fichier : les listes de choix sont déclarées sur les champs, et le dictionnaire
  « type d'intervention → sens du mouvement » est local au calcul.
- **Docstrings et commentaires longs** (déjà comptés dans le tableau) : `create()` 10 lignes, `_detail_articles_html()` 16,
  `action_soumettre()` 18, commentaire du routeur de validation Stock 15, contrôle de stock 12, PDF 7, `name_search()` 11.
- Les wizards de **quantité**, de **clôture** et de **validation** sont déjà dans des fichiers séparés.
- **Dépendances** : les modèles se référencent par leur **nom** (`"dss.request"`, `"dss.request.line"`), pas par un import Python
  de classe : il n'y a donc pas de cycle à craindre. Il faut seulement respecter l'ordre de chargement dans `models/__init__.py`
  (modèle principal avant ses extensions, ligne DSS avant le fichier d'affichage).
- La cartographie est **statique** : l'agent n'a exécuté ni Odoo ni les actions du workflow.

## 5. Plan de refactorisation proposé par l'agent

1. Extraire `DssRequestLine` dans `dss_request_line.py`.
2. Extraire le wizard de rejet dans `dss_rejet_wizard.py`.
3. Extraire l'extension `ProductProduct.name_search` dans `product_product.py`.
4. Réduire `dss_request.py` à la déclaration du modèle principal, ses champs et ses calculs.
5. Pour alléger davantage, répartir les méthodes de `DssRequest` dans des extensions Odoo utilisant
   `_inherit = "dss.request"` :
   - workflow dans `dss_request_workflow.py` ;
   - mouvements de stock et PDF dans `dss_request_stock.py`.

Les imports devront suivre l'import du modèle principal dans `__init__.py` (le fichier de base d'abord).

Ordre recommandé : d'abord les trois extractions de classes en conservant strictement le comportement,
puis la séparation workflow / stock, afin de localiser facilement une éventuelle régression.

## 6. Analyse complémentaire (Claude) — corrigée après l'étape 2A

**Correction.** Dans une version précédente de ce document, j'estimais `DssRequest` à environ 540 lignes et j'évoquais une zone
inexpliquée d'environ 310 lignes, à partir d'un repère de ligne (411) donné dans la première analyse de l'agent. La cartographie
de l'étape 2A montre que ce repère était inexact : `DssRequest` fait **847 lignes** et il n'y a pas de zone inexpliquée.

**Conséquence.** Après l'extraction du wizard de rejet (32 lignes) et de l'extension produit (50 lignes), il resterait encore
environ 860 lignes dans `dss_request.py`. La séparation de `DssRequest` en extensions `_inherit` est donc **le cœur** du Sprint 11.

**Répartition proposée** (estimations d'après les tailles de l'agent, à valider) :

| Fichier cible | Contenu | Lignes approx. |
|---|---|---:|
| `dss_request.py` (base) | champs, sens du mouvement, onchange, `create()` | environ 190 (175 + en-tête) |
| `dss_request_workflow.py` | `_detail_articles_html()`, soumission, validations Chef / Stock | environ 184 |
| `dss_request_actions.py` | impression, approbation, rejet, renvoi, ouverture des wizards | environ 155 |
| `dss_request_stock.py` | générateurs de mouvements (sortie, entrée, transfert) | environ 276 |
| `dss_request_report.py` | Bon de Livraison (génération et pièce jointe) | environ 57 |
| `dss_rejet_wizard.py` | wizard de rejet | environ 32 |
| `product_product.py` | extension `name_search()` | environ 50 |

Le fichier des mouvements de stock (276 lignes) dépasse un peu la cible : acceptable puisque le contenu est cohérent,
à moins qu'on le sépare plus tard par type de mouvement.

**Ordre conseillé, du moins risqué au plus risqué :** wizard de rejet, extension produit, Bon de Livraison,
mouvements de stock, puis workflow et actions.

**Règles d'Odoo à respecter pour les extensions `_inherit` :** `_name` n'apparaît que dans le fichier de base ;
chaque extension déclare seulement `_inherit = "dss.request"` ; les surcharges de l'ORM (`create()`) restent dans le fichier de base ;
aucune méthode ne doit exister en double entre deux fichiers ; aucun renommage de champ ni de méthode.

## 7. Test de référence (à faire avant et après chaque découpage)

Il n'existe pas de dossier de tests automatiques dans le module. La vérification est manuelle :

1. Créer une demande pour chaque type d'intervention, avec 2 articles.
2. Soumettre, valider Chef, valider Stock, approuver.
3. Refuser une demande au niveau Chef, puis la renvoyer.
4. Contrôler les mouvements de stock générés (Sortie, Entrée, Sortie + Entrée).
5. Bouton « Bon de Livraison » et PDF joint au chatter.
6. Les wizards (quantités, clôture, validation, rejet).
7. Les droits avec un utilisateur de chaque groupe (Demandeur, Chef, Magasin, Sécurité).

## 8. Points à préserver ou à traiter séparément (hors refactorisation)

Ces points ont été relevés par l'agent et figurent déjà dans le document `02-modele-dss-request.md`
du dépôt (ligne 234). Ils ne doivent **pas** être modifiés implicitement pendant le découpage :

- **Parcours « Sortie + Entrée »** : `picking_id` ne référence que le dernier mouvement créé.
  Sujet fonctionnel à traiter à part.
- **`action_approuver()`** passe la demande à « approuvé » sans créer les mouvements de stock ni
  le Bon de Livraison, contrairement à `action_valider_magasin()`. À clarifier avec l'encadreur
  plutôt que de changer le comportement pendant le refactor.
- **Contrôle de stock dupliqué** entre la sortie et le transfert. Factorisation envisageable plus tard,
  avec des tests ciblés.

## 9. Suivi d'avancement

- [x] Mesure de la taille des fichiers
- [x] Sauvegarde de la base avant refactorisation
- [x] Analyse en lecture seule de `dss_request.py` par l'agent
- [ ] Création de la branche `refactor/decoupage-dss-request`
- [ ] Test de référence manuel avant découpage
- [x] Étape 1 : extraction de `DssRequestLine` faite ; démarrage d'Odoo et test manuel OK (déclaré par Armel, 8 octobre 2026) ; commit à confirmer
- [ ] Étape 2 : extraction du wizard de rejet (code modifié par l'agent le 8 octobre 2026 ; contrôle du diff, test manuel et commit à confirmer)
- [ ] Étape 3 : extraction de `ProductProduct.name_search` (code modifié par l'agent le 8 octobre 2026 ; test manuel et commit à confirmer)
- [x] Étape 2A : cartographie de `dss_request.py` par l'agent (8 octobre 2026)
- [x] Étape 4 : extraction du Bon de Livraison dans `dss_request_bon_livraison.py` (déclaré par Armel ; nom différent du plan ; tests et commit à confirmer)
- [x] Étape 5 : extraction des mouvements de stock dans `dss_request_stock.py` (déclaré par Armel ; tests et commit à confirmer)
- [x] Étape 6 : extraction du workflow dans `dss_request_workflow.py` (déclaré par Armel ; pas de fichier `dss_request_actions.py` mentionné ; tests et commit à confirmer)
- [ ] Nouvelle mesure des fichiers et test de référence final

## 10. Décisions en attente

- Valider l'ordre du plan (d'abord `DssRequestLine`) et les noms de fichiers proposés.
- Décider si `picking_id` pour « Sortie + Entrée » et le contrôle de stock dupliqué sont traités dans un sprint ultérieur.
- Clarifier avec l'encadreur le rôle de `action_approuver()`.
- Choisir entre le découpage de l'agent (workflow dans un seul fichier, environ 280 lignes) et la proposition de la section 6
  (workflow et actions séparés).

---

## 11. Journal des étapes

### Étape 1 — Extraction de `DssRequestLine` (8 octobre 2026)

**Inventaire réalisé par l'agent avant l'extraction (lecture seule)**

- Bornes exactes de la classe dans `dss_request.py` : **lignes 16 à 101** (environ 86 lignes).
- Contenu : le modèle `dss.request.line`, **neuf champs** et **deux méthodes**.
- La classe n'utilise du fichier d'origine que `models`, `fields` et `api` : aucune constante,
  aucun choix de liste, aucune fonction utilitaire externe.
- Aucun `import` direct de `DssRequestLine` ailleurs dans le module : le seul import concerné est
  celui du module dans `models/__init__.py`.
- Références au modèle, toutes par son **nom** (`dss.request.line`) et non par la classe Python :
  - le champ `One2many` (`line_ids`) de la demande et ses parcours ;
  - l'extension `_inherit` du fichier d'affichage ;
  - les relations des wizards de quantité et de clôture, et leurs vues ;
  - les vues du formulaire (`line_ids`) ;
  - le rapport du Bon de Livraison (`o.line_ids`) ;
  - l'entrée de droits d'accès (ACL).

**Modifications faites (trois fichiers)**

| Fichier | Changement |
|---|---|
| `models/dss_request_line.py` | Nouveau : classe recopiée telle quelle (même nom de modèle, mêmes neuf champs, mêmes deux méthodes) |
| `models/dss_request.py` | La classe `DssRequestLine` est retirée |
| `models/__init__.py` | Import de `dss_request_line` ajouté **après** `dss_request` |

**Vérifications annoncées par l'agent**

- Aucun problème signalé par l'éditeur sur les trois fichiers.
- Une vérification de syntaxe, un comptage de lignes et un contrôle de l'import ont été lancés dans le terminal.
  **Leur résultat ne figure pas dans le rapport reçu.**

**Non vérifié à ce stade**

- Le résultat de la commande de contrôle (syntaxe, nombre de lignes avant/après).
- La vérification de syntaxe a utilisé Python 3 (`py -3`), alors qu'Odoo 10 tourne sous **Python 2.7** :
  elle ne garantit pas que les fichiers se chargent sous Odoo. À refaire avec le Python d'Odoo.
- Le démarrage d'Odoo sans erreur d'import.
- Le test de référence manuel (section 7), en particulier le comportement des lignes d'articles.
- Le nouveau fichier doit commencer par la ligne d'encodage UTF-8 (nécessaire sous Python 2.7 à cause des accents).

**Commit prévu :** `refactor(models): extraire DssRequestLine dans dss_request_line.py`

### Question ouverte de l'étape 1 : résolue

La « zone de 310 lignes » évoquée après l'étape 1 n'existait pas : elle venait d'un repère de ligne inexact (voir étape 2A).

**Résultat des tests (déclaré par Armel) :** après l'extraction, le code et le module fonctionnent correctement.
Les points listés plus haut comme « non vérifiés » restent à confirmer par le rapport de l'agent
(vérification avec Python 2.7, ligne d'encodage UTF-8, nombre de lignes avant/après).

### Étape 2A — Cartographie de `dss_request.py` (8 octobre 2026, lecture seule)

- L'agent a relu le fichier après l'extraction : **944 lignes**, dont `DssRequest` **847**, le wizard de rejet 32 et
  l'extension produit 50 (tableau complet en section 4).
- Il n'y a **pas de constante globale** ni de dépendance Python circulaire à craindre.
- L'agent propose d'extraire `DssRejetWizard` et `ProductProduct`, puis de déplacer les actions de stock et le PDF dans
  `dss_request_stock.py` et le workflow restant dans `dss_request_workflow.py`, en extensions `_inherit`.
- **Non vérifié** : cartographie statique, Odoo et les actions du workflow n'ont pas été exécutés.
- **Impact sur le plan** : l'estimation de 540 lignes pour `DssRequest` était fausse (voir section 6) ; la répartition en
  sept fichiers de la section 6 remplace l'ancien plan en cinq étapes.

### Étape 2 — Extraction du wizard de rejet (8 octobre 2026)

**Inventaire de l'agent avant extraction**

- `DssRejetWizard` occupait les lignes 863 à 892 de `dss_request.py` (environ 30 lignes), juste avant `ProductProduct`.
- Elle n'utilise que `models.TransientModel`, `fields` (`Many2one`, `Text`) et `api.multi`, puis délègue le rejet à
  `request_id.action_rejeter()`. Aucune constante ni fonction utilitaire du fichier n'est nécessaire.
- Références par **nom technique** (`dss.rejet.wizard`) : l'action `action_open_wizard_rejeter`, la vue XML et la ligne ACL.
  Aucun import Python de la classe ailleurs.

**Modifications (trois fichiers)**

| Fichier | Lignes avant | Lignes après |
|---|---:|---:|
| `models/dss_request.py` | 944 | 912 |
| `models/dss_rejet_wizard.py` (nouveau, en-tête UTF-8) | absent | 35 |
| `models/__init__.py` (import ajouté après `dss_request`) | 11 | 12 |

`_name` (`dss.rejet.wizard`), les champs `request_id` et `motif` et la méthode `action_confirmer()` sont conservés.
Les vues, les droits d'accès, l'action de refus et le core d'Odoo n'ont pas été modifiés.

**Incident pendant l'extraction**

Le premier patch de l'agent a supprimé par erreur la méthode voisine `action_open_wizard_approuver`. L'agent l'a repérée en
contrôlant les bornes, puis l'a rétablie « à l'identique ». Ce rétablissement n'a pas été comparé au texte d'origine dans le rapport :
**il faut vérifier par comparaison avec le dernier commit** que cette méthode, comme le reste de `dss_request.py`,
n'a changé que par le retrait du bloc du wizard.

**Non vérifié ou à contrôler**

- **Python 2.7** : aucun interpréteur 2.7 n'a pu être confirmé ; l'environnement disponible est Python 3.14.7. La syntaxe n'a donc
  été contrôlée que par les diagnostics de l'éditeur (aucune erreur). La vérification réelle sera le démarrage d'Odoo, qui charge
  le module avec son propre Python 2.7.
- Pendant ses essais, l'agent a lancé des outils de configuration d'environnement Python (« Configuring / Creating a Virtual Environment ») ;
  il a pu créer un dossier `.venv` dans le projet. À vérifier avec `git status` et à ne pas commiter.
- Démarrage d'Odoo, test manuel du refus de demande et du bouton d'approbation (voisin du code touché) : à faire.
- Aucun commit n'a été créé par l'agent.

**Commit prévu :** `refactor(models): extraire DssRejetWizard dans dss_rejet_wizard.py`

### Étape 3 — Extraction de `ProductProduct` (8 octobre 2026)

Source : rapport de l'agent (captures d'écran fournies par Armel).

- `ProductProduct` n'avait **aucune dépendance Python** directe à `DssRequest`. La classe n'utilise que l'API Odoo, le contexte
  `dss_location_id` et le modèle `stock.quant`. La vue DSS fournit toujours ce contexte au champ article, donc l'intégration
  fonctionnelle par la vue est conservée.
- La classe est maintenant dans `models/product_product.py` et a été retirée de `dss_request.py`.
- Son import a été ajouté dans `models/__init__.py` (ligne 4), **sans changer l'ordre relatif des imports existants**.
- Aucun autre fichier et aucun fichier du core d'Odoo n'ont été modifiés.
- Les diagnostics de l'éditeur ne signalent aucune erreur ; une recherche confirme que `ProductProduct` n'est déclarée que dans le nouveau fichier.

**Non vérifié :** Python 2.7 n'est pas disponible dans l'environnement de l'agent, donc la vérification de syntaxe propre à Python 2.7
reste à faire (le démarrage d'Odoo en tient lieu). Les lignes avant/après de cette extraction ne figurent pas dans le rapport.
Aucun commit n'a été créé par l'agent. Test manuel à faire : recherche d'un article dans le formulaire DSS, filtrée selon le stock
de l'emplacement choisi.

**Commit prévu :** `refactor(models): extraire ProductProduct dans product_product.py`

### Scan du découpage du reste de `DssRequest` (agent, lecture seule)

L'agent juge pertinent un découpage par extensions `_inherit = "dss.request"` (sans importer la classe Python `DssRequest`) :

| Fichier proposé | Contenu | Taille indiquée |
|---|---|---|
| `dss_request_workflow.py` | `action_soumettre`, `action_valider_chef`, `action_valider_magasin`, `action_approuver`, `action_rejeter`, `action_renvoyer_demandeur` et les actions d'ouverture des wizards ; `_detail_articles_html()` peut suivre `action_soumettre()` (seul appelant) | environ 280 lignes, réparties entre les repères `dss_request.py:234` et `:720` |
| `dss_request_stock.py` | `_generer_mouvement_sortie`, `_generer_mouvement_entree`, `_generer_mouvement_transfert` ; `action_valider_magasin` reste dans le workflow et les appelle via le modèle étendu | environ 276 lignes (repère `:375`) |
| `dss_request_report.py` (optionnel) | `_generer_bon_livraison()` et `action_imprimer_bon_livraison()` ; sépare le PDF du mouvement de stock, mais ajoute un fichier à maintenir | repère `:708` |

Restent dans `dss_request.py` : les champs, `create()`, le calcul du sens du mouvement et l'onchange.
Dans `models/__init__.py`, les extensions doivent être importées **après** `dss_request`. Les appels des vues et des wizards
(par exemple `dss_request_views.xml` et `dss_validation_wizard.py`) n'ont pas à changer.

À **ne pas corriger implicitement** pendant le découpage (comportement existant) : le contrôle de stock dupliqué entre sortie et
transfert, et `picking_id` qui peut ne garder que le dernier mouvement dans le cas « Sortie + Entrée ».

**Estimation (Claude, d'après les tailles de l'agent) :** avec ces trois extensions, `dss_request.py` retomberait autour de 190 à 250 lignes,
c'est-à-dire dans la cible. Les points de repère de lignes sont ceux du moment du scan et se décaleront à chaque extraction.

### Étapes 4 à 6 — Bon de Livraison, mouvements de stock et workflow (déclaré par Armel, 9 octobre 2026)

Armel indique avoir terminé ces trois extractions, sous forme d'extensions de `dss.request` :

| Nouveau fichier | Contenu |
|---|---|
| `models/dss_request_workflow.py` | Workflow de `DssRequest` |
| `models/dss_request_stock.py` | Mouvements de stock |
| `models/dss_request_bon_livraison.py` | Bon de Livraison (génération et impression) |

Écarts avec le plan de la section 6 : le Bon de Livraison est dans `dss_request_bon_livraison.py` (et non `dss_request_report.py`),
et aucun fichier `dss_request_actions.py` n'est mentionné : les actions d'impression, d'approbation, de rejet, de renvoi
et d'ouverture des wizards sont donc soit dans le fichier du workflow, soit restées dans `dss_request.py`. À préciser.

**Non documenté à ce stade** (je n'ai pas reçu les rapports de l'agent pour ces trois étapes) :

- les lignes avant/après de chaque fichier et la taille actuelle de `dss_request.py` ;
- l'ordre des imports dans `models/__init__.py` (le modèle principal doit rester importé avant ses extensions) ;
- que le contenu a été déplacé sans modification de logique, et que les extensions n'importent pas la classe `DssRequest` ;
- les points sensibles : surcharges de l'ORM (`create()`) restées dans le fichier de base, aucune méthode en double ;
- le démarrage d'Odoo, le test de référence manuel (section 7), en particulier le cycle complet jusqu'au Bon de Livraison et aux mouvements de stock ;
- les commits.

**Pour compléter ce chapitre :** coller le rapport de l'agent de chacune des trois extractions, ou lui demander une mesure
des lignes de tous les fichiers du dossier `models` et un contrôle de l'ordre des imports.
