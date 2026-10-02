# Jour 2 — Le modèle `dss.request` : champs, circuit de validation, mouvements de stock

**Auteur :** Tiavina Armel
**Fichier étudié :** `models/dss_request.py`
**Contexte :** Odoo 10 Community — Python 2.7 — ORM Odoo

## Objectifs du jour

- Comprendre les deux classes du fichier : `DssRequestLine` et `DssRequest`
- Distinguer champ saisi, champ calculé (`compute`) et champ `onchange`
- Comprendre la machine à états (`state`) et son circuit complet
- Comprendre comment une demande approuvée génère de vrais mouvements de
  stock Odoo (`stock.picking`, `stock.move`, `stock.quant`)
- Repérer les points fragiles du code, à vérifier au Jour 3

---

## 1. Vue d'ensemble du fichier

Le fichier contient 4 classes :

| Classe | Type de modèle | Rôle |
|---|---|---|
| `DssRequestLine` | `models.Model` | Une ligne d'article dans une demande |
| `DssRequest` | `models.Model` | La demande DSS elle-même (l'en-tête) |
| `DssRejetWizard` | `models.TransientModel` | Popup de saisie du motif de rejet |
| `ProductProduct` | `models.Model` (hérité) | Filtre les articles proposés selon le stock disponible |

---

## 2. `DssRequestLine` — une ligne d'article

### Champs

| Champ | Type | Rôle |
|---|---|---|
| `request_id` | `Many2one` vers `dss.request` | Rattache la ligne à sa demande. `ondelete='cascade'` : supprimée si la demande parente l'est |
| `product_id` | `Many2one` vers `product.product` | L'article concerné. `required=True` |
| `qty_standard` | `Float`, **calculé** | Quantité disponible en stock, recalculée dès que `product_id` change |
| `qty_demandee` | `Float`, saisi | Quantité demandée par l'utilisateur |
| `qty_sortie` | `Float`, saisi | Quantité réellement sortie du stock |
| `qty_installee` | `Float`, saisi | Quantité installée chez le client |
| `qty_retour` | `Float`, saisi | Quantité de matériel qui revient en stock |
| `observation` | `Char` | Remarque libre |
| `qty_demandee_readonly` | `Boolean` | Champ technique : pilote l'affichage (lecture seule ou non) de `qty_demandee` |

### Champ calculé vs champ onchange

C'est la distinction la plus importante de cette partie :

- **`@api.depends` + `compute=`** (`_compute_qty_standard`) : le champ est recalculé et **sauvegardé en base** (`store=True`) à chaque fois que `product_id` change. Sert à des données qu'on veut pouvoir filtrer/trier.
- **`@api.onchange`** (`_onchange_product_id_qty_demandee_readonly`) : s'exécute uniquement **côté interface**, en direct, avant toute sauvegarde. Sert à ajuster dynamiquement l'écran (ici, verrouiller `qty_demandee` si le type d'intervention est un retour de matériel).

---

## 3. `DssRequest` — la demande (l'en-tête)

### Hérite de `mail.thread`

```python
_inherit = ['mail.thread']
```

Ajoute le **chatter** (fil de discussion/historique), les notifications et le suivi des modifications. C'est ce qui permet d'utiliser `message_post()` dans tout le reste du fichier. Explique la dépendance à `mail` dans le manifest (Jour 1).

### Champs principaux

| Champ | Type | Rôle |
|---|---|---|
| `name` | `Char`, `readonly=True` | Numéro de la demande (ex: `DSS-00001`), attribué automatiquement — voir `create()` plus bas |
| `state` | `Selection` | **La machine à états** (voir section 4) |
| `bci` | `Char` | Référence administrative (Bon de Commande Interne) |
| `partner_id` | `Many2one` vers `res.partner` | Le client |
| `lieu_intervention` | `Char` | Texte libre |
| `date_intervention` | `Date`, défaut = aujourd'hui | — |
| `location_id` | `Many2one` vers `stock.location` | Emplacement source (filtré sur `usage = internal`) |
| `location_dest_id` | `Many2one` vers `stock.location` | Emplacement destination, utilisé seulement pour un transfert |
| `type_intervention` | `Selection` | Le champ clé qui pilote tout le reste (voir section 4) |
| `sens_mouvement` | `Char`, **calculé** | Reflet lisible de `type_intervention` : "Sortie", "Entree", "Sortie + Entree", "Transfert" |
| `picking_id` | `Many2one` vers `stock.picking` | Lien vers le mouvement de stock généré |
| `has_ecart` | `Boolean` | Prévu pour signaler un écart — jamais utilisé dans ce fichier |
| `motif_rejet` | `Text` | Rempli par le wizard de rejet |
| `line_ids` | `One2many` vers `dss.request.line` | Les lignes d'articles |
| `signataire_chef_id` / `date_validation_chef` | `Many2one` / `Datetime` | Piste d'audit : qui a validé en tant que Chef, et quand |
| `signataire_magasin_id` / `date_validation_magasin` | `Many2one` / `Datetime` | Piste d'audit : qui a validé en tant que Magasin, et quand |

### `name` : attention à `readonly`

`readonly=True` signifie **lecture seule** : l'utilisateur ne peut pas modifier ce champ depuis l'interface. Ce n'est pas une contrainte d'unicité — aucune règle du code n'empêche deux demandes d'avoir le même nom (pas de `sql_constraints` dans ce fichier). L'unicité en pratique vient uniquement du bon fonctionnement de la séquence Odoo.

### La table de correspondance `type_intervention` → `sens_mouvement`

```python
mapping = {
    'nouvelle_installation': 'Sortie',
    'basculement': 'Sortie + Entree',
    'depannage': 'Sortie + Entree',
    'appro_distant': 'Transfert',
    'installation_interne': 'Sortie',
    'retour_materiel': 'Entree',
}
```

C'est la **table de correspondance centrale** du module : tout le reste (quelle(s) méthode(s) de génération de mouvement sera appelée) en dépend.

### `create()` — numérotation automatique

```python
@api.model
def create(self, vals):
    if vals.get('name', '/') == '/':
        vals['name'] = self.env['ir.sequence'].next_by_code('dss.request') or '/'
    return super(DssRequest, self).create(vals)
```

Si aucun nom n'est fourni (valeur par défaut `/`), on va chercher le prochain numéro auprès de la séquence Odoo `dss.request` (définie dans `data/dss_sequence.xml`, vue au Jour 1 : préfixe `DSS-`, 5 chiffres). C'est une **surcharge** : on ajoute un comportement avant d'appeler la création standard d'Odoo (`super()`).

---

## 4. Le circuit de validation (machine à états)

### Les 6 états possibles

```
brouillon → valide_chef → valide_magasin → approuve → cloture
                                                 ↓
                                              rejete
```

### Les actions, dans l'ordre du circuit

| Méthode | État de départ requis | État d'arrivée | Ce qu'elle fait en plus |
|---|---|---|---|
| `action_soumettre()` | `brouillon` (implicite) | `valide_chef` | Vérifie 6 champs obligatoires + au moins 1 ligne, puis poste le détail des articles dans le chatter |
| `action_valider_chef()` | `valide_chef` | `valide_magasin` | Trace qui a validé (Chef) et quand |
| `action_valider_magasin()` | `valide_magasin` | `approuve` | **Génère les mouvements de stock réels**, puis le bon de livraison |
| `action_rejeter()` | **aucun garde-fou** | `rejete` | Poste le motif s'il existe |
| `action_renvoyer_demandeur()` | — | `brouillon` | Seule action qui fait reculer l'état |

### Règles métier vs contraintes techniques

Les champs obligatoires de `action_soumettre()` (`bci`, `partner_id`, `lieu_intervention`...) ne sont **pas** déclarés `required=True` sur le champ lui-même. Ils ne deviennent obligatoires qu'au moment de la soumission, via des `raise ValidationError(...)` explicites dans le code. Un brouillon peut donc rester incomplet tant qu'il n'est pas soumis. Règle conditionnelle à noter : `location_dest_id` n'est obligatoire que si `type_intervention == 'appro_distant'`.

### Le routeur de `action_valider_magasin()`

C'est la méthode la plus importante du fichier : elle lit `sens_mouvement` et appelle la ou les méthodes de génération de mouvement correspondantes.

```python
if rec.sens_mouvement == 'Sortie':
    rec._generer_mouvement_sortie()
elif rec.sens_mouvement == 'Entree':
    rec._generer_mouvement_entree()
elif rec.sens_mouvement == 'Sortie + Entree':
    rec._generer_mouvement_sortie()
    rec._generer_mouvement_entree()
elif rec.sens_mouvement == 'Transfert':
    rec._generer_mouvement_transfert()
```

**Point important sur l'ordre des opérations** : l'état ne passe à `'approuve'` qu'**après** l'appel aux méthodes de génération. Si une de ces méthodes échoue (par exemple stock insuffisant, qui lève un `ValidationError`), l'exécution s'arrête immédiatement et la ligne `rec.state = 'approuve'` n'est jamais atteinte. La demande reste alors bloquée à l'état `valide_magasin` — ce qui est cohérent : on ne marque pas "approuvé" un mouvement qui n'a pas pu être fait.

---

## 5. Génération des mouvements de stock

Trois méthodes privées (préfixées `_`), toutes suivant le même schéma général.

| Méthode | Sens | Emplacement source | Emplacement destination | Quantité utilisée | Type de picking |
|---|---|---|---|---|---|
| `_generer_mouvement_sortie()` | Vers le client | `location_id` | Emplacement client (`property_stock_customer`) | `qty_sortie` | `outgoing` |
| `_generer_mouvement_entree()` | Depuis le client | Emplacement client | `location_id` | `qty_retour` | `incoming` |
| `_generer_mouvement_transfert()` | Entre 2 emplacements internes | `location_id` | `location_dest_id` | `qty_sortie` | `internal` |

### Les 3 modèles Odoo utilisés

- **`stock.quant`** : la quantité réellement disponible d'un article à un emplacement donné, à un instant T. Interrogé via `read_group()` pour vérifier la disponibilité avant de sortir du stock.
- **`stock.move`** : un mouvement élémentaire (un article, une quantité, d'un emplacement A vers un emplacement B). Il y en a un par ligne d'article.
- **`stock.picking`** : le "bon" qui regroupe plusieurs `stock.move` ensemble (l'équivalent d'un bon de livraison/réception). Il y en a un par appel de méthode.

### Le contrôle de disponibilité (sortie et transfert uniquement)

```python
quants = StockQuant.read_group(
    [('location_id', '=', self.location_id.id), ('product_id', '=', ligne.product_id.id)],
    ['qty'], []
)
qty_disponible = quants[0]['qty'] if quants else 0.0
if ligne.qty_sortie > qty_disponible:
    raise ValidationError(...)
```

Empêche de sortir plus que ce qui est réellement en stock. **Absent de `_generer_mouvement_entree()`** — logique, puisqu'un retour de matériel ne consomme pas de stock existant.

### Le cycle de vie standard d'un mouvement Odoo

Les trois méthodes se terminent toutes par la même séquence :

```python
picking.action_confirm()  # confirme le picking, le rend "prêt à traiter"
picking.action_assign()   # réserve le stock nécessaire
picking.action_done()     # valide définitivement, décrémente le stock en base
```

*(Le détail de chacune de ces 3 étapes sera approfondi au Jour 4, avec des tests pratiques.)*

### Le bon de livraison (`_generer_bon_livraison`)

Appelée uniquement après le passage à l'état `approuve`. Génère le PDF via le rapport QWeb `dss_v2.report_bon_livraison_document`, puis l'attache au chatter sous forme de pièce jointe (`ir.attachment`). C'est ici qu'intervient l'import `base64` vu en tête de fichier : le PDF est un contenu **binaire**, mais le champ `datas` d'`ir.attachment` attend du texte — d'où la conversion `base64.b64encode(pdf_content)`.

---

## 6. La surcharge de `ProductProduct.name_search()`

```python
class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        ...
        location_id = self._context.get('dss_location_id')
        if location_id:
            # ne garder que les articles ayant du stock > 0 à cet emplacement
            ...
        return super(ProductProduct, self).name_search(...)
```

De l'**héritage par extension** (`_inherit` seul, sans `_name`) : on modifie le comportement d'un modèle standard d'Odoo existant, sans en créer un nouveau. Concrètement : si le contexte `dss_location_id` est présent (probablement transmis par la vue du champ `product_id` d'une ligne DSS), seuls les articles ayant réellement du stock à cet emplacement sont proposés dans la liste déroulante. À confirmer au Jour 5 en lisant les vues XML.

---

## 7. Points fragiles identifiés — à vérifier au Jour 3

1. **`action_approuver()` ne génère aucun mouvement de stock**, contrairement à `action_valider_magasin()`, bien que les deux fassent passer l'état à `approuve`. Les deux méthodes ne sont donc pas équivalentes. À vérifier : quel bouton de la vue appelle réellement laquelle ?

2. **`action_rejeter()` n'a aucun garde-fou d'état** (pas de `if rec.state != ...`), contrairement à toutes les autres actions du circuit. Une demande peut être rejetée à n'importe quelle étape. Volontaire ou oubli ?

3. **Trois méthodes ouvrent des wizards dont le nom technique n'a pas été vu dans `models/__init__.py`** (Jour 1) :
   - `action_open_wizard_chef` → `dss.validation.chef.wizard`
   - `action_open_wizard_stock` → `dss.validation.stock.wizard`
   - `action_open_wizard_approuver` → `dss.validation.approuver.wizard`

   Le `__init__.py` n'importe qu'un seul fichier `dss_validation_wizard`. À vérifier en priorité au Jour 3 : ces 3 modèles existent-ils bien dans ce fichier (avec 3 classes), ou y a-t-il une incohérence à corriger ?

4. **Code dupliqué** entre `_generer_mouvement_sortie()` et `_generer_mouvement_transfert()` : le bloc de contrôle de disponibilité (`StockQuant.read_group` + comparaison) est identique dans les deux méthodes. Candidat naturel à factoriser en une méthode partagée — à proposer à l'encadreur.

5. **`_generer_mouvement_entree()` écrase `picking_id`** : dans le cas `sens_mouvement == 'Sortie + Entree'`, les deux méthodes sont appelées l'une après l'autre, mais `picking_id` ne garde que le **dernier** picking créé (celui de l'entrée). Le picking de sortie reste accessible via `stock.picking` mais plus directement depuis la fiche DSS. À vérifier en pratique au Jour 4.

---

## Exercices — corrigé

**Q1. Pourquoi `qty_standard` a-t-il `compute=` alors que `qty_demandee` n'en a pas ?**
`qty_standard` est une information système (le stock réel), non modifiable par l'utilisateur — elle doit être calculée par Odoo. `qty_demandee` est une saisie métier : c'est à l'utilisateur de la renseigner.

**Q2. Pourquoi les contrôles obligatoires sont-ils faits dans `action_soumettre()` plutôt qu'avec `required=True` ?**
Pour permettre de sauvegarder un **brouillon incomplet**. Si ces champs étaient `required=True`, l'utilisateur devrait tout remplir dès la création de l'enregistrement, avant même d'avoir eu le temps de réfléchir à sa demande — moins pratique pour un usage réel.

**Q3. Pourquoi l'état passe-t-il à `'approuve'` seulement après la génération des mouvements ?**
Pour éviter de marquer une demande comme définitivement approuvée alors que le mouvement de stock correspondant a échoué (ex. stock insuffisant). Si la génération échoue, la demande reste bloquée à `valide_magasin`, ce qui reflète la réalité.

---

## Points à revoir

- Bien distinguer `@api.depends` (champ calculé, stocké) et `@api.onchange` (ajustement d'écran, non stocké)
- `readonly=True` ≠ contrainte d'unicité
- Toujours vérifier l'ordre des opérations dans une méthode qui modifie `state` : qu'est-ce qui se passe AVANT le changement d'état, qu'est-ce qui se passe APRÈS ?
- `_generer_mouvement_sortie`, `_generer_mouvement_entree`, `_generer_mouvement_transfert` suivent toujours le même schéma : filtrer les lignes → (vérifier le stock) → déterminer les emplacements → créer le picking → créer les moves → confirmer/assigner/valider
