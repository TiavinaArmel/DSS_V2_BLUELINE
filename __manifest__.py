{
  "name": "DSS V2 - Demande de Sortie de Stock",
  "version": "2.5",
  "depends": [
    "web",
    "stock",
    "mail",
    "hr"
  ],
  "author": "Tiavina Armel",
  "category": "Inventory",
  "description": "Digitalisation des Demandes de Sortie de Stock (DSS) selon cahier des charges",
  "data": [
    "security/dss_security.xml",
    "security/ir.model.access.csv",
    "data/dss_sequence.xml",
    "data/dss_mail_templates.xml",
    "data/dss_department_data.xml",
    "views/dss_qty_sortie_wizard_views.xml",
    "views/dss_rejet_wizard_views.xml",
    "views/dss_cloture_wizard_views.xml",
    "views/dss_validation_wizard_views.xml",
    "views/dss_request_search_views.xml",
    "views/dss_request_views.xml",
    "views/assets_backend.xml",
    "views/dss_menu.xml",
    "views/dss_group_menus.xml",
    "views/dss_request_display_views.xml",
    "report/dss_report.xml"
  ],
  "application": True,
  "installable": True,
  "tests": [
    "tests/test_dss_notifications.py",
    "tests/test_dss_stock_location.py",
    "tests/test_dss_closure.py"
  ]
}