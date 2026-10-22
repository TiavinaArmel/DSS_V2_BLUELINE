# Courriels, chatter et SMTP

## 1. Architecture

Les messages métier du chatter sont créés par `message_post()` sur `dss.request`. Les courriels explicites utilisent le template `dss_v2.mail_template_dss_workflow`, puis créent des enregistrements `mail.mail` autonomes. La configuration du serveur SMTP est extérieure au module.

## 2. Événements et destinataires

| Événement | Destinataires du code | Motif rendu |
|---|---|---|
| `submission` | Groupe Chef actif | Non |
| `chef_validation` | Groupe Magasin actif et demandeur | Non |
| `chef_rejection` | Demandeur | Oui |
| `stock_rejection` | Demandeur et groupe Chef actif | Oui |
| `stock_approval` | Demandeur | Non |
| `return_to_requester` | Demandeur | Oui |
| `closure` | Demandeur et groupe Magasin actif | Non |

La méthode de résolution des utilisateurs préfère `partner_id.email`, puis `user.email`. Les adresses vides et doublons sont exclus. Le demandeur est identifié par `signataire_demandeur_id`, avec `create_uid` en repli.

## 3. Template et file d'envoi

Le template XML compose le sujet, l'action, l'état, le lien vers la demande et l'en-tête du courriel. Le motif n'apparaît que pour les clés de rejet et de renvoi. Le logo est affiché depuis la route Odoo `/web/binary/company_logo`; son URL est construite avec `web.base.url`, le nom de la base et l'identifiant de la société de l'utilisateur qui déclenche la notification. Si `web.base.url` n'est pas configuré, le template affiche le nom de l'entreprise à la place du logo.

Pour que les destinataires voient le logo, `web.base.url` doit contenir l'adresse du serveur joignable par eux, idéalement en HTTPS; une valeur `localhost` ne fonctionne que sur la machine locale. La route de l'image doit également être accessible depuis leur client de messagerie, qui peut par ailleurs bloquer les images distantes par défaut.

Le code fixe `model=False`, `res_id=False` et `auto_delete=False`, puis crée le mail sans appeler `send()`; il dépend donc de la file de courriels Odoo pour l'envoi réel.

Le modèle `dss.notification.log` garde la demande, la clé d'événement, le mail et les destinataires. Sa contrainte unique limite chaque paire demande/événement à une entrée. Une notification déjà journalisée ne sera pas recréée par un nouvel appel de même clé.

## 4. Configuration SMTP et diagnostic

Le module ne contient pas les identifiants SMTP. Le serveur sortant et la tâche planifiée qui traite la file sont à configurer et superviser dans l'instance Odoo. Les fichiers du module ne fixent pas l'intervalle du cron ni une adresse d'expéditeur valide.

| Symptôme | Vérifications à faire |
|---|---|
| Aucun `mail.mail` créé | Destinataires disponibles, template externe présent, erreurs dans le journal Odoo. |
| Mail en attente | État du `mail.mail`, tâche de file active, serveur SMTP sortant configuré. |
| Mail en échec | Raison d'échec du mail et journaux Odoo; la méthode DSS n'effectue pas de relance dédiée. |
| Mail non reçu | Vérifier la livraison côté serveur et boîte destinataire; la création du mail ne prouve pas sa réception. |

Ne jamais ajouter de mot de passe SMTP, de mot de passe de base ou de jeton dans cette documentation.

## 5. Fiche de mémorisation

| Repère | À retenir |
|---|---|
| Chatter | Trace métier visible sur la fiche DSS. |
| Email | Mail autonome en file, pas attaché au chatter DSS. |
| SMTP | Configuration d'instance, pas du code du module. |
| Sources | [`dss_notification.py`](../../models/dss_notification.py), [`dss_mail_templates.xml`](../../data/dss_mail_templates.xml), [`test_dss_notifications.py`](../../tests/test_dss_notifications.py). |