# -*- coding: utf-8 -*-
# Coded by German Ponce Dominguez 
#     ▬▬▬▬▬.◙.▬▬▬▬▬  
#       ▂▄▄▓▄▄▂  
#    ◢◤█▀▀████▄▄▄▄▄▄ ◢◤  
#    █▄ █ █▄ ███▀▀▀▀▀▀▀ ╬  
#    ◥ █████ ◤  
#     ══╩══╩═  
#       ╬═╬  
#       ╬═╬ Dream big and start with something small!!!  
#       ╬═╬  
#       ╬═╬ You can do it!  
#       ╬═╬   Let's go...
#    ☻/ ╬═╬   
#   /▌  ╬═╬   
#   / \
# Cherman Seingalt - german.ponce@outlook.com


{
    'name': 'Reporte de operaciones bancarias',
    'summary': "Reporte Contable Personalizado",
    'description': 'Reporte de operaciones bancarias',

    'author': 'German Ponce Dominguez',
    'website': 'http://poncesoft.blogspot.com.mx',
    "support": "german.ponce@outlook.com",

    'category': 'Account',
    'version': '15.0.0.1.0',
    'depends': [
                    'account',
                    'company_child_of_rules',
                    'report_xlsx'
                    ],

    'data': [
        'views/account_view.xml',
        'security/ir.model.access.csv',
    ],
    'license': "AGPL-3",

    'installable': True,
}
