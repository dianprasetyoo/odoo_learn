from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class DailyPriceLine(models.Model):
    _name = 'daily.price.line'
    _description = 'Daily Price Line'
    _order = 'date'

    daily_price_id = fields.Many2one('daily.price', string='Daily Price', required=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True)
    unit_price = fields.Float(string='Unit Price', required=True, digits=(10, 2))
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 default=lambda self: self.env.company.currency_id)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_daily_price_date', 'unique(daily_price_id, date)', 
         'A price for this date already exists in this daily price record!')
    ]

    @api.constrains('unit_price')
    def _check_unit_price_positive(self):
        for record in self:
            if record.unit_price <= 0:
                raise ValidationError(_('Unit price must be greater than zero.'))

    def action_save(self):
        """Save the price line and close the wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window_close'
        }


class DailyPrice(models.Model):
    _name = 'daily.price'
    _description = 'Daily Price Management'
    _order = 'date desc, product_id, customer_id'
    _rec_name = 'display_name'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, 
                      default=lambda self: _('New'))
    product_id = fields.Many2one('product.product', string='Product', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company)
    active = fields.Boolean(string='Active', default=True)
    notes = fields.Text(string='Notes')
    
    # Daily Price Lines
    daily_price_line_ids = fields.One2many('daily.price.line', 'daily_price_id', string='Daily Price Lines')
    
    # Computed fields
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # Constraints
    _sql_constraints = [
        ('unique_product_customer', 'unique(product_id, customer_id, active)', 
         'A daily price record for this product-customer combination already exists!')
    ]

    @api.depends('date', 'product_id', 'customer_id')
    def _compute_display_name(self):
        for record in self:
            if record.product_id and record.customer_id:
                if record.date:
                    record.display_name = f"{record.date} - {record.product_id.name} - {record.customer_id.name}"
                else:
                    record.display_name = f"{record.product_id.name} - {record.customer_id.name}"
            else:
                record.display_name = record.name or _('New Daily Price')

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle both single and batch creation"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('daily.price') or _('New')
        
        return super(DailyPrice, self).create(vals_list)

    @api.model
    def _remove_old_constraints(self):
        """Remove any old constraints that might still exist in the database"""
        try:
            # This is a safety method to ensure old constraints are removed
            # It can be called manually if needed
            pass
        except Exception as e:
            _logger.warning(f"Error removing old constraints: {e}")

    @api.model
    def check_record_exists(self, product_id, customer_id):
        """Check if a daily price record already exists for this product-customer combination"""
        return self.search_count([
            ('product_id', '=', product_id),
            ('customer_id', '=', customer_id),
            ('active', '=', True)
        ]) > 0

    @api.model
    def get_existing_record(self, product_id, customer_id):
        """Get the existing daily price record for this product-customer combination"""
        return self.search([
            ('product_id', '=', product_id),
            ('customer_id', '=', customer_id),
            ('active', '=', True)
        ], limit=1)

    @api.model
    def add_price_line_to_existing(self, product_id, customer_id, date, unit_price, currency_id=None, notes=None):
        """Add a price line to an existing daily price record"""
        existing_record = self.get_existing_record(product_id, customer_id)
        
        if not existing_record:
            raise ValidationError(_('No existing daily price record found for this product-customer combination.'))
        
        if not currency_id:
            currency_id = self.env.company.currency_id.id
        
        # Check if price line already exists for this date
        existing_price_line = existing_record.daily_price_line_ids.filtered(lambda l: l.date == date)
        if existing_price_line:
            raise ValidationError(_('A price line already exists for date %s') % date.strftime('%Y-%m-%d'))
        
        # Create new price line
        return self.env['daily.price.line'].create({
            'daily_price_id': existing_record.id,
            'date': date,
            'unit_price': unit_price,
            'currency_id': currency_id,
            'notes': notes,
        })

    def copy(self, default=None):
        """Override copy to also copy daily price lines"""
        if default is None:
            default = {}
        
        # Copy the daily price
        new_record = super(DailyPrice, self).copy(default)
        
        # Copy daily price lines
        for line in self.daily_price_line_ids:
            self.env['daily.price.line'].create({
                'daily_price_id': new_record.id,
                'date': line.date,
                'unit_price': line.unit_price,
                'currency_id': line.currency_id.id,
                'notes': line.notes,
            })
        
        return new_record

    @api.constrains('date')
    def _check_date_not_future(self):
        for record in self:
            # Allow future dates for planning purposes
            # Only warn if date is more than 1 year in the future
            if record.date and record.date > fields.Date.today() + timedelta(days=365):
                raise ValidationError(_('Price date cannot be more than 1 year in the future.'))

    @api.constrains('product_id', 'customer_id')
    def _check_unique_product_customer(self):
        for record in self:
            if record.product_id and record.customer_id:
                # Check if another record exists with the same product-customer combination
                existing_record = self.search([
                    ('product_id', '=', record.product_id.id),
                    ('customer_id', '=', record.customer_id.id),
                    ('active', '=', True),
                    ('id', '!=', record.id)
                ], limit=1)
                
                if existing_record:
                    raise ValidationError(_(
                        'A daily price record already exists for product "%s" and customer "%s". '
                        'Please use the existing record to add price lines for different dates.'
                    ) % (record.product_id.name, record.customer_id.name))

    def get_price_for_date(self, product_id, customer_id, date):
        """Get unit price for a specific product, customer and date"""
        # Search for the daily price record for this product-customer combination
        price_record = self.search([
            ('product_id', '=', product_id),
            ('customer_id', '=', customer_id),
            ('active', '=', True)
        ], limit=1)
        
        if price_record and price_record.daily_price_line_ids:
            # Get the price line for this date
            price_line = price_record.daily_price_line_ids.filtered(lambda l: l.date == date)
            return price_line.unit_price if price_line else 0.0
        
        return 0.0

    def get_price_for_date_range(self, product_id, customer_id, start_date, end_date):
        """Get unit prices for a product-customer combination within a date range"""
        # Search for the daily price record for this product-customer combination
        price_record = self.search([
            ('product_id', '=', product_id),
            ('customer_id', '=', customer_id),
            ('active', '=', True)
        ], limit=1)
        
        if price_record and price_record.daily_price_line_ids:
            # Filter price lines within the date range
            filtered_lines = price_record.daily_price_line_ids.filtered(
                lambda l: start_date <= l.date <= end_date
            )
            if filtered_lines:
                return price_record
        
        return self.env['daily.price']

    def check_price_exists(self, product_id, customer_id, date):
        """Check if price exists for a specific product, customer and date"""
        # Search for the daily price record for this product-customer combination
        price_record = self.search([
            ('product_id', '=', product_id),
            ('customer_id', '=', customer_id),
            ('active', '=', True)
        ], limit=1)
        
        if price_record and price_record.daily_price_line_ids:
            # Check if there's a price line for this specific date
            price_line = price_record.daily_price_line_ids.filtered(lambda l: l.date == date)
            return bool(price_line)
        
        return False

    def action_copy_to_next_day(self):
        """Copy this daily price to the next day"""
        next_day = self.date + timedelta(days=1)
        
        # Get the current price line for today
        today_price_line = self.daily_price_line_ids.filtered(lambda l: l.date == self.date)
        
        # Check if price line already exists for next day
        existing_price_line = self.daily_price_line_ids.filtered(lambda l: l.date == next_day)
        
        if existing_price_line:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('Daily price line already exists for %s') % next_day.strftime('%Y-%m-%d'),
                    'type': 'warning',
                }
            }
        
        # Add price line to the existing record
        if today_price_line:
            self.env['daily.price.line'].create({
                'daily_price_id': self.id,
                'date': next_day,
                'unit_price': today_price_line.unit_price,
                'currency_id': today_price_line.currency_id.id,
                'notes': f'Copied from {self.name}',
            })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Daily price copied to %s') % next_day.strftime('%Y-%m-%d'),
                'type': 'success',
            }
        }

    def action_add_price_line(self):
        """Add a new price line"""
        return {
            'name': _('Add Price Line'),
            'type': 'ir.actions.act_window',
            'res_model': 'daily.price.line',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_daily_price_id': self.id,
                'default_currency_id': self.env.company.currency_id.id,
                'default_date': fields.Date.today(),
            }
        }

    def action_view_price_lines(self):
        """View daily price lines for this daily price"""
        return {
            'name': _('Daily Price Lines for %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'daily.price.line',
            'view_mode': 'list,form',
            'domain': [('daily_price_id', '=', self.id)],
            'context': {'default_daily_price_id': self.id},
        }

    def action_create_new(self):
        """Action to create a new daily price record"""
        return {
            'name': _('Create Daily Price'),
            'type': 'ir.actions.act_window',
            'res_model': 'daily.price',
            'view_mode': 'form',
            'target': 'current',
            'context': {},
        }

    @api.model
    def action_create_or_open(self, product_id=None, customer_id=None):
        """Create new daily price record or open existing one if it exists"""
        if product_id and customer_id:
            existing_record = self.get_existing_record(product_id, customer_id)
            if existing_record:
                return {
                    'name': _('Daily Price - %s - %s') % (existing_record.product_id.name, existing_record.customer_id.name),
                    'type': 'ir.actions.act_window',
                    'res_model': 'daily.price',
                    'view_mode': 'form',
                    'res_id': existing_record.id,
                    'target': 'current',
                }
        
        return self.action_create_new()

    @api.model
    def validate_before_create(self, product_id, customer_id):
        """Validate if a new record can be created for this product-customer combination"""
        if self.check_record_exists(product_id, customer_id):
            existing_record = self.get_existing_record(product_id, customer_id)
            raise ValidationError(_(
                'A daily price record already exists for product "%s" and customer "%s". '
                'Please use the existing record (ID: %s) to add price lines for different dates.'
            ) % (existing_record.product_id.name, existing_record.customer_id.name, existing_record.id))
        
        return True

    @api.onchange('product_id', 'customer_id')
    def _onchange_product_customer_check_existing(self):
        """Check if a record already exists for this product-customer combination"""
        if self.product_id and self.customer_id:
            existing_record = self.get_existing_record(self.product_id.id, self.customer_id.id)
            if existing_record:
                return {
                    'warning': {
                        'title': _('Record Already Exists'),
                        'message': _(
                            'A daily price record already exists for product "%s" and customer "%s". '
                            'Please use the existing record to add price lines for different dates.'
                        ) % (self.product_id.name, self.customer_id.name)
                    }
                }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    daily_price_ids = fields.One2many('daily.price', 'product_id', string='Daily Prices')
    has_daily_pricing = fields.Boolean(string='Has Daily Pricing', compute='_compute_has_daily_pricing', store=True)

    @api.depends('daily_price_ids')
    def _compute_has_daily_pricing(self):
        for product in self:
            product.has_daily_pricing = bool(product.daily_price_ids)

    def get_daily_price(self, customer_id, date):
        """Get daily price for this product, customer and date"""
        self.ensure_one()
        daily_price = self.env['daily.price'].get_price_for_date(self.id, customer_id, date)
        return daily_price

    def check_daily_price_exists(self, customer_id, date):
        """Check if daily price exists for this product, customer and date"""
        self.ensure_one()
        return self.env['daily.price'].check_price_exists(self.id, customer_id, date)

    def action_view_daily_prices(self):
        """Action to view daily prices for this product"""
        return {
            'name': _('Daily Prices for %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'daily.price',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }

    def check_daily_price_record_exists(self, customer_id):
        """Check if a daily price record exists for this product and customer"""
        self.ensure_one()
        return self.env['daily.price'].check_record_exists(self.id, customer_id)

    def get_existing_daily_price_record(self, customer_id):
        """Get the existing daily price record for this product and customer"""
        self.ensure_one()
        return self.env['daily.price'].get_existing_record(self.id, customer_id)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_id_daily_price(self):
        """Apply daily pricing when product changes"""
        if self.product_id and self.order_id.partner_id and self.order_id.date_order:
            # Check if product has daily pricing
            if self.product_id.has_daily_pricing:
                # Get the date from sale order
                order_date = self.order_id.date_order.date()
                
                # Check if daily price exists for this date
                if self.product_id.check_daily_price_exists(self.order_id.partner_id.id, order_date):
                    # Get the daily price
                    daily_price = self.product_id.get_daily_price(self.order_id.partner_id.id, order_date)
                    if daily_price > 0:
                        self.price_unit = daily_price
                else:
                    # Show warning that daily price is missing
                    return {
                        'warning': {
                            'title': _('Daily Price Missing'),
                            'message': _('Product %s does not have a daily price set for customer %s on %s. Please set the daily price first.') % (
                                self.product_id.name, 
                                self.order_id.partner_id.name, 
                                order_date.strftime('%Y-%m-%d')
                            )
                        }
                    }

    @api.constrains('product_id', 'price_unit')
    def _check_daily_price_required(self):
        """Validate that products with daily pricing have valid prices"""
        for line in self:
            if (line.product_id and line.product_id.has_daily_pricing and 
                line.order_id.partner_id and line.order_id.date_order):
                
                order_date = line.order_id.date_order.date()
                
                # Check if daily price exists
                if not line.product_id.check_daily_price_exists(line.order_id.partner_id.id, order_date):
                    raise ValidationError(_(
                        'Product %s requires a daily price for customer %s on %s. '
                        'Please set the daily price in Daily Prices menu first.'
                    ) % (
                        line.product_id.name,
                        line.order_id.partner_id.name,
                        order_date.strftime('%Y-%m-%d')
                    ))


class ResPartner(models.Model):
    _inherit = 'res.partner'

    daily_price_ids = fields.One2many('daily.price', 'customer_id', string='Daily Prices')

    def get_daily_price_for_product(self, product_id, date):
        """Get daily price for a specific product and date for this customer"""
        self.ensure_one()
        return self.env['daily.price'].get_price_for_date(product_id, self.id, date)

    def check_daily_price_record_exists(self, product_id):
        """Check if a daily price record exists for this customer and product"""
        self.ensure_one()
        return self.env['daily.price'].check_record_exists(product_id, self.id)

    def get_existing_daily_price_record(self, product_id):
        """Get the existing daily price record for this customer and product"""
        self.ensure_one()
        return self.env['daily.price'].get_existing_record(product_id, self.id) 