# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import html_escape
from odoo.tools.float_utils import float_compare

"""
Ce fichier permet au magasin d'ajuster les quantités avant la validation finale.

POURQUOI :
    Parce que le magasin peut constater que :
        - le stock réel diffère du stock demandé,
        - il faut sortir moins que demandé,
        - il faut retourner plus que prévu,
        - il faut tracer ces changements.
"""


class DssQtySortieWizard(models.TransientModel):

    _name = "dss.qty.sortie.wizard"
    _description = "Assistant de saisie des quantites"

    request_id = fields.Many2one(
        "dss.request", string="Demande DSS", required=True, readonly=True
    )
    line_ids = fields.One2many(
        "dss.qty.sortie.wizard.line", "wizard_id", string="Articles"
    )

    # One2many pointe vers dss.qty.sortie.wizard.line.
    # One2many permet au wizard d'accéder à plusieurs enregistrements
    # de dss.qty.sortie.wizard.line liés à ce wizard grâce au champ wizard_id.

    @api.model
    def default_get(self, fields_list):
        # self ici = DssQtySortieWizard.
        # fields_list = liste des champs demandés par Odoo à pré-remplir
        # (elle est fournie par Odoo, pas par dss.request).

        # Méthode appelée automatiquement par Odoo à l'ouverture du wizard.
        res = super(DssQtySortieWizard, self).default_get(fields_list)
        # Appel du modèle parent pour récupérer la structure de base
        # du pré-remplissage.

        request_id = self.env.context.get("default_request_id") or self.env.context.get(
            "active_id"
        )
        # Deux façons de récupérer l'id de la demande pour pré-remplir
        # les champs du wizard :
        #   - default_request_id : id passé par le bouton dans la vue
        #   - active_id          : enregistrement courant sélectionné

        if request_id:
            # Si l'id de la demande est trouvé
            request = self.env["dss.request"].browse(request_id)
            # On charge la DSS correspondante
            lines = []  # Liste vide pour contenir les lignes de la demande
            for line in request.line_ids:
                lines.append(
                    (
                        0,
                        0,
                        {
                            "request_line_id": line.id,
                            "product_id": line.product_id.id,
                            "qty_demandee": line.qty_demandee,
                            "qty_sortie": line.qty_sortie,
                            "qty_retour": line.qty_retour,
                            "motif_ecart": line.motif_ecart,
                            "qty_sortie_initiale": line.qty_sortie,
                            "qty_retour_initiale": line.qty_retour,
                            "motif_ecart_initial": line.motif_ecart,
                        },
                    )
                    # (0, 0, {...}) = créer une nouvelle ligne One2many
                )
            res["request_id"] = request_id
            res["line_ids"] = lines
        return res
        # Sinon, on retourne simplement le résultat du pré-remplissage
        # par défaut.

    @api.multi
    def action_valider(self):
        # self ici = DssQtySortieWizard.
        # Cette méthode compare les anciennes valeurs aux nouvelles,
        # puis poste un message dans le chatter.

        self.ensure_one()  # S'assurer de ne traiter qu'un seul enregistrement
        changements = []  # Pour stocker la liste des changements détectés
        lignes_modifiees = False
        for line in self.line_ids:
            parties = []
            # Comparaison entre l'ancienne et la nouvelle Quantité de sortie
            ancienne_sortie = line.request_line_id.qty_sortie
            nouvelle_sortie = line.qty_sortie
            if ancienne_sortie != nouvelle_sortie:
                parties.append(
                    u"Qte Sortie %s \u2192 %s" % (ancienne_sortie, nouvelle_sortie)
                )
            # Comparaison entre l'ancienne et la nouvelle Quantité de retour
            ancienne_retour = line.request_line_id.qty_retour
            nouvelle_retour = line.qty_retour
            if ancienne_retour != nouvelle_retour:
                parties.append(
                    u"Qte Retour %s \u2192 %s" % (ancienne_retour, nouvelle_retour)
                )

            ligne_modifiee = (
                float_compare(
                    nouvelle_sortie,
                    line.qty_sortie_initiale,
                    precision_digits=2,
                ) != 0
                or float_compare(
                    nouvelle_retour,
                    line.qty_retour_initiale,
                    precision_digits=2,
                ) != 0
                or line.motif_ecart != line.motif_ecart_initial
            )

            # Une ligne non touchée suit automatiquement la demande initiale.
            if not ligne_modifiee:
                nouvelle_sortie = line.qty_demandee
                nouvelle_retour = 0.0
            else:
                lignes_modifiees = True

            # Toute sortie différente de la demande initiale doit être
            # justifiée avant l'écriture dans la ligne DSS.
            sortie_differente = float_compare(
                nouvelle_sortie,
                line.qty_demandee,
                precision_digits=2,
            ) != 0
            if ligne_modifiee and sortie_differente and not line.motif_ecart:
                raise ValidationError(
                    u"Le motif de l'écart est obligatoire pour l'article %s."
                    % line.product_id.name
                )

            if line.motif_ecart != line.request_line_id.motif_ecart:
                parties.append(u"Motif de l'écart modifié")

            line.request_line_id.write(
                {
                    "qty_sortie": nouvelle_sortie,
                    "qty_retour": nouvelle_retour,
                    "motif_ecart": line.motif_ecart,
                }
            )
            # Si des changements ont été détectés
            if parties:  # parties n'est pas vide → il y a des changements
                details = (
                    u"Quantité demandée : %s, Quantité sortie : %s, "
                    u"Motif de modification : %s"
                    % (
                        line.qty_demandee,
                        nouvelle_sortie,
                        html_escape(line.motif_ecart or u"Non renseigné").replace(
                            "\n", "<br/>"
                        ),
                    )
                )
                if ancienne_retour != nouvelle_retour:
                    details += u", Quantité retournée : %s" % nouvelle_retour
                changements.append(
                    u"\u2022 Article %s : %s"
                    % (
                        html_escape(line.product_id.name or u""),
                        details,
                    )
                )  # On ajoute un message décrivant le changement
                # dans la liste changements[] 
                # On écrit les nouvelles valeurs dans la VRAIE ligne de la DSS

        # La validation de ce wizard constitue l'intervention explicite du
        # magasinier, même si les valeurs saisies restent identiques.
        self.request_id.is_qty_modified = lignes_modifiees

        if changements:
            # Si la liste des changements n'est pas vide
            message = (
                u"Le Responsable Stock %s a modifi\u00e9 les quantit\u00e9s.<br/><br/>%s"
                % (
                    html_escape(self.env.user.name or u""),
                    u"<br/>".join(changements),
                )
            )
            self.request_id.message_post(body=message)
            # On poste un message du type :
            # "Le Responsable Stock XXXX a modifié les quantités ..."
        return {"type": "ir.actions.act_window_close"}


class DssQtySortieWizardLine(models.TransientModel):
    # Ligne du wizard de saisie des quantités.
    # Représente une COPIE d'une ligne de la DSS, manipulable dans la popup.
    _name = "dss.qty.sortie.wizard.line"
    _description = "Ligne de assistant de saisie des quantites"

    # Champ de relation Many2one qui pointe vers le modèle
    # "dss.qty.sortie.wizard" (clé étrangère).
    # ondelete='cascade' : si le wizard est supprimé, ses lignes le sont aussi.
    wizard_id = fields.Many2one(
        "dss.qty.sortie.wizard", string="Assistant", ondelete="cascade"
    )

    # Clé étrangère provenant du modèle dss.request.line.
    # readonly=True : l'utilisateur ne peut pas changer la ligne DSS liée.
    # required=True : obligatoire.
    request_line_id = fields.Many2one(
        "dss.request.line", string="Ligne DSS", readonly=True, required=True
    )

    # Clé étrangère par référence au modèle standard Odoo product.product.
    # readonly=True : l'article ne peut pas être modifié dans le wizard.
    product_id = fields.Many2one("product.product", string="Article", readonly=True)

    # Quantité demandée (non modifiable dans le wizard).
    qty_demandee = fields.Float(string="Qte Demandee", readonly=True)

    # Quantité de sortie (modifiable par le Magasin).
    qty_sortie = fields.Float(string="Qte Sortie")

    # Quantité de retour (modifiable par le Magasin).
    qty_retour = fields.Float(string="Qte Retour")

    # Motif propre à la ligne lorsque la quantité sortie diffère de la
    # quantité demandée.
    motif_ecart = fields.Text(string="Motif de l'écart")
    qty_sortie_initiale = fields.Float(string="Qte Sortie initiale")
    qty_retour_initiale = fields.Float(string="Qte Retour initiale")
    motif_ecart_initial = fields.Text(string="Motif initial")
