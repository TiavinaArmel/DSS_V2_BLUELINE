# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    """Ajoute des champs DSS et une validation dédiée aux transferts de stock."""

    _inherit = 'stock.picking'

    # Ces champs étendent le modèle Odoo existant sans créer une nouvelle table métier.
    dss_number = fields.Char(string="Numero DSS", copy=False, readonly=True)
    dss_justification = fields.Text(string="Justification d'ecart")
    dss_movement_type = fields.Selection([
        ('sortie', 'Sortie'),
        ('entree', 'Entree'),
        ('transfert', 'Transfert'),
    ], string="Type de mouvement DSS")
    dss_validation_state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('demandeur', 'Demandeur'),
        ('valide_chef', 'Validation Chef'),
        ('valide_magasin', 'Validation Stock'),
        ('valide_securite', 'Validation Demandeur'),
        ('approuve', 'Approuve'),
    ], string="Statut DSS", default='brouillon')

    @api.model
    def create(self, vals):
        """Attribue un numéro DSS avant la création ORM du transfert."""
        # create() reçoit les valeurs du nouvel enregistrement dans un dictionnaire.
        if not vals.get('dss_number'):
            # next_by_code() demande à la séquence Odoo le prochain numéro disponible.
            vals['dss_number'] = self.env['ir.sequence'].next_by_code('dss.number') or '/'
        # super() conserve le comportement standard de création de stock.picking.
        return super(StockPicking, self).create(vals)

    def check_dss_ecart(self):
        """Exige une justification lorsque la quantité diffère du standard article."""
        # La boucle accepte également un ensemble de transferts fourni par l'appelant.
        for picking in self:
            for move in picking.move_lines:
                # La tolérance évite de signaler les écarts dus aux arrondis décimaux.
                standard_qty = move.product_id.dss_standard_qty
                if standard_qty and abs(move.product_uom_qty - standard_qty) > 0.001:
                    if not picking.dss_justification:
                        raise ValidationError(
                            "ECART DETECTE sur '%s' : standard=%s, demande=%s.\n"
                            "Le champ Justification d ecart est obligatoire." % (
                                move.product_id.name,
                                standard_qty,
                                move.product_uom_qty,
                            )
                        )

    @api.multi
    def action_soumettre_dss(self):
        """Place les transferts sélectionnés dans l'étape de soumission DSS."""
        for picking in self:
            picking.dss_validation_state = 'soumis'

    @api.multi
    def action_valider_chef(self):
        """Valide l'étape Chef après avoir vérifié l'état précédent."""
        for picking in self:
            if picking.dss_validation_state != 'soumis':
                raise ValidationError("La demande doit etre soumise avant validation du Chef.")
            picking.dss_validation_state = 'valide_chef'

    @api.multi
    def action_valider_magasin(self):
        """Valide l'étape Magasin uniquement après l'accord du Chef."""
        for picking in self:
            if picking.dss_validation_state != 'valide_chef':
                raise ValidationError("La demande doit etre validee par le Chef avant le Magasin.")
            picking.dss_validation_state = 'valide_magasin'

    @api.multi
    def action_valider_securite(self):
        """Valide l'étape Sécurité uniquement après l'accord du Magasin."""
        for picking in self:
            if picking.dss_validation_state != 'valide_magasin':
                raise ValidationError("La demande doit etre validee par le Magasin avant la Securite.")
            picking.dss_validation_state = 'valide_securite'

    @api.multi
    def action_approuver(self):
        """Termine le workflow DSS après la validation de l'étape Sécurité."""
        for picking in self:
            if picking.dss_validation_state != 'valide_securite':
                raise ValidationError("La demande doit etre validee par la Securite avant approbation.")
            picking.dss_validation_state = 'approuve'


class StockImmediateTransfer(models.TransientModel):
    """Intercepte le wizard de transfert immédiat pour appliquer le contrôle DSS."""

    _inherit = 'stock.immediate.transfer'

    @api.multi
    def process(self):
        """Contrôle les écarts avant de déléguer le traitement standard à Odoo."""
        # pick_id désigne le transfert associé au wizard temporaire.
        self.pick_id.check_dss_ecart()
        # super() exécute ensuite le traitement immédiat natif d'Odoo 10.
        return super(StockImmediateTransfer, self).process()