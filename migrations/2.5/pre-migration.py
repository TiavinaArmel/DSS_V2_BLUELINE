# -*- coding: utf-8 -*-
"""Transfère les anciens services RH vers le modèle DSS autonome."""


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


def _ensure_column(cr, table_name, column_name, definition):
    if column_name not in _columns(cr, table_name):
        cr.execute(
            "ALTER TABLE %s ADD COLUMN %s %s"
            % (table_name, column_name, definition)
        )


def _prepare_service_tables(cr):
    """Crée les tables minimales avant que le registre Odoo ajoute les modèles."""
    cr.execute(
        """
        CREATE TABLE IF NOT EXISTS dss_service (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL,
            dss_chef_id INTEGER,
            active BOOLEAN NOT NULL DEFAULT TRUE
        )
        """
    )
    cr.execute("CREATE SEQUENCE IF NOT EXISTS dss_service_id_seq")
    cr.execute(
        "ALTER SEQUENCE dss_service_id_seq OWNED BY dss_service.id"
    )
    cr.execute(
        """
        ALTER TABLE dss_service
        ALTER COLUMN id SET DEFAULT nextval('dss_service_id_seq')
        """
    )
    _ensure_column(cr, "dss_service", "name", "VARCHAR")
    _ensure_column(cr, "dss_service", "dss_chef_id", "INTEGER")
    _ensure_column(
        cr, "dss_service", "active", "BOOLEAN NOT NULL DEFAULT TRUE"
    )
    cr.execute("UPDATE dss_service SET active = TRUE WHERE active IS NULL")
    cr.execute(
        "ALTER TABLE dss_service ALTER COLUMN active SET DEFAULT TRUE"
    )
    cr.execute(
        """
        CREATE TABLE IF NOT EXISTS dss_service_demandeur_rel (
            service_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (service_id, user_id)
        )
        """
    )


def _copy_services(cr):
    """Copie les services et leurs demandeurs sans écraser une configuration existante."""
    if not _table_exists(cr, "hr_department") or not _table_exists(
        cr, "dss_request"
    ):
        return

    department_columns = _columns(cr, "hr_department")
    chef_column = (
        "dss_chef_id" if "dss_chef_id" in department_columns else "NULL"
    )
    cr.execute(
        "SELECT id, name, %s FROM hr_department ORDER BY id" % chef_column
    )
    departments = cr.fetchall()
    id_map = {}

    for department_id, name, chef_id in departments:
        cr.execute(
            "SELECT name FROM dss_service WHERE id = %s",
            (department_id,),
        )
        existing = cr.fetchone()
        if existing and existing[0] == name:
            service_id = department_id
            if chef_id:
                cr.execute(
                    """
                    UPDATE dss_service
                       SET dss_chef_id = COALESCE(dss_chef_id, %s)
                     WHERE id = %s
                    """,
                    (chef_id, service_id),
                )
        else:
            if existing:
                cr.execute(
                    """
                    INSERT INTO dss_service (name, dss_chef_id, active)
                    VALUES (%s, %s, TRUE)
                    RETURNING id
                    """,
                    (name, chef_id),
                )
                service_id = cr.fetchone()[0]
            else:
                cr.execute(
                    """
                    INSERT INTO dss_service (id, name, dss_chef_id, active)
                    VALUES (%s, %s, %s, TRUE)
                    RETURNING id
                    """,
                    (department_id, name, chef_id),
                )
                service_id = cr.fetchone()[0]

        id_map[department_id] = service_id
        cr.execute(
            """
            UPDATE dss_request
               SET service_demandeur_id = %s
             WHERE service_demandeur_id = %s
            """,
            (service_id, department_id),
        )

    if _table_exists(cr, "hr_department_res_users_rel"):
        relation_columns = _columns(cr, "hr_department_res_users_rel")
        if set(("hr_department_id", "res_users_id")).issubset(
            relation_columns
        ):
            for department_id, service_id in id_map.items():
                cr.execute(
                    """
                    INSERT INTO dss_service_demandeur_rel (service_id, user_id)
                    SELECT %s, res_users_id
                      FROM hr_department_res_users_rel
                     WHERE hr_department_id = %s
                       AND NOT EXISTS (
                           SELECT 1
                             FROM dss_service_demandeur_rel AS existing
                            WHERE existing.service_id = %s
                              AND existing.user_id =
                                    hr_department_res_users_rel.res_users_id
                       )
                    """,
                    (service_id, department_id, service_id),
                )

    # Une ancienne référence sans département correspondant ne peut pas être convertie.
    cr.execute(
        """
        UPDATE dss_request AS request
           SET service_demandeur_id = NULL
         WHERE request.service_demandeur_id IS NOT NULL
           AND NOT EXISTS (
               SELECT 1
                 FROM dss_service AS service
                WHERE service.id = request.service_demandeur_id
           )
        """
    )

    # Les identifiants copiés ne doivent pas entrer en collision avec les prochains services.
    cr.execute(
        """
        SELECT setval(
            pg_get_serial_sequence('dss_service', 'id'),
            GREATEST(COALESCE(MAX(id), 1), 1),
            MAX(id) IS NOT NULL
        )
          FROM dss_service
        """
    )


def _archive_old_department_views(cr):
    """Désactive les vues RH DSS qui pointent vers des champs désormais supprimés."""
    if not _table_exists(cr, "ir_ui_view") or not _table_exists(
        cr, "ir_model_data"
    ):
        return

    cr.execute(
        """
        UPDATE ir_ui_view AS target_view
           SET active = FALSE
          FROM ir_model_data AS data
         WHERE data.module = 'dss_v2'
           AND data.model = 'ir.ui.view'
           AND data.name IN (
               'view_dss_department_form',
               'view_dss_department_tree'
           )
           AND data.res_id = target_view.id
        """
    )


def migrate(cr, installed_version):
    """Prépare les données avant le changement du champ vers dss.service."""
    _prepare_service_tables(cr)
    _copy_services(cr)
    _archive_old_department_views(cr)
