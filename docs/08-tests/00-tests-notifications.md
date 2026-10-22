# Tests des notifications

## 1. Fichier et périmètre

Le manifeste déclare `tests/test_dss_notifications.py`. Ce fichier utilise `odoo.tests.common.TransactionCase` et vérifie le routage, le journal et le rendu des courriels. Les tests n'envoient pas de message à un serveur SMTP; les adresses utilisées sont sous le domaine réservé `.invalid`.

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
| `test_rejection_mapping_is_explicit` | Vérifie seulement l'état brouillon par défaut et l'absence de motif initial. |

Les deux tests signalés avec « seulement » ont des assertions plus étroites que leur nom ne le suggère.

## 3. Exécution

L'exécution doit se faire avec le lanceur et l'interpréteur de l'installation Odoo 10, sur une base de test. Exemple de commande à adapter à cette installation :

```bash
python odoo-bin -c odoo.conf -d BASE_DE_TEST -u dss_v2 --test-enable --stop-after-init
```

L'audit documentaire n'a pas exécuté Odoo ni cette commande; le résultat des tests n'est donc pas certifié ici.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Couverture | Les tests portent sur les notifications, pas sur l'ensemble du workflow, des mouvements ou des PDF. |
| SMTP | Aucun e-mail réel n'est envoyé par ces tests. |
| Résultat | Toujours lire le résultat du test runner de l'environnement ciblé. |
| Source | [`tests/test_dss_notifications.py`](../../tests/test_dss_notifications.py), entrée dans [`__manifest__.py`](../../__manifest__.py). |