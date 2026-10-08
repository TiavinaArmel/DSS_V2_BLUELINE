# -*- coding: utf-8 -*-

import base64

from odoo import models, api


class DssRequestBonLivraison(models.Model):
    _inherit = "dss.request"

    def _generer_bon_livraison(self):
        """
    Génère le PDF du bon de livraison et l'attache au chatter.

    Utilise le rapport QWeb 'dss_v2.report_bon_livraison_document'
    avec un paperformat explicite pour éviter le bug d'Odoo 10
    où Report.get_pdf() ignore le paperformat du rapport.
        """
        self.ensure_one()

        paperformat = self.env.ref(
            "dss_v2.paperformat_dss_a5",
            raise_if_not_found=False,
        )

        ctx = dict(self.env.context)
        if paperformat:
            ctx["paperformat_id"] = paperformat.id

        pdf_content = self.env["report"].with_context(ctx).get_pdf(
            [self.id],
            "dss_v2.report_bon_livraison_document",
        )

        attachment_name = "Bon_Livraison_%s.pdf" % self.name
        attachment_values = {
            "name": "Bon_Livraison_%s.pdf" % self.name,
            "type": "binary",
            "datas": base64.b64encode(pdf_content),
            "datas_fname": attachment_name,
            "res_model": "dss.request",
            "res_id": self.id,
        }
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
            attachment.write(attachment_values)
        else:
            attachment = attachment_model.create(attachment_values)
            self.message_post(
                body="Bon de Livraison genere automatiquement.",
                attachment_ids=[attachment.id],
            )

    @api.multi
    def action_imprimer_bon_livraison(self):
        self.ensure_one()
        if self.state == "approuve":
            self._generer_bon_livraison()
        return self.env['report'].get_action(
            self, 'dss_v2.report_bon_livraison_document')