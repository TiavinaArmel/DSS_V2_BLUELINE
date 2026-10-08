# Renomme l'identifiant du format sans creer un second enregistrement.
def migrate(cr, installed_version):
    cr.execute(
        """
        UPDATE ir_model_data AS ancien
           SET name = 'paperformat_dss_a5'
         WHERE ancien.module = 'dss_v2'
           AND ancien.name = 'paperformat_dss_a4'
           AND ancien.model = 'report.paperformat'
           AND NOT EXISTS (
                SELECT 1
                  FROM ir_model_data AS nouveau
                 WHERE nouveau.module = ancien.module
                   AND nouveau.name = 'paperformat_dss_a5'
           )
        """
    )