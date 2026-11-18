# Tests des notifications

## 1. Fichier et périmètre

Le manifeste déclare des tests de notifications, d'emplacements, de services, de clôture et de quantités. Ils utilisent `odoo.tests.common.TransactionCase`. Les tests de notifications vérifient le routage, le journal et le rendu des courriels; les tests de quantités vérifient la validation directe, la modification par wizard, le motif obligatoire, la conservation de `qty_demandee` et la précision à deux décimales. Les tests de clôture vérifient l'accès, les motifs exceptionnels, le calcul des retours et leur transfert vers l'emplacement source. Les cas « Retour de matériel » couvrent aussi la correction motivée de `qty_retour`, sa conservation si elle est inchangée et la clôture sans réécriture ni nouveau mouvement.

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
| `test_stock_approval_email_contains_quantity_change_motif` | L'e-mail de validation Stock contient le motif d'écart et le nom de l'article dans une liste `<ul><li>`, sans `<br/>` dans le bloc des motifs. |
| `test_return_material_approval_email_uses_return_quantity` | Le courriel d'approbation affiche la quantité retournée validée, son motif et non la quantité demandée/sortie. |
| `test_sortie_closure_defaults_to_all_installed` | Une ligne de sortie laissée intacte est clôturée avec toute la quantité installée et aucun retour. |
| `test_sortie_closure_calculates_return_and_replenishes_origin` | Le retour calculé crée un picking entrant vers l'emplacement source et apparaît dans le chatter et l'e-mail. |
| `test_sortie_closure_can_use_return_as_the_input` | Saisir le retour calcule la quantité installée complémentaire. |
| `test_sortie_closure_onchange_updates_the_complementary_quantity` | Le wizard recalcule immédiatement l'autre quantité lorsque le mode ou la valeur saisie change. |
| `test_sortie_closure_rejects_quantity_above_stock_output` | Le serveur rejette une quantité installée supérieure à la quantité sortie. |
| `test_sortie_closure_rejects_negative_return` | Le serveur rejette une quantité retournée négative. |
| `test_other_movement_types_keep_manual_closure_quantities` | Les autres sens de mouvement conservent leur saisie antérieure. |
| `test_return_material_closure_only_confirms_validated_quantity` | La clôture de retour matériel conserve la quantité validée au Stock et ne crée pas de second transfert. |
| `test_requester_closure_can_create_the_return_picking` | Le demandeur peut fermer une sortie avec retour sans avoir les droits Stock nécessaires à la création du picking. |
| `test_sortie_only_return_is_deferred_to_closure` | Le wizard Stock ne peut pas enregistrer un retour pour les deux types de sortie seule. |
| `test_return_material_defaults_preserve_return_quantity` | Le wizard Stock préremplit la quantité de retour et conserve une ligne inchangée. |
| `test_return_material_quantity_change_requires_motif` | Une variation de quantité retournée sans motif est refusée. |
| `test_return_material_quantity_change_is_saved_and_traced` | Une variation motivée est enregistrée, notifiée dans le chatter et gardée séparée des autres quantités. |
| `test_return_material_rejects_negative_quantity` | Une quantité retournée négative est refusée côté serveur. |
| `test_rejection_mapping_is_explicit` | Vérifie seulement l'état brouillon par défaut et l'absence de motif initial. |
| `test_appro_distant_closure_defaults_to_all_installed` | Un approvisionnement distant clôturé sans modification préremplit `qty_installee = qty_sortie` et ne crée aucun retour. |
| `test_appro_distant_closure_return_is_an_internal_transfer` | Un retour positif crée un picking `internal` de `location_dest_id` vers `location_id`, terminé, avec la quantité retournée. |
| `test_appro_distant_closure_can_use_return_as_the_input` | Saisir le retour calcule la quantité installée complémentaire. |
| `test_appro_distant_closure_rejects_quantity_above_transfer` | Une quantité supérieure à `qty_sortie` est refusée et l'état reste `approuve`. |
| `test_appro_distant_stock_wizard_defers_return_to_closure` | Le wizard Stock met `qty_retour` à zéro pour un approvisionnement distant; le retour se décide à la clôture. |
| `test_depannage_stock_wizard_defers_return_to_closure` | Le wizard Stock met `qty_retour` à zéro pour un dépannage : l'entrée est reportée à la clôture. |
| `test_basculement_keeps_manual_quantities_at_stock` | Le basculement conserve la saisie manuelle au Stock (drapeau `is_sortie_only` faux). |
| `test_depannage_closure_defaults_to_all_installed` | Un dépannage clôturé sans modification préremplit `qty_installee = qty_sortie` et ne crée aucun retour. |
| `test_depannage_closure_return_creates_incoming_picking` | Un retour positif de dépannage crée un picking `incoming` vers `location_id`, terminé, avec la quantité retournée. |
| `test_depannage_closure_can_use_return_as_the_input` | Saisir le retour calcule la quantité installée complémentaire du dépannage. |
| `test_depannage_closure_rejects_quantity_above_output` | Une quantité supérieure à `qty_sortie` est refusée et l'état reste `approuve`. |
| `test_loopback_base_url_omits_broken_image_and_link` | Avec `web.base.url` sur `localhost`, le corps ne contient ni URL d'image ni lien `/web?db=`, affiche le nom de la société, et conserve le bouton sans adresse. |
| `test_lan_base_url_keeps_logo_and_button` | Une adresse du réseau interne (`192.168.1.50`) conserve l'URL du logo et le lien vers la demande. |
| `test_email_displays_readable_status_label` | La carte de référence affiche le libellé du statut (« Validation Chef ») et non le code technique (`valide_chef`). |
| `test_rejection_email_escapes_the_motif` | Un motif contenant `<script>` est rendu échappé (`&lt;script&gt;`) et aucune balise active n'est injectée. |
| `test_subject_contains_intervention_label` | Le sujet contient le numéro DSS et le libellé du type d'intervention. |

Les deux tests signalés avec « seulement » ont des assertions plus étroites que leur nom ne le suggère.

## 2 bis. Tests de sécurité (version 2.14)

Le fichier [`tests/test_dss_security.py`](../../tests/test_dss_security.py) vérifie les contrôles d'accès. Il crée quatre utilisateurs, chacun avec un rôle distinct, deux services indépendants, puis construit un environnement Odoo par utilisateur avec `api.Environment(cr, uid, context)` — indispensable puisque la suite de tests s'exécute en superutilisateur.

| Test | Contrôle vérifié |
|---|---|
| `test_outsider_has_no_access_to_requests` | Un utilisateur sans groupe DSS ne peut pas lire les demandes (ACL). |
| `test_requester_cannot_read_request_of_another_service` | Règle d'enregistrement : un demandeur ne voit que ses demandes. |
| `test_chef_sees_only_his_service` | Règle d'enregistrement : un Chef ne voit que les demandes de son service. |
| `test_magasin_sees_all_requests` | Le Magasin voit bien toutes les demandes. |
| `test_state_cannot_be_written_directly` | Un `write({'state': ...})` hors workflow lève `AccessError`. |
| `test_workflow_still_changes_state` | `_dss_set_state()` continue de faire avancer la demande. |
| `test_stock_validation_requires_magasin_group` | Un non-magasinier est refusé sur son rôle, avant le contrôle d'étape. |
| `test_magasinier_passes_the_role_check` | Le magasinier franchit le contrôle de rôle et bute sur le contrôle d'étape. |
| `test_quantity_wizard_requires_stock_stage` | L'ajustement des quantités est refusé hors de l'état `valide_magasin`. |
| `test_chef_cannot_validate_his_own_request` | Un Chef demandeur ne peut pas valider sa propre demande. |
| `test_validation_wizards_are_open_to_their_groups` | Les assistants de confirmation Chef et Stock sont accessibles à leur groupe. |

## 2 ter. Tests de fiabilité des quantités et de purge (version 2.15)

| Test | Contrôle vérifié |
|---|---|
| `test_negative_quantity_is_refused_on_create` | Une quantité négative est refusée dès la création de la ligne (contrainte `@api.constrains`). |
| `test_negative_quantity_is_refused_on_write` | Une quantité négative est refusée lors d'une modification, et l'écriture est annulée. |
| `test_zero_quantity_is_accepted_to_allow_empty_line` | Le zéro reste autorisé : on peut ajouter une ligne vide puis la remplir. |
| `test_submission_requires_positive_demanded_quantity` | Une ligne à quantité demandée nulle bloque la soumission. |
| `test_submission_requires_positive_return_for_return_material` | Un retour de matériel exige une quantité retournée strictement positive. |
| `test_submission_accepts_positive_quantities` | Une quantité positive passe le contrôle. |
| `test_cron_purges_old_sent_mails_and_keeps_log` | Le cron supprime un courriel de plus de 60 jours à l'état `sent`, mais conserve le journal. |
| `test_cron_keeps_recent_mails` | Un courriel récent n'est jamais purgé. |
| `test_cron_keeps_pending_mails_even_when_old` | Un courriel encore en file (`outgoing`) n'est pas purgé, même ancien. |

## 2 quater. Tests de garde-fou (versions 2.16 et 2.17)

[`tests/test_dss_no_parallel_circuit.py`](../../tests/test_dss_no_parallel_circuit.py) empêche la réintroduction du code retiré.

| Test | Contrôle vérifié |
|---|---|
| `test_stock_picking_has_no_dss_fields` | `stock.picking` ne porte plus `dss_number`, `dss_validation_state`, `dss_justification` ni `dss_movement_type` (2.16). |
| `test_product_template_has_no_standard_quantity` | `product.template` ne porte plus `dss_standard_qty` (2.16). |
| `test_stock_picking_keeps_eccart_method_removed` | La méthode `check_dss_ecart()` a disparu du modèle (2.16). |
| `test_approval_wizard_method_is_removed` | `action_open_wizard_approuver()` a disparu de `dss.request` (2.17). |
| `test_approval_wizard_model_is_still_absent` | Le modèle `dss.validation.approuver.wizard`, jamais écrit, n'est pas réapparu (2.17). |

## 3. Exécution

L'exécution doit se faire avec le lanceur et l'interpréteur de l'installation Odoo 10, sur une base de test. Exemple de commande à adapter à cette installation :

```bash
python odoo-bin -c odoo.conf -d BASE_DE_TEST -u dss_v2 --test-enable --stop-after-init
```

L'audit documentaire n'a pas exécuté Odoo ni cette commande; le résultat des tests n'est donc pas certifié ici.

La compilation Python et l'analyse des diagnostics peuvent être exécutées localement. Les tests Odoo doivent être lancés sur une base de test et avec l'interpréteur compatible avec l'instance Odoo 10; ne pas lancer le module sur une base de production.

## 3 bis. Incident Unicode du wizard de quantités

Un `UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3` a été observé dans `dss_qty_sortie_wizard.py`, dans `action_valider()`, lors de la construction d'un message contenant le nom d'un article ou d'un utilisateur. La cause était l'interpolation d'une valeur Unicode dans une chaîne `str` Python 2. La correction consiste à utiliser des chaînes Unicode `u"..."` pour les messages et les séparateurs construits par cette méthode. Le scénario à rejouer sur Odoo 10 doit inclure un article, un utilisateur et un motif comportant des accents.

## 4. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Couverture | Les tests portent sur les notifications, pas sur l'ensemble du workflow, des mouvements ou des PDF. |
| SMTP | Aucun e-mail réel n'est envoyé par ces tests. |
| Résultat | Toujours lire le résultat du test runner de l'environnement ciblé. |
| Source | [`tests/test_dss_notifications.py`](../../tests/test_dss_notifications.py), entrée dans [`__manifest__.py`](../../__manifest__.py). |