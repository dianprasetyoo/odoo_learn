from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# Constants
CLIENT_ACTION = 'ir.actions.client'
MONEY_FORMAT = '{:,.2f}'
DAILY_PRICE_MODEL = 'daily.price'
VALIDATION_ERROR_TITLE = 'Validation Error'
ORDER_DATE_FIELD = 'order_id.date_order'


class PurchasePricingConfig(models.Model):
    _name = 'purchase.pricing.config'
    _description = 'Purchase Pricing Configuration'
    _rec_name = 'display_name'

    name = fields.Char(string='Name', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True, 
                               domain=['|', ('is_company', '=', True), ('supplier_rank', '>', 0)])
    
    # Pricing method
    pricing_method = fields.Selection([
        ('min_price', 'Minimum Sale Price'),
        ('avg_price', 'Average Sale Price'),
    ], string='Pricing Method', required=True, default='min_price',
       help="Method to calculate base price from daily sale prices")
    
    # Purchase margin configuration
    purchase_margin = fields.Float(string='Purchase Margin (%)', default=10.0, digits=(5,2),
                                  help="Percentage margin for purchase pricing (example: 10 = 10%)")
    
    # Date range for calculation
    date_range_days = fields.Integer(string='Date Range (Days)', default=30,
                                   help="Number of days to look back for price calculation")
    
    # Computed fields
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # Test calculation results (computed fields)
    test_base_price = fields.Float(string='Base Sale Price', compute='_compute_test_calculation', readonly=True)
    test_margin_amount = fields.Float(string='Margin Amount', compute='_compute_test_calculation', readonly=True)
    test_final_price = fields.Float(string='Final Purchase Price', compute='_compute_test_calculation', readonly=True)
    test_price_count = fields.Integer(string='Sale Orders Found', compute='_compute_test_calculation', readonly=True)
    test_status_message = fields.Char(string='Status', compute='_compute_test_calculation', readonly=True)
    active = fields.Boolean(string='Active', default=True)
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company)

    @api.depends('name', 'product_id', 'vendor_id')
    def _compute_display_name(self):
        for record in self:
            if record.product_id and record.vendor_id:
                record.display_name = f"{record.name} - {record.product_id.name} - {record.vendor_id.name}"
            else:
                record.display_name = record.name or _('New Configuration')

    @api.depends('product_id', 'purchase_margin', 'pricing_method', 'date_range_days')
    def _compute_test_calculation(self):
        for record in self:
            if not record.product_id:
                record._set_empty_test_values()
                record.test_status_message = _('Please select a product first')
                continue
                
            try:
                price_details = record.get_price_details()
                record._set_test_values_from_details(price_details)
                    
            except Exception as e:
                record._set_empty_test_values()
                record.test_status_message = _('Error: %s') % str(e)

    def _set_empty_test_values(self):
        """Helper method to set empty test values"""
        self.test_base_price = 0.0
        self.test_margin_amount = 0.0
        self.test_final_price = 0.0
        self.test_price_count = 0

    def _set_test_values_from_details(self, price_details):
        """Helper method to set test values from price details"""
        self.test_base_price = price_details['base_price']
        self.test_margin_amount = price_details['margin_amount']
        self.test_final_price = price_details['final_price']
        self.test_price_count = price_details['price_count']
        
        if price_details['price_count'] == 0:
            self.test_status_message = _('No sale orders found in date range')
        else:
            self.test_status_message = _('Calculation ready - click "View Details" for breakdown')

    def _get_no_data_message(self):
        """Helper method to get no data message"""
        from datetime import timedelta
        date_from = fields.Date.today() - timedelta(days=self.date_range_days)
        date_to = fields.Date.today()
        
        return _(
            'No sale orders found for product "%s"\n'
            'Date range: %s to %s (%s days)\n\n'
            'To get pricing calculation:\n'
            '• Create confirmed sale orders for this product\n'
            '• Ensure order dates are within the date range'
        ) % (
            self.product_id.name,
            date_from.strftime('%Y-%m-%d'),
            date_to.strftime('%Y-%m-%d'),
            self.date_range_days
        )



    @api.constrains('purchase_margin')
    def _check_purchase_margin(self):
        for record in self:
            if record.purchase_margin < 0 or record.purchase_margin > 100:
                raise ValidationError(_('Purchase margin must be between 0 and 100%.'))

    @api.constrains('date_range_days')
    def _check_date_range_days(self):
        for record in self:
            if record.date_range_days <= 0:
                raise ValidationError(_('Date range must be greater than 0.'))

    @api.constrains('product_id', 'vendor_id')
    def _check_unique_product_vendor(self):
        for record in self:
            if record.product_id and record.vendor_id:
                existing_config = self.search([
                    ('product_id', '=', record.product_id.id),
                    ('vendor_id', '=', record.vendor_id.id),
                    ('id', '!=', record.id),
                    ('active', '=', True)
                ])
                if existing_config:
                    raise ValidationError(_(
                        'An active pricing configuration already exists for product "%s" and vendor "%s".'
                    ) % (record.product_id.name, record.vendor_id.name))

    def calculate_purchase_price(self, date_from=None, date_to=None):
        """Calculate purchase price based on sale orders for the same product"""
        self.ensure_one()
        
        if not date_from:
            from datetime import timedelta
            date_from = fields.Date.today() - timedelta(days=self.date_range_days)
        
        if not date_to:
            date_to = fields.Date.today()

        # Get sale order lines for this product from all vendors
        sale_lines = self.env['sale.order.line'].search([
            ('product_id', '=', self.product_id.id),
            (ORDER_DATE_FIELD, '>=', date_from),
            (ORDER_DATE_FIELD, '<=', date_to),
            ('order_id.state', 'in', ['sale'])  # Only confirmed orders
        ])

        if not sale_lines:
            return 0.0

        prices = sale_lines.mapped('price_unit')
        
        if self.pricing_method == 'min_price':
            base_price = min(prices)
        else:  # avg_price
            base_price = sum(prices) / len(prices)

        # Apply purchase margin
        margin_amount = base_price * (self.purchase_margin / 100)
        final_price = base_price - margin_amount

        return final_price

    def get_price_details(self, date_from=None, date_to=None):
        """Get detailed price calculation information from sale orders"""
        self.ensure_one()
        
        if not date_from:
            from datetime import timedelta
            date_from = fields.Date.today() - timedelta(days=self.date_range_days)
        
        if not date_to:
            date_to = fields.Date.today()

        # Get sale order lines for this product from all vendors
        sale_lines = self.env['sale.order.line'].search([
            ('product_id', '=', self.product_id.id),
            (ORDER_DATE_FIELD, '>=', date_from),
            (ORDER_DATE_FIELD, '<=', date_to),
            ('order_id.state', 'in', ['sale'])  # Only confirmed orders
        ])

        if not sale_lines:
            return {
                'base_price': 0.0,
                'margin_amount': 0.0,
                'final_price': 0.0,
                'price_count': 0,
                'pricing_method': self.pricing_method,
                'purchase_margin': self.purchase_margin,
                'sale_orders': []
            }

        prices = sale_lines.mapped('price_unit')
        
        if self.pricing_method == 'min_price':
            base_price = min(prices)
        else:  # avg_price
            base_price = sum(prices) / len(prices)

        # Apply purchase margin
        margin_amount = base_price * (self.purchase_margin / 100)
        final_price = base_price - margin_amount

        return {
            'base_price': base_price,
            'margin_amount': margin_amount,
            'final_price': final_price,
            'price_count': len(prices),
            'pricing_method': self.pricing_method,
            'purchase_margin': self.purchase_margin,
            'sale_orders': sale_lines.mapped(lambda line: {
                'date': line.order_id.date_order.date(),
                'price': line.price_unit,
                'customer': line.order_id.partner_id.name,
                'order_name': line.order_id.name,
                'quantity': line.product_uom_qty
            })
        }

    @api.model
    def get_config_for_product_vendor(self, product_id, vendor_id):
        """Get active pricing configuration for product and vendor"""
        return self.search([
            ('product_id', '=', product_id),
            ('vendor_id', '=', vendor_id),
            ('active', '=', True)
        ], limit=1)

    @api.model
    def get_purchase_price_for_product_vendor(self, product_id, vendor_id, date_from=None, date_to=None):
        """Get calculated purchase price for product and vendor
        Returns dict with price info or False if no config found"""
        config = self.get_config_for_product_vendor(product_id, vendor_id)
        if not config:
            return False
        
        try:
            price_details = config.get_price_details(date_from, date_to)
            return {
                'config_id': config.id,
                'final_price': price_details['final_price'],
                'base_price': price_details['base_price'],
                'margin_amount': price_details['margin_amount'],
                'price_count': price_details['price_count'],
                'pricing_method': price_details['pricing_method'],
                'purchase_margin': price_details['purchase_margin'],
            }
        except Exception:
            return False

    def action_test_price_calculation(self):
        """Action wrapper for testing price calculation"""
        self.ensure_one()
        
        # Validate required fields
        if not self.product_id:
            return {
                'type': CLIENT_ACTION,
                'tag': 'display_notification',
                'params': {
                    'title': _(VALIDATION_ERROR_TITLE),
                    'message': _('Please select a product before testing price calculation.'),
                    'type': 'warning',
                }
            }
        
        if not self.vendor_id:
            return {
                'type': CLIENT_ACTION,
                'tag': 'display_notification',
                'params': {
                    'title': _(VALIDATION_ERROR_TITLE),
                    'message': _('Please select a vendor before testing price calculation.'),
                    'type': 'warning',
                }
            }
        
        try:
            price_details = self.get_price_details()
            
            if price_details['price_count'] == 0:
                from datetime import timedelta
                date_from = fields.Date.today() - timedelta(days=self.date_range_days)
                date_to = fields.Date.today()
                
                message = _(
                    '⚠️ No Sale Orders Found\n\n'
                    'Product: %s\n'
                    'Date Range: %s to %s (%s days)\n'
                    'Sale Orders Found: 0\n\n'
                    '💡 To fix this:\n'
                    '1. Go to Sales > Orders\n'
                    '2. Create confirmed sale orders for this product\n'
                    '3. Ensure the order dates are within the specified range\n'
                    '4. Orders must be in "Sale Order" or "Locked" state'
                ) % (
                    self.product_id.name,
                    date_from.strftime('%Y-%m-%d'),
                    date_to.strftime('%Y-%m-%d'),
                    self.date_range_days
                )
                
                return {
                    'type': CLIENT_ACTION,
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Data Found'),
                        'message': message,
                        'type': 'warning',
                        'sticky': True,
                    }
                }
            
            method_name = _('Minimum') if self.pricing_method == 'min_price' else _('Average')
            
            # Create detailed sale order breakdown
            order_info = []
            for sale_order in price_details['sale_orders']:
                order_info.append(f"  • {sale_order['customer']} ({sale_order['date']}) - {sale_order['order_name']}: {MONEY_FORMAT.format(sale_order['price'])} x {sale_order['quantity']:.0f}")
            
            order_breakdown = '\n'.join(order_info[:5])  # Show max 5 entries
            if len(price_details['sale_orders']) > 5:
                order_breakdown += f"\n  ... and {len(price_details['sale_orders']) - 5} more"
            
            # Calculate profit margin percentage
            if price_details['base_price'] > 0:
                profit_margin = (price_details['margin_amount'] / price_details['base_price']) * 100
            else:
                profit_margin = 0
            
            message = _(
                '✅ Price Calculation Test Results\n\n'
                '📦 Product: %s\n'
                '🏭 Vendor: %s\n'
                '📊 Method: %s Sale Price\n'
                '📅 Date Range: %s days\n'
                '📈 Sale Orders Found: %s\n\n'
                '💰 Pricing Details:\n'
                '  Base Sale Price: %s\n'
                '  Purchase Margin: %s%% (-%s)\n'
                '  Final Purchase Price: %s\n'
                '  Expected Profit: %s%%\n\n'
                '📋 Sale Order Sources:\n%s'
            ) % (
                self.product_id.name,
                self.vendor_id.name,
                method_name,
                self.date_range_days,
                price_details['price_count'],
                MONEY_FORMAT.format(price_details['base_price']),
                price_details['purchase_margin'],
                MONEY_FORMAT.format(price_details['margin_amount']),
                MONEY_FORMAT.format(price_details['final_price']),
                '{:.1f}'.format(profit_margin),
                order_breakdown
            )
            
            return {
                'type': CLIENT_ACTION,
                'tag': 'display_notification',
                'params': {
                    'title': _('💰 Price Calculation Test'),
                    'message': message,
                    'type': 'success',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error in price calculation test: {e}")
            
            return {
                'type': CLIENT_ACTION,
                'tag': 'display_notification',
                'params': {
                    'title': _('❌ Error'),
                    'message': _('Error calculating price: %s\n\nPlease check your configuration and try again.') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_open_sale_orders(self):
        """Open sale orders for this product to help user view data source"""
        self.ensure_one()
        
        if not self.product_id:
            return {
                'type': CLIENT_ACTION,
                'tag': 'display_notification',
                'params': {
                    'title': _(VALIDATION_ERROR_TITLE),
                    'message': _('Please select a product first.'),
                    'type': 'warning',
                }
            }
        
        return {
            'name': _('Sale Orders for %s') % self.product_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('order_line.product_id', '=', self.product_id.id),
                ('state', 'in', ['sale'])
            ],
            'context': {
                'search_default_product_id': self.product_id.id,
            },
            'target': 'current',
        }

    def action_view_calculation_details(self):
        """Show detailed calculation breakdown in modal wizard"""
        self.ensure_one()
        
        if not self.product_id:
            return {
                'type': CLIENT_ACTION,
                'tag': 'display_notification',
                'params': {
                    'title': _(VALIDATION_ERROR_TITLE),
                    'message': _('Please select a product first.'),
                    'type': 'warning',
                }
            }
        
        try:
            price_details = self.get_price_details()
            
            if price_details['price_count'] == 0:
                return {
                    'type': CLIENT_ACTION,
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Data Found'),
                        'message': self._get_no_data_message(),
                        'type': 'warning',
                        'sticky': True,
                    }
                }
            
            # Calculate profit margin percentage
            if price_details['base_price'] > 0:
                profit_margin = (price_details['margin_amount'] / price_details['base_price']) * 100
            else:
                profit_margin = 0
            
            from datetime import timedelta
            date_from = fields.Date.today() - timedelta(days=self.date_range_days)
            date_to = fields.Date.today()
            
            # Create wizard record with calculation details
            wizard = self.env['wizard.calculation.details'].create({
                'config_id': self.id,
                'product_name': self.product_id.name,
                'vendor_name': self.vendor_id.name if self.vendor_id else _('Not Set'),
                'pricing_method': self.pricing_method,
                'purchase_margin': self.purchase_margin,
                'date_range_days': self.date_range_days,
                'date_from': date_from,
                'date_to': date_to,
                'price_count': price_details['price_count'],
                'base_price': price_details['base_price'],
                'margin_amount': price_details['margin_amount'],
                'final_price': price_details['final_price'],
                'profit_margin': profit_margin,
            })
            
            # Create sale order lines
            line_vals = []
            for sale_order in price_details['sale_orders']:
                line_vals.append({
                    'wizard_id': wizard.id,
                    'customer_name': sale_order['customer'],
                    'order_name': sale_order['order_name'],
                    'order_date': sale_order['date'],
                    'unit_price': sale_order['price'],
                    'quantity': sale_order['quantity'],
                    'subtotal': sale_order['price'] * sale_order['quantity'],
                })
            
            if line_vals:
                self.env['wizard.calculation.details.line'].create(line_vals)
            
            # Return modal wizard
            return {
                'name': _('Price Calculation Details'),
                'type': 'ir.actions.act_window',
                'res_model': 'wizard.calculation.details',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',  # This makes it a modal
                'context': self.env.context,
            }
            
        except Exception as e:
            return {
                'type': CLIENT_ACTION,
                'tag': 'display_notification',
                'params': {
                    'title': _('❌ Error'),
                    'message': _('Error calculating price details: %s\n\nPlease check your configuration and try again.') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
