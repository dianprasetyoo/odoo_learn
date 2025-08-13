{
    'name': 'Sale Mill',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Sale Mill Management Module with Daily Price Management',
    'description': """
        This module provides comprehensive mill management functionality within the Sales module.
        
        Features include:
        - Daily price management per product-customer-date combination
        - Simple and intuitive interface for daily price input
        - Automatic integration with sales orders
        - Automatic integration with purchase orders
        - Validation to ensure daily prices exist for order dates
        - Copy daily prices to next day functionality
        - Product and customer/supplier integration with daily price visibility
        - Advanced search and filtering capabilities
        
        The module ensures that products with daily pricing have valid prices set for specific dates,
        and automatically applies these prices when creating sales and purchase orders.
    """,
    'author': 'Tyo',
    'depends': [
        'base',
        'sale',
        'sale_management',
        'purchase',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/ir_sequence_data.xml',
        'views/daily_price_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
} 