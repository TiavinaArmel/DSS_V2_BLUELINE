# Bon de Livraison PDF

## 1. Rôle

Le rapport rend une demande `dss.request` en document PDF intitulé « BON DE LIVRAISON ». Il est associé à l'action d'impression `action_report_bon_livraison`.

## 2. Données affichées

| Zone | Champs QWeb |
|---|---|
| En-tête du layout | Logo de la société active du rapport (100 × 50 px), titre « BON DE LIVRAISON », `name` et `bci`, sans cadres autour des références. |
| Informations de livraison | Tableau sans bordure à deux colonnes : destinataire/date, lieu/type d'intervention, puis emplacement sur toute la largeur. Les libellés complets « DATE D'INTERVENTION » et « TYPE D'INTERVENTION » sont utilisés. |
| Articles | `product_id.name`, `qty_demandee`, `qty_sortie`, `qty_installee`, `qty_retour`, `observation`. |
| Signataires | Demandeur/date de soumission, Chef/date de validation, Magasin/date de validation. |
| État | `state`. |
| Zones de signature | Demandeur, Chef DSS, Magasinier, Sécurité et « Reçu par ». Les deux dernières zones sont des espaces de signature, sans signataire lié par le code. |

Le template ajoute une ligne vide après les articles. Il conserve toutes les lignes et le tableau peut continuer sur les pages suivantes; l'en-tête personnalisé est répété, sans pied de page standard. Les cases du demandeur, du Chef et du Magasin sont liées à la présence de leur signataire. « État DSS » est présenté sur une seule ligne alignée à gauche.

## 3. Génération et rattachement

| Déclencheur | Chemin |
|---|---|
| Validation Stock | Après `state = approuve`, `_generer_bon_livraison()` crée ou met à jour la pièce jointe. |
| Impression manuelle | `action_imprimer_bon_livraison()` régénère le document si la demande est approuvée, puis retourne l'action de rapport. |

Le contenu PDF est encodé avec Base64 et conservé dans `ir.attachment` sous `Bon_Livraison_<name>.pdf`, lié à `dss.request`. Lors de la création initiale, un message de chatter est ajouté avec la pièce jointe; une régénération met à jour l'attachement trouvé.

## 4. Template QWeb et format A5

| Élément | Déclaration |
|---|---|
| Template | `report_bon_livraison_document` dans `report/dss_report.xml`. |
| Action | `ir.actions.report.xml`, identifiant `dss_v2.action_report_bon_livraison`, modèle `dss.request`, type `qweb-pdf`. |
| Format papier | `paperformat_dss_a5`, A5 paysage, marges définies dans le XML, `dpi=0`. |
| Layout | `report_bon_livraison_layout`, dédié à ce rapport et sans pied de page standard. |
| CSS | `static/src/css/report_bl_server.css`, inclus dans `report.assets_common` avec des sélecteurs ciblés DSS. |

Le code Python ajoute `paperformat_id` au contexte du rendu automatique si l'identifiant externe existe. Le code ne fixe pas une version wkhtmltopdf.

## 5. Validation visuelle

Une capture du PDF local à 100 % a confirmé le logo agrandi, les références sans bordures, le tableau d'informations sans quadrillage et la lisibilité des tableaux articles/signatures. À la suite de cette vérification, un espace CSS supplémentaire de 10 px a été demandé entre l'en-tête et le bloc d'informations et ajouté à `.dss-info`.

Le PDF serveur après cette dernière modification n'a pas encore été vérifié. Le poste Windows utilise wkhtmltopdf 0.12.1.2; le rendu doit aussi être contrôlé sur la version réellement installée sur le serveur.

La marge supérieure du format A5 est maintenant réglée localement à 15 mm; les marges basse, gauche et droite restent à 5 mm. `header_spacing` est maintenant réglé à 15 mm : il règle l'espace/décalage entre l'en-tête PDF et le contenu, et non la marge physique du papier. Une valeur plus élevée éloigne le contenu de l'en-tête et consomme davantage de hauteur imprimable; une valeur plus faible rapproche le contenu et peut provoquer une superposition selon le moteur PDF. Les deux valeurs sont à vérifier ensemble sur le PDF. La modification de `header_spacing` doit encore être déployée et testée sur le serveur.

## 6. État du déploiement serveur

Les sauvegardes des fichiers serveur ont été réalisées sur le poste avant remplacement. Les versions précédentes du XML et du CSS ont ensuite été copiées via `/tmp`, installées dans le dossier du module avec `sudo`, et leurs empreintes SHA-256 correspondaient aux sources locales de l'époque. Un redémarrage de `odoo.service` a été demandé. Plus tard, après suppression d'une entrée de rapport incorrecte et mise à niveau de `dss_v2`, l'utilisateur a rapporté que l'impression serveur était revenue à la normale.

La confirmation du PDF normal concerne le correctif de l'entrée de rapport et la mise à niveau du module. La présence sur le serveur de la dernière modification CSS locale (`margin-top: 10px` sur `.dss-info`) n'a pas été vérifiée séparément. Voir [le guide de dépannage et déploiement](../09-maintenance/00-depannage.md).

## 7. Action de rapport et changement de base

Le rapport est déclaré dans le XML avec `model = dss.request`, `report_type = qweb-pdf`, et `report_name` / `report_file = dss_v2.report_bon_livraison_document`. Après un changement ou une restauration de base, vérifier l'action dans **Technique > Rapports > Rapports** : les actions, vues QWeb et identifiants externes sont enregistrés séparément dans chaque base.

Un incident a été corrigé en supprimant une entrée « Bon de livraison » qui affichait le modèle technique `dss_v2_report_bon_livraison_documentation`, puis en mettant à niveau le module. Le rendu est revenu à la normale selon le test rapporté. La cause la plus probable est une action de rapport ancienne, incorrecte ou incompatible avec la déclaration du module dans cette base; son origine exacte n'est pas connue. Avant suppression, sauvegarder la base, vérifier qu'il s'agit bien d'une action en doublon ou obsolète, et ne pas supprimer la vue QWeb ni les données métier. La procédure détaillée est décrite dans [le dépannage](../09-maintenance/00-depannage.md).

## 8. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Données | Le rapport reprend les champs et lignes existants; aucune date de mouvement propre aux lignes n'est déclarée. |
| Format | A5 paysage, marge supérieure de 15 mm et autres marges de 5 mm, `header_spacing` de 15 mm, DPI configuré à `0`; le nouveau réglage reste à valider visuellement. |
| Pièce jointe | Remplacement par recherche nom/modèle/enregistrement, pas une nouvelle pièce à chaque génération. |
| Sources | [`report/dss_report.xml`](../../report/dss_report.xml), [`report_bl_server.css`](../../static/src/css/report_bl_server.css), [`dss_request_bon_livraison.py`](../../models/dss_request_bon_livraison.py). |