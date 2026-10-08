# -*- coding: utf-8 -*-
# Chargement des fichiers Python du dossier models/.
# L'ordre respecte les dépendances entre modèles.
from . import stock_picking  # héritage de stock.picking
from . import product_template  # héritage de product.template
from . import product_product  # filtre de recherche des articles en stock
from . import dss_request  # modèles principaux DSS
from . import dss_request_line  # lignes des demandes DSS
from . import dss_rejet_wizard  # wizard de rejet DSS
from . import dss_qty_sortie_wizard  # wizard de quantité à sortir
from . import dss_cloture_wizard  # wizard de clôture
from . import dss_request_display  # modèle d'affichage
from . import dss_validation_wizard  # wizards de validation
