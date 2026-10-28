# Dépannage

## 1. PDF blanc ou incomplet

| Symptôme | Vérifications dans le module et l'environnement |
|---|---|
| PDF vide alors que le HTML est rendu | Vérifier les journaux Odoo, l'exécutable wkhtmltopdf réellement lancé et les fichiers HTML transmis. Le moteur PDF et sa version dépendent de l'installation. |
| Format ou orientation inattendus | Contrôler `paperformat_dss_a5`, l'action du rapport et le contexte utilisé par `_generer_bon_livraison()`. Pour un problème d'espacement vertical, vérifier ensemble `margin_top` (réserve supérieure de page) et `header_spacing` (espacement/décalage du contenu par rapport à l'en-tête) : augmenter ce dernier éloigne le corps, le diminuer peut créer un chevauchement. |
| Styles absents | Contrôler le chargement de `report_bl_server.css` via `report.assets_common` et l'URL `/dss_v2/static/src/css/report_bl_server.css`. |
| Erreur 500 `MissingError` sur `o.partner_id.name` | Vérifier d'abord que l'action de rapport QWeb correcte est appelée et que son modèle est bien `dss.request`. Si l'erreur subsiste avec la bonne action, contrôler le partenaire de la demande concernée et les enregistrements supprimés ou restaurés dans la base. |

### Action de rapport obsolète après changement ou restauration de base

Un incident de déploiement a été résolu après suppression, dans **Technique > Rapports > Rapports**, d'une entrée « Bon de livraison » dont le modèle technique affiché était `dss_v2_report_bon_livraison_documentation`, puis mise à niveau de `dss_v2` et nouvel essai d'impression. Le bon a alors retrouvé son rendu attendu.

La cause exacte des données présentes dans cette base n'a pas été établie. L'explication la plus probable est une ancienne action de rapport QWeb créée ou conservée dans la base, avec un nom technique qui ne correspond plus au rapport déclaré par le module. Un changement de base ne modifie pas en soi le code du module : chaque base possède ses propres enregistrements Odoo (actions de rapport, vues QWeb et identifiants externes), lesquels peuvent être absents, obsolètes ou différents après restauration, migration ou installation manuelle.

Dans le code du module, la déclaration de référence est dans `report/dss_report.xml` :

| Propriété | Valeur attendue |
|---|---|
| Libellé | `Bon de Livraison` |
| Modèle métier | `dss.request` |
| Type | `qweb-pdf` |
| Nom du rapport QWeb / `report_name` | `dss_v2.report_bon_livraison_document` |
| Fichier du rapport / `report_file` | `dss_v2.report_bon_livraison_document` |
| Identifiant XML de l'action | `dss_v2.action_report_bon_livraison` |

En cas de reproduction après un changement de base :

1. Confirmer la base sélectionnée et effectuer une sauvegarde de la base avant toute suppression ou mise à niveau.
2. Ouvrir **Activer le mode développeur > Paramètres > Technique > Rapports > Rapports** et rechercher « Bon de livraison ».
3. Comparer les actions trouvées avec les valeurs de référence ci-dessus. Vérifier également qu'une action en doublon ou une action manuelle ne pointe pas vers un modèle ou un rapport QWeb obsolète.
4. Si une entrée manifestement obsolète ou en doublon est identifiée, noter ses valeurs et son identifiant, puis ne supprimer que cette action de rapport fautive. Ne pas supprimer le template QWeb `dss_v2.report_bon_livraison_document`, les demandes DSS ni les données de partenaires.
5. Mettre à niveau `dss_v2` sur la base concernée afin que l'action déclarée dans le XML soit chargée, puis vérifier ses champs et réimprimer le PDF.
6. Si l'action correcte existe déjà ou si l'erreur persiste, examiner la trace complète et les relations de la demande; ne pas utiliser la suppression d'action comme remède générique à un `MissingError` de partenaire.

La suppression de l'action suivie d'une mise à niveau est une technique de dépannage observée pour cet incident, pas une étape de maintenance systématique. Préférer d'abord la sauvegarde et l'inspection, car les actions de rapports et leurs identifiants externes sont des données de configuration de la base.

Un ancien compte rendu du projet attribue un PDF blanc sur l'environnement Windows étudié à l'option `--dpi 96` avec wkhtmltopdf 0.12.1.2; le format DSS a alors été réglé à `dpi=0`. Il s'agit d'un constat d'environnement, pas d'une garantie que cette cause vaut pour toute installation.

## 2. Déploiement du rapport sur Debian

Procéder étape par étape et conserver une copie des fichiers distants avant leur remplacement.

### 2.1 Sauvegarde des fichiers distants sur le poste

Depuis PowerShell, adapter la cible SSH et le dossier local de sauvegarde :

```powershell
scp -O utilisateur@serveur:/chemin/addons/dss_v2/report/dss_report.xml C:\chemin\sauvegarde\dss_report.xml.server.bak
scp -O utilisateur@serveur:/chemin/addons/dss_v2/static/src/css/report_bl_server.css C:\chemin\sauvegarde\report_bl_server.css.server.bak
```

### 2.2 Copier vers `/tmp`, puis installer avec `sudo`

Si le compte SSH ne peut pas écrire dans le dossier des addons, transférer d'abord les fichiers vers `/tmp`. Le mode `-O` force le protocole SCP historique si le serveur ne prend pas en charge SFTP :

```powershell
scp -O C:\chemin\local\dss_report.xml utilisateur@serveur:/tmp/dss_report.xml
scp -O C:\chemin\local\report_bl_server.css utilisateur@serveur:/tmp/report_bl_server.css
ssh -t utilisateur@serveur "sudo cp /tmp/dss_report.xml /chemin/addons/dss_v2/report/dss_report.xml && sudo cp /tmp/report_bl_server.css /chemin/addons/dss_v2/static/src/css/report_bl_server.css"
```

`ssh -t` alloue un terminal pour permettre à `sudo` de demander son mot de passe. Ne pas mettre le mot de passe dans la commande ou dans la documentation.

### 2.3 Vérifier l'intégrité, mettre à niveau et tester

Comparer les SHA-256 locaux et distants avant de recharger Odoo :

```powershell
Get-FileHash C:\chemin\local\dss_report.xml -Algorithm SHA256
Get-FileHash C:\chemin\local\report_bl_server.css -Algorithm SHA256
ssh utilisateur@serveur "sha256sum /chemin/addons/dss_v2/report/dss_report.xml /chemin/addons/dss_v2/static/src/css/report_bl_server.css"
```

Les valeurs doivent correspondre fichier par fichier. Ensuite, redémarrer le service réellement utilisé et mettre à niveau le module dans la base serveur, par l'interface Applications ou par une commande Odoo utilisant explicitement le fichier de configuration et la base corrects. Un simple redémarrage ne recharge pas les vues QWeb XML enregistrées en base. Enfin, imprimer un PDF et vérifier le rendu avec la version de wkhtmltopdf du serveur.

**État de la session de déploiement :** les anciennes versions serveur ont été sauvegardées puis remplacées par les versions locales disponibles à ce moment-là; leurs SHA-256 correspondaient après la copie. Le redémarrage de `odoo.service` a été demandé. Lors de l'incident ultérieur, l'encadreur a supprimé l'entrée de rapport au modèle technique incorrect, mis à niveau le module et retesté l'impression; le rendu est alors revenu à la normale, selon son retour. Le statut actuel du service n'a pas été vérifié séparément. Le CSS local a ensuite reçu `margin-top: 10px` sur `.dss-info`, puis la marge supérieure du papier A5 et `header_spacing` ont été réglés à 15 mm. Ces changements récents ne sont pas confirmés sur le serveur et doivent être déployés et vérifiés.

## 3. Notification non reçue

Vérifier d'abord si un `dss.notification.log` et un `mail.mail` existent, puis l'état du mail, les destinataires résolus, le serveur SMTP et les journaux Odoo. Le module crée le courriel en file sans l'envoyer immédiatement. Voir [courriels et SMTP](../06-integrations/01-email-smtp.md).

## 4. Problèmes de chargement ou d'action

| Symptôme possible | Élément source à contrôler |
|---|---|
| Action de wizard introuvable | `action_open_wizard_approuver()` référence `dss.validation.approuver.wizard`, non déclaré dans les fichiers Python recensés; aucun bouton ne l'appelle dans la vue principale. |
| État de picking inattendu | `action_soumettre_dss()` écrit `soumis`, qui n'est pas une option de `dss_validation_state`. |
| Numéro picking `/` | L'extension cherche `ir.sequence` de code `dss.number`; aucune séquence de ce code n'est déclarée dans les données de ce module. |
| Refus de soumission | Lire le message `ValidationError` de `action_soumettre()` et vérifier les champs et lignes requis. |
| Refus de mouvement | Lire l'erreur de quantité du modèle stock et contrôler l'emplacement source et les quantités saisies. |

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Diagnostic | Partir de l'enregistrement Odoo, des journaux et des fichiers de configuration réellement chargés. |
| Environnement | Les observations PDF historiques sont spécifiques à une machine et à sa version wkhtmltopdf. |
| Secrets | Ne pas copier de paramètres d'accès, mots de passe ou jetons dans les rapports de diagnostic. |