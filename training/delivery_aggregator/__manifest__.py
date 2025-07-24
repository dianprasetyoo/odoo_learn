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
        #Security
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        #Data
        'data/delivery_sequence.xml',
        'data/delivery_cron.xml',  # Cron job untuk auto-generate monthly summary
        #Views
        'views/delivery_order_views.xml',
        'views/monthly_summary_views.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}