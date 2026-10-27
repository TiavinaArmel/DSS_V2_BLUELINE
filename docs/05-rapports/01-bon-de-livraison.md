# Bon de Livraison PDF

## 1. Rôle

Le rapport rend une demande `dss.request` en document PDF intitulé « BON DE LIVRAISON ». Il est associé à l'action d'impression `action_report_bon_livraison`.

## 2. Données affichées

| Zone | Champs QWeb |
|---|---|
| En-tête du layout | Logo de la société active du rapport, titre « BON DE LIVRAISON », `name` et `bci`. |
| Informations de livraison | Tableau sans bordure à deux colonnes : destinataire/date, lieu/type d'intervention, puis emplacement sur toute la largeur. |
| Articles | `product_id.name`, `qty_demandee`, `qty_sortie`, `qty_installee`, `qty_retour`, `observation`. |
| Signataires | Demandeur/date de soumission, Chef/date de validation, Magasin/date de validation. |
| État | `state`. |
| Zones de signature | Demandeur, Chef DSS, Magasinier, Sécurité et « Reçu par ». Les deux dernières zones sont des espaces de signature, sans signataire lié par le code. |

Le template ajoute une ligne vide après les articles. Il conserve toutes les lignes et le tableau peut continuer sur les pages suivantes; l'en-tête personnalisé est répété, sans pied de page standard. Les cases du demandeur, du Chef et du Magasin sont liées à la présence de leur signataire.

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
| Action | `ir.actions.report.xml`, type `qweb-pdf`. |
| Format papier | `paperformat_dss_a5`, A5 paysage, marges définies dans le XML, `dpi=0`. |
| Layout | `report_bon_livraison_layout`, dédié à ce rapport et sans pied de page standard. |
| CSS | `static/src/css/report_bl_server.css`, inclus dans `report.assets_common` avec des sélecteurs ciblés DSS. |

Le code Python ajoute `paperformat_id` au contexte du rendu automatique si l'identifiant externe existe. Le code ne fixe pas une version wkhtmltopdf.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Données | Le rapport reprend les champs et lignes existants; aucune date de mouvement propre aux lignes n'est déclarée. |
| Format | A5 paysage, marges de 22 mm en haut et 5 mm sur les autres côtés, `header_spacing` de 10 mm, DPI configuré à `0`. |
| Pièce jointe | Remplacement par recherche nom/modèle/enregistrement, pas une nouvelle pièce à chaque génération. |
| Sources | [`report/dss_report.xml`](../../report/dss_report.xml), [`report_bl_server.css`](../../static/src/css/report_bl_server.css), [`dss_request_bon_livraison.py`](../../models/dss_request_bon_livraison.py). |