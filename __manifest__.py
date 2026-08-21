{
    'name': 'Library Management',
    'version': '18.0.1.0',
    'license': 'LGPL-3',
    'author': 'Mamduha Younus',
    'depends': ['base', 'product', 'stock', 'account', 'sale'],
    'data': [
        'security/ir.model.access.csv',  # Put this back at the top
        'data/library_cron.xml',
        'reports/acknowledgment_report.xml',
        'views/product_template.xml',
        'views/res_partner.xml',
        'views/stock_picking.xml',
        # 'views/account_move.xml',
        'views/library_menus.xml',
    ],
    'installable': True,
    'application': True,
}