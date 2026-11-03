# Tests des notifications

## 1. Fichier et périmètre

Le manifeste déclare `tests/test_dss_notifications.py`, `tests/test_dss_stock_location.py` et `tests/test_dss_quantities.py`. Les tests utilisent `odoo.tests.common.TransactionCase`. Les tests de notifications vérifient le routage, le journal et le rendu des courriels; les tests de quantités vérifient la validation directe, la modification par wizard, le motif obligatoire, la conservation de `qty_demandee` et la précision à deux décimales.

## 2. Cas couverts

| Test | Objet vérifié |
|---|---|
| `test_group_email_resolution_ignores_missing_email` | Le groupe Chef existe et les adresses retournées sont uniques. |
| `test_missing_recipient_does_not_create_mail_or_log` | Aucun destinataire ne produit ni mail ni journal. |
| `test_mail_is_queued_without_sending` | Mail en état `outgoing`, autonome du chatter, journal lié à la demande, URL du logo issue de `web.base.url` et absence de ligne motif pour une soumission. |
| `test_same_event_is_not_queued_twice` | Une même paire demande/événement n'est pas créée deux fois par la méthode. |
| `test_notification_event_keys_are_unique` | La contrainte SQL rejette un doublon demande/événement. |
| `test_approval_uses_one_event_for_both_entry_points` | Vérifie seulement l'absence initiale de journal `stock_approval`; il ne teste pas les deux points d'entrée annoncés par son nom. |
| `test_rejection_keeps_motif_in_notification_context` | Le motif fourni apparaît dans le corps rendu du mail de rejet. |
| `test_return_to_requester_email_contains_rejection_motif` | Destinataire demandeur et motif inclus dans le courriel de renvoi. |
| `test_security_is_not_notified_without_a_real_dss_security_transition` | L'action d'approbation Stock ne crée pas de clé d'événement `security`. |
| `test_stock_approval_email_contains_quantity_change_motif` | L'e-mail de validation Stock contient le motif d'écart et le nom de l'article concernés. |
| `test_rejection_mapping_is_explicit` | Vérifie seulement l'état brouillon par défaut et l'absence de motif initial. |

Les deux tests signalés avec « seulement » ont des assertions plus étroites que leur nom ne le suggère.

## 3. Exécution

L'exécution doit se faire avec le lanceur et l'interpréteur de l'installation Odoo 10, sur une base de test. Exemple de commande à adapter à cette installation :

```bash
python odoo-bin -c odoo.conf -d BASE_DE_TEST -u dss_v2 --test-enable --stop-after-init
```

L'audit documentaire n'a pas exécuté Odoo ni cette commande; le résultat des tests n'est donc pas certifié ici.

Pour l'évolution du 3 novembre 2026, la compilation Python et l'analyse syntaxique XML ont été vérifiées. Le test runner Odoo n'a pas été exécuté dans l'environnement de développement utilisé, car aucun `odoo-bin` ou `odoo.py` n'y a été trouvé.

## 3 bis. Incident Unicode du wizard de quantités

Un `UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3` a été observé dans `dss_qty_sortie_wizard.py`, dans `action_valider()`, lors de la construction d'un message contenant le nom d'un article ou d'un utilisateur. La cause était l'interpolation d'une valeur Unicode dans une chaîne `str` Python 2. La correction consiste à utiliser des chaînes Unicode `u"..."` pour les messages et les séparateurs construits par cette méthode. Le scénario à rejouer sur Odoo 10 doit inclure un article, un utilisateur et un motif comportant des accents.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Couverture | Les tests portent sur les notifications, pas sur l'ensemble du workflow, des mouvements ou des PDF. |
| SMTP | Aucun e-mail réel n'est envoyé par ces tests. |
| Résultat | Toujours lire le résultat du test runner de l'environnement ciblé. |
| Source | [`tests/test_dss_notifications.py`](../../tests/test_dss_notifications.py), entrée dans [`__manifest__.py`](../../__manifest__.py). |