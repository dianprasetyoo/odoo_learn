from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    # Additional fields for pricing configuration
    use_pricing_config = fields.Boolean(string='Use Pricing Configuration', default=True,
                                       help="Use automatic pricing based on sale prices")
    pricing_date_from = fields.Date(string='Pricing Date From', 
                                  default=lambda self: fields.Date.today() - timedelta(days=30),
                                  help="Start date for price calculation")
    pricing_date_to = fields.Date(string='Pricing Date To', 
                                default=fields.Date.today,
                                help="End date for price calculation")
    
    @api.onchange('use_pricing_config')
    def _onchange_use_pricing_config(self):
        """Update pricing dates when enabling pricing configuration"""
        if self.use_pricing_config and not self.pricing_date_from:
            self.pricing_date_from = fields.Date.today() - timedelta(days=30)
            self.pricing_date_to = fields.Date.today()

    @api.onchange('partner_id')
    def _onchange_partner_id_pricing_config(self):
        """Apply pricing configuration when vendor changes"""
        # Otomatis terapkan pricing ketika vendor berubah, tidak peduli flag use_pricing_config
        if self.partner_id:
            for line in self.order_line:
                if line.product_id:
                    line._apply_pricing_config()
                    
    def write(self, vals):
        """Override write to apply pricing when partner changes"""
        result = super().write(vals)
        
        # If partner_id changed, apply pricing to all lines
        if 'partner_id' in vals and vals['partner_id']:
            for order in self:
                for line in order.order_line:
                    if line.product_id:
                        line._apply_pricing_config()
                        
        return result

    def action_apply_pricing_config(self):
        """Manually re-apply pricing configuration to all order lines"""
        for line in self.order_line:
            line._apply_pricing_config()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Pricing configuration re-applied to all lines.'),
                'type': 'success',
            }
        }
