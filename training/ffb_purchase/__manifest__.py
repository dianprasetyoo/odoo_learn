{
    'name': 'FFB Purchase',
    'version': '1.0.0',
    'summary': 'FFB Purchase Management',
    'description': 'FFB Purchase module with standard purchase order functionality and daily price management',
    'author': 'Tyo',
    'category': 'Purchases',
    'depends': ['purchase', 'sale', 'stock', 'account', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/wizard_calculation_details_views.xml',
        'views/purchase_pricing_config_views.xml',
        'views/purchase_order_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}