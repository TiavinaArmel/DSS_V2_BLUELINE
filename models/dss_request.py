# -*- coding: utf-8 -*-

from odoo import (
    models,
    fields,
    api,
)  # importation de 3 outils : models, fields, api provenant du core d'odoo
# lisible et compréhensible par l'utilisateur (pas un traceback technique)


class DssRequest(models.Model):
    # la classe principale du module : une DEMANDE DE SORTIE DE STOCK

    _name = "dss.request"
    _description = "Demande de Sortie de Stock"
    # ajoute à dss.request toutes les fonctionnalités du modèle
    # standard mail.thread d'Odoo : le chatter, les notifications, le suivi
    # des modifications. C'est ce qui permet d'utiliser message_post()
    _inherit = ["mail.thread"]

    # le champ du numéro de la demande (EX: DSS-00001)
    # readonly=True = lecture seule : l'utilisateur ne peut PAS modifier ce
    # champ à la main (il est rempli automatiquement par create(), plus bas)
    # copy=False : si on duplique une demande, ce numéro n'est PAS recopié
    # (pas de règle d'unicité dans ce code : rien ne garantit en base que
    # deux demandes ne pourraient pas avoir le même nom)
    name = fields.Char(string="Numero DSS", copy=False, readonly=True, default="/")

    # champ de type selection des états du DSS
    state = fields.Selection(
        [
            ("brouillon", "Brouillon"),
            ("valide_chef", "Validation Chef"),
            ("valide_magasin", "Validation Stock"),
            ("approuve", "Approuve"),
            ("cloture", "Cloture"),
            ("rejete", "Rejete"),
        ],
        string="Statut",
        default="brouillon",
    )
    # LE CHAMP LE PLUS IMPORTANT DU MODULE : c'est la "machine à états" qui
    # représente où en est la demande dans son circuit de validation.
    # Chaque tuple (clé technique, libellé affiché) est une valeur possible.
    # Toute demande commence à 'brouillon' par défaut. Les méthodes
    # action_xxx() plus bas font avancer ce champ d'une valeur à l'autre.

    # BCI = Bon de Commande Interne : une référence administrative
    # liée à la demande
    bci = fields.Char(string="BCI")

    # le client concerné par l'intervention. res.partner est le modèle
    # standard d'Odoo pour tous les contacts (clients, fournisseurs...)
    partner_id = fields.Many2one("res.partner", string="Client")
    # champ de texte simple pour décrire où a lieu l'intervention
    lieu_intervention = fields.Char(string="Lieu d intervention")

    # date de l'intervention ; par défaut, elle vaut la date du jour
    # (fields.Date.today, et non "il", car "date" est un nom féminin)
    date_intervention = fields.Date(
        string="Date d intervention", default=fields.Date.today
    )
    # L'emplacement de stock SOURCE (d'où part le matériel).
    # stock.location est aussi un modèle standard d'Odoo
    # domain=[("usage", "=", "internal")] : filtre la liste déroulante pour
    # ne proposer que les emplacements internes
    location_id = fields.Many2one(
        "stock.location", string="Emplacement", domain=[("usage", "=", "internal")]
    )
    # l'emplacement de destination du stock
    location_dest_id = fields.Many2one(
        "stock.location",
        string="Emplacement destination",
        domain=[("usage", "=", "internal")],
    )
    # champ de sélection des types d'intervention
    type_intervention = fields.Selection(
        [
            ("nouvelle_installation", "Nouvelle installation client"),
            ("basculement", "Basculement client"),
            ("depannage", "Depannage"),
            ("appro_distant", "Approvisionnement de stock distant"),
            ("installation_interne", "Installation interne (relais, infrastructure)"),
            ("retour_materiel", "Retour de materiel (desinstallation)"),
        ],
        string="Type d intervention",
    )
    # champ calculé et stocké, en lecture seule pour l'utilisateur :
    # reflète le type_intervention choisi, sous une forme plus parlante
    # ("Sortie", "Entree", "Sortie + Entree", "Transfert"). Recalculé par
    # _compute_sens_mouvement() dès que type_intervention change.
    sens_mouvement = fields.Char(
        string="Sens du mouvement",
        compute="_compute_sens_mouvement",
        store=True,
        readonly=True,
    )
    # champ de relation Many2one vers stock.picking.
    # Une fois les mouvements de stock générés (dans action_valider_magasin),
    # ce champ garde le LIEN vers le stock.picking créé par Odoo, pour
    # pouvoir le retrouver et le consulter depuis la fiche DSS.
    picking_id = fields.Many2one(
        "stock.picking", string="Mouvement de stock Odoo", readonly=True
    )
    # champ prévu pour signaler un écart (par exemple entre quantité
    # demandée et quantité réellement sortie/installée) — jamais mis à
    # True dans ce fichier, probablement utilisé ailleurs (wizards) ou
    # prévu pour une évolution future
    has_ecart = fields.Boolean(string="Ecart detecte", readonly=True)
    # champ de texte contenant le motif du rejet de la demande, rempli via
    # le wizard DssRejetWizard tout en bas de ce fichier
    motif_rejet = fields.Text(string="Motif de rejet")

    # champ One2many : liste de TOUTES les lignes (DssRequestLine)
    # rattachées à cette demande. C'est le miroir exact du champ
    # request_id défini dans DssRequestLine plus haut
    line_ids = fields.One2many("dss.request.line", "request_id", string="Lignes")

    # Ces champs gardent la trace des personnes qui soumettent et valident la DSS.
    # Ils sont remplis par le workflow et ne sont pas saisis manuellement.
    signataire_demandeur_id = fields.Many2one(
        "res.users", string="Soumis par", readonly=True, copy=False
    )
    date_soumission = fields.Datetime(
        string="Date de soumission", readonly=True, copy=False
    )

    signataire_chef_id = fields.Many2one(
        "res.users", string="Valide par Chef", readonly=True
    )
    date_validation_chef = fields.Datetime(string="Date validation Chef", readonly=True)
    signataire_magasin_id = fields.Many2one(
        "res.users", string="Valide par Stock", readonly=True
    )
    date_validation_magasin = fields.Datetime(
        string="Date validation Stock", readonly=True
    )

    @api.depends("type_intervention")
    def _compute_sens_mouvement(self):
        # dictionnaire Python qui associe chaque type d'intervention
        # technique à son "sens" fonctionnel. C'est la table de
        # correspondance centrale du module
        mapping = {
            "nouvelle_installation": "Sortie",
            "basculement": "Sortie + Entree",
            "depannage": "Sortie + Entree",
            "appro_distant": "Transfert",
            "installation_interne": "Sortie",
            "retour_materiel": "Entree",
        }

        for rec in self:
            rec.sens_mouvement = mapping.get(rec.type_intervention, "")

    # .get(clé, valeur_par_defaut) : si type_intervention n'est pas
    # encore choisi (None), on met une chaîne vide plutôt que de
    # planter avec une KeyError.

    @api.onchange("type_intervention")
    def _onchange_type_intervention_lines(self):
        # si l'intervention est un "retour matériel", on verrouille
        # la quantité demandée sur toutes les lignes (lecture seule)
        for line in self.line_ids:
            line.qty_demandee_readonly = self.type_intervention == "retour_materiel"

    @api.model
    def create(self, vals):
        """
        Surcharge de create() pour attribuer automatiquement un numéro
        à chaque nouvelle demande DSS.

        - Si 'name' est vide ou absent (égal à "/"), on récupère le
          prochain numéro de la séquence 'dss.request'.
        - Sinon, la valeur fournie dans vals est conservée telle quelle
          (en pratique, ce cas n'arrive jamais depuis l'interface,
          puisque le champ est readonly dans la vue).
        """
        # si aucun nom n'est fourni ("/" = valeur par défaut)
        if vals.get("name", "/") == "/":
            # on génère un numéro via la séquence dédiée aux demandes DSS
            vals["name"] = self.env["ir.sequence"].next_by_code("dss.request") or "/"
        # on laisse ensuite Odoo effectuer la création standard
        return super(DssRequest, self).create(vals)
