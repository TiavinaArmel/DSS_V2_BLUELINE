# -*- coding: utf-8 -*-
from odoo import models, fields, api

"""
Wizard est une Popup qui demande à l'utilisateur :
"êtes-vous sûr de vouloire  valider cette DSS " 
POURQUOI? , on ne valide pas une DSS par accident 
on veut : 
 - une confirmation explicite 
 -  une popup claire 
 -  une bouton confirmer et un bouton annuler 
 !!!!!!!Ces wizards ne contiennent aucune logique métier :!!!!

pas de calcul,pas de mouvement de stock,pas de changement d’état.

    Le wizard = interface de confirmation.
    Le modèle principal = logique métier.

"""


class DssValidationChefWizard(models.TransientModel):
    # models.TransientModel : modèle temporaire (popup/wizard)
    # la classe DssValidationChefWizard est un assisttant de confirmation
    _name = "dss.validation.chef.wizard"  # nom téchnique du wizard
    _description = "Wizard de confirmation Validation Chef"

    request_id = fields.Many2one("dss.request", string="Demande DSS", required=True)

    # request_id est une champs de relation plusieur à un ,
    # qui est comme une clée étrangère qui fait référence a dss_request.id
    # pour savoir sur quelle DSS le wizard travaille
    @api.multi
    def action_confirmer(
        self,
    ):  # méhodes appéle si on clique sur le bouton confirmer sur le wizard
        self.ensure_one()  # assurer qu'il n'y a qu'une wizard actif
        self.request_id.action_valider_chef()  # appelle la méthodes action_valider_chef() sur la DSS request
        return {"type": "ir.actions.act_window_close"}  # fermeture de la pop up

    @api.multi
    def action_annuler(
        self,
    ):
        # méthode appelée si on clique sur le bouton annuler sur le wizard
        # le wizard va juste se référmée
        return {"type": "ir.actions.act_window_close"}


class DssValidationStockWizard(models.TransientModel):
    # la classe  DssValidationStockWizard est de même fonctinnement qui DssValidationChefWizard
    #  sauf, les méthodes sont après de confirmation appelle juste 
    # la méthode "action_valider_magasin" mais par "valider chef "
    _name = "dss.validation.stock.wizard"
    _description = "Wizard de confirmation Validation Stock du magasin"

    request_id = fields.Many2one("dss.request", string="Demande DSS", required=True)

    @api.multi
    def action_confirmer(self):
        self.ensure_one()
        self.request_id.action_valider_magasin()
        return {"type": "ir.actions.act_window_close"}

    @api.multi
    def action_annuler(self):
        return {"type": "ir.actions.act_window_close"}


class DssValidationApprouverWizard(models.TransientModel):
    #wizard de confirmatoin pour l'approbation finale 
    _name = "dss.validation.approuver.wizard"
    _description = "Wizard de confirmation Approbation"

    request_id = fields.Many2one("dss.request", string="Demande DSS", required=True)

    @api.multi
    def action_confirmer(self):
        self.ensure_one()
        self.request_id.action_approuver()#méthodes appelée pour changée juste ne approuveé 
        return {"type": "ir.actions.act_window_close"}

    @api.multi
    def action_annuler(self):
        return {"type": "ir.actions.act_window_close"}
