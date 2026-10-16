# -*- coding: utf-8 -*-

import base64

from odoo import models, api


class DssRequestBonLivraison(models.Model):
    """Ajoute à la demande DSS la génération et l'impression du bon PDF."""

    _inherit = "dss.request"

    def _generer_bon_livraison(self):
        """
    Génère le PDF du bon de livraison et l'attache au chatter.

    Utilise le rapport QWeb 'dss_v2.report_bon_livraison_document'
    avec un paperformat explicite pour éviter le bug d'Odoo 10
    où Report.get_pdf() ignore le paperformat du rapport.
        """
        # ensure_one() garantit qu'un seul bon PDF est généré pour cet appel.
        self.ensure_one()

        # L'identifiant externe peut manquer lors d'une installation ou d'une migration incomplète.
        paperformat = self.env.ref(
            "dss_v2.paperformat_dss_a5",
            raise_if_not_found=False,
        )

        # Copie le contexte Odoo pour ajouter une option sans modifier celui de l'appelant.
        ctx = dict(self.env.context)
        if paperformat:
            # Le moteur de rapport lit cet identifiant pour choisir le format de page.
            ctx["paperformat_id"] = paperformat.id

        # get_pdf() rend le rapport QWeb en PDF pour l'identifiant de demande fourni.
        pdf_content = self.env["report"].with_context(ctx).get_pdf(
            [self.id],
            "dss_v2.report_bon_livraison_document",
        )

        # Les valeurs associent le contenu binaire au modèle et à son enregistrement.
        attachment_name = "Bon_Livraison_%s.pdf" % self.name
        attachment_values = {
            "name": "Bon_Livraison_%s.pdf" % self.name,
            "type": "binary",
            "datas": base64.b64encode(pdf_content),
            "datas_fname": attachment_name,
            "res_model": "dss.request",
            "res_id": self.id,
        }
        # Recherche un ancien PDF du même nom pour le remplacer au lieu de le dupliquer.
        attachment_model = self.env["ir.attachment"]
        attachment = attachment_model.search(
            [
                ("name", "=", attachment_name),
                ("res_model", "=", "dss.request"),
                ("res_id", "=", self.id),
            ],
            limit=1,
        )
        if attachment:
            # write() met à jour l'attachement existant avec le nouveau fichier.
            attachment.write(attachment_values)
        else:
            # create() enregistre le PDF ; message_post() le rend visible dans le chatter.
            attachment = attachment_model.create(attachment_values)
            self.message_post(
                body="Bon de Livraison genere automatiquement.",
                attachment_ids=[attachment.id],
            )

    @api.multi
    def action_imprimer_bon_livraison(self):
        """Régénère le bon si la demande est approuvée, puis retourne l'action d'impression."""
        self.ensure_one()
        # Le PDF n'est produit que pour une demande ayant atteint l'état approuvé.
        if self.state == "approuve":
            self._generer_bon_livraison()
        # get_action() fournit au client Odoo l'action qui ouvre ou télécharge le rapport.
        return self.env['report'].get_action(
            self, 'dss_v2.report_bon_livraison_document')