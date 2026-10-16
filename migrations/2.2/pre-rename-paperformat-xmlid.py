# Renomme l'identifiant du format sans creer un second enregistrement.
def migrate(cr, installed_version):
    """Met à jour l'identifiant externe du format A5 lors de la migration 2.2."""
    # cr est le curseur PostgreSQL fourni par Odoo pour exécuter la migration.
    # La requête conserve l'enregistrement existant au lieu d'en créer un autre.
    cr.execute(
        """
      -- Renomme l'identifiant externe uniquement s'il correspond à l'ancien format DSS.
        UPDATE ir_model_data AS ancien
           SET name = 'paperformat_dss_a5'
         WHERE ancien.module = 'dss_v2'
           AND ancien.name = 'paperformat_dss_a4'
           AND ancien.model = 'report.paperformat'
           -- Évite un conflit si le nouvel identifiant existe déjà dans ce module.
           AND NOT EXISTS (
                SELECT 1
                  FROM ir_model_data AS nouveau
                 WHERE nouveau.module = ancien.module
                   AND nouveau.name = 'paperformat_dss_a5'
           )
        """
    )