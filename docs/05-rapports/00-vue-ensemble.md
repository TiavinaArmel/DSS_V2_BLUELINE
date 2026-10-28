# Vue d'ensemble des rapports

## 1. Rapports déclarés

| Rapport | Identifiant | Modèle | Format |
|---|---|---|---|
| Bon de Livraison | `dss_v2.report_bon_livraison_document` | `dss.request` | QWeb PDF, format papier A5 paysage. |

Le fichier `report/dss_report.xml` ne déclare pas de rapport séparé pour un bon de retour.

## 2. Format papier

| Identifiant XML | Taille | Orientation | DPI |
|---|---|---|---:|
| `dss_v2.paperformat_dss_a5` | A5 | Landscape | 0 |

Les marges déclarées sont 15 mm en haut et 5 mm en bas et sur les côtés; `header_spacing` vaut 15 mm pour régler l'écart entre l'en-tête PDF et le contenu. Le tableau d'informations a également un `margin-top` CSS de 10 px. `margin_top` réserve la zone supérieure de la page, tandis que `header_spacing` règle le décalage du contenu par rapport à l'en-tête; ces deux paramètres influencent ensemble l'espace vertical et doivent être vérifiés sur le PDF produit.

## 3. Génération PDF

Le rapport utilise `report.html_container` et le layout QWeb dédié `report_bon_livraison_layout`, sans pied de page standard. L'en-tête affiche le logo, le titre et les références DSS/BCI sans cadres. Le bloc d'informations est une grille sans bordure à deux colonnes; les articles et les signatures conservent leurs bordures. Ses styles ciblés sont chargés depuis `static/src/css/report_bl_server.css`. La méthode Python de génération place explicitement l'ID du format papier dans le contexte lorsque le format existe.

## 4. État de validation et déploiement

| Environnement | État vérifié |
|---|---|
| Poste Windows | Le XML a été validé, le module `dss_v2` a été mis à niveau dans `DSS_V2_DB`, Odoo a démarré et `/web/login` a répondu HTTP 200. Une capture PDF à 100 % a confirmé la lisibilité de l'en-tête, du tableau et des signatures. |
| Serveur Debian | Les versions précédentes de `dss_report.xml` et `report_bl_server.css` ont été copiées et leurs SHA-256 comparés avec les sources locales à ce moment-là. Après un incident lié à une entrée de rapport affichant le modèle technique `dss_v2_report_bon_livraison_documentation`, l'entrée a été supprimée dans l'interface technique, `dss_v2` a été mis à niveau et l'impression a été retestée avec le rendu revenu à la normale (résultat rapporté par l'utilisateur). La cause exacte de l'entrée incorrecte n'est pas établie. La dernière modification CSS locale (`margin-top: 10px` sur `.dss-info`) n'a pas de confirmation indépendante de copie sur le serveur. |

Le test rapporté confirme la réparation fonctionnelle de l'incident, mais ne prouve pas que le serveur utilise la dernière version de chaque fichier local. Pour un prochain déploiement, vérifier les empreintes des fichiers, le modèle et le nom QWeb de l'action de rapport, puis imprimer un PDF de contrôle. La marge supérieure A5 et `header_spacing` ont été fixés localement à 15 mm; leur déploiement serveur et leur rendu PDF restent à vérifier.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Rapport existant | Un BL QWeb PDF sur `dss.request`. |
| Bon de retour | Aucun rapport autonome n'est déclaré; voir [la fiche dédiée](02-bon-de-retour.md). |
| Source | [`report/dss_report.xml`](../../report/dss_report.xml). |