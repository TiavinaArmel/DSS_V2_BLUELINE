# Jour 3 — Les wizards du circuit de validation

**Auteur :** Tiavina Armel
**Fichiers étudiés :** `models/dss_validation_wizard.py`, `models/dss_cloture_wizard.py`, `models/dss_qty_sortie_wizard.py`
**Contexte :** Odoo 10 Community — Python 2.7 — ORM Odoo

## Objectifs du jour

- Comprendre le rôle des `models.TransientModel` (popups/wizards)
- Distinguer un wizard de simple confirmation et un wizard avec logique métier
- Comprendre `default_get()` et le mécanisme de pré-remplissage
- Comprendre comment un wizard reporte ses modifications sur les vraies données
- Lever l'anomalie du Jour 2 sur les 3 wizards de validation

---

## 1. Rappel : qu'est-ce qu'un `TransientModel` ?

Contrairement à `models.Model` (utilisé par `dss.request`, `dss.request.line`), un `models.TransientModel` est un modèle **temporaire** : ses enregistrements ne sont pas conservés indéfiniment, Odoo les nettoie automatiquement après un certain temps. C'est le type de modèle standard pour tout ce qui est popup/assistant (« wizard » en anglais) : une interface qui aide l'utilisateur à faire quelque chose, sans que les données saisies dans la popup elle-même aient besoin d'être gardées pour toujours.

---

## 2. Anomalie du Jour 2 résolue

Au Jour 2, on avait repéré que `dss_request.py` ouvrait 3 wizards (`dss.validation.chef.wizard`, `dss.validation.stock.wizard`, `dss.validation.approuver.wizard`) dont les noms n'apparaissaient pas dans `models/__init__.py`.

**Confirmation :** les 3 modèles existent bien, tous les trois regroupés dans le même fichier `dss_validation_wizard.py`, qui est bien importé sous le nom `dss_validation_wizard`. Il n'y a ni bug ni incohérence — simplement 3 classes dans un seul fichier, ce qui n'était pas visible depuis la seule lecture du `__init__.py`.

---

## 3. Les wizards de confirmation simple (`dss_validation_wizard.py`)

### Structure commune aux 3 classes

| Classe | `_name` | Appelle sur la demande |
|---|---|---|
| `DssValidationChefWizard` | `dss.validation.chef.wizard` | `action_valider_chef()` |
| `DssValidationStockWizard` | `dss.validation.stock.wizard` | `action_valider_magasin()` |
| `DssValidationApprouverWizard` | `dss.validation.approuver.wizard` | `action_approuver()` |

Les 3 classes suivent exactement le même patron :

```python
class DssValidationChefWizard(models.TransientModel):
    _name = 'dss.validation.chef.wizard'
    _description = 'Wizard de confirmation Validation Chef'

    request_id = fields.Many2one('dss.request', string='Demande DSS', required=True)

    @api.multi
    def action_confirmer(self):
        self.ensure_one()
        self.request_id.action_valider_chef()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_annuler(self):
        return {'type': 'ir.actions.act_window_close'}
```

- **Un seul champ** : `request_id`, qui pointe vers la demande concernée.
- **`action_confirmer()`** : ne fait qu'une seule chose — appeler la méthode d'action correspondante sur la **vraie** demande. Toute la logique métier (vérification d'état, changement de `state`, génération des mouvements...) reste dans `dss_request.py`.
- **`action_annuler()`** : ferme la popup sans rien faire.

### Pourquoi ces wizards existent-ils, s'ils ne font « que » appeler une méthode ?

Ce sont des **popups de confirmation** (« êtes-vous sûr de vouloir valider ? »), qui évitent qu'un clic accidentel sur un bouton déclenche immédiatement une action irréversible (comme la génération de mouvements de stock). C'est une bonne pratique Odoo : séparer la **confirmation utilisateur** (dans le wizard) de la **logique métier** (dans le modèle principal).

---

## 4. Le wizard de modification des quantités (`dss_qty_sortie_wizard.py`)

### Rôle

Permet au Responsable Stock d'ajuster les quantités de sortie et de retour **avant** la validation finale, sans modifier directement les vraies lignes de la demande tant que la popup n'est pas confirmée.

### Les 2 classes

| Classe | `_name` | Rôle |
|---|---|---|
| `DssQtySortieWizard` | `dss.qty.sortie.wizard` | Le wizard lui-même (l'en-tête) |
| `DssQtySortieWizardLine` | `dss.qty.sortie.wizard.line` | Une ligne temporaire, copie d'une ligne de la demande |

### `default_get()` — le pré-remplissage

```python
@api.model
def default_get(self, fields_list):
    res = super(DssQtySortieWizard, self).default_get(fields_list)
    request_id = self.env.context.get('default_request_id') or self.env.context.get('active_id')
    if request_id:
        request = self.env['dss.request'].browse(request_id)
        lines = []
        for line in request.line_ids:
            lines.append((0, 0, {
                'request_line_id': line.id,
                'product_id': line.product_id.id,
                'qty_demandee': line.qty_demandee,
                'qty_sortie': line.qty_sortie,
                'qty_retour': line.qty_retour,
            }))
        res['request_id'] = request_id
        res['line_ids'] = lines
    return res
```

- **`default_get()`** est une méthode standard d'Odoo, appelée automatiquement à l'ouverture d'un formulaire pour calculer les valeurs par défaut de chaque champ.
- **`self.env.context.get('default_request_id') or self.env.context.get('active_id')`** : récupère l'ID de la demande depuis **deux sources possibles**.
  - `default_request_id` : une clé de contexte qu'on a nous-mêmes définie, dans `action_open_modifier_qte_sortie()` (`dss_request.py`), via `'context': {'default_request_id': self.id}`.
  - `active_id` : une clé **standard et automatique** d'Odoo, remplie sans intervention du développeur dès qu'une action est ouverte depuis une fiche déjà affichée.
  - Le `or` sert de filet de sécurité à deux niveaux : on utilise `default_request_id` s'il a été explicitement fourni, sinon on retombe sur le mécanisme standard `active_id`.
- **`(0, 0, {...})`** : syntaxe spéciale d'Odoo pour les champs `One2many`/`Many2many` en création, qui signifie « crée une nouvelle ligne liée avec ces valeurs ». On copie ici chaque ligne réelle de la demande dans une ligne temporaire du wizard.

### `action_valider()` — le report des modifications

```python
@api.multi
def action_valider(self):
    self.ensure_one()
    changements = []
    for line in self.line_ids:
        parties = []
        ancienne_sortie = line.request_line_id.qty_sortie
        nouvelle_sortie = line.qty_sortie
        if ancienne_sortie != nouvelle_sortie:
            parties.append(u'Qte Sortie %s \u2192 %s' % (ancienne_sortie, nouvelle_sortie))

        ancienne_retour = line.request_line_id.qty_retour
        nouvelle_retour = line.qty_retour
        if ancienne_retour != nouvelle_retour:
            parties.append(u'Qte Retour %s \u2192 %s' % (ancienne_retour, nouvelle_retour))

        if parties:
            changements.append(u'\u2022 %s : %s' % (line.product_id.name, u', '.join(parties)))
            line.request_line_id.write({'qty_sortie': nouvelle_sortie, 'qty_retour': nouvelle_retour})

    if changements:
        message = u'Le Responsable Stock %s a modifi\u00e9 les quantit\u00e9s.<br/><br/>%s' % (
            self.env.user.name, '<br/>'.join(changements))
        self.request_id.message_post(body=message)

    return {'type': 'ir.actions.act_window_close'}
```

**Point clé** : `line` est une ligne **temporaire** du wizard, `line.request_line_id` est la **vraie** ligne de la demande. Le wizard travaille sur une copie, et ne répercute les changements que si on confirme.

- Pour chaque ligne, on **compare** l'ancienne valeur (sur la vraie ligne) et la nouvelle (saisie dans le wizard).
- On n'ajoute au message et on n'écrit en base **que les lignes réellement modifiées** (`if parties:` / `if ancienne_xxx != nouvelle_xxx:`).
- Si **aucune** ligne n'a changé, `changements` reste vide et **aucun message n'est posté** dans le chatter — pas de bruit inutile pour une validation sans modification.
- `\u2192` (→) et `\u2022` (•) sont des caractères Unicode écrits sous forme de code, une pratique courante en Python 2 pour éviter des soucis d'encodage selon l'éditeur.

### `DssQtySortieWizardLine`

| Champ | `readonly` | Rôle |
|---|---|---|
| `qty_demandee` | Oui | Fige ce qui a été demandé à l'origine |
| `qty_sortie` | Non | Modifiable : c'est l'objet de ce wizard |
| `qty_retour` | Non | Modifiable |

---

## 5. Le wizard de clôture (`dss_cloture_wizard.py`)

### Rôle

Permet de clôturer une demande déjà approuvée, en saisissant les quantités réellement **installées** et **retournées** sur le terrain, et détecte automatiquement les écarts avec ce qui avait été sorti.

### Les 2 classes

| Classe | `_name` | Rôle |
|---|---|---|
| `DssClotureWizard` | `dss.cloture.wizard` | Le wizard lui-même |
| `DssClotureWizardLine` | `dss.cloture.wizard.line` | Une ligne temporaire |

`default_get()` suit exactement le même principe que pour le wizard précédent (même lecture du contexte, même construction de lignes avec `(0, 0, {...})`), avec cette fois `qty_sortie`, `qty_installee` et `qty_retour` copiés depuis la vraie ligne.

### `action_confirmer()` — clôture et détection d'écart

```python
@api.multi
def action_confirmer(self):
    self.ensure_one()
    ecarts = []
    recap = []
    for line in self.line_ids:
        line.request_line_id.write({
            'qty_installee': line.qty_installee,
            'qty_retour': line.qty_retour,
        })
        recap.append(u'\u2022 %s : Qte Installee %s, Qte Retour %s' % (
            line.product_id.name, line.qty_installee, line.qty_retour))
        if line.qty_installee != line.qty_sortie:
            ecarts.append(u'%s : sorti %s, installe %s' % (
                line.product_id.name, line.qty_sortie, line.qty_installee))

    self.request_id.has_ecart = bool(ecarts)
    self.request_id.state = 'cloture'

    message = u'<b>%s</b> a cloture la demande.<br/>%s' % (self.env.user.name, u'<br/>'.join(recap))
    if ecarts:
        message += u'<br/><br/><b>Ecarts detectes :</b><br/>' + u'<br/>'.join(ecarts)
    self.request_id.message_post(body=message)

    return {'type': 'ir.actions.act_window_close'}
```

- **Différence de style avec `action_valider()` du wizard précédent** : ici, chaque ligne est **systématiquement** réécrite (`line.request_line_id.write(...)` n'est protégé par aucun `if`), même si rien n'a changé — contrairement au wizard de quantité sortie, plus sélectif. Une petite incohérence entre les deux wizards, à noter sans gravité.
- **`recap`** accumule un résumé de **toutes** les lignes.
- **`ecarts`** accumule uniquement les lignes où `qty_installee != qty_sortie`.
- **`self.request_id.has_ecart = bool(ecarts)`** : c'est ici que le champ `has_ecart` de `dss.request` (resté un mystère au Jour 2, jamais utilisé dans `dss_request.py`) prend tout son sens. `bool(une_liste)` vaut `False` si la liste est vide, `True` sinon : `has_ecart` devient donc un simple indicateur **« y a-t-il eu au moins un écart lors de la clôture ? »**.
- **`self.request_id.state = 'cloture'`** : c'est ici, et seulement ici, que l'état `cloture` (le dernier de la machine à états, vu au Jour 2) est atteint.
- Le message final a 2 parties : le récap est **toujours** affiché ; le bloc « Ecarts detectes » ne s'ajoute que **si `ecarts` n'est pas vide**.

### `DssClotureWizardLine`

| Champ | `readonly` | Rôle |
|---|---|---|
| `qty_sortie` | Oui | Fige ce qui a été sorti (décidé à l'étape précédente) |
| `qty_installee` | Non | Modifiable : c'est l'objet de ce wizard |
| `qty_retour` | Non | Modifiable |

---

## 6. Comparaison des 2 wizards « avec logique »

| | `dss_qty_sortie_wizard` | `dss_cloture_wizard` |
|---|---|---|
| Étape du circuit | Avant validation Stock | Après approbation, pour clôturer |
| Champ figé (readonly) | `qty_demandee` | `qty_sortie` |
| Champs modifiables | `qty_sortie`, `qty_retour` | `qty_installee`, `qty_retour` |
| Écrit en base | Seulement les lignes modifiées | Toutes les lignes, systématiquement |
| Détecte un écart | Non | Oui (`has_ecart`) |
| Change `state` | Non | Oui → `'cloture'` |

La logique de « figer le champ de l'étape précédente » est cohérente avec l'ordre chronologique du circuit : à chaque étape, on verrouille ce qui a été décidé avant, pour ne faire évoluer que la donnée propre à cette étape.

---

## 7. Points à vérifier au Jour 4 ou 5

1. **Incohérence mineure** entre les deux wizards : `dss_qty_sortie_wizard` n'écrit que les lignes modifiées, `dss_cloture_wizard` écrit systématiquement toutes les lignes. Sans conséquence fonctionnelle grave, mais à harmoniser si le code est retravaillé.
2. **Aucun des 3 wizards de confirmation simple (`dss_validation_wizard.py`) n'a de vue associée visible pour l'instant** — à confirmer au Jour 5 que `views/dss_validation_wizard_views.xml` définit bien 3 formulaires (un par wizard), avec les boutons Confirmer/Annuler.
3. **`action_open_modifier_qte_sortie()`** (dans `dss_request.py`) n'a, à ce stade, aucun garde-fou sur l'état de la demande pour autoriser l'ouverture de ce wizard — à vérifier si c'est voulu (le Magasin peut-il modifier les quantités à n'importe quelle étape ?) ou si un contrôle manque.

---

## Exercices — corrigé

**Q1. Pourquoi deux façons de récupérer l'ID de la demande (`default_request_id` et `active_id`) ?**
`default_request_id` est une clé de contexte définie par nous dans `dss_request.py` lors de l'ouverture du wizard. `active_id` est une clé standard, automatiquement fournie par Odoo quand une action est lancée depuis une fiche ouverte. Le `or` garantit que le wizard fonctionne même si le contexte explicite n'a pas été précisé.

**Q2. Pourquoi `qty_sortie` est readonly dans `DssClotureWizardLine` mais pas dans `DssQtySortieWizardLine` ?**
Parce que ce sont deux étapes différentes du circuit : au moment du wizard de quantité sortie, `qty_sortie` est justement ce qu'on est en train de décider (modifiable). Au moment de la clôture, cette décision est déjà prise et ne doit plus changer (figée en lecture seule) ; seules les quantités installée et retour, propres à la clôture, restent modifiables.

**Q3. À quoi sert `has_ecart` ?**
C'est un indicateur booléen qui signale si, au moment de la clôture, au moins un article a été installé en quantité différente de ce qui avait été sorti du stock.

---

## Points à revoir

- `TransientModel` : données temporaires, nettoyées automatiquement par Odoo, à utiliser pour toute popup/assistant
- `default_get()` : méthode standard appelée à l'ouverture d'un formulaire, pour calculer les valeurs par défaut
- `(0, 0, {...})` : syntaxe de création en lot pour un champ `One2many`/`Many2many`
- `self.env.context.get(...)` : lire une valeur du contexte, avec une valeur de repli possible via `or`
- Un wizard « bien conçu » sépare la confirmation utilisateur de la logique métier, qui reste sur le modèle principal
