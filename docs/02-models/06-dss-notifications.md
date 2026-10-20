# Notifications du workflow DSS

## 1. Rôle

`models/dss_notification.py` ajoute un journal persistant `dss.notification.log` et une extension de `dss.request` qui résout les destinataires, rend le template et crée un `mail.mail` en file. La création ne déclenche pas directement l'envoi SMTP.

## 2. Modèles et champs

| Élément | Rôle |
|---|---|
| `dss.notification.log.request_id` | Demande concernée; suppression en cascade. |
| `event_key` | Identifiant stable de l'événement notifié. |
| `mail_id` | Courriel Odoo associé au journal. |
| `recipient_emails` | Destinataires consignés sous forme de texte. |
| Contrainte SQL | Unicité de `(request_id, event_key)`. |

Le template est `dss_v2.mail_template_dss_workflow`. La matrice des événements, les destinataires et la file sont documentés dans [Courriels, chatter et SMTP](../06-integrations/01-email-smtp.md).

## 3. Rendu et création

Le code transmet au template le libellé d'action, la clé d'événement, le motif, l'état et l'URL de la demande. Il crée `mail.mail` avec `model=False`, `res_id=False` et `auto_delete=False`; le mail est indépendant du chatter, tandis que le journal conserve le lien métier.

## 4. Gestion des erreurs

Sans destinataire valide ou sans template, la méthode n'enfile pas de courriel. Les erreurs de création sont journalisées et interceptées dans `_dss_notify_once()` afin de ne pas interrompre la transition métier. Le succès de création d'un `mail.mail` ne prouve pas la livraison finale.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Envoi | Le module crée un mail en file; le traitement réel dépend de la file Odoo et du SMTP configuré. |
| Déduplication | Une notification par demande et clé d'événement. |
| Référence détaillée | Consulter la fiche [courriels et SMTP](../06-integrations/01-email-smtp.md). |
| Source | [`models/dss_notification.py`](../../models/dss_notification.py), [`data/dss_mail_templates.xml`](../../data/dss_mail_templates.xml). |