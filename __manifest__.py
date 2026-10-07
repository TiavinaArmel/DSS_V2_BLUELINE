{
    # Nom lisible du module affiché dans la liste des applications Odoo
    "name": "DSS V2 - Demande de Sortie de Stock",

    # Version du module DSS
    "version": "2.1",

    # Dépendances Odoo :
    # - web   : assets et rapports QWeb
    # - stock : mouvements de stock (Inventory)
    # - mail  : chatter et notifications internes
    "depends": ["web", "stock", "mail"],

    # Auteur du module
    "author": "Tiavina Armel",

    # Catégorie Odoo (ici Inventory)
    "category": "Inventory",

    # Description fonctionnelle du module
    "description": "Digitalisation des Demandes de Sortie de Stock (DSS) selon cahier des charges",

    # Fichiers XML/CSV chargés par Odoo dans l'ordre :
    # sécurité → données → vues → menus → rapport
    "data": [
        # Sécurité : groupes et droits d'accès
        "security/dss_security.xml",
        "security/ir.model.access.csv",

        # Données techniques : séquence de numérotation DSS 
        #Format DSS/XX/XX/XXXX
        "data/dss_sequence.xml",

        # Vues des assistants (wizards)
        "views/dss_qty_sortie_wizard_views.xml",     # quantité à sortir
        "views/dss_rejet_wizard_views.xml",          # rejet de la DSS
        "views/dss_cloture_wizard_views.xml",        # clôture de la DSS
        "views/dss_validation_wizard_views.xml",     # validation de la DSS

        # Vues principales de la DSS
        "views/dss_request_views.xml",

        # Menus et actions
        "views/dss_menu.xml",

        # Vues d'affichage
        "views/dss_request_display_views.xml",

        # Rapport PDF
        "report/dss_report.xml",
    ],

    # Le module apparaît comme une application dans Odoo
    "application": True,

    # Le module peut être installé
    "installable": True,
}