# -*- coding: utf-8 -*-

import base64  # module qui transforme des données binaires (PDF, image, ZIP file) en texte lisible
from odoo import (
    models,
    fields,
    api,
)  # importation de 3 outils : models, fields, api provenant du core d'odoo
from odoo.exceptions import (
    ValidationError,
)  # importation de ValidationError pour bloquer une action avec un message d'erreur

# lisible et compréhensible par l'utilisateur (pas un traceback technique)


class DssRequestLine(
    models.Model
):  # Nom de la classe Python, représente une ligne d'article à l'intérieur d'une
    # demande DSS (le dss.request)
    _name = "dss.request.line"  # nom technique du modèle utilisé par Odoo == nom de la table dans PostgreSQL
    _description = (
        "Ligne de DSS"  # une DSS Request Line est une ligne qui se trouve dans un DSS
    )
    # une ligne contient un article et ses caractéristiques de demande

    # champ de relation : request_id, clé étrangère qui référence dss.request
    # depuis le modèle dss.request.line (crée la colonne request_id dans la
    # table dss_request_line en base PostgreSQL)
    request_id = fields.Many2one(
        "dss.request",
        string="Demande DSS",
        ondelete="cascade",  # à la suppression du parent dss.request, cette ligne
        # sera supprimée aussi : pas de ligne orpheline
    )
    # champ de relation product_id qui se réfère à un article, dans le modèle
    # standard d'Odoo pour les articles/produits
    product_id = fields.Many2one("product.product", string="Article", required=True)

    # champ de type décimal CALCULÉ (compute=...) : sa valeur n'est pas saisie
    # à la main par l'utilisateur mais calculée automatiquement par la méthode
    # _compute_qty_standard, et le résultat du calcul est sauvegardé en base
    # (store=True)
    qty_standard = fields.Float(
        string="Qte Disponible", compute="_compute_qty_standard", store=True
    )
    # champ de type décimal, pour la saisie de la quantité demandée en sortie/retour
    qty_demandee = fields.Float(string="Qte Demandee")
    # champ de type décimal, pour la quantité réellement sortie du stock
    qty_sortie = fields.Float(string="Qte Sortie")
    # champ de type décimal, pour la quantité réellement installée chez le
    # client, une fois l'intervention terminée
    qty_installee = fields.Float(string="Qte Installee")
    # champ décimal, dédié à la quantité de matériel qui retourne en stock
    # (en cas de retour)
    qty_retour = fields.Float(string="Qte Retour")
    # simple champ de texte libre, pour une remarque sur la ligne de DSS
    observation = fields.Char(string="Observation")
    # champ booléen qui sert uniquement à piloter l'affichage du champ
    # qty_demandee dans la vue (le rendre modifiable ou non)
    qty_demandee_readonly = fields.Boolean(
        string="Qte Demandee lecture seule", default=False
    )

    # Décorateur @api.depends('product_id') : dit à Odoo "recalcule ce
    # champ automatiquement à chaque fois que product_id change".
    # C'est ce qui relie ce compute à sa déclaration plus haut.
    @api.depends("product_id")
    def _compute_qty_standard(self):
        for line in self:
            # self peut contenir plusieurs lignes à la fois, alors on boucle
            # sur chacune
            if line.product_id:
                # si un article est choisi sur cette ligne
                line.qty_standard = line.product_id.qty_available
                # on récupère sa quantité disponible ("qty_available") en
                # stock, un champ déjà fourni nativement par le modèle
                # product.product
            else:  # sinon
                line.qty_standard = 0.0
                # si aucun article n'est encore choisi, pas de quantité à
                # afficher : on met 0 plutôt que de laisser une valeur vide

    # @api.onchange (différent de @api.depends) : s'exécute UNIQUEMENT
    # côté interface, en direct pendant que l'utilisateur remplit le
    # formulaire, AVANT toute sauvegarde en base. Sert à ajuster
    # dynamiquement l'écran (ici, verrouiller ou non un champ).
    @api.onchange("product_id")
    def _onchange_product_id_qty_demandee_readonly(self):
        if self.request_id:
            # on vérifie que la ligne est bien rattachée à une demande
            # (sécurité : au tout début de la saisie, ça peut ne pas
            # encore être le cas)

            # Logique métier : si le type d'intervention de la demande
            # parente est "Retour de materiel", alors qty_demandee devient
            # en lecture seule sur cette ligne (dans ce cas, c'est plutôt
            # qty_retour qui a du sens à remplir, pas une nouvelle demande)
            self.qty_demandee_readonly = (
                self.request_id.type_intervention == "retour_materiel"
            )


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

    # Ces 4 champs forment une PISTE D'AUDIT (traçabilité) : qui a validé
    # en tant que Chef et quand, qui a validé en tant que Magasin et quand.
    # Tous en readonly=True car remplis uniquement par le code (les
    # méthodes action_valider_chef et action_valider_magasin plus bas),
    # jamais saisis à la main.

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

    def _detail_articles_html(
        self,
    ):  # méthode privée qui retourne une chaîne HTML détaillant les articles
        """
        Génère un résumé HTML des articles de la demande.

        Pour chaque ligne (line_ids), affiche le nom du produit suivi
        des quantités renseignées :
          - Quantité demandée
          - Quantité sortie
          - Quantité installée
          - Quantité retour

        Les quantités nulles sont ignorées. Si aucune quantité n'est
        renseignée, la quantité demandée est affichée par défaut.

        Retour : chaîne HTML avec un <br/> entre chaque article.
        Utilisé notamment dans les messages du chatter.
        """
        self.ensure_one()  # pour s'assurer de travailler sur un seul enregistrement
        lignes_detail = []  # liste vide qui va accumuler un texte par ligne d'article
        for line in self.line_ids:  # parcourir chaque ligne d'article de la demande
            parties = (
                []
            )  # liste vide pour contenir les différentes quantités à afficher
            if (
                line.qty_demandee
            ):  # si la quantité demandée existe, on l'ajoute à parties
                parties.append("Qte Demandee %s" % line.qty_demandee)
            if line.qty_sortie:  # si la quantité sortie existe, on l'ajoute aussi
                parties.append("Qte Sortie %s" % line.qty_sortie)
            if line.qty_installee:  # idem pour la quantité installée
                parties.append("Qte Installee %s" % line.qty_installee)
            if line.qty_retour:  # si une quantité retournée existe, on l'ajoute
                parties.append("Qte Retour %s" % line.qty_retour)
            if (
                not parties
            ):  # si AUCUNE quantité n'a été ajoutée, on affiche quand même la quantité demandée
                parties.append("Qte Demandee %s" % line.qty_demandee)
            lignes_detail.append("%s : %s" % (line.product_id.name, ", ".join(parties)))
        return "<br/>".join(lignes_detail)

    @api.multi
    def action_soumettre(
        self,
    ):
        """
        Action déclenchée par le bouton "Soumettre".

        Étapes :
            1. Vérifie les champs obligatoires :
                - bci, partner_id, lieu_intervention, date_intervention,
                  type_intervention, location_id
            2. Vérifie la règle conditionnelle :
                - si type_intervention == "appro_distant", alors
                  location_dest_id est obligatoire
            3. Vérifie qu'au moins une ligne d'article existe (line_ids)
            4. Change le statut en 'valide_chef'
            5. Poste un message dans le chatter avec le résumé HTML
               des articles (_detail_articles_html)

        :raises ValidationError: si un champ obligatoire est manquant
                                 ou si aucun article n'est renseigné.
        """
        # cette méthode est appelée quand on clique sur "Soumettre"
        for rec in self:  # parcourir les demandes sélectionnées
            if not rec.bci:  # si bci n'est pas défini, erreur
                raise ValidationError(
                    "Le champ BCI est obligatoire avant de soumettre."
                )
            if not rec.partner_id:
                raise ValidationError(
                    "Le champ Client est obligatoire avant de soumettre."
                )
            if not rec.lieu_intervention:
                raise ValidationError(
                    "Le champ Lieu d intervention est obligatoire avant de soumettre."
                )
            if not rec.date_intervention:
                raise ValidationError(
                    "Le champ Date d intervention est obligatoire avant de soumettre."
                )
            if not rec.type_intervention:
                raise ValidationError(
                    "Le champ Type d intervention est obligatoire avant de soumettre."
                )
            if not rec.location_id:
                raise ValidationError(
                    "Le champ Emplacement est obligatoire avant de soumettre."
                )
            if rec.type_intervention == "appro_distant" and not rec.location_dest_id:
                raise ValidationError(
                    "Le champ Emplacement destination est obligatoire pour un Transfert."
                )
            if not rec.line_ids:
                raise ValidationError(
                    "Vous devez ajouter au moins un article avant de soumettre."
                )
            rec.state = "valide_chef"
            detail = rec._detail_articles_html()
            rec.message_post(
                body="<b>%s</b> a soumis la demande.<br/>%s"
                % (self.env.user.name, detail)
            )

    @api.multi
    def action_valider_chef(self):
        for rec in self:
            if rec.state != "valide_chef":
                raise ValidationError("La demande doit etre en Validation Chef.")
            # garde-fou d'état : on ne peut valider "en tant que Chef" que
            # si la demande est déjà dans l'état valide_chef (donc déjà
            # soumise). Empêche de valider un brouillon directement, en
            # sautant l'étape de soumission. Si ce contrôle passe, le code
            # continue normalement ci-dessous.

            rec.state = "valide_magasin"
            # on fait avancer l'état vers valide_magasin
            rec.signataire_chef_id = (
                self.env.user
            )  # pour tracer qui est le chef validateur
            rec.date_validation_chef = fields.Datetime.now()  # et la date de validation
            rec.message_post(
                body="<b>%s</b> a valide la demande en tant que <b>Responsable Chef</b>."
                % self.env.user.name
            )
            # on trace QUI a validé (l'utilisateur connecté) et QUAND
            # (l'heure serveur actuelle) — remplissage de 2 des 4 champs
            # d'audit vus plus haut

    @api.multi
    def action_valider_magasin(self):
        for rec in self:
            if rec.state != "valide_magasin":
                raise ValidationError("La demande doit etre en Validation Stock.")
                # on vérifie, pour chaque enregistrement traité, qu'il est
                # bien à l'état valide_magasin, pour éviter les sauts
                # d'état. Si ce n'est pas le cas, on arrête ici.

            rec.signataire_magasin_id = self.env.user
            rec.date_validation_magasin = fields.Datetime.now()
            # traçage du magasinier qui approuve et de la date de validation
            """
             Routeur : selon le sens de mouvement (calculé à partir de
             type_intervention), on déclenche la ou les méthodes privées de
             génération de mouvement de stock.

               Sortie            -> _generer_mouvement_sortie()
               Entree            -> _generer_mouvement_entree()
               Sortie + Entree   -> les deux méthodes ci-dessus
               Transfert         -> _generer_mouvement_transfert()

             Pas de "else" volontaire : toute autre valeur (normalement
             impossible via le compute) ne génère rien, silencieusement.
             Penser à mettre à jour ce bloc si une nouvelle valeur est
             ajoutée au mapping de sens_mouvement.
            """
            if rec.sens_mouvement == "Sortie":
                rec._generer_mouvement_sortie()
            elif rec.sens_mouvement == "Entree":
                rec._generer_mouvement_entree()
            elif rec.sens_mouvement == "Sortie + Entree":
                rec._generer_mouvement_sortie()
                rec._generer_mouvement_entree()
            elif rec.sens_mouvement == "Transfert":
                rec._generer_mouvement_transfert()

            rec.message_post(
                body="<b>%s</b> a valide la demande en tant que <b>Responsable Stock</b>."
                % self.env.user.name
            )
            # poste dans le chatter une trace de validation par
            # l'utilisateur courant (rôle : Responsable Stock)

            rec.state = "approuve"  # l'état de la demande passe à approuvée
            rec._generer_bon_livraison()  # on génère le bon de livraison
            rec.message_post(
                body="<b>%s</b> a approuve definitivement la demande."
                % self.env.user.name
            )  # poste un message indiquant que le magasinier a approuvé
            # définitivement la demande, en reprenant son nom (user.name)

    def _generer_mouvement_sortie(self):
        # génère un mouvement de SORTIE de stock : du magasin vers le
        # client. Utilisé pour les types "Nouvelle installation",
        # "Basculement", "Depannage", "Installation interne"
        self.ensure_one()  # s'assurer de ne traiter qu'un seul enregistrement
        StockQuant = self.env["stock.quant"]
        StockMove = self.env["stock.move"]
        StockPicking = self.env["stock.picking"]

        # ces trois lignes préparent des "raccourcis" vers les modèles
        # stock standards d'Odoo qu'on va utiliser :
        #   - stock.quant : la quantité réellement disponible d'un article
        #     à un emplacement donné, à un instant T
        #   - stock.move : UN mouvement élémentaire (un article, une
        #     quantité, d'un emplacement A vers un emplacement B)
        #   - stock.picking : le "bon" qui regroupe plusieurs stock.move
        #     ensemble (l'équivalent d'un bon de livraison/réception)

        lignes_a_traiter = self.line_ids.filtered(lambda l: l.qty_sortie > 0)
        if not lignes_a_traiter:
            return
        # ne conserve que les lignes ayant une quantité de sortie > 0.
        # Si aucune ligne n'est concernée, on sort de la méthode :
        # inutile de générer un mouvement de stock vide.

        """
        Vérifie que le stock disponible est suffisant pour chaque ligne
        d'article à sortir.

        Pour chaque ligne (parmi celles filtrées), interroge StockQuant
        afin de connaître la quantité disponible du produit dans
        l'emplacement source (self.location_id), puis compare avec la
        quantité demandée en sortie.

        :raises ValidationError: si la quantité demandée dépasse la
            quantité disponible pour au moins un article.
        """

        for ligne in lignes_a_traiter:
            # agrège la quantité en stock pour ce produit dans l'emplacement source
            quants = StockQuant.read_group(
                [
                    ("location_id", "=", self.location_id.id),  # emplacement source
                    ("product_id", "=", ligne.product_id.id),  # produit concerné
                ],
                ["qty"],  # champ à sommer
                [],  # pas de regroupement supplémentaire
            )

            # quantité totale disponible (0 si aucun quant trouvé)
            qty_disponible = quants[0]["qty"] if quants else 0.0

            # contrôle : impossible de sortir plus que le stock disponible
            if ligne.qty_sortie > qty_disponible:
                raise ValidationError(
                    "Quantite insuffisante pour l article %s dans l emplacement %s : "
                    "demande %s, disponible %s."
                    % (
                        ligne.product_id.name,  # produit
                        self.location_id.name,  # emplacement
                        ligne.qty_sortie,  # quantité demandée
                        qty_disponible,  # quantité disponible
                    )
                )
        # on détermine l'emplacement de destination du matériel qui va
        # sortir : en priorité l'emplacement client spécifique défini sur
        # la fiche du partenaire (property_stock_customer, champ standard
        # d'Odoo)
        emplacement_destination = self.partner_id.property_stock_customer
        if not emplacement_destination:
            emplacement_destination = self.env.ref("stock.stock_location_customers")
        # sinon, l'emplacement destination sera l'emplacement client
        # générique fourni par le module stock de base
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "outgoing")], limit=1
        )
        # on cherche le "type d'opération" Odoo correspondant à une sortie
        # (code 'outgoing'). limit=1 : on n'a besoin que d'un seul résultat

        picking = StockPicking.create(
            {
                "partner_id": self.partner_id.id,
                "picking_type_id": picking_type.id,
                "location_id": self.location_id.id,
                "location_dest_id": emplacement_destination.id,
                "origin": self.name,
            }
        )
        # création du bon de sortie du DSS, en reprenant les informations
        # du client (partner_id.id), le type d'intervention (ici "outgoing"),
        # l'emplacement d'où provient le matériel (location_id.id), la
        # destination de la sortie (emplacement_destination.id), et le
        # numéro de la DSS d'origine (self.name)

        for ligne in lignes_a_traiter:
            StockMove.create(
                {
                    "name": ligne.product_id.name,  # nom de l'article
                    "product_id": ligne.product_id.id,  # identifiant de l'article
                    "product_uom_qty": ligne.qty_sortie,  # quantité à sortir
                    "product_uom": ligne.product_id.uom_id.id,  # unité de mesure de l'article
                    "location_id": self.location_id.id,  # emplacement source
                    "location_dest_id": emplacement_destination.id,  # destination de l'article
                    "picking_id": picking.id,  # rattachement au bon créé ci-dessus
                }
            )
        # création d'un mouvement de stock pour chaque ligne d'article du
        # DSS, en reprenant le nom et l'identifiant du produit, et son
        # uom (Unit of Measure, FR : unité de mesure)

        picking.action_confirm()
        picking.action_assign()
        picking.action_done()
        # le cycle de vie standard d'un mouvement Odoo, en 3 étapes :
        #   1. action_confirm() : confirme le picking (il devient "prêt à
        #      traiter")
        #   2. action_assign() : réserve le stock nécessaire
        #   3. action_done() : valide définitivement le mouvement, ce qui
        #      décrémente réellement le stock en base
        self.picking_id = picking.id
        # on sauvegarde le lien vers ce picking sur la demande DSS
        # elle-même, pour pouvoir le retrouver depuis la fiche (champ
        # picking_id)

    def _generer_mouvement_entree(self):
        # génère un mouvement d'ENTRÉE : du client vers le magasin. Utilisé
        # pour "Retour de materiel", et en complément pour "Basculement"/
        # "Depannage" (qui ont sens_mouvement = "Sortie + Entree")

        self.ensure_one()  # s'assurer de ne traiter qu'un seul enregistrement
        StockMove = self.env["stock.move"]
        StockPicking = self.env["stock.picking"]

        lignes_a_traiter = self.line_ids.filtered(lambda l: l.qty_retour > 0)
        if not lignes_a_traiter:
            return

        # contrairement à _generer_mouvement_sortie, on filtre ici sur
        # qty_retour et non sur qty_sortie

        emplacement_source = self.partner_id.property_stock_customer
        if not emplacement_source:
            emplacement_source = self.env.ref("stock.stock_location_customers")
        # ici c'est l'inverse de la sortie : l'emplacement client
        # (stock.stock_location_customers) est la SOURCE (d'où revient le
        # matériel), pas la destination

        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )
        # type d'opération "entrée" (code 'incoming'), symétrique de
        # "outgoing"
        picking = StockPicking.create(
            {
                "partner_id": self.partner_id.id,
                "picking_type_id": picking_type.id,
                "location_id": emplacement_source.id,
                "location_dest_id": self.location_id.id,
                "origin": self.name,
            }
        )
        # notez l'inversion par rapport à la sortie :
        # location_id (source) est maintenant l'emplacement client, et
        # location_dest_id (destination) est notre emplacement de stock
        # interne

        for ligne in lignes_a_traiter:
            StockMove.create(
                {
                    "name": ligne.product_id.name,
                    "product_id": ligne.product_id.id,
                    "product_uom_qty": ligne.qty_retour,
                    "product_uom": ligne.product_id.uom_id.id,
                    "location_id": emplacement_source.id,
                    "location_dest_id": self.location_id.id,
                    "picking_id": picking.id,
                }
            )
        # même structure que pour la sortie, mais avec qty_retour comme
        # quantité, et le sens des emplacements inversé

        picking.action_confirm()
        picking.action_assign()
        picking.action_done()

        self.picking_id = picking.id

    def _generer_mouvement_transfert(self):
        # génère un TRANSFERT entre deux emplacements internes (pas de
        # client impliqué). Utilisé uniquement pour "Approvisionnement de
        # stock distant"
        self.ensure_one()
        StockQuant = self.env["stock.quant"]
        StockMove = self.env["stock.move"]
        StockPicking = self.env["stock.picking"]

        lignes_a_traiter = self.line_ids.filtered(lambda l: l.qty_sortie > 0)
        if not lignes_a_traiter:
            return
        # comme pour la sortie classique, on se base sur qty_sortie (la
        # quantité qui "sort" de l'emplacement source, même si elle ne
        # sort pas de l'entreprise dans ce cas)

        if not self.location_dest_id:
            raise ValidationError(
                "L emplacement destination est obligatoire pour un Transfert."
            )
        # double vérification (déjà faite dans action_soumettre, mais
        # refaite ici par prudence, au cas où cette méthode serait un jour
        # appelée depuis ailleurs sans être passée par la soumission)

        for ligne in lignes_a_traiter:
            quants = StockQuant.read_group(
                [
                    ("location_id", "=", self.location_id.id),
                    ("product_id", "=", ligne.product_id.id),
                ],
                ["qty"],
                [],
            )
            qty_disponible = quants[0]["qty"] if quants else 0.0
            if ligne.qty_sortie > qty_disponible:
                raise ValidationError(
                    "Quantite insuffisante pour l article %s dans l emplacement %s : "
                    "demande %s, disponible %s."
                    % (
                        ligne.product_id.name,
                        self.location_id.name,
                        ligne.qty_sortie,
                        qty_disponible,
                    )
                )
        # même contrôle de disponibilité que dans _generer_mouvement_sortie
        # (code presque identique — un candidat naturel à factoriser en une
        # seule méthode partagée,
        ########## à refactoriser plus tard ##########
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "internal")], limit=1
        )
        # troisième et dernier type de picking utilisé dans ce fichier :
        # 'internal', pour un mouvement qui reste entièrement DANS
        # l'entreprise (ni sortie vers un client, ni entrée depuis un
        # client)

        picking = StockPicking.create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.location_id.id,
                "location_dest_id": self.location_dest_id.id,
                "origin": self.name,
            }
        )
        # pas de partner_id ici (contrairement aux méthodes entrée/sortie) :
        # un transfert interne n'a pas de client associé — c'est un
        # déplacement d'un emplacement interne A vers un emplacement
        # interne B (pas nécessairement deux entrepôts différents)

        for ligne in lignes_a_traiter:
            StockMove.create(
                {
                    "name": ligne.product_id.name,
                    "product_id": ligne.product_id.id,
                    "product_uom_qty": ligne.qty_sortie,
                    "product_uom": ligne.product_id.uom_id.id,
                    "location_id": self.location_id.id,
                    "location_dest_id": self.location_dest_id.id,
                    "picking_id": picking.id,
                }
            )

        picking.action_confirm()
        picking.action_assign()
        picking.action_done()

        self.picking_id = picking.id

    def _generer_bon_livraison(self):
        """
    Génère le PDF du bon de livraison et l'attache au chatter.

    Utilise le rapport QWeb 'dss_v2.report_bon_livraison_document'
    avec un paperformat explicite pour éviter le bug d'Odoo 10
    où Report.get_pdf() ignore le paperformat du rapport.
        """
        self.ensure_one()
    
        # Récupère le paperformat défini dans report/dss_report.xml
        paperformat = self.env.ref(
            "dss_v2.paperformat_dss_bon_livraison",
            raise_if_not_found=False,
        )
    
        # Prépare le contexte avec le paperformat explicite
        ctx = dict(self.env.context)
        if paperformat:
            ctx["paperformat_id"] = paperformat.id
    
        # Génère le PDF en forçant le paperformat dans le contexte
        pdf_content = self.env["report"].with_context(ctx).get_pdf(
            [self.id],
            "dss_v2.report_bon_livraison_document",
        )
    
        # Crée la pièce jointe
        attachment = self.env["ir.attachment"].create({
            "name": "Bon_Livraison_%s.pdf" % self.name,
            "type": "binary",
            "datas": base64.b64encode(pdf_content),
            "datas_fname": "Bon_Livraison_%s.pdf" % self.name,
            "res_model": "dss.request",
            "res_id": self.id,
        })
    
        # Poste le message dans le chatter
        self.message_post(
            body="Bon de Livraison genere automatiquement.",
            attachment_ids=[attachment.id],
        )

    @api.multi
    def action_imprimer_bon_livraison(self):
        # Impression du Bon de Livraison à la demande : on laisse Odoo
        # construire l'action (report.get_action) pour qu'elle contienne
        # bien l'id de la demande à imprimer (active_ids).
        self.ensure_one()
        return self.env['report'].get_action(
            self, 'dss_v2.report_bon_livraison_document')

    @api.multi
    def action_approuver(self):
        # action d'approbation "directe" : ATTENTION, contrairement à
        # action_valider_magasin, cette méthode ne génère AUCUN mouvement
        # de stock. Elle passe l'état à 'approuve' sans appeler
        # _generer_mouvement_xxx() ni _generer_bon_livraison(). Ce n'est
        # donc PAS un équivalent de action_valider_magasin, malgré un
        # résultat final (state = 'approuve') identique. À clarifier avec
        # l'encadreur : quel bouton appelle réellement cette méthode ?
        for rec in self:
            if rec.state != "valide_magasin":
                raise ValidationError(
                    "La demande doit etre validee par le Stock avant approbation."
                )
            rec.state = "approuve"
            rec.message_post(
                body="<b>%s</b> a approuve definitivement la demande."
                % self.env.user.name
            )

    @api.multi
    def action_rejeter(self):
        # fait passer la demande à l'état 'rejete', QUEL QUE SOIT l'état
        # de départ : contrairement aux actions de validation, cette
        # méthode n'a AUCUN garde-fou d'état (pas de
        # "if rec.state != ..."). Une demande peut donc être rejetée à
        # n'importe quelle étape du circuit. À confirmer si c'est
        # volontaire ou un oubli.

        for rec in self:
            rec.state = "rejete"
            if rec.motif_rejet:
                rec.message_post(
                    body="<b>%s</b> a rejete la demande.<br/>Motif : %s"
                    % (self.env.user.name, rec.motif_rejet)
                )
            else:
                rec.message_post(
                    body="<b>%s</b> a rejete la demande." % self.env.user.name
                )
                # le message posté dans le chatter varie selon qu'un motif
                # de rejet a été renseigné ou non. En pratique, c'est le
                # wizard DssRejetWizard (plus bas) qui remplit motif_rejet
                # AVANT d'appeler cette méthode

    @api.multi
    def action_open_wizard_rejeter(self):
        # ouvre une fenêtre popup (le wizard de rejet), pour demander le
        # motif AVANT d'appeler action_rejeter (qui sera déclenché depuis
        # le wizard)
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Motif du rejet",
            "res_model": "dss.rejet.wizard",  # utilise le modèle dss.rejet.wizard
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    @api.multi
    def action_renvoyer_demandeur(self):
        # renvoie la demande en arrière, à l'état 'brouillon', pour que le
        # demandeur puisse la corriger et la resoumettre
        for rec in self:
            rec.state = "brouillon"  # retour à l'état de brouillon
            rec.message_post(
                body="<b>%s</b> a renvoye la demande au demandeur." % self.env.user.name
            )  # poste un message de retour de la demande au demandeur

    @api.multi
    def action_open_modifier_qte_sortie(self):
        # ouvre le wizard permettant d'ajuster la quantité de sortie

        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Modifier Qte",
            "res_model": "dss.qty.sortie.wizard",  # utilise le modèle dss.qty.sortie.wizard
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    @api.multi
    def action_open_wizard_cloture(self):
        # ouvre le wizard permettant la clôture de la DSS
        # (passage de l'état approuvé à l'état clôturé)
        self.ensure_one()  # s'assurer de ne traiter qu'un seul enregistrement
        return {
            "type": "ir.actions.act_window",
            "name": "Cloturer la demande",
            "res_model": "dss.cloture.wizard",  # utilise le modèle dss.cloture.wizard
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    @api.multi
    def action_open_wizard_chef(self):
        # ouvre le wizard du chef pour la validation DSS
        # À VÉRIFIER AU JOUR 3 : ce modèle 'dss.validation.chef.wizard'
        # n'a pas été vu dans models/__init__.py au Jour 1 — à confirmer
        # qu'il existe bien dans dss_validation_wizard.py
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Confirmation de validation",
            "res_model": "dss.validation.chef.wizard",  # modèle dss.validation.chef.wizard
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    @api.multi
    def action_open_wizard_stock(self):
        # même remarque que ci-dessus : à vérifier si
        # 'dss.validation.stock.wizard' existe réellement
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Confirmation de validation",
            "res_model": "dss.validation.stock.wizard",  # utilise le modèle dss.validation.stock.wizard
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    @api.multi
    def action_open_wizard_approuver(self):
        # ouvre le wizard pour approuver
        # même remarque : à vérifier si 'dss.validation.approuver.wizard'
        # existe réellement
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Confirmation d approbation",
            "res_model": "dss.validation.approuver.wizard",  # modèle pour la validation de DSS
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }


class DssRejetWizard(models.TransientModel):
    # models.TransientModel : un modèle "temporaire", utilisé pour les
    # popups/wizards. Ses données ne sont PAS conservées indéfiniment
    # (Odoo les nettoie automatiquement après un certain temps)
    _name = "dss.rejet.wizard"
    _description = "Assistant de rejet de la demande DSS"

    request_id = fields.Many2one(
        "dss.request", string="Demande DSS", required=True, readonly=True
    )
    # le lien vers la demande à rejeter. readonly=True : l'utilisateur ne
    # choisit pas cette demande lui-même dans le wizard, elle est
    # pré-remplie automatiquement par le contexte (default_request_id) vu
    # dans action_open_wizard_rejeter plus haut

    motif = fields.Text(string="Motif du rejet", required=True)
    # le seul champ que l'utilisateur remplit réellement dans ce wizard :
    # obligatoire (required=True), donc impossible de rejeter sans motif

    @api.multi
    def action_confirmer(self):
        self.ensure_one()
        self.request_id.motif_rejet = self.motif
        # on reporte le motif saisi dans le wizard vers le champ
        # motif_rejet de la VRAIE demande DSS (request_id)
        self.request_id.action_rejeter()
        # puis on appelle la méthode de rejet déjà vue plus haut : le
        # wizard ne fait donc que collecter le motif avant de déclencher
        # l'action réelle
        return {"type": "ir.actions.act_window_close"}


class ProductProduct(models.Model):
    _inherit = "product.product"
    # on N'UTILISE PAS _name ici : on utilise _inherit SEUL sur un modèle
    # qui existe déjà (product.product, le modèle standard des articles
    # Odoo). C'est de l'HÉRITAGE PAR EXTENSION : on ne crée pas un nouveau
    # modèle, on ajoute/modifie du comportement sur un modèle existant

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """
        Surcharge de name_search() pour filtrer les articles proposés
        selon l'emplacement passé dans le contexte ('dss_location_id').

        Si ce contexte est présent, seuls les articles ayant un stock
        strictement positif (qty > 0) à cet emplacement sont proposés
        dans les champs Many2one vers product.product.

        Si le contexte est absent, comportement standard d'Odoo
        (tous les articles sont proposés).
        """
        # cette méthode est appelée AUTOMATIQUEMENT par Odoo chaque fois
        # qu'un utilisateur tape du texte dans un champ "Article"
        args = args or []
        # si on ne nous donne aucune liste de filtres, on en crée une
        # vide pour pouvoir la compléter plus loin
        location_id = self._context.get("dss_location_id")
        # on regarde si la vue en cours a précisé un emplacement
        # (context.get("dss_location_id")) — l'emplacement où doit se
        # trouver l'article recherché

        if location_id:
            # si on sait dans quel emplacement on travaille, on demande
            # quels articles sont réellement disponibles à cet endroit :
            # on interroge l'inventaire d'Odoo (stock.quant) pour cet
            # emplacement, en demandant, pour chaque article, combien il
            # y en a en stock
            Quant = self.env["stock.quant"]
            quants = Quant.read_group(
                [("location_id", "=", location_id)],
                ["product_id", "qty"],
                ["product_id"],
            )
            product_ids = []
            for q in quants:
                if q["product_id"] and q["qty"] > 0:
                    product_ids.append(q["product_id"][0])
            args = args + [("id", "in", product_ids)]
        return super(ProductProduct, self).name_search(
            name=name, args=args, operator=operator, limit=limit
        )
