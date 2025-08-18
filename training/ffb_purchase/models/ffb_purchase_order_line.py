from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# Constants
MONEY_FORMAT = '{:,.2f}'
CLIENT_ACTION = 'ir.actions.client'
PRICING_CONFIG_MODEL = 'purchase.pricing.config'

# pylint: disable=no-member


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    # Additional fields for pricing information
    pricing_config_id = fields.Many2one(PRICING_CONFIG_MODEL, string='Pricing Configuration',
                                       help="Configuration used for automatic pricing")
    base_sale_price = fields.Float(string='Base Sale Price', readonly=True,
                                  help="Base price from sale (min/avg)")
    margin_amount = fields.Float(string='Purchase Margin Amount', readonly=True,
                                help="Amount reduced from base sale price for purchase margin")
    price_calculation_info = fields.Text(string='Price Calculation Info', readonly=True,
                                        help="Details about price calculation")
    pricing_config_available = fields.Boolean(string='Pricing Config Available', 
                                             compute='_compute_pricing_config_available', 
                                             help="Whether pricing configuration is available for this product and vendor")
    pricing_status = fields.Char(string='Pricing Status', compute='_compute_pricing_status',
                                help="Status of automatic pricing")
    
    @api.depends('product_id', 'order_id.partner_id')
    def _compute_pricing_config_available(self):
        """Check if pricing configuration is available for this product and vendor"""
        for line in self:
            if line.product_id and line.order_id.partner_id:
                # Get pricing configuration using the model method
                pricing_config_model = self.env[PRICING_CONFIG_MODEL]
                config = pricing_config_model.get_config_for_product_vendor(  # type: ignore
                    line.product_id.id, line.order_id.partner_id.id
                )
                line.pricing_config_available = bool(config)
            else:
                line.pricing_config_available = False

    @api.depends('pricing_config_available', 'price_unit', 'product_id', 'order_id.partner_id')
    def _compute_pricing_status(self):
        """Compute pricing status for display"""
        for line in self:
            if not line.product_id:
                line.pricing_status = "No Product"
            elif not line.order_id.partner_id:
                line.pricing_status = "No Vendor"
            elif line.pricing_config_available:
                if line.price_unit > 0:
                    line.pricing_status = "Auto-priced"
                else:
                    line.pricing_status = "Config Available"
            else:
                line.pricing_status = "Manual Pricing"

    @api.onchange('product_id')
    def _onchange_product_id_pricing_config(self):
        """Apply pricing configuration when product changes"""
        # Call standard onchange if it exists
        result = None
        
        # Then apply our pricing config
        if self.product_id:
            # Coba terapkan pricing config jika vendor sudah ada
            if self.order_id and self.order_id.partner_id:
                self._apply_pricing_config()
            # Jika vendor belum ada, akan otomatis diterapkan saat vendor dipilih
        
        return result

    # Remove this method as the field dependency doesn't work properly in this context

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity_pricing_config(self):
        """Apply pricing configuration when quantity changes (after product selection)"""
        # Apply standard quantity logic first
        result = None
        
        # Apply pricing config if we have product and vendor but no price yet
        if (self.product_id and self.order_id and self.order_id.partner_id and 
            (not self.price_unit or self.price_unit == 0)):
            self._apply_pricing_config()
            
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically apply pricing configuration"""
        lines = super().create(vals_list)
        for line in lines:
            # Otomatis terapkan pricing jika ada produk dan vendor, tidak peduli flag use_pricing_config
            if line.product_id and line.order_id.partner_id:
                line._apply_pricing_config()
        return lines

    def write(self, vals):
        """Override write to automatically apply pricing configuration when relevant fields change"""
        result = super().write(vals)
        
        # Check if product_id or partner_id changed
        if 'product_id' in vals or (self.order_id and 'partner_id' in vals):
            for line in self:
                if line.product_id and line.order_id and line.order_id.partner_id:
                    line._apply_pricing_config()
                    
        return result

    def _apply_pricing_config(self):
        """Apply pricing configuration to this line"""
        if not (self.product_id and self.order_id and self.order_id.partner_id):
            self._clear_pricing_info()
            return

        try:
            # Get pricing configuration
            pricing_config_model = self.env[PRICING_CONFIG_MODEL]
            config = pricing_config_model.get_config_for_product_vendor(  # type: ignore
                self.product_id.id, self.order_id.partner_id.id
            )
            
            if not config:
                self._apply_fallback_pricing()
                return

            self._apply_config_pricing(config)
                
        except Exception as e:
            # Handle any errors gracefully
            self.base_sale_price = 0.0
            self.margin_amount = 0.0
            self.price_calculation_info = _('Error calculating price: %s') % str(e)

    def _clear_pricing_info(self):
        """Clear pricing information"""
        self.pricing_config_id = False
        self.base_sale_price = 0.0
        self.margin_amount = 0.0
        self.price_calculation_info = _('Product or vendor not specified.')

    def _apply_fallback_pricing(self):
        """Apply fallback pricing when no config found"""
        self.pricing_config_id = False
        self.base_sale_price = 0.0
        self.margin_amount = 0.0
        
        if self.product_id.standard_price > 0:
            self.price_unit = self.product_id.standard_price
            self.price_calculation_info = _('Using product standard cost: %s') % (
                MONEY_FORMAT.format(self.product_id.standard_price)
            )
        elif self.product_id.list_price > 0:
            self.price_unit = self.product_id.list_price
            self.price_calculation_info = _('Using product list price: %s') % (
                MONEY_FORMAT.format(self.product_id.list_price)
            )
        else:
            self.price_calculation_info = _('No pricing configuration found. Please set price manually.')

    def _apply_config_pricing(self, config):
        """Apply pricing from configuration"""
        self.pricing_config_id = config.id
        date_from = self.order_id.pricing_date_from or False
        date_to = self.order_id.pricing_date_to or False
        
        price_details = config.get_price_details(date_from, date_to)
        
        if price_details['price_count'] == 0:
            self._apply_fallback_with_config()
        else:
            self._apply_calculated_pricing(price_details)

    def _apply_fallback_with_config(self):
        """Apply fallback pricing when config exists but no sale data"""
        self.base_sale_price = 0.0
        self.margin_amount = 0.0
        
        if self.product_id.standard_price > 0:
            self.price_unit = self.product_id.standard_price
            self.price_calculation_info = _('No sale data found. Using product standard cost: %s') % (
                MONEY_FORMAT.format(self.product_id.standard_price)
            )
        elif self.product_id.list_price > 0:
            self.price_unit = self.product_id.list_price  
            self.price_calculation_info = _('No sale data found. Using product list price: %s') % (
                MONEY_FORMAT.format(self.product_id.list_price)
            )
        else:
            self.price_calculation_info = _('No sale prices found in the specified date range.')

    def _apply_calculated_pricing(self, price_details):
        """Apply calculated pricing from sale data"""
        self.base_sale_price = price_details['base_price']
        self.margin_amount = price_details['margin_amount']
        self.price_unit = price_details['final_price']
        
        method_name = _('Minimum') if price_details['pricing_method'] == 'min_price' else _('Average')
        self.price_calculation_info = _(
            'Auto-calculated:\n'
            'Method: %s Sale Price\n'
            'Base Price: %s\n'
            'Purchase Margin: %s%% (-%s)\n'
            'Final Price: %s\n'
            'Based on %s sale orders'
        ) % (
            method_name,
            MONEY_FORMAT.format(price_details['base_price']),
            price_details['purchase_margin'],
            MONEY_FORMAT.format(price_details['margin_amount']),
            MONEY_FORMAT.format(price_details['final_price']),
            price_details['price_count']
        )

    def action_view_pricing_details(self):
        """Show detailed pricing calculation"""
        if not self.pricing_config_id:
            return {
                'type': CLIENT_ACTION,
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No pricing configuration available for this line.'),
                    'type': 'warning',
                }
            }

        date_from = self.order_id.pricing_date_from or False
        date_to = self.order_id.pricing_date_to or False
        # Get price details from the pricing configuration
        price_details = self.pricing_config_id.get_price_details(date_from, date_to)  # type: ignore

        message = _(
            'Product: %s\n'
            'Vendor: %s\n'
            'Pricing Method: %s\n'
            'Date Range: %s to %s\n'
            'Sale Orders Found: %s\n'
            'Base Price: %s\n'
            'Purchase Margin: %s%% (-%s)\n'
            'Final Purchase Price: %s'
        ) % (
            self.product_id.name,
            self.order_id.partner_id.name,
            _('Minimum') if price_details['pricing_method'] == 'min_price' else _('Average'),
            date_from or _('Not Set'),
            date_to or _('Not Set'),
            price_details['price_count'],
            MONEY_FORMAT.format(price_details['base_price']),
            price_details['purchase_margin'],
            MONEY_FORMAT.format(price_details['margin_amount']),
            MONEY_FORMAT.format(price_details['final_price'])
        )

        return {
            'type': CLIENT_ACTION,
            'tag': 'display_notification',
            'params': {
                'title': _('Pricing Calculation Details'),
                'message': message,
                'type': 'info',
            }
        }

    def action_recalculate_price(self):
        """Recalculate price based on current configuration"""
        self._apply_pricing_config()
        return {
            'type': CLIENT_ACTION,
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Price recalculated successfully.'),
                'type': 'success',
            }
        }
