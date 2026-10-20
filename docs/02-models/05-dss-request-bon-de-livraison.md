# Extension de génération du bon de livraison

## 1. Rôle

`DssRequestBonLivraison` ajoute au modèle `dss.request` la génération du PDF, son rattachement à la demande et l'action d'impression. Le contenu et le format du document sont déclarés dans [`report/dss_report.xml`](../../report/dss_report.xml).

## 2. Méthodes

| Méthode | Déclencheur | Effet |
|---|---|---|
| `_generer_bon_livraison()` | Validation Stock après passage à `approuve`, ou impression manuelle si déjà approuvée | Génère le PDF QWeb, l'encode en Base64, puis crée ou met à jour un `ir.attachment`. |
| `action_imprimer_bon_livraison()` | Bouton visible sur une demande approuvée | Régénère le PDF si l'état vaut `approuve`, puis retourne `report.get_action(...)`. |

## 3. Format papier dans le contexte

La méthode cherche `dss_v2.paperformat_dss_a5` sans lever d'erreur si l'identifiant est absent. Si le format existe, elle ajoute son ID à `paperformat_id` dans le contexte passé à `report.get_pdf()`. Cette solution est explicitement décrite par le code comme contournement du comportement observé avec `Report.get_pdf()` sous Odoo 10.

## 4. Encodage et pièce jointe

| Étape | Implémentation |
|---|---|
| Rendu | `get_pdf([self.id], 'dss_v2.report_bon_livraison_document')`. |
| Nom | `Bon_Livraison_<numéro DSS>.pdf`. |
| Encodage | `base64.b64encode(pdf_content)` vers `ir.attachment.datas`. |
| Liaison | `res_model='dss.request'` et `res_id=self.id`. |
| Remplacement | Recherche par nom, modèle et ID; mise à jour si trouvé. |
| Chatter | `message_post()` avec la pièce jointe lors de sa création initiale. |

## 5. Cycle

```text
Validation Stock réussie
  `-- état approuve
      `-- _generer_bon_livraison()
          `-- QWeb PDF -> Base64 -> ir.attachment lié à dss.request
```

## 6. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Rapport | Identifiant QWeb `dss_v2.report_bon_livraison_document`. |
| Format | `paperformat_dss_a5`, A5 paysage, `dpi=0`, appliqué également via contexte dans le rendu automatique. |
| Régénération | L'impression manuelle régénère l'attachement uniquement lorsque l'état est `approuve`. |
| Source | [`models/dss_request_bon_livraison.py`](../../models/dss_request_bon_livraison.py). |