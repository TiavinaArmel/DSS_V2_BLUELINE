# Bon de Livraison PDF

## 1. Rôle

Le rapport rend une demande `dss.request` en document PDF intitulé « BON DE LIVRAISON ». Il est associé à l'action d'impression `action_report_bon_livraison`.

## 2. Données affichées

| Zone | Champs QWeb |
|---|---|
| En-tête | `partner_id.name`, `type_intervention`, `lieu_intervention`, `date_intervention`, `location_id.display_name`, `name`, `bci`. |
| Articles | `product_id.name`, `qty_demandee`, `qty_sortie`, `qty_installee`, `qty_retour`, `observation`. |
| Signataires | Demandeur/date de soumission, Chef/date de validation, Magasin/date de validation. |
| État | `state`. |
| Zones de signature | Demandeur, Chef DSS, Magasinier, Sécurité et « Reçu par ». Les deux dernières zones sont des espaces de signature, sans signataire lié par le code. |

Le template ajoute des lignes vides lorsque la demande comporte moins de deux articles. La case du demandeur est liée au fait que l'état ne soit pas `brouillon`; les cases Chef et Magasin sont liées à la présence de leur signataire.

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
| CSS | `static/src/css/report_bl.css`, inclus dans `report.assets_common`. |

Le code Python ajoute `paperformat_id` au contexte du rendu automatique si l'identifiant externe existe. Le code ne fixe pas une version wkhtmltopdf.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Données | Le rapport reprend les champs et lignes existants; aucune date de mouvement propre aux lignes n'est déclarée. |
| Format | A5 paysage, DPI configuré à `0`. |
| Pièce jointe | Remplacement par recherche nom/modèle/enregistrement, pas une nouvelle pièce à chaque génération. |
| Sources | [`report/dss_report.xml`](../../report/dss_report.xml), [`report_bl.css`](../../static/src/css/report_bl.css), [`dss_request_bon_livraison.py`](../../models/dss_request_bon_livraison.py). |