# -*- coding: utf-8 -*-
"""Ajoute le propriétaire des DSS et impose une affiliation par utilisateur."""

import logging


_logger = logging.getLogger(__name__)


def _table_exists(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", ("public.%s" % table_name,))
    return bool(cr.fetchone()[0])


def _columns(cr, table_name):
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


def _remove_duplicate_affiliations(cr):
    """Garde, pour chaque utilisateur, l'affiliation au service au plus petit ID."""
    relation_table = "dss_service_demandeur_rel"
    if not _table_exists(cr, relation_table):
        raise RuntimeError(
            "Migration DSS 2.6 impossible : la table %s est absente."
            % relation_table
        )

    columns = _columns(cr, relation_table)
    if not set(("service_id", "user_id")).issubset(columns):
        raise RuntimeError(
            "Migration DSS 2.6 impossible : colonnes service_id/user_id absentes."
        )

    cr.execute(
        """
        WITH affiliations_classees AS (
            SELECT ctid,
                   ROW_NUMBER() OVER (
                       PARTITION BY user_id
                       ORDER BY service_id, ctid
                   ) AS rang
              FROM dss_service_demandeur_rel
        )
        DELETE FROM dss_service_demandeur_rel AS affiliation
         USING affiliations_classees
         WHERE affiliation.ctid = affiliations_classees.ctid
           AND affiliations_classees.rang > 1
        """
    )
    if cr.rowcount:
        _logger.warning(
            "DSS migration 2.6: removed %s duplicate service affiliations; "
            "the affiliation with the smallest service_id was kept.",
            cr.rowcount,
        )

    cr.execute(
        """
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'dss_service_demandeur_rel_user_id_uniq'
           AND conrelid =
               'public.dss_service_demandeur_rel'::regclass
        """
    )
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE dss_service_demandeur_rel
            ADD CONSTRAINT dss_service_demandeur_rel_user_id_uniq
            UNIQUE (user_id)
            """
        )


def _backfill_request_owner(cr):
    """Renseigne le propriétaire depuis le signataire ou le créateur historique."""
    if not _table_exists(cr, "dss_request"):
        raise RuntimeError(
            "Migration DSS 2.6 impossible : la table dss_request est absente."
        )

    columns = _columns(cr, "dss_request")
    required_columns = set(("signataire_demandeur_id", "create_uid"))
    if not required_columns.issubset(columns):
        raise RuntimeError(
            "Migration DSS 2.6 impossible : signataire ou créateur historique "
            "introuvable dans dss_request."
        )

    if "demandeur_id" not in columns:
        cr.execute(
            """
            ALTER TABLE dss_request
            ADD COLUMN demandeur_id INTEGER
            """
        )
    cr.execute(
        """
        UPDATE dss_request
           SET demandeur_id =
               COALESCE(signataire_demandeur_id, create_uid)
         WHERE demandeur_id IS NULL
           AND EXISTS (
               SELECT 1
                 FROM res_users
                WHERE res_users.id =
                      COALESCE(dss_request.signataire_demandeur_id,
                               dss_request.create_uid)
           )
        """
    )

    cr.execute(
        """
        SELECT id
          FROM dss_request
         WHERE demandeur_id IS NULL
         ORDER BY id
        """
    )
    missing_owner_ids = [row[0] for row in cr.fetchall()]
    if missing_owner_ids:
        raise RuntimeError(
            "Migration DSS 2.6 interrompue : aucun propriétaire récupérable "
            "pour les demandes DSS %s."
            % ", ".join(str(request_id) for request_id in missing_owner_ids)
        )

    # Pour les anciennes demandes sans signataire, le créateur est la seule
    # identité conservée en base; les DSS créées par automation doivent être
    # vérifiées et corrigées par un administrateur si elles étaient au nom d'un tiers.
    cr.execute(
        """
        SELECT id
          FROM dss_request
         WHERE signataire_demandeur_id IS NULL
           AND create_uid = 1
         ORDER BY id
        """
    )
    system_created_ids = [row[0] for row in cr.fetchall()]
    if system_created_ids:
        _logger.warning(
            "DSS migration 2.6: owner could not be inferred from a submission "
            "signer for system-created requests %s; create_uid was used. "
            "Review these requests and correct demandeur_id if needed.",
            ", ".join(str(request_id) for request_id in system_created_ids),
        )

    cr.execute(
        """
        ALTER TABLE dss_request
        ALTER COLUMN demandeur_id SET NOT NULL
        """
    )


def migrate(cr, installed_version):
    """Nettoie les affiliations, ajoute leur unicité et prépare demandeur_id."""
    _remove_duplicate_affiliations(cr)
    _backfill_request_owner(cr)
