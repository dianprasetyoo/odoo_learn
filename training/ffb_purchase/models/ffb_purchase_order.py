from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    # Inherit all standard purchase order functionality
    # No additional fields or methods needed as per requirement
