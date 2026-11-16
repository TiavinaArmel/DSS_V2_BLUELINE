# Courriels, chatter et SMTP

## 1. Architecture

Les messages métier du chatter sont créés par `message_post()` sur `dss.request`. Les courriels explicites utilisent le template `dss_v2.mail_template_dss_workflow`, puis créent des enregistrements `mail.mail` autonomes. La configuration du serveur SMTP est extérieure au module.

Les messages du chatter sont des **notes internes** : chaque appel passe `subtype="mail.mt_note"`. Odoo 10 applique déjà cette valeur par défaut; elle est déclarée explicitement pour que le rendu ne dépende pas d'un changement du cœur Odoo.

Chaque corps est construit en HTML. Le nom de l'utilisateur, le nom des articles et les motifs saisis par les utilisateurs passent par `html_escape()` avant l'injection; les retours à la ligne d'un motif deviennent des `<br/>`. Les libellés de quantités sont accentués et identiques dans tout le module : `Qté demandée`, `Qté sortie`, `Qté installée`, `Qté retour`.

| Situation | Trace produite dans le chatter |
|---|---|
| Soumission | `<b>{utilisateur}</b> a soumis la demande.` puis une ligne par article |
| Validation Chef | `<b>{utilisateur}</b> a validé la demande en tant que <b>Responsable Chef</b>.` |
| Validation Stock | `<b>{utilisateur}</b> a validé la demande en tant que <b>Responsable Stock</b> et l'a approuvée définitivement.` (un seul message) |
| Rejet | `<b>{utilisateur}</b> a rejeté la demande.` et, si un motif existe, `<b>Motif :</b> {motif}` échappé |
| Renvoi au demandeur | `<b>{utilisateur}</b> a renvoyé la demande au demandeur <b>{demandeur}</b>.` |
| Modification des quantités | `Le Responsable Stock {utilisateur} a modifié les quantités.` puis des puces par article modifié |
| Clôture | `<b>{utilisateur}</b> a clôturé la demande.` ou `<b>{utilisateur}</b> a effectué une <b>clôture exceptionnelle</b>.` avec son motif |
| Bon de livraison | `Bon de livraison généré automatiquement.` avec la pièce jointe PDF |
| Changement administratif | `L'administrateur a modifié le service demandeur : …` ou `L'administrateur a modifié le demandeur : …` |

## 2. Événements et destinataires

| Événement | Destinataires du code | Motif rendu |
|---|---|---|
| `submission` | Chef DSS assigné au service | Non |
| `chef_validation` | Groupe Magasin actif et demandeur | Non |
| `chef_rejection` | Demandeur | Oui |
| `stock_rejection` | Demandeur et groupe Chef actif | Oui |
| `stock_approval` | Demandeur et groupe Chef actif | Oui, si une ligne possède `motif_ecart`; rendu dans une liste HTML `<ul><li>` |
| `return_to_requester` | Demandeur | Oui |
| `closure` | Groupe Chef, groupe Magasin actif et demandeur | Le contexte peut préciser une clôture exceptionnelle, son acteur et son motif; les retours à l'emplacement d'origine sont listés par article |

La méthode de résolution des utilisateurs préfère `partner_id.email`, puis `user.email`. Les adresses vides et doublons sont exclues. Le Chef est recherché via `service_demandeur_id.dss_chef_id` lorsqu'un événement le cible directement. Le destinataire demandeur est le propriétaire `demandeur_id`; `signataire_demandeur_id` identifie l'acteur qui a effectivement soumis la DSS.

## 3. Template et file d'envoi

Le template XML affiche le demandeur (`demandeur_id`), le service (`service_demandeur_id`) et le **libellé** du statut (« Validation Chef », « Clôture »…) plutôt que son code technique. L'introduction est écrite du point de vue du **destinataire réel** de l'événement :

| Événement | Destinataire principal | Formulation de l'introduction |
|---|---|---|
| `submission` | Chef du service | « Vous avez reçu une demande de sortie de stock de la part de **X**, du service **Y**. Elle attend votre validation en tant que Chef de service. » |
| `chef_validation` | Magasin et demandeur | « La demande de **X**, du service **Y**, a été validée par le Chef de service. Elle attend maintenant la validation du magasin. » |
| `chef_rejection` | Demandeur | « Votre demande a été rejetée par le Chef du service **Y**. Le motif figure ci-dessous. » |
| `return_to_requester` | Demandeur | « Votre demande vous a été renvoyée pour correction… » |
| `stock_approval` | Demandeur et Chef | « La demande de **X** a été validée par le magasin. Elle peut maintenant être clôturée. » |
| `stock_rejection` | Demandeur et Chef | « La demande a été rejetée par le magasin. Motif : … » |
| `closure` | Chef, Magasin et demandeur | « La demande de **X** a été officiellement clôturée. » ou clôture exceptionnelle |

Le sujet rappelle le type d'intervention (`DSS <numéro> - <action> - <type>`), et l'adresse de réponse (`reply_to`) reprend l'e-mail de la société.

L'approbation Stock invite le demandeur à consulter et clôturer sa demande, et liste en puces les lignes modifiées avec produit, quantités demandée/sortie et motif. Pour les interventions à clôture calculée, l'e-mail de clôture énumère chaque article retourné, la quantité remise en stock et l'emplacement source d'origine. Une clôture exceptionnelle affiche également son acteur et son motif. Les motifs de rejet et de renvoi sont **échappés** avant l'injection HTML; ceux des modifications de quantités le sont dans `_dss_quantity_change_motifs()`. Le lien de la demande inclut le nom de la base afin que le navigateur ouvre le bon registre Odoo; le destinataire doit s'authentifier et disposer des droits nécessaires.

Le logo et le bouton reposent sur `web.base.url`, lu par `_dss_base_url()`. Cette méthode refuse une adresse de bouclage (`localhost`, `127.0.0.1`, `::1`, `0.0.0.0`) : dans ce cas elle retourne une chaîne vide et le template affiche le nom de la société à la place du logo, évitant une image cassée chez le destinataire. Le bouton « Consulter la demande » reste présent dans le modèle quel que soit le cas. Une adresse privée du réseau interne (`192.168.x`, `10.x`, `172.16.x`) reste acceptée, car elle est joignable depuis les postes internes.

Le nom d'hôte est extrait par `_dss_url_hostname()`, un découpage manuel de l'URL. Ce choix évite l'import conditionnel de `urlparse` (Python 2) vers `urllib.parse` (Python 3), qui produit un faux positif `reportMissingImports` dans les analyseurs statiques configurés pour Python 3, alors que l'instance Odoo 10 s'exécute en Python 2.

Pour que les destinataires voient réellement le logo, `web.base.url` doit donc contenir l'adresse du serveur sur le réseau, par exemple `http://192.168.1.50:8069`. Deux limites subsistent indépendamment du module : le client de messagerie peut bloquer les images distantes par défaut (Gmail, Outlook) jusqu'à un clic « Afficher les images », et une adresse uniquement locale n'est jamais joignable depuis l'extérieur du réseau.

Le code fixe `model=False`, `res_id=False` et `auto_delete=False`, puis crée le mail sans appeler `send()`; il dépend donc de la file de courriels Odoo pour l'envoi réel.

Le modèle `dss.notification.log` garde la demande, la clé d'événement, le mail et les destinataires. Sa contrainte unique limite chaque paire demande/événement à une entrée. Une notification déjà journalisée ne sera pas recréée par un nouvel appel de même clé.

Pour `stock_approval`, les motifs de modification sont regroupés par article dans une liste HTML non ordonnée. Le bloc n'utilise pas `<br/>`, afin d'éviter l'affichage de balises dans le courriel.

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
| Chatter | Trace métier visible sur la fiche DSS, toujours postée en note interne (`mail.mt_note`) et échappée en HTML. |
| Email | Mail autonome en file, pas attaché au chatter DSS. |
| SMTP | Configuration d'instance, pas du code du module. |
| Sources | [`dss_notification.py`](../../models/dss_notification.py), [`dss_mail_templates.xml`](../../data/dss_mail_templates.xml), [`test_dss_notifications.py`](../../tests/test_dss_notifications.py). |