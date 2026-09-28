# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DssRequestLine(models.Model):
    _name = 'dss.request.line'
    _description = 'Ligne de DSS'

    request_id = fields.Many2one('dss.request', string='Demande DSS', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Article', required=True)
    qty_standard = fields.Float(
        string=u'Qte Disponible',
        compute='_compute_qty_standard',
        store=True
    )
    qty_demandee = fields.Float(string=u'Qte Demandee')
    qty_sortie = fields.Float(string=u'Qte Sortie')
    qty_installee = fields.Float(string=u'Qte Installee')
    qty_retour = fields.Float(string=u'Qte Retour')
    observation = fields.Char(string='Observation')

    qty_demandee_readonly = fields.Boolean(
        string='Qte Demandee lecture seule',
        default=False
    )

    @api.depends('product_id')
    def _compute_qty_standard(self):
        for line in self:
            if line.product_id:
                line.qty_standard = line.product_id.qty_available
            else:
                line.qty_standard = 0.0

    @api.onchange('product_id')
    def _onchange_product_id_qty_demandee_readonly(self):
        if self.request_id:
            self.qty_demandee_readonly = (self.request_id.type_intervention == 'retour_materiel')


class DssRequest(models.Model):
    _name = 'dss.request'
    _description = 'Demande de Sortie de Stock'
    _inherit = ['mail.thread']

    name = fields.Char(string='Numero DSS', copy=False, readonly=True, default='/')
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('valide_chef', 'Validation Chef'),
        ('valide_magasin', 'Validation Stock'),
        ('approuve', 'Approuve'),
        ('cloture', 'Cloture'),
        ('rejete', 'Rejete'),
    ], string='Statut', default='brouillon')

    bci = fields.Char(string='BCI')
    partner_id = fields.Many2one('res.partner', string='Client')
    lieu_intervention = fields.Char(string="Lieu d intervention")
    date_intervention = fields.Date(string="Date d intervention", default=fields.Date.today)
    location_id = fields.Many2one('stock.location', string='Emplacement',
        domain=[('usage', '=', 'internal')])
    location_dest_id = fields.Many2one('stock.location', string='Emplacement destination',
        domain=[('usage', '=', 'internal')])

    type_intervention = fields.Selection([
        ('nouvelle_installation', 'Nouvelle installation client'),
        ('basculement', 'Basculement client'),
        ('depannage', 'Depannage'),
        ('appro_distant', 'Approvisionnement de stock distant'),
        ('installation_interne', 'Installation interne (relais, infrastructure)'),
        ('retour_materiel', 'Retour de materiel (desinstallation)'),
    ], string="Type d intervention")

    sens_mouvement = fields.Char(
        string='Sens du mouvement',
        compute='_compute_sens_mouvement',
        store=True,
        readonly=True
    )

    picking_id = fields.Many2one('stock.picking', string='Mouvement de stock Odoo', readonly=True)
    has_ecart = fields.Boolean(string='Ecart detecte', readonly=True)
    motif_rejet = fields.Text(string='Motif de rejet')

    line_ids = fields.One2many('dss.request.line', 'request_id', string='Lignes')

    signataire_chef_id = fields.Many2one('res.users', string='Valide par Chef', readonly=True)
    date_validation_chef = fields.Datetime(string='Date validation Chef', readonly=True)
    signataire_magasin_id = fields.Many2one('res.users', string='Valide par Stock', readonly=True)
    date_validation_magasin = fields.Datetime(string='Date validation Stock', readonly=True)

    @api.depends('type_intervention')
    def _compute_sens_mouvement(self):
        mapping = {
            'nouvelle_installation': 'Sortie',
            'basculement': 'Sortie + Entree',
            'depannage': 'Sortie + Entree',
            'appro_distant': 'Transfert',
            'installation_interne': 'Sortie',
            'retour_materiel': 'Entree',
        }
        for rec in self:
            rec.sens_mouvement = mapping.get(rec.type_intervention, '')

    @api.onchange('type_intervention')
    def _onchange_type_intervention_lines(self):
        for line in self.line_ids:
            line.qty_demandee_readonly = (self.type_intervention == 'retour_materiel')

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('dss.request') or '/'
        return super(DssRequest, self).create(vals)

    def _detail_articles_html(self):
        self.ensure_one()
        lignes_detail = []
        for line in self.line_ids:
            parties = []
            if line.qty_demandee:
                parties.append(u"Qte Demandee %s" % line.qty_demandee)
            if line.qty_sortie:
                parties.append(u"Qte Sortie %s" % line.qty_sortie)
            if line.qty_installee:
                parties.append(u"Qte Installee %s" % line.qty_installee)
            if line.qty_retour:
                parties.append(u"Qte Retour %s" % line.qty_retour)
            if not parties:
                parties.append(u"Qte Demandee %s" % line.qty_demandee)
            lignes_detail.append(
                u"%s : %s" % (line.product_id.name, u", ".join(parties))
            )
        return u"<br/>".join(lignes_detail)

    @api.multi
    def action_soumettre(self):
        for rec in self:
            if not rec.bci:
                raise ValidationError("Le champ BCI est obligatoire avant de soumettre.")
            if not rec.partner_id:
                raise ValidationError("Le champ Client est obligatoire avant de soumettre.")
            if not rec.lieu_intervention:
                raise ValidationError("Le champ Lieu d intervention est obligatoire avant de soumettre.")
            if not rec.date_intervention:
                raise ValidationError("Le champ Date d intervention est obligatoire avant de soumettre.")
            if not rec.type_intervention:
                raise ValidationError("Le champ Type d intervention est obligatoire avant de soumettre.")
            if not rec.location_id:
                raise ValidationError("Le champ Emplacement est obligatoire avant de soumettre.")
            if rec.type_intervention == 'appro_distant' and not rec.location_dest_id:
                raise ValidationError("Le champ Emplacement destination est obligatoire pour un Transfert.")
            if not rec.line_ids:
                raise ValidationError("Vous devez ajouter au moins un article avant de soumettre.")
            rec.state = 'valide_chef'
            detail = rec._detail_articles_html()
            rec.message_post(body=u"<b>%s</b> a soumis la demande.<br/>%s" % (
                self.env.user.name, detail))

    @api.multi
    def action_valider_chef(self):
        for rec in self:
            if rec.state != 'valide_chef':
                raise ValidationError("La demande doit etre en Validation Chef.")
            rec.state = 'valide_magasin'
            rec.signataire_chef_id = self.env.user
            rec.date_validation_chef = fields.Datetime.now()
            rec.message_post(body=u"<b>%s</b> a valide la demande en tant que <b>Responsable Chef</b>." % self.env.user.name)

    @api.multi
    def action_valider_magasin(self):
        for rec in self:
            if rec.state != 'valide_magasin':
                raise ValidationError("La demande doit etre en Validation Stock.")
            rec.signataire_magasin_id = self.env.user
            rec.date_validation_magasin = fields.Datetime.now()

            if rec.sens_mouvement == 'Sortie':
                rec._generer_mouvement_sortie()
            elif rec.sens_mouvement == 'Entree':
                rec._generer_mouvement_entree()
            elif rec.sens_mouvement == 'Sortie + Entree':
                rec._generer_mouvement_sortie()
                rec._generer_mouvement_entree()
            elif rec.sens_mouvement == 'Transfert':
                rec._generer_mouvement_transfert()

            rec.message_post(body=u"<b>%s</b> a valide la demande en tant que <b>Responsable Stock</b>." % self.env.user.name)

            rec.state = 'approuve'
            rec._generer_bon_livraison()
            rec.message_post(body=u"<b>%s</b> a approuve definitivement la demande." % self.env.user.name)

    def _generer_mouvement_sortie(self):
        self.ensure_one()
        StockQuant = self.env['stock.quant']
        StockMove = self.env['stock.move']
        StockPicking = self.env['stock.picking']

        lignes_a_traiter = self.line_ids.filtered(lambda l: l.qty_sortie > 0)
        if not lignes_a_traiter:
            return

        for ligne in lignes_a_traiter:
            quants = StockQuant.read_group(
                [('location_id', '=', self.location_id.id),
                 ('product_id', '=', ligne.product_id.id)],
                ['qty'],
                []
            )
            qty_disponible = quants[0]['qty'] if quants else 0.0
            if ligne.qty_sortie > qty_disponible:
                raise ValidationError(
                    u"Quantite insuffisante pour l article %s dans l emplacement %s : "
                    u"demande %s, disponible %s." % (
                        ligne.product_id.name,
                        self.location_id.name,
                        ligne.qty_sortie,
                        qty_disponible,
                    )
                )

        emplacement_destination = self.partner_id.property_stock_customer
        if not emplacement_destination:
            emplacement_destination = self.env.ref('stock.stock_location_customers')

        picking_type = self.env['stock.picking.type'].search(
            [('code', '=', 'outgoing')], limit=1)

        picking = StockPicking.create({
            'partner_id': self.partner_id.id,
            'picking_type_id': picking_type.id,
            'location_id': self.location_id.id,
            'location_dest_id': emplacement_destination.id,
            'origin': self.name,
        })

        for ligne in lignes_a_traiter:
            StockMove.create({
                'name': ligne.product_id.name,
                'product_id': ligne.product_id.id,
                'product_uom_qty': ligne.qty_sortie,
                'product_uom': ligne.product_id.uom_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': emplacement_destination.id,
                'picking_id': picking.id,
            })

        picking.action_confirm()
        picking.action_assign()
        picking.action_done()

        self.picking_id = picking.id

    def _generer_mouvement_entree(self):
        self.ensure_one()
        StockMove = self.env['stock.move']
        StockPicking = self.env['stock.picking']

        lignes_a_traiter = self.line_ids.filtered(lambda l: l.qty_retour > 0)
        if not lignes_a_traiter:
            return

        emplacement_source = self.partner_id.property_stock_customer
        if not emplacement_source:
            emplacement_source = self.env.ref('stock.stock_location_customers')

        picking_type = self.env['stock.picking.type'].search(
            [('code', '=', 'incoming')], limit=1)

        picking = StockPicking.create({
            'partner_id': self.partner_id.id,
            'picking_type_id': picking_type.id,
            'location_id': emplacement_source.id,
            'location_dest_id': self.location_id.id,
            'origin': self.name,
        })

        for ligne in lignes_a_traiter:
            StockMove.create({
                'name': ligne.product_id.name,
                'product_id': ligne.product_id.id,
                'product_uom_qty': ligne.qty_retour,
                'product_uom': ligne.product_id.uom_id.id,
                'location_id': emplacement_source.id,
                'location_dest_id': self.location_id.id,
                'picking_id': picking.id,
            })

        picking.action_confirm()
        picking.action_assign()
        picking.action_done()

        self.picking_id = picking.id

    def _generer_mouvement_transfert(self):
        self.ensure_one()
        StockQuant = self.env['stock.quant']
        StockMove = self.env['stock.move']
        StockPicking = self.env['stock.picking']

        lignes_a_traiter = self.line_ids.filtered(lambda l: l.qty_sortie > 0)
        if not lignes_a_traiter:
            return

        if not self.location_dest_id:
            raise ValidationError(u"L emplacement destination est obligatoire pour un Transfert.")

        for ligne in lignes_a_traiter:
            quants = StockQuant.read_group(
                [('location_id', '=', self.location_id.id),
                 ('product_id', '=', ligne.product_id.id)],
                ['qty'],
                []
            )
            qty_disponible = quants[0]['qty'] if quants else 0.0
            if ligne.qty_sortie > qty_disponible:
                raise ValidationError(
                    u"Quantite insuffisante pour l article %s dans l emplacement %s : "
                    u"demande %s, disponible %s." % (
                        ligne.product_id.name,
                        self.location_id.name,
                        ligne.qty_sortie,
                        qty_disponible,
                    )
                )

        picking_type = self.env['stock.picking.type'].search(
            [('code', '=', 'internal')], limit=1)

        picking = StockPicking.create({
            'picking_type_id': picking_type.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'origin': self.name,
        })

        for ligne in lignes_a_traiter:
            StockMove.create({
                'name': ligne.product_id.name,
                'product_id': ligne.product_id.id,
                'product_uom_qty': ligne.qty_sortie,
                'product_uom': ligne.product_id.uom_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'picking_id': picking.id,
            })

        picking.action_confirm()
        picking.action_assign()
        picking.action_done()

        self.picking_id = picking.id

    def _generer_bon_livraison(self):
        self.ensure_one()
        Report = self.env['report']
        pdf_content = Report.get_pdf([self.id], 'dss_v2.report_bon_livraison_document')

        attachment = self.env['ir.attachment'].create({
            'name': u'Bon_Livraison_%s.pdf' % self.name,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'datas_fname': u'Bon_Livraison_%s.pdf' % self.name,
            'res_model': 'dss.request',
            'res_id': self.id,
        })
        self.message_post(
            body=u"Bon de Livraison genere automatiquement.",
            attachment_ids=[attachment.id]
        )

    @api.multi
    def action_imprimer_bon_livraison(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'dss_v2.report_bon_livraison_document',
            'report_type': 'qweb-pdf',
            'context': self.env.context,
        }

    @api.multi
    def action_approuver(self):
        for rec in self:
            if rec.state != 'valide_magasin':
                raise ValidationError("La demande doit etre validee par le Stock avant approbation.")
            rec.state = 'approuve'
            rec.message_post(body=u"<b>%s</b> a approuve definitivement la demande." % self.env.user.name)

    @api.multi
    def action_rejeter(self):
        for rec in self:
            rec.state = 'rejete'
            if rec.motif_rejet:
                rec.message_post(body=u"<b>%s</b> a rejete la demande.<br/>Motif : %s" % (
                    self.env.user.name, rec.motif_rejet))
            else:
                rec.message_post(body=u"<b>%s</b> a rejete la demande." % self.env.user.name)

    @api.multi
    def action_open_wizard_rejeter(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Motif du rejet',
            'res_model': 'dss.rejet.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    @api.multi
    def action_renvoyer_demandeur(self):
        for rec in self:
            rec.state = 'brouillon'
            rec.message_post(body=u"<b>%s</b> a renvoye la demande au demandeur." % self.env.user.name)

    @api.multi
    def action_open_modifier_qte_sortie(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Modifier Qte',
            'res_model': 'dss.qty.sortie.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    @api.multi
    def action_open_wizard_cloture(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cloturer la demande',
            'res_model': 'dss.cloture.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    @api.multi
    def action_open_wizard_chef(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirmation de validation',
            'res_model': 'dss.validation.chef.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    @api.multi
    def action_open_wizard_stock(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirmation de validation',
            'res_model': 'dss.validation.stock.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    @api.multi
    def action_open_wizard_approuver(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirmation d approbation',
            'res_model': 'dss.validation.approuver.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }


class DssRejetWizard(models.TransientModel):
    _name = 'dss.rejet.wizard'
    _description = 'Assistant de rejet de la demande DSS'

    request_id = fields.Many2one('dss.request', string='Demande DSS', required=True, readonly=True)
    motif = fields.Text(string='Motif du rejet', required=True)

    @api.multi
    def action_confirmer(self):
        self.ensure_one()
        self.request_id.motif_rejet = self.motif
        self.request_id.action_rejeter()
        return {'type': 'ir.actions.act_window_close'}


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        location_id = self._context.get('dss_location_id')
        if location_id:
            Quant = self.env['stock.quant']
            quants = Quant.read_group(
                [('location_id', '=', location_id)],
                ['product_id', 'qty'],
                ['product_id']
            )
            product_ids = []
            for q in quants:
                if q['product_id'] and q['qty'] > 0:
                    product_ids.append(q['product_id'][0])
            args = args + [('id', 'in', product_ids)]
        return super(ProductProduct, self).name_search(
            name=name, args=args, operator=operator, limit=limit)