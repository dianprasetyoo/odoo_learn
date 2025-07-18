{
    'name': 'Delivery Aggregator',
    'version': '1.0.0',
    'category': 'Inventory',
    'summary': 'Aggregate delivery orders and generate monthly summaries',
    'description': """
        This module provides functionality to:
        - Create and manage delivery orders
        - Aggregate delivery data by month
        - Generate monthly summary reports
        - Track delivery performance metrics
    """,
    'author': 'Tyo',
    'depends': [
        'base',
        'stock',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/delivery_sequence.xml',
        'views/delivery_order_views.xml',
        'views/monthly_summary_views.xml',
    ],
    'demo': [
        'data/delivery_sequence.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}