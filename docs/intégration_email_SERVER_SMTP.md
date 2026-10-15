# Notifications, Chatter et SMTP — DSS V2

**Date de consolidation :** 15 octobre 2026  
**Module :** `dss_v2`  
**Environnement :** Odoo 10 Community, instance locale Windows  
**Dépôt observé :** `custom-addons/dss_v2`, branche `main`

## 1. Objet et état du document

Ce document regroupe les deux rapports présents dans l'ancien fichier d'analyse et les constats établis pendant les échanges : architecture, workflow, Chatter, notifications par e-mail, destinataires, motif, file d'attente Odoo, SMTP, tests et limites.

Le premier rapport décrivait un état antérieur où aucun routage d'e-mail métier n'était encore implémenté. Un rapport final, puis les modifications effectuées dans la conversation, ont fait évoluer cet état. Les sections ci-dessous décrivent le code actuel observé et signalent les décisions ou tests qui restent à faire.

À la dernière vérification, le dépôt était sur `main`, avec des modifications locales non committées. Aucun changement n'a été fait dans le code natif d'Odoo. Les informations de connexion et mots de passe ne sont pas reproduits ici.

## 2. Fichiers et architecture

Le modèle principal `dss.request` hérite de `mail.thread`. Il fournit le Chatter, les abonnés et les champs `message_ids` et `message_follower_ids`. La vue du formulaire affiche le fil avec le widget `mail_thread`.

Les dépendances déclarées par le module sont `web`, `stock` et `mail`. Le manifeste charge le template d'e-mail `data/dss_mail_templates.xml` et déclare les tests de notification.

| Fichier | Responsabilité |
|---|---|
| `models/dss_request.py` | Modèle de la demande, états, signataires et champs métier |
| `models/dss_request_workflow.py` | Soumission, validations, rejet, renvoi et appels de notification |
| `models/dss_request_stock.py` | Création des pickings et mouvements de stock |
| `models/dss_request_bon_livraison.py` | Création et rattachement du PDF de bon de livraison |
| `models/dss_notification.py` | Résolution des destinataires, création des e-mails et journal anti-doublon |
| `models/dss_rejet_wizard.py` | Saisie du motif obligatoire avant rejet |
| `models/dss_validation_wizard.py` | Confirmation des validations Chef et Stock |
| `models/dss_qty_sortie_wizard.py` | Modification des quantités par le Magasin et trace Chatter |
| `models/dss_cloture_wizard.py` | Clôture, calcul des écarts, trace Chatter et notification |
| `models/stock_picking.py` | Workflow DSS distinct ajouté au modèle `stock.picking` |
| `data/dss_mail_templates.xml` | Contenu du modèle d'e-mail DSS |
| `tests/test_dss_notifications.py` | Tests Odoo du routage et de la mise en file des e-mails |

Le fichier `docs/Filtres_et_Regroupements.md` a été conservé. Aucun secret SMTP ne doit être ajouté au code ou à la documentation.

## 3. Workflow actuel de `dss.request`

Les états métier définis sont :

```text
brouillon -> valide_chef -> valide_magasin -> approuve -> cloture
                  |                |
                  +---- rejete <---+
                         |
                         +---- renvoi par un Chef -> brouillon
```

### Soumission

`action_soumettre()` vérifie le BCI, le client, le lieu et la date d'intervention, le type d'intervention, l'emplacement source, l'emplacement de destination si le type est `appro_distant`, ainsi que la présence d'au moins une ligne.

Elle enregistre le demandeur dans `signataire_demandeur_id`, date la soumission et passe la demande de `brouillon` à `valide_chef`. Elle poste ensuite dans le Chatter un message de soumission avec le récapitulatif des articles et déclenche l'e-mail destiné au groupe Chef.

### Validation Chef

`action_valider_chef()` exige l'état `valide_chef`, passe à `valide_magasin`, enregistre le signataire et la date de validation Chef, puis poste le message Chatter et prépare un e-mail pour le groupe Magasin et le demandeur.

### Validation Stock et approbation

`action_valider_magasin()` exige l'état `valide_magasin`, enregistre le signataire et la date Stock, puis génère le ou les mouvements de stock selon `sens_mouvement` :

| Type d'intervention | Sens de mouvement |
|---|---|
| Nouvelle installation client | Sortie |
| Basculement client | Sortie + Entrée |
| Dépannage | Sortie + Entrée |
| Approvisionnement de stock distant | Transfert |
| Installation interne | Sortie |
| Retour de matériel | Entrée |

Les fonctions de stock créent les pickings et leurs mouvements, vérifient la disponibilité pour une sortie ou un transfert, puis confirment et terminent le picking. Si une génération échoue, la suite de la validation n'est pas exécutée.

Après les mouvements, l'action poste une trace de validation Stock, passe à `approuve`, génère le PDF du bon de livraison, poste une seconde trace Chatter d'approbation définitive, puis prépare l'e-mail d'approbation au demandeur.

L'ancienne action `action_approuver()` et son wizard ont été retirés du workflow `dss.request` : ils n'étaient reliés à aucun bouton de la vue et permettaient une approbation sans générer les mouvements ni le PDF. Une méthode de même nom existe toujours sur `stock.picking`, mais elle appartient à un workflow différent.

### Rejet

Le bouton de rejet est proposé au Chef quand la demande est à `valide_chef` et au Magasin quand elle est à `valide_magasin`. Le wizard de rejet impose un motif, le copie dans `motif_rejet` et appelle `action_rejeter()`.

L'action mémorise l'état précédent, passe la demande à `rejete`, ajoute au Chatter un message avec le motif, puis choisit la notification appropriée : rejet Chef ou rejet Stock. L'action elle-même ne vérifie toujours pas l'état de départ; les restrictions de boutons ne sont donc pas une protection serveur suffisante contre un appel direct.

### Renvoi au demandeur

Le bouton de renvoi est visible uniquement au groupe `dss_v2.group_dss_chef` et seulement sur une demande `rejete`. La méthode contrôle aussi ces deux conditions côté serveur : elle vérifie le groupe avec `has_group()` et l'état avec une `ValidationError`.

Au renvoi, la demande revient à `brouillon`. Le message Chatter indique le nom du Chef qui agit et celui du demandeur, identifié par `signataire_demandeur_id` ou, à défaut, `create_uid`. La notification par e-mail est adressée au demandeur et reprend le motif du rejet conservé dans `motif_rejet`.

### Clôture

Le wizard de clôture reporte les quantités réellement installées et retournées sur les lignes DSS. Il compare `qty_installee` et `qty_sortie`, met `has_ecart` à jour, passe la demande à `cloture`, poste un récapitulatif et les écarts éventuels dans le Chatter, puis prépare un e-mail pour le demandeur et le groupe Magasin.

## 4. Messages du Chatter

Le Chatter conserve des traces métier liées à la demande. Il ne constitue pas une preuve d'envoi ou de réception d'un e-mail.

| Action | Trace Chatter |
|---|---|
| Soumission | Auteur, action et détail des articles/quantités |
| Validation Chef | Auteur et validation en tant que Responsable Chef |
| Validation Stock | Auteur et validation en tant que Responsable Stock |
| Approbation Stock | Auteur et approbation définitive |
| Rejet | Auteur; motif ajouté s'il est fourni |
| Renvoi | Auteur du renvoi et nom du demandeur |
| Modification de quantités | Détail des quantités modifiées, seulement si elles ont changé |
| Clôture | Quantités installées/retournées et écarts calculés |
| Bon de livraison | Message avec la pièce jointe lors de sa première création |

Ces traces sont produites par `message_post()`. Les abonnés à une demande peuvent également recevoir les notifications natives de `mail.thread` selon leurs préférences Odoo. Ce mécanisme est distinct du routage explicite des e-mails DSS décrit ci-dessous.

Les e-mails métier sont volontairement créés avec `model=False` et `res_id=False` dans `mail.mail`. Ils ne sont donc pas attachés au fil Chatter de la demande. Le modèle de journal `dss.notification.log`, lui, conserve le lien vers la demande pour le suivi technique.

## 5. Routage des e-mails DSS

### Identification des destinataires

Pour les groupes, le code parcourt les utilisateurs actifs du groupe, récupère d'abord `user.partner_id.email`, puis `user.email` en repli. Les adresses vides et les doublons sont écartés.

Pour le demandeur, le code prend `signataire_demandeur_id`, puis `create_uid` si le signataire n'est pas renseigné. Si aucune adresse n'est disponible, aucune notification n'est mise en file.

La méthode Python `strip()` retire les espaces au début et à la fin d'une adresse. Elle ne supprime pas les espaces situés au milieu.

### Matrice actuelle

| Événement (`event_key`) | Destinataires | Motif dans l'e-mail |
|---|---|---|
| `submission` | Utilisateurs actifs du groupe DSS / Chef | Non |
| `chef_validation` | Utilisateurs actifs du groupe DSS / Magasin et demandeur | Non |
| `chef_rejection` | Demandeur | Oui |
| `stock_rejection` | Demandeur et utilisateurs actifs du groupe DSS / Chef | Oui |
| `stock_approval` | Demandeur | Non |
| `return_to_requester` | Demandeur | Oui, reprend `motif_rejet` |
| `closure` | Demandeur et utilisateurs actifs du groupe DSS / Magasin | Non |

Le renvoi au demandeur était initialement routé vers le groupe Chef; cette règle a été corrigée. Le Chef est l'auteur du renvoi et non le destinataire du courriel.

### Template et affichage du motif

Le modèle XML `dss_v2.mail_template_dss_workflow` produit le sujet et le corps HTML. Le message contient le numéro DSS, l'action, le statut, le lien vers la demande et une mention automatique.

Le code passe maintenant la clé `dss_event_key` dans le contexte du template. La ligne « Motif » est affichée uniquement pour `chef_rejection`, `stock_rejection` et `return_to_requester`. Pour les autres événements, cette ligne est absente. Si le motif est vide lors d'un événement concerné, le template affiche « Non renseigne ».

L'adresse d'expédition du template est fondée sur l'adresse e-mail de l'utilisateur Odoo courant. L'adresse de destination est définie explicitement par le code DSS.

### Prévention des doublons et création du mail

Le modèle `dss.notification.log` conserve la demande, la clé d'événement, l'enregistrement `mail.mail` et les adresses utilisées. Une contrainte SQL unique sur `(request_id, event_key)` empêche la création d'un second journal pour le même événement sur une même demande.

`_dss_notify_once()` suit ces étapes :

1. vérifie qu'une seule demande est traitée ;
2. nettoie et déduplique les adresses ;
3. abandonne et journalise un avertissement s'il n'y a aucun destinataire ;
4. cherche si l'événement a déjà un journal ;
5. récupère le template et prépare son contexte ;
6. rend le sujet et le corps du mail ;
7. renseigne les destinataires et détache le mail du modèle `dss.request` ;
8. crée le `mail.mail` avec `auto_delete=False` ;
9. crée le journal relié à la demande.

La création est faite dans un savepoint et les exceptions sont consignées dans le journal Odoo sans interrompre la transition métier. La notification n'est pas envoyée directement par cette méthode.

La déduplication est par clé et par demande, sans notion de cycle. Si une même demande est renvoyée, soumise à nouveau puis rejetée une seconde fois, un événement déjà journalisé sous la même clé ne produira pas un nouvel e-mail. Si le besoin métier exige une notification à chaque cycle, il faudra faire évoluer la clé ou le modèle de journal.

Le module ne possède pas de mécanisme propre de relance d'un e-mail en erreur. Si un `mail.mail` passe à l'état `exception`, l'administrateur doit traiter l'erreur et gérer la nouvelle tentative avec les outils Odoo; rappeler la même notification DSS ne recrée pas automatiquement un mail tant que le journal de cet événement existe.

## 6. File d'attente, SMTP et diagnostic

Le code DSS utilise `mail.mail.create()` sans appeler `send()` ni `send_mail(..., force_send=True)`. Un e-mail créé apparaît d'abord avec l'état `outgoing`. Il est ensuite pris en charge par la tâche planifiée Odoo **Email Queue Manager**, qui appelle `mail.mail.process_email_queue()` et utilise le serveur SMTP sortant configuré dans Odoo.

Dans les données du module natif Odoo 10, l'intervalle par défaut de cette tâche est d'une heure. Cela peut expliquer une attente avant envoi si la tâche reste à cet intervalle. Une action manuelle depuis le menu des courriels peut envoyer un élément immédiatement, mais n'est pas nécessaire lorsque la tâche planifiée fonctionne.

Pour diminuer le délai dans l'interface Odoo 10 :

1. activer le mode développeur si le menu Technique n'est pas visible ;
2. ouvrir **Paramètres → Technique → Automatisation → Actions planifiées** ;
3. rechercher **Email Queue Manager** et vérifier qu'il est actif ;
4. réduire **Exécuter toutes les** de `1 heure` à une valeur adaptée, par exemple `5 minutes` ;
5. enregistrer et vérifier la prochaine exécution.

Un intervalle de cinq minutes signifie qu'un e-mail en file peut attendre jusqu'à environ cinq minutes avant son traitement. L'action **Exécuter manuellement**, si elle est proposée, permet de déclencher un essai immédiat.

Le serveur SMTP sortant se configure dans les paramètres techniques Odoo, séparément de ce module. Le fichier `odoo.conf` local ne contient pas de paramètres SMTP; aucun mot de passe SMTP/Gmail n'est stocké dans le code.

Pour une mise en production, vérifier aussi l'adresse d'expédition, les restrictions éventuelles du fournisseur, les limites de débit et la configuration de domaine SPF, DKIM et DMARC. Ces réglages relèvent du serveur de messagerie et du DNS, pas du template DSS.

### Traces runtime observées

Le journal local `odoo.log` contient des preuves que la file a fonctionné le 15 octobre 2026 :

- vers `12:22:40`, un appel manuel à `mail.mail(16).send()` a été suivi d'un succès vers `12:22:43` ;
- à `13:03:42`, le job `Email Queue Manager` a démarré ; le mail `ID 17` a été marqué comme envoyé avec succès vers `13:03:46`, puis le job s'est terminé.

Ces traces montrent une prise en charge par le serveur d'envoi configuré et une exécution réussie côté Odoo. Elles ne prouvent pas à elles seules la réception finale dans la boîte du destinataire. L'état `exception` indique un échec de livraison; le champ de raison d'échec et les logs Odoo sont alors à consulter.

## 7. Rôles et limites de sécurité

Les groupes DSS définis dans `security/dss_security.xml` sont :

| XML ID | Rôle fonctionnel |
|---|---|
| `dss_v2.group_dss_demandeur` | Demandeur |
| `dss_v2.group_dss_chef` | Chef |
| `dss_v2.group_dss_magasin` | Magasin |
| `dss_v2.group_dss_securite` | Sécurité |

Les notifications de groupe visent tous les utilisateurs actifs du groupe et non un responsable d'entrepôt particulier. Aucun champ de `dss.request` ne désigne un Chef unique associé à l'emplacement.

Le groupe Sécurité existe, mais le workflow principal `dss.request` n'a ni état, ni bouton, ni signataire, ni transition de validation Sécurité. Aucune notification Sécurité n'est donc envoyée par ce workflow. Une règle future nécessiterait une décision métier explicite (par exemple selon l'intervention ou un écart).

Le rejet n'a pas encore de garde-fou d'état dans sa méthode serveur. Les boutons de vue et le wizard cadrent le parcours courant, mais la méthode `action_rejeter()` reste appelable depuis un autre état par un appel direct si les droits le permettent.

Le renvoi est maintenant vérifié dans l'interface et côté serveur : seuls les utilisateurs du groupe Chef peuvent le déclencher, et seulement pour une demande rejetée.

## 8. Workflow distinct sur `stock.picking`

`models/stock_picking.py` ajoute des champs DSS et un circuit de validation distinct au modèle standard `stock.picking`. Ce parcours n'est pas le workflow principal des boutons `dss.request` et n'est pas raccordé aux notifications DSS décrites ici.

Des incohérences ont été relevées dans ce circuit parallèle :

- la sélection `dss_validation_state` ne déclare pas la valeur `soumis`, alors que `action_soumettre_dss()` l'affecte ;
- la valeur `valide_securite` porte actuellement le libellé « Validation Demandeur » ;
- `action_approuver()` existe toujours sur `stock.picking` et exige l'état `valide_securite` ;
- le contrôle d'écart vérifie une justification avant le traitement du transfert immédiat.

Cette méthode `stock.picking.action_approuver()` est différente de l'ancienne action `dss.request.action_approuver()` retirée. Le circuit ne doit pas être confondu avec l'approbation effectuée par `action_valider_magasin()` sur la demande DSS.

## 9. Tests et vérifications

Le fichier `tests/test_dss_notifications.py` contient des tests Odoo `TransactionCase`. Les adresses `example.invalid` sont fictives et les tests ne contactent pas de serveur SMTP.

Les tests couvrent notamment :

- résolution des adresses des groupes et absence de doublons ;
- absence de mail/journal si aucun destinataire n'est fourni ;
- création d'un mail en état `outgoing` sans rattachement au chatter DSS ;
- conservation du lien entre journal technique et demande ;
- prévention du double traitement d'un même événement ;
- contrainte SQL d'unicité ;
- présence du motif de rejet dans le corps rendu ;
- absence de la ligne Motif pour une soumission ;
- destinataire demandeur et motif dans un e-mail de renvoi ;
- absence de notification Sécurité sans transition métier dédiée.

Deux noms de tests existants suggèrent une couverture plus large que leurs assertions : `test_approval_uses_one_event_for_both_entry_points` vérifie seulement l'absence initiale d'un journal d'approbation; `test_rejection_mapping_is_explicit` vérifie l'état et le motif par défaut d'une nouvelle demande. Ces cas pourraient être renommés ou renforcés.

Les diagnostics de l'éditeur n'ont signalé aucune erreur dans les fichiers récemment modifiés. Les tests Odoo `TransactionCase`, la mise à jour du module et un test de livraison SMTP n'ont pas été exécutés dans cette consolidation. Une tentative de compilation Python via `python` n'a pas abouti parce que cet exécutable n'était pas disponible dans le PATH du terminal.

## 10. Historique des décisions et points à suivre

Les constats et décisions du travail sont les suivants :

- le workflow de référence pour les boutons étudiés est `dss.request` ; le workflow `stock.picking` reste séparé ;
- les notifications utilisent les groupes Chef et Magasin existants, avec tous leurs utilisateurs actifs ;
- le demandeur est identifié par le signataire de soumission, avec repli sur le créateur ;
- le Chatter conserve ses notes métier, tandis que les e-mails DSS sont autonomes et hors du fil de la demande ;
- le motif apparaît uniquement sur les deux types de rejet et le renvoi au demandeur ;
- l'e-mail de renvoi va au demandeur et non au groupe Chef ; le Chef est l'auteur autorisé de cette action ;
- l'approbation principale se fait par `action_valider_magasin()`, qui crée les mouvements et le bon de livraison ; l'ancienne approbation alternative de `dss.request` a été retirée ;
- les réponses entrantes aux e-mails et leur rattachement au Chatter ne sont pas implémentés ;
- le cron de mail est configuré par défaut toutes les heures dans les données Odoo 10; le réduire est une configuration opérationnelle, non une modification déjà appliquée à la base ;
- le traitement de plusieurs cycles de rejet/soumission pour une même demande peut être limité par la déduplication permanente `(request_id, event_key)` ;
- les mouvements « Sortie + Entrée » créent deux pickings successifs, mais `picking_id` ne conserve que le dernier identifiant directement sur la demande ;
- le rejet ne vérifie pas encore l'état côté serveur ;
- aucune règle métier ne définit quand la Sécurité doit être notifiée.

## 11. État Git au moment de la consolidation

Le dépôt du module se trouve dans `custom-addons/dss_v2`, et non à la racine `C:\ODOO_10_DEV`. L'ancien rapport mentionnait `feat/notifications-email` et faisait référence à `feat/dss-chatter-modern-ui`; la dernière vérification du dépôt indiquait plutôt la branche `main`, à jour avec `origin/main`. Le worktree comportait des modifications locales non committées, notamment dans le workflow, les notifications, le manifeste, les vues, les tests et des documents existants.

Aucun commit n'a été créé pendant ce travail. Les modifications sans rapport avec cette documentation doivent être conservées. L'ancien document de rapport est remplacé par ce fichier consolidé; `docs/Filtres_et_Regroupements.md` n'est pas supprimé.

## 12. Références du module

- Modèle et états : `../models/dss_request.py`
- Transitions et messages Chatter : `../models/dss_request_workflow.py`
- Création des mouvements : `../models/dss_request_stock.py`
- Bon de livraison : `../models/dss_request_bon_livraison.py`
- Notifications et journal : `../models/dss_notification.py`
- Modèle d'e-mail : `../data/dss_mail_templates.xml`
- Vue de la demande et visibilité des boutons : `../views/dss_request_views.xml`
- Sécurité et groupes : `../security/dss_security.xml`
- Tests de notifications : `../tests/test_dss_notifications.py`
- Configuration de l'instance locale : `../../odoo.conf`
- Traces du gestionnaire de file : `../../odoo.log`
