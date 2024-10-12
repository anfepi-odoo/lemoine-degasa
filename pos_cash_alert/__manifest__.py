{
    'name': 'POS Cash Alert',
    'version': '1.0',
    'summary': 'Alert when cash limit is reached in POS',
    'category': 'Point of Sale',
    'author': 'Roberto Requejo Jiménez',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_cash_limit_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_cash_alert/static/src/js/pos_cash_alert.js',
        ],
    },
    'installable': True,
    'application': False,
}
