# Dépannage

## 1. PDF blanc ou incomplet

| Symptôme | Vérifications dans le module et l'environnement |
|---|---|
| PDF vide alors que le HTML est rendu | Vérifier les journaux Odoo, l'exécutable wkhtmltopdf réellement lancé et les fichiers HTML transmis. Le moteur PDF et sa version dépendent de l'installation. |
| Format ou orientation inattendus | Contrôler `paperformat_dss_a5`, l'action du rapport et le contexte utilisé par `_generer_bon_livraison()`. |
| Styles absents | Contrôler le chargement de `report_bl.css` via `report.assets_common` et l'URL `/dss_v2/static/src/css/report_bl.css`. |

Un ancien compte rendu du projet attribue un PDF blanc sur l'environnement Windows étudié à l'option `--dpi 96` avec wkhtmltopdf 0.12.1.2; le format DSS a alors été réglé à `dpi=0`. Il s'agit d'un constat d'environnement, pas d'une garantie que cette cause vaut pour toute installation.

## 2. Notification non reçue

Vérifier d'abord si un `dss.notification.log` et un `mail.mail` existent, puis l'état du mail, les destinataires résolus, le serveur SMTP et les journaux Odoo. Le module crée le courriel en file sans l'envoyer immédiatement. Voir [courriels et SMTP](../06-integrations/01-email-smtp.md).

## 3. Problèmes de chargement ou d'action

| Symptôme possible | Élément source à contrôler |
|---|---|
| Boutons Valider/Rejeter Chef ou Magasin absents | Le header DSS a été simplifié : les boutons sont des éléments directs du `<header>` et portent chacun leur attribut `groups`. Mettre à niveau le module sur la base concernée, puis vérifier le groupe de l'utilisateur et l'état de la demande (`valide_chef` pour Chef, `valide_magasin` pour Magasin). Si le problème persiste, inspecter la vue formulaire combinée et les personnalisations de la base. |
| Action de wizard introuvable | `action_open_wizard_approuver()` référence `dss.validation.approuver.wizard`, non déclaré dans les fichiers Python recensés; aucun bouton ne l'appelle dans la vue principale. |
| État de picking inattendu | `action_soumettre_dss()` écrit `soumis`, qui n'est pas une option de `dss_validation_state`. |
| Numéro picking `/` | L'extension cherche `ir.sequence` de code `dss.number`; aucune séquence de ce code n'est déclarée dans les données de ce module. |
| Refus de soumission | Lire le message `ValidationError` de `action_soumettre()` et vérifier les champs et lignes requis. |
| Refus de mouvement | Lire l'erreur de quantité du modèle stock et contrôler l'emplacement source et les quantités saisies. |

### Historique du problème d'affichage des boutons DSS

Les boutons d'action Chef et Magasin étaient enveloppés dans des éléments `<span groups="…">` dans le header. Cette structure a été considérée comme une cause possible de leur absence, car certaines versions ou personnalisations de l'en-tête peuvent attendre des éléments directs tels que `<button>` et `<field>`. Sans trace d'erreur du serveur ou inspection de la vue combinée sur la base concernée, cette cause reste une hypothèse de compatibilité, et non un diagnostic confirmé.

Solution appliquée dans `views/dss_request_views.xml` : suppression des deux `<span>` et déplacement de la restriction `groups` sur chaque bouton qu'ils contenaient. L'ordre des boutons, les libellés, les conditions `attrs` et les classes CSS ont été conservés. Après mise à niveau du module, contrôler également que l'utilisateur possède le groupe approprié et que la demande est à l'étape attendue.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Diagnostic | Partir de l'enregistrement Odoo, des journaux et des fichiers de configuration réellement chargés. |
| Environnement | Les observations PDF historiques sont spécifiques à une machine et à sa version wkhtmltopdf. |
| Secrets | Ne pas copier de paramètres d'accès, mots de passe ou jetons dans les rapports de diagnostic. |