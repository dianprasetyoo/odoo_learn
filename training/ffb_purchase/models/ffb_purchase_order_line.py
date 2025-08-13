from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    # Inherit all standard purchase order functionality
    # No additional fields or methods needed as per requirement
