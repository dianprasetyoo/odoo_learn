{
    'name': 'Sale Mill',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Sale Mill Management Module with Daily Price Management',
    'description': """
        This module provides comprehensive mill management functionality within the Sales module.
        
        Features include:
        - Daily price management per product-customer combination
        - Notebook-style interface for better organization
        - Bulk creation of daily prices for date ranges
        - Automatic integration with sales orders
        - Validation to ensure daily prices exist for order dates
        - Copy daily prices to next day functionality
        - Archive/unarchive daily prices
        - Product and customer integration with daily price visibility
        - Advanced search and filtering capabilities
        
        The module ensures that products with daily pricing have valid prices set for specific dates,
        and automatically applies these prices when creating sale orders.
    """,
    'author': 'Tyo',
    'depends': [
        'base',
        'sale',
        'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/daily_price_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
} 