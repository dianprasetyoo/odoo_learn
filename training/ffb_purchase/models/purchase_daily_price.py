from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class PurchaseDailyPrice(models.Model):
    _name = 'purchase.daily.price'
    _description = 'Purchase Daily Price Management'
    _order = 'date desc, product_id, supplier_id'
    _rec_name = 'display_name'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, 
                      default=lambda self: _('New'))
    product_id = fields.Many2one('product.product', string='Product', required=True)
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    unit_price = fields.Float(string='Unit Price', required=True, digits=(10, 2))
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company)
    notes = fields.Text(string='Notes')
    
    # Computed fields
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # Constraints
    _sql_constraints = [
        ('unique_product_supplier_date', 'unique(product_id, supplier_id, date)', 
         'A purchase daily price record for this product-supplier-date combination already exists!')
    ]

    @api.constrains('unit_price')
    def _check_unit_price_positive(self):
        for record in self:
            if record.unit_price <= 0:
                raise ValidationError(_('Unit price must be greater than zero.'))

    @api.depends('date', 'product_id', 'supplier_id')
    def _compute_display_name(self):
        for record in self:
            if record.product_id and record.supplier_id:
                if record.date:
                    record.display_name = f"{record.date} - {record.product_id.name} - {record.supplier_id.name}"
                else:
                    record.display_name = f"{record.product_id.name} - {record.supplier_id.name}"
            else:
                record.display_name = record.name or _('New Purchase Daily Price')

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle both single and batch creation"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.daily.price') or _('New')
        
        return super(PurchaseDailyPrice, self).create(vals_list)

    def get_price_for_date(self, product_id, supplier_id, date):
        """Get unit price for a specific product, supplier and date"""
        price_record = self.search([
            ('product_id', '=', product_id),
            ('supplier_id', '=', supplier_id),
            ('date', '=', date)
        ], limit=1)
        
        if price_record:
            return price_record.unit_price
        
        return 0.0

    def check_price_exists(self, product_id, supplier_id, date):
        """Check if price exists for a specific product, supplier and date"""
        price_record = self.search([
            ('product_id', '=', product_id),
            ('supplier_id', '=', supplier_id),
            ('date', '=', date)
        ], limit=1)
        
        return bool(price_record)

    def action_copy_to_next_day(self):
        """Copy this purchase daily price to the next day"""
        next_day = self.date + timedelta(days=1)
        
        # Check if record already exists for next day
        if self.check_price_exists(self.product_id.id, self.supplier_id.id, next_day):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('Purchase daily price record already exists for %s') % next_day.strftime('%Y-%m-%d'),
                    'type': 'warning',
                }
            }
        
        # Create new purchase daily price record for next day
        self.create({
            'product_id': self.product_id.id,
            'supplier_id': self.supplier_id.id,
            'date': next_day,
            'unit_price': self.unit_price,
            'currency_id': self.currency_id.id,
            'notes': f'Copied from {self.name}',
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Purchase daily price copied to %s') % next_day.strftime('%Y-%m-%d'),
                'type': 'success',
            }
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    purchase_daily_price_ids = fields.One2many('purchase.daily.price', 'product_id', string='Purchase Daily Prices')
    has_purchase_daily_pricing = fields.Boolean(string='Has Purchase Daily Pricing', compute='_compute_has_purchase_daily_pricing', store=True)

    @api.depends('purchase_daily_price_ids')
    def _compute_has_purchase_daily_pricing(self):
        for product in self:
            product.has_purchase_daily_pricing = bool(product.purchase_daily_price_ids)

    def get_purchase_daily_price(self, supplier_id, date):
        """Get purchase daily price for this product, supplier and date"""
        self.ensure_one()
        purchase_daily_price = self.env['purchase.daily.price'].get_price_for_date(self.id, supplier_id, date)
        return purchase_daily_price

    def check_purchase_daily_price_exists(self, supplier_id, date):
        """Check if purchase daily price exists for this product, supplier and date"""
        self.ensure_one()
        return self.env['purchase.daily.price'].check_price_exists(self.id, supplier_id, date)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_id')
    def _onchange_product_id_purchase_daily_price(self):
        """Apply purchase daily pricing when product changes - SAME LOGIC AS SALE ORDER"""
        _logger.info(f"Purchase daily price onchange triggered for product: {self.product_id.name if self.product_id else 'None'}")
        
        if self.product_id and self.order_id.partner_id and self.order_id.date_planned:
            _logger.info(f"Product: {self.product_id.name}, Partner: {self.order_id.partner_id.name}, Date: {self.order_id.date_planned}")
            
            # Check if product has purchase daily pricing
            if self.product_id.has_purchase_daily_pricing:
                _logger.info(f"Product {self.product_id.name} has purchase daily pricing")
                
                # Get the date from purchase order - use date_planned (Order Deadline)
                order_date = self.order_id.date_planned.date()
                _logger.info(f"Order date: {order_date}")
                
                # Check if purchase daily price exists for this date
                if self.product_id.check_purchase_daily_price_exists(self.order_id.partner_id.id, order_date):
                    _logger.info(f"Daily price exists for {self.product_id.name} + {self.order_id.partner_id.name} + {order_date}")
                    
                    # Get the purchase daily price
                    purchase_daily_price = self.product_id.get_purchase_daily_price(self.order_id.partner_id.id, order_date)
                    _logger.info(f"Retrieved daily price: {purchase_daily_price}")
                    
                    if purchase_daily_price > 0:
                        # Update the price_unit field directly - SAME AS SALE ORDER
                        old_price = self.price_unit
                        self.price_unit = purchase_daily_price
                        _logger.info(f"Updated price_unit from {old_price} to {self.price_unit}")
                    else:
                        _logger.warning(f"Daily price is zero or negative: {purchase_daily_price}")
                else:
                    _logger.info(f"No daily price exists for {self.product_id.name} + {self.order_id.partner_id.name} + {order_date}")
                    # Show warning that purchase daily price is missing
                    return {
                        'warning': {
                            'title': _('Purchase Daily Price Missing'),
                            'message': _('Product %s does not have a purchase daily price set for supplier %s on %s. Please set the purchase daily price first.') % (
                                self.product_id.name, 
                                self.order_id.partner_id.name, 
                                order_date.strftime('%Y-%m-%d')
                            )
                        }
                    }
            else:
                _logger.info(f"Product {self.product_id.name} does not have purchase daily pricing")
        else:
            _logger.info(f"Missing required fields - Product: {bool(self.product_id)}, Partner: {bool(self.order_id.partner_id if self.order_id else None)}, Date: {bool(self.order_id.date_planned if self.order_id else None)}")

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty_purchase_daily_price(self):
        """Ensure unit price follows daily price when quantity changes"""
        if self.product_id and self.order_id.partner_id and self.order_id.date_planned:
            # Check if product has purchase daily pricing
            if self.product_id.has_purchase_daily_pricing:
                # Get the date from purchase order
                order_date = self.order_id.date_planned.date()
                
                # Check if purchase daily price exists for this date
                if self.product_id.check_purchase_daily_price_exists(self.order_id.partner_id.id, order_date):
                    # Get the purchase daily price
                    purchase_daily_price = self.product_id.get_purchase_daily_price(self.order_id.partner_id.id, order_date)
                    if purchase_daily_price > 0:
                        # Ensure unit price follows daily price
                        if self.price_unit != purchase_daily_price:
                            self.price_unit = purchase_daily_price
                            _logger.info(f"Quantity changed - Updated price_unit to daily price: {purchase_daily_price}")

    @api.onchange('product_uom')
    def _onchange_product_uom_purchase_daily_price(self):
        """Ensure unit price follows daily price when UoM changes"""
        if self.product_id and self.order_id.partner_id and self.order_id.date_planned:
            # Check if product has purchase daily pricing
            if self.product_id.has_purchase_daily_pricing:
                # Get the date from purchase order
                order_date = self.order_id.date_planned.date()
                
                # Check if purchase daily price exists for this date
                if self.product_id.check_purchase_daily_price_exists(self.order_id.partner_id.id, order_date):
                    # Get the purchase daily price
                    purchase_daily_price = self.product_id.get_purchase_daily_price(self.order_id.partner_id.id, order_date)
                    if purchase_daily_price > 0:
                        # Ensure unit price follows daily price
                        if self.price_unit != purchase_daily_price:
                            self.price_unit = purchase_daily_price
                            _logger.info(f"UoM changed - Updated price_unit to daily price: {purchase_daily_price}")

    @api.onchange('price_unit')
    def _onchange_price_unit_purchase_daily_price(self):
        """Ensure unit price follows daily price when manually changed"""
        if self.product_id and self.order_id.partner_id and self.order_id.date_planned:
            # Check if product has purchase daily pricing
            if self.product_id.has_purchase_daily_pricing:
                # Get the date from purchase order
                order_date = self.order_id.date_planned.date()
                
                # Check if purchase daily price exists for this date
                if self.product_id.check_purchase_daily_price_exists(self.order_id.partner_id.id, order_date):
                    # Get the purchase daily price
                    purchase_daily_price = self.product_id.get_purchase_daily_price(self.order_id.partner_id.id, order_date)
                    if purchase_daily_price > 0:
                        # Ensure unit price follows daily price
                        if self.price_unit != purchase_daily_price:
                            self.price_unit = purchase_daily_price
                            _logger.info(f"Price manually changed - Updated price_unit to daily price: {purchase_daily_price}")

    def _ensure_daily_price_applied(self):
        """Helper method to ensure daily price is always applied"""
        if self.product_id and self.order_id.partner_id and self.order_id.date_planned:
            # Check if product has purchase daily pricing
            if self.product_id.has_purchase_daily_pricing:
                # Get the date from purchase order
                order_date = self.order_id.date_planned.date()
                
                # Check if purchase daily price exists for this date
                if self.product_id.check_purchase_daily_price_exists(self.order_id.partner_id.id, order_date):
                    # Get the purchase daily price
                    purchase_daily_price = self.product_id.get_purchase_daily_price(self.order_id.partner_id.id, order_date)
                    if purchase_daily_price > 0:
                        # Ensure unit price follows daily price
                        if self.price_unit != purchase_daily_price:
                            self.price_unit = purchase_daily_price
                            _logger.info(f"Ensuring daily price applied: {purchase_daily_price}")
                            return True
        return False

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure daily price is applied"""
        records = super(PurchaseOrderLine, self).create(vals_list)
        
        # Apply daily price after creation
        for record in records:
            record._ensure_daily_price_applied()
        
        return records

    def write(self, vals):
        """Override write to ensure daily price is applied after changes"""
        result = super(PurchaseOrderLine, self).write(vals)
        
        # Apply daily price after write
        for record in self:
            record._ensure_daily_price_applied()
        
        return result

    def copy(self, default=None):
        """Override copy to ensure daily price is applied"""
        if default is None:
            default = {}
        
        # Copy the line
        new_line = super(PurchaseOrderLine, self).copy(default)
        
        # Apply daily price after copy
        new_line._ensure_daily_price_applied()
        
        return new_line

    @api.constrains('product_id', 'price_unit')
    def _check_purchase_daily_price_required(self):
        """Validate that products with purchase daily pricing have valid prices"""
        for line in self:
            if (line.product_id and line.product_id.has_purchase_daily_pricing and 
                line.order_id.partner_id and line.order_id.date_planned):
                
                order_date = line.order_id.date_planned.date()
                
                # Check if purchase daily price exists
                if not line.product_id.check_purchase_daily_price_exists(line.order_id.partner_id.id, order_date):
                    raise ValidationError(_(
                        'Product %s requires a purchase daily price for supplier %s on %s. '
                        'Please set the purchase daily price in Purchase Daily Prices menu first.'
                    ) % (
                        line.product_id.name,
                        line.order_id.partner_id.name,
                        order_date.strftime('%Y-%m-%d')
                    ))


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('partner_id', 'date_planned')
    def _onchange_partner_date_purchase_daily_price(self):
        """Trigger daily price update when supplier or date changes"""
        for line in self.order_line:
            if line.product_id:
                line._onchange_product_id_purchase_daily_price()

    def _update_all_lines_daily_price(self):
        """Update daily price for all lines in the order"""
        for line in self.order_line:
            if line.product_id:
                line._ensure_daily_price_applied()

    @api.onchange('order_line')
    def _onchange_order_line_purchase_daily_price(self):
        """Ensure daily price is applied when order lines change"""
        for line in self.order_line:
            if line.product_id:
                line._ensure_daily_price_applied()

    def write(self, vals):
        """Override write to update daily prices when order changes"""
        result = super(PurchaseOrder, self).write(vals)
        
        # If partner or date changed, update all lines
        if 'partner_id' in vals or 'date_planned' in vals:
            self._update_all_lines_daily_price()
        
        return result


class ResPartner(models.Model):
    _inherit = 'res.partner'

    purchase_daily_price_ids = fields.One2many('purchase.daily.price', 'supplier_id', string='Purchase Daily Prices')

    def get_purchase_daily_price_for_product(self, product_id, date):
        """Get purchase daily price for a specific product and date for this supplier"""
        self.ensure_one()
        return self.env['purchase.daily.price'].get_price_for_date(product_id, self.id, date)
