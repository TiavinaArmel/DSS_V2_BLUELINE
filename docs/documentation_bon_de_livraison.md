# Bon de Livraison PDF — Documentation du travail (Sprint 10)

Projet : DSS Odoo 10 (module `dss_v2`) — Bluelin Madagascar
Date : 05 – 06 octobre 2026
Environnement : Odoo 10.0 Community, Windows, wkhtmltopdf 0.12.1.2 (with patched qt)
Règle respectée : **aucune modification du core d'Odoo** (consigne de l'encadreur).

---

## 1. Objectif

Générer le **Bon de Livraison (BL)** d'une demande DSS en PDF, à partir du rapport QWeb
`dss_v2.report_bon_livraison_document` (modèle `dss.request`) :

- impression à la demande par le bouton **« Bon de Livraison »** ;
- génération automatique à l'approbation, avec pièce jointe dans le chatter.

## 2. Symptôme

Le PDF généré par Odoo était **blanc** (environ 2 Ko), alors que :

- la vue HTML du rapport (`/report/html/...`) affichait correctement toutes les données ;
- le log d'Odoo ne montrait **aucune erreur** (`POST /report/download 200`) ;
- les rapports **standard** d'Odoo (Inventaire : bon de livraison, réception) sortaient blancs eux aussi.

Le problème venait donc de l'environnement, pas du template du rapport DSS.

## 3. Diagnostic (ce qui a été éliminé)

| Piste testée | Résultat |
|---|---|
| Version de wkhtmltopdf (0.12.1.2 patched qt installée ; la 0.12.5 abandonnée) | Pas la cause |
| wkhtmltopdf lancé à la main sur une page web / sur le HTML du rapport | Fonctionne |
| Rapport avec et sans `report.external_layout` | Toujours blanc |
| Changement du format de papier (`paperformat_euro`) | Toujours blanc |
| Deux copies de wkhtmltopdf (`thirdparty` d'Odoo et `C:\wkhtmltopdf`) | Même version, Odoo utilise celle de `bin_path` |
| Une ou deux instances Odoo (service Windows) | Une seule instance sur le port 8069 |
| Dossier temporaire (`ajrnta~1`, nom court Windows) | Forcé sur `C:\temp` dans le `.bat`, sans effet sur le blanc |
| HTML envoyé par Odoo à wkhtmltopdf | Complet (corps 10 Ko, en-tête 14 Ko, pied 3 Ko) |

## 4. Méthode qui a permis de trouver la cause

**Capturer la commande exacte lancée par Odoo** (sans toucher au core), dans PowerShell :

```powershell
while ($true) { Get-CimInstance Win32_Process -Filter "name='wkhtmltopdf.exe'" | Select-Object -ExpandProperty CommandLine; Start-Sleep -Milliseconds 100 }
```

**Récupérer les fichiers temporaires** envoyés à wkhtmltopdf (corps, en-tête, pied de page) :

```powershell
while ($true) { Get-ChildItem C:\temp\report.body.tmp.*.html -EA SilentlyContinue | % { Copy-Item $_.FullName C:\temp\b.html -Force }; Get-ChildItem C:\temp\report.header.tmp.*.html -EA SilentlyContinue | % { Copy-Item $_.FullName C:\temp\h.html -Force }; Get-ChildItem C:\temp\report.footer.tmp.*.html -EA SilentlyContinue | % { Copy-Item $_.FullName C:\temp\f.html -Force }; Start-Sleep -Milliseconds 50 }
```

**Rejouer la commande à la main, sans `--quiet`**, pour voir les vrais messages d'erreur
(Odoo les masque avec `--quiet`), en ajoutant les options **une par une** :

```
"C:\wkhtmltopdf\bin\wkhtmltopdf.exe" C:\temp\b.html C:\temp\a1.pdf
"C:\wkhtmltopdf\bin\wkhtmltopdf.exe" --page-size A4 C:\temp\b.html C:\temp\a2.pdf
"C:\wkhtmltopdf\bin\wkhtmltopdf.exe" --page-size A4 --margin-top 40.0 --margin-left 7.0 --margin-bottom 23.0 --margin-right 7.0 C:\temp\b.html C:\temp\a3.pdf
"C:\wkhtmltopdf\bin\wkhtmltopdf.exe" --page-size A4 --margin-top 40.0 --margin-left 7.0 --margin-bottom 23.0 --margin-right 7.0 --dpi 96 C:\temp\b.html C:\temp\a4.pdf
```

Résultat : les étapes 1 à 3 fonctionnent, l'étape 4 échoue avec
`QPainter::begin(): Returned false` puis `Error: Unable to write to destination`.

## 5. Cause racine

L'option **`--dpi 96`**.

- Le format de papier « European A4 » avait une **résolution de 90 ppp**.
- Sous Windows, Odoo remplace toute valeur inférieure à 96 par `--dpi 96`
  (message du log : *« Generating PDF on Windows platform require DPI >= 96. Using 96 instead. »*).
- Avec cette option, wkhtmltopdf 0.12.1.2 n'arrive pas à écrire le PDF sur cette machine, et
  Odoo, qui lance l'outil avec `--quiet`, livre un PDF vide.

Constat complémentaire : dans Odoo 10, le nom du fichier téléchargé ne reçoit **pas
d'extension automatique** ; le `.pdf` doit être écrit dans `print_report_name`.

## 6. Solution (tout est dans le module, rien dans le core)

### 6.1 Format de papier propre au DSS, sans option `--dpi`

Dans `report/dss_report.xml` (identifiant utilisé par le code : `paperformat_dss_bon_livraison`) :

```xml
<record id="paperformat_dss_bon_livraison" model="report.paperformat">
    <field name="name">A4 DSS</field>
    <field name="default" eval="False"/>
    <field name="format">A4</field>
    <field name="orientation">Portrait</field>
    <field name="margin_top">40</field>
    <field name="margin_bottom">23</field>
    <field name="margin_left">7</field>
    <field name="margin_right">7</field>
    <field name="header_line" eval="False"/>
    <field name="header_spacing">35</field>
    <field name="dpi">0</field>
</record>
```

`dpi = 0` : Odoo n'envoie plus aucune option `--dpi` à wkhtmltopdf.
Vérification : la commande capturée par PowerShell ne contient plus `--dpi`.

### 6.2 Déclaration du rapport

```xml
<record id="action_report_bon_livraison" model="ir.actions.report.xml">
    <field name="name">Bon de Livraison</field>
    <field name="model">dss.request</field>
    <field name="report_type">qweb-pdf</field>
    <field name="report_name">dss_v2.report_bon_livraison_document</field>
    <field name="report_file">dss_v2.report_bon_livraison_document</field>
    <field name="paperformat_id" ref="paperformat_dss_bon_livraison"/>
    <field name="print_report_name">'Bon de Livraison - %s.pdf' % (object.name or 'DSS')</field>
</record>
```

### 6.3 Bouton « Bon de Livraison » (impression à la demande)

Vue (`dss_request_view.xml`) :

```xml
<button name="action_imprimer_bon_livraison" type="object" string="Bon de Livraison"
        attrs="{'invisible': [('state', '!=', 'approuve')]}" class="oe_highlight"/>
```

Méthode Python (`dssrequest.py`) : l'action est construite par Odoo, ce qui transmet
correctement l'identifiant de la demande :

```python
@api.multi
def action_imprimer_bon_livraison(self):
    self.ensure_one()
    return self.env['report'].get_action(
        self, 'dss_v2.report_bon_livraison_document')
```

### 6.4 Génération automatique et pièce jointe du chatter

Lorsque le PDF est généré depuis le code (et non par le bouton), le format de papier du rapport
n'était pas appliqué (constat fait pendant les tests). Le correctif consiste à **forcer le
format dans le contexte** :

```python
def _generer_bon_livraison(self):
    """
    Génère le PDF du bon de livraison et l'attache au chatter.

    Utilise le rapport QWeb 'dss_v2.report_bon_livraison_document'
    avec un paperformat explicite pour éviter le bug d'Odoo 10
    où Report.get_pdf() ignore le paperformat du rapport.
    """
    self.ensure_one()

    # Récupère le paperformat défini dans report/dss_report.xml
    paperformat = self.env.ref(
        "dss_v2.paperformat_dss_bon_livraison",
        raise_if_not_found=False,
    )

    # Prépare le contexte avec le paperformat explicite
    ctx = dict(self.env.context)
    if paperformat:
        ctx["paperformat_id"] = paperformat.id

    # Génère le PDF en forçant le paperformat dans le contexte
    pdf_content = self.env["report"].with_context(ctx).get_pdf(
        [self.id],
        "dss_v2.report_bon_livraison_document",
    )

    # Crée la pièce jointe
    attachment = self.env["ir.attachment"].create({
        "name": "Bon_Livraison_%s.pdf" % self.name,
        "type": "binary",
        "datas": base64.b64encode(pdf_content),
        "datas_fname": "Bon_Livraison_%s.pdf" % self.name,
        "res_model": "dss.request",
        "res_id": self.id,
    })

    # Poste le message dans le chatter
    self.message_post(
        body="Bon de Livraison genere automatiquement.",
        attachment_ids=[attachment.id],
    )
```

Prérequis : `import base64` en haut de `dssrequest.py`.

## 7. Résultat

| Test | Résultat |
|---|---|
| Adresse directe `/report/pdf/dss_v2.report_bon_livraison_document/ID` | PDF avec contenu |
| Bouton « Bon de Livraison » | PDF avec contenu, nom en `.pdf` |
| PDF joint au chatter à l'approbation | PDF avec contenu |
| Core d'Odoo | Non modifié |

## 8. Points d'attention

- **DPI à 0 sur la machine locale** : réglage nécessaire à cause de wkhtmltopdf sous Windows.
  Sur le serveur (Linux), vérifier le rendu après la connexion du projet ; le format « A4 DSS »
  reste valable.
- Ne pas remettre la résolution à 90 sur le format **European A4** tant que le travail se fait
  sur ce poste : les rapports standard d'Odoo redeviendraient blancs.
- Ne jamais copier dans la documentation ou sur GitHub : `session_id` des commandes capturées,
  mot de passe de la base (`odoo.conf`).
- Le `.bat` de lancement positionne `TEMP` et `TMP` sur `C:\temp` : sans conséquence sur le
  résultat final, à conserver ou à retirer selon les préférences.

## 9. Améliorations du Bon de Livraison à vérifier

À cocher selon l'état du template `report/dss_report.xml` :

- [ ] Case « Soumis » basée sur l'état de la demande (et non sur le validateur Chef)
- [ ] Colonne **Observation** dans le tableau des articles
- [ ] Emplacements de signature : Demandeur, Sécurité, Reçu par
- [ ] Emplacement de destination affiché pour les transferts inter-sites
- [ ] Clés d'état vérifiées dans `dssrequest.py` (`'approuve'`, brouillon)

## 10. Note pour le suivi de sprint

```
Sprint 10 — Bon de Livraison PDF
Réalisé : 10h

 - Identification du problème (PDF blanc, analyse du rapport QWeb, wkhtmltopdf, log Odoo)
 - Débogage (capture de la commande wkhtmltopdf, tests manuels option par option, cause : --dpi 96)
 - Correction du code (format de papier dans le module, bouton d'impression, génération du PDF du chatter)
 - Amélioration visuelle du Bon de Livraison

Résultat : PDF du Bon de Livraison fonctionnel (bouton et chatter), sans modification du core d'Odoo.
```