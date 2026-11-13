# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, models, fields, api
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import html_escape
from odoo.tools.float_utils import float_compare

"""
Ce fichier définit le wizard de clôture d'une DSS.

RÔLE :
    Permettre au Chef (ou au rôle autorisé) de clôturer une DSS
    en saisissant les quantités RÉELLEMENT installées et retournées,
    puis de détecter les écarts entre :
        - la quantité SORTIE du stock (qty_sortie),
        - la quantité INSTALLÉE chez le client (qty_installee).

POURQUOI :
    Parce qu'après une intervention, il peut y avoir un écart :
        - matériel sorti mais non installé,
        - matériel installé mais non prévu,
        - matériel retourné au stock.
    Ces écarts doivent être TRACÉS et VISIBLES.

POINT CLÉ :
    C'est CE fichier qui remplit enfin le champ `has_ecart` du modèle
    dss.request — champ qui était déclaré mais jamais utilisé au Jour 2.
"""


class DssClotureWizard(models.TransientModel):
    # Wizard de clôture de la DSS.
    # Popup qui permet de saisir les quantités installées / retournées,
    # puis de passer la DSS à l'état 'cloture'.
    _name = 'dss.cloture.wizard'
    _description = 'Assistant de cloture de la demande DSS'

    # DSS concernée (pré-remplie par le contexte, non modifiable).
    request_id = fields.Many2one(
        'dss.request', string='Demande DSS', required=True, readonly=True)

    is_exception = fields.Boolean(
        string='Clôture exceptionnelle',
        default=False,
        readonly=True,
    )
    motif_exception = fields.Text(
        string='Motif de la clôture exceptionnelle')

    # Lignes du wizard : une COPIE des lignes de la DSS.
    # One2many vers dss.cloture.wizard.line via wizard_id.
    line_ids = fields.One2many(
        'dss.cloture.wizard.line', 'wizard_id', string='Articles')
    is_sortie_only = fields.Boolean(
        string='Intervention avec mouvement sortie uniquement',
        compute='_compute_is_sortie_only',
    )

    @api.depends('request_id.sens_mouvement')
    def _compute_is_sortie_only(self):
        for wizard in self:
            wizard.is_sortie_only = (
                wizard.request_id.sens_mouvement == 'Sortie'
            )

    @api.model
    def default_get(self, fields_list):
        # Méthode appelée automatiquement par Odoo à l'ouverture du wizard.
        # Pré-remplit les champs avec une COPIE des lignes de la DSS.
        res = super(DssClotureWizard, self).default_get(fields_list)

        # Récupération de l'id de la DSS depuis le contexte :
        #   - default_request_id : passé par le bouton dans la vue
        #   - active_id          : enregistrement courant sélectionné
        request_id = (
            self.env.context.get('default_request_id')
            or self.env.context.get('active_id')
        )

        if request_id:
            request = self.env['dss.request'].browse(request_id)
            lines = []
            for line in request.line_ids:
                # (0, 0, {...}) = créer une nouvelle ligne One2many.
                # On copie les valeurs utiles de la vraie ligne DSS
                # dans le wizard.
                lines.append((0, 0, {
                    'request_line_id': line.id,
                    'product_id': line.product_id.id,
                    'qty_sortie': line.qty_sortie,
                    'is_sortie_only': line.is_sortie_only,
                    'qty_installee': (
                        line.qty_sortie if line.is_sortie_only
                        else line.qty_installee
                    ),
                    'qty_retour': (
                        0.0 if line.is_sortie_only else line.qty_retour
                    ),
                    'mode_saisie': 'installee',
                }))
            res['request_id'] = request_id
            res['line_ids'] = lines
        return res

    @api.multi
    def action_confirmer(self):
        # Méthode appelée au clic sur "Confirmer".
        # Elle :
        #   1. écrit les nouvelles quantités dans les VRAIES lignes DSS,
        #   2. détecte les écarts entre qty_sortie et qty_installee,
        #   3. remplit le champ has_ecart sur dss.request,
        #   4. passe l'état à 'cloture',
        #   5. poste un message récapitulatif dans le chatter,
        #   6. ferme la popup.
        self.ensure_one()

        request = self.request_id
        demandeur = (
            request.demandeur_id
            or request.signataire_demandeur_id
            or request.create_uid
        )
        is_requester = self.env.user == demandeur
        is_chef_exception = (
            self.is_exception
            and self.env.user.has_group("dss_v2.group_dss_chef")
        )
        if request.state != 'approuve':
            raise ValidationError(
                "Seule une demande approuvée peut être clôturée."
            )
        if self.is_exception and not is_chef_exception:
            raise AccessError(
                "Seul un utilisateur du groupe DSS / Chef peut effectuer une clôture exceptionnelle."
            )
        if (
            not self.is_exception
            and self.env.uid != SUPERUSER_ID
            and not is_requester
        ):
            raise AccessError(
                "Seul le demandeur d'origine peut clôturer cette DSS."
            )
        if self.is_exception and not (self.motif_exception or "").strip():
            raise ValidationError(
                "Le motif de la clôture exceptionnelle est obligatoire."
            )

        ecarts = []   # Liste des écarts détectés
        recap = []    # Liste du récapitulatif des quantités
        retours_stock = []
        is_sortie_only = request.sens_mouvement == 'Sortie'

        for line in self.line_ids:
            qty_installee = line.qty_installee
            qty_retour = line.qty_retour
            qty_sortie = line.request_line_id.qty_sortie
            if is_sortie_only:
                qty_saisie = (
                    qty_installee
                    if line.mode_saisie == 'installee'
                    else qty_retour
                )
                if line.mode_saisie not in ('installee', 'retour'):
                    raise ValidationError(
                        "Choisissez la quantité à saisir pour l'article %s."
                        % line.product_id.name
                    )
                if (
                    float_compare(qty_saisie, 0.0, precision_digits=2) < 0
                    or float_compare(
                        qty_saisie,
                        qty_sortie,
                        precision_digits=2,
                    ) > 0
                ):
                    raise ValidationError(
                        "La quantité saisie pour l'article %s doit être comprise "
                        "entre 0 et la quantité sortie (%s)."
                        % (line.product_id.name, qty_sortie)
                    )

                if float_compare(
                    qty_saisie, 0.0, precision_digits=2
                ) == 0:
                    qty_saisie = 0.0
                elif float_compare(
                    qty_saisie,
                    qty_sortie,
                    precision_digits=2,
                ) == 0:
                    qty_saisie = line.qty_sortie

                if line.mode_saisie == 'installee':
                    qty_installee = qty_saisie
                    qty_retour = qty_sortie - qty_installee
                else:
                    qty_retour = qty_saisie
                    qty_installee = qty_sortie - qty_retour

            # Écrit les nouvelles quantités dans la VRAIE ligne DSS.
            # Comme pour le wizard de quantité, le wizard travaille
            # sur une COPIE, puis écrit dans la vraie ligne à la validation.
            line.request_line_id.write({
                'qty_installee': qty_installee,
                'qty_retour': qty_retour,
            })

            # Ajoute une ligne au récapitulatif du message.
            recap.append(
                    u'\u2022 %s : Qte Installee %s, Qte Retour %s' % (
                    html_escape(line.product_id.name or ''),
                    qty_installee,
                    qty_retour)
            )
            if is_sortie_only and qty_retour > 0:
                emplacement_origine = request.location_id.name or ''
                retours_stock.append({
                    'product': html_escape(line.product_id.name or ''),
                    'quantity': qty_retour,
                    'location': html_escape(emplacement_origine),
                })

            # L'indicateur d'écart reste défini par la règle métier des
            # quantités demandées, sorties et retournées.
            qty_totale_traitee = (
                qty_installee + qty_retour
                if is_sortie_only
                else line.request_line_id.qty_sortie
                + line.request_line_id.qty_retour
            )
            if float_compare(
                qty_totale_traitee,
                line.request_line_id.qty_demandee,
                precision_digits=2,
            ) != 0:
                ecarts.append(
                    u'%s : demande %s, sorti %s, installe %s, retour %s' % (
                        html_escape(line.product_id.name or ''),
                        line.request_line_id.qty_demandee,
                        line.request_line_id.qty_sortie,
                        qty_installee,
                        qty_retour,
                    )
                )

        if retours_stock:
            request._generer_mouvement_retour_cloture()

        # Remplit le champ has_ecart sur la DSS :
        #   - bool(ecarts) = True  s'il y a au moins un écart
        #   - bool(ecarts) = False si aucun écart
        # C'est ICI que le mystère du champ has_ecart est résolu :
        # il est enfin mis à jour par le wizard de clôture.
        request.has_ecart = bool(ecarts)

        # Fait passer la DSS à l'état 'cloture'.
        request.state = 'cloture'

        # Construit le message pour le chatter.
        nom_acteur = html_escape(self.env.user.name or '')
        if self.is_exception:
            message = (
                u'<b>%s</b> a effectué une <b>clôture exceptionnelle</b>.'
                u'<br/><b>Motif :</b><br/>%s<br/>%s'
            ) % (
                nom_acteur,
                html_escape(self.motif_exception or '').replace('\n', '<br/>'),
                u'<br/>'.join(recap),
            )
        else:
            message = u'<b>%s</b> a clôturé la demande.<br/>%s' % (
                nom_acteur, u'<br/>'.join(recap))
        if retours_stock:
            message += (
                u'<br/><br/><b>Retours à l’emplacement d’origine :</b><br/>'
                + u'<br/>'.join(
                    u'\u2022 Une quantité %s de l’article %s a été retournée '
                    u'à l’emplacement d’origine : %s.'
                    % (
                        item['quantity'],
                        item['product'],
                        item['location'],
                    )
                    for item in retours_stock
                )
            )
        if ecarts:
            message += (
                u'<br/><br/><b>Ecarts detectes :</b><br/>'
                + u'<br/>'.join(ecarts)
            )

        # Poste le message dans le chatter.
        request.message_post(body=message)
        request.with_context(
            dss_closure_type='exception' if self.is_exception else 'normal',
            dss_closure_is_exception=self.is_exception,
            dss_closure_actor=self.env.user.name or '',
            dss_closure_reason=self.motif_exception or '',
            dss_closure_motif_exception=self.motif_exception or '',
            dss_closure_returns=retours_stock,
        )._dss_notify_closure()

        # Ferme la popup.
        return {'type': 'ir.actions.act_window_close'}


class DssClotureWizardLine(models.TransientModel):
    # Ligne du wizard de clôture.
    # C'est une COPIE d'une ligne de la DSS, manipulable dans la popup.
    _name = 'dss.cloture.wizard.line'
    _description = 'Ligne de assistant de cloture'

    # Lien vers le wizard parent.
    # ondelete='cascade' : si le wizard est supprimé, ses lignes aussi.
    wizard_id = fields.Many2one(
        'dss.cloture.wizard', string='Assistant', ondelete='cascade')

    # Lien vers la VRAIE ligne DSS.
    # readonly=True : l'utilisateur ne peut pas changer la ligne liée.
    request_line_id = fields.Many2one(
        'dss.request.line', string='Ligne DSS', readonly=True, required=True)

    # Article (non modifiable dans le wizard).
    product_id = fields.Many2one(
        'product.product', string='Article', readonly=True)

    # Quantité sortie : en lecture seule.
    # C'est la valeur de référence pour détecter les écarts.
    qty_sortie = fields.Float(string='Qte Sortie', readonly=True)

    # Quantités modifiables par l'utilisateur qui clôture :
    #   - qty_installee : quantité réellement installée chez le client
    #   - qty_retour    : quantité retournée au stock
    qty_installee = fields.Float(string='Qte Installee')
    qty_retour = fields.Float(string='Qte Retour')
    mode_saisie = fields.Selection(
        [
            ('installee', 'Saisir la quantité installée'),
            ('retour', 'Saisir la quantité retournée'),
        ],
        string='Quantité à saisir',
        required=True,
        default='installee',
    )
    is_sortie_only = fields.Boolean(
        related='request_line_id.is_sortie_only',
        readonly=True,
    )

    @api.onchange('mode_saisie', 'qty_installee', 'qty_retour')
    def _onchange_quantites_sortie(self):
        for line in self:
            if not line.is_sortie_only:
                continue
            qty_saisie = (
                line.qty_installee
                if line.mode_saisie == 'installee'
                else line.qty_retour
            )
            if (
                float_compare(qty_saisie, 0.0, precision_digits=2) < 0
                or float_compare(
                    qty_saisie,
                    line.qty_sortie,
                    precision_digits=2,
                ) > 0
            ):
                return {
                    'warning': {
                        'title': 'Quantité invalide',
                        'message': (
                            "La quantité saisie doit être comprise entre 0 "
                            "et la quantité sortie (%s)." % line.qty_sortie
                        ),
                    }
                }
            if line.mode_saisie == 'installee':
                line.qty_retour = line.qty_sortie - qty_saisie
            else:
                line.qty_installee = line.qty_sortie - qty_saisie