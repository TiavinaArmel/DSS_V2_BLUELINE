# -*- coding: utf-8 -*-
# Chargement des fichiers Python du dossier models/.
# L'ordre respecte les dépendances entre modèles.
#
# Depuis la version 2.16, les deux extensions suivantes ne sont PLUS chargées :
#   - stock_picking.py    : second circuit DSS sur le transfert de stock,
#                           jamais utilisé (aucune vue, aucun menu, 0 picking
#                           concerné) et porteur d'un risque de blocage de
#                           l'application Stock ;
#   - product_template.py : champ « Quantité standard DSS », qui n'existait que
#                           pour ce circuit.
# Les fichiers restent sur le disque, vidés de leur code et documentés, en
# attendant leur suppression physique. Ne pas réactiver ces imports sans avoir
# relu leur en-tête.
from . import product_product  # filtre de recherche des articles en stock
from . import dss_service  # services du workflow DSS
from . import dss_request  # modèles principaux DSS
from . import dss_request_line  # lignes des demandes DSS
from . import dss_request_stock  # génération des mouvements de stock
from . import dss_request_bon_livraison  # génération du bon de livraison
from . import dss_request_workflow  # actions du workflow DSS
from . import dss_rejet_wizard  # wizard de rejet DSS
from . import dss_qty_sortie_wizard  # wizard de quantité à sortir
from . import dss_cloture_wizard  # wizard de clôture
from . import dss_request_display  # modèle d'affichage
from . import dss_validation_wizard  # wizards de validation
from . import dss_notification  # notifications métier DSS
