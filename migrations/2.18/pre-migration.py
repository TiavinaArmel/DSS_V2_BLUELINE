# -*- coding: utf-8 -*-
"""Normalise les BCI et vérifie les doublons avant la contrainte d'unicité.

CONTEXTE
Le modèle dss.request porte une contrainte SQL d'unicité sur `bci`
(_sql_constraints « dss_request_bci_unique ») et un contrôle Python équivalent.
Odoo crée cette contrainte lors de la mise à jour du module.

LE RISQUE
Si deux demandes partagent déjà le même BCI dans une base ancienne, PostgreSQL
refuse la création de l'index unique et la mise à jour du module échoue avec une
erreur technique peu lisible.

CE QUE FAIT CE SCRIPT
  1. Il retire les espaces autour des BCI («  ABC » et « ABC  » deviennent
     « ABC »), ce qui correspond au nettoyage déjà appliqué par write().
  2. Il transforme les BCI vides en NULL, pour que la contrainte d'unicité ne
     les considère pas comme une valeur répétée (PostgreSQL autorise plusieurs
     NULL dans un index unique).
  3. Il liste les doublons restants et INTERROMPT la migration avec un message
     explicite qui nomme les demandes concernées.

CE QU'IL NE FAIT PAS
Il ne supprime ni ne modifie aucune demande. Choisir laquelle garde un BCI est
une décision métier qui doit être prise par un administrateur, pas par un
script exécuté automatiquement pendant une mise à jour.
"""

import logging


_logger = logging.getLogger(__name__)


def _table_exists(cr, table_name):
    """Indique si une table existe dans le schéma public."""
    # to_regclass() renvoie NULL si l'objet n'existe pas, sans lever d'erreur.
    cr.execute("SELECT to_regclass(%s)", ("public.%s" % table_name,))
    return bool(cr.fetchone()[0])


def _columns(cr, table_name):
    """Retourne l'ensemble des colonnes d'une table."""
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = %s
        """,
        (table_name,),
    )
    return set(row[0] for row in cr.fetchall())


def _normalize_bci(cr):
    """Retire les espaces autour des BCI existants."""
    # btrim() supprime les espaces en début et en fin de chaîne.
    # La condition « bci <> btrim(bci) » cible uniquement les valeurs à corriger,
    # ce qui évite d'écrire inutilement sur toutes les lignes.
    cr.execute(
        """
        UPDATE dss_request
           SET bci = btrim(bci)
         WHERE bci IS NOT NULL
           AND bci <> btrim(bci)
        """
    )
    if cr.rowcount:
        _logger.warning(
            "DSS migration 2.18: %s BCI normalisé(s) (espaces retirés).",
            cr.rowcount,
        )

    # Une chaîne vide n'est pas une valeur métier : on la remplace par NULL.
    # Sinon la contrainte unique considérerait deux BCI vides comme un doublon.
    cr.execute(
        """
        UPDATE dss_request
           SET bci = NULL
         WHERE bci IS NOT NULL
           AND btrim(bci) = ''
        """
    )
    if cr.rowcount:
        _logger.warning(
            "DSS migration 2.18: %s BCI vide(s) converti(s) en NULL.",
            cr.rowcount,
        )


def _report_duplicates(cr):
    """Interrompt la migration si des BCI restent en doublon."""
    # Groupement sur la valeur nettoyée : c'est exactement ce que comparera
    # l'index unique. string_agg() rassemble les identifiants concernés pour
    # que le message soit directement exploitable.
    cr.execute(
        """
        SELECT btrim(bci) AS bci,
               count(*) AS total,
               string_agg(id::text, ', ' ORDER BY id) AS ids
          FROM dss_request
         WHERE bci IS NOT NULL
           AND btrim(bci) <> ''
         GROUP BY 1
        HAVING count(*) > 1
         ORDER BY 1
        """
    )
    duplicates = cr.fetchall()
    if not duplicates:
        _logger.info(
            "DSS migration 2.18: aucun doublon de BCI, la contrainte d'unicité "
            "peut être créée."
        )
        return

    # Message volontairement lisible : il doit permettre à un administrateur de
    # corriger les données sans avoir à déchiffrer une erreur PostgreSQL.
    details = "\n".join(
        u"  - BCI « %s » : %s demandes (ids %s)" % (bci, total, ids)
        for bci, total, ids in duplicates
    )
    raise RuntimeError(
        u"Migration DSS 2.18 interrompue : des BCI en doublon empêchent la "
        u"création de la contrainte d'unicité.\n%s\n"
        u"Corrigez ces demandes (champ BCI) puis relancez la mise à jour. "
        u"Le script n'a volontairement rien supprimé." % details
    )


def migrate(cr, installed_version):
    """Point d'entrée appelé par Odoo avant la mise à jour du module."""
    # Sur une installation neuve, aucune migration n'est exécutée par Odoo.
    # La sécurité ci-dessous protège d'un appel direct sur une base incomplète.
    if not _table_exists(cr, "dss_request"):
        return
    if "bci" not in _columns(cr, "dss_request"):
        return

    _normalize_bci(cr)
    _report_duplicates(cr)
