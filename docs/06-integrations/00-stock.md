# Intégration avec Stock

## 1. Modèles Odoo utilisés

| Modèle | Rôle dans le code DSS |
|---|---|
| `product.product` | Article de la ligne DSS et unité de mesure du mouvement. |
| `stock.quant` | Quantité `qty` agrégée pour le contrôle de sortie et de transfert. |
| `stock.location` | Emplacement source, destination interne ou emplacement client. |
| `stock.picking.type` | Type de picking recherché par code. |
| `stock.picking` | En-tête du transfert créé. |
| `stock.move` | Mouvement associé à chaque ligne traitée. |

## 2. Types de picking dans le workflow principal

| Code Odoo recherché | Sens DSS | Emplacements |
|---|---|---|
| `outgoing` | Sortie | `location_id` vers l'emplacement client du partenaire ou le repli standard. |
| `incoming` | Entrée | Emplacement client vers `location_id`. |
| `internal` | Transfert | `location_id` vers `location_dest_id`. |

Le code effectue une recherche `limit=1` par code de picking; il ne filtre pas la recherche sur un entrepôt ou une société dans les méthodes présentées.

## 3. Contrôle de stock et cycle

Les méthodes de sortie et de transfert agrègent `stock.quant.qty` par produit et emplacement, puis lèvent `ValidationError` si `qty_sortie` dépasse la valeur obtenue. Le mouvement entrant utilise `qty_retour` et ne fait pas ce contrôle de disponibilité.

```text
DSS line_ids
  `-- lignes dont la quantité correspondante est positive
        `-- stock.picking + stock.move par ligne
              `-- action_confirm()
                    `-- action_assign()
                          `-- action_done()
```

## 4. Workflow DSS parallèle sur `stock.picking`

`models/stock_picking.py` ajoute des champs DSS et des méthodes de validation au modèle standard. Ce parcours est distinct des transitions de `dss.request` et aucun fichier de vue stock spécifique n'est déclaré dans le manifeste.

Deux incohérences sont directement visibles dans le code : `action_soumettre_dss()` écrit la valeur `soumis`, absente de la sélection `dss_validation_state`; par ailleurs, `valide_securite` porte le libellé « Validation Demandeur ». La séquence `dss.number` de cette extension est distincte de la séquence `dss.request`.

L'extension de `stock.immediate.transfer.process()` appelle `check_dss_ecart()` avant la méthode parente. Ce contrôle exige une justification lorsque `dss_standard_qty` est non nul et diffère de la quantité du move de plus de `0.001`.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Flux principal | Les méthodes de `dss.request` créent et terminent les pickings. |
| Contrôle de quantité | Présent avant sortie et transfert; pas dans la méthode d'entrée. |
| Circuit secondaire | Le workflow ajouté à `stock.picking` est séparé et comporte une valeur d'état incohérente. |
| Sources | [`dss_request_stock.py`](../../models/dss_request_stock.py), [`stock_picking.py`](../../models/stock_picking.py). |