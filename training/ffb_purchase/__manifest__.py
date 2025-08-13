{
    'name': 'FFB Purchase',
    'version': '1.0.0',
    'summary': 'FFB Purchase Management',
    'description': 'FFB Purchase module with standard purchase order functionality and daily price management',
    'author': 'Tyo',
    'category': 'Purchases',
    'depends': ['purchase', 'stock', 'account', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'data/purchase_daily_price_sequence.xml',
        'views/purchase_daily_price_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}