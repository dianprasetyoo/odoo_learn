from odoo import models, fields, api, exceptions

class DeliveryOrder(models.Model):
    _name = 'delivery.order'
    _description = 'Delivery Order'
    _order = 'delivery_date desc, customer_id, trip'

    name = fields.Char(string='Name', required=True, default=lambda self: self._get_sequence())
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    delivery_date = fields.Date(string='Delivery Date', required=True)
    trip = fields.Char(string='Trip', compute='_compute_trip', store=True, readonly=True)
    trip_info = fields.Text(string='Trip Information', compute='_compute_trip_info', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    unit_price = fields.Float(string='Unit Price', required=True)
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True, readonly=True)
    monthly_summary_id = fields.Many2one('monthly.summary', string='Monthly Summary')
    # Integration with Sales
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', help='Related sale order')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', help='Related sale order line')
    state = fields.Selection([
        ('draft', 'New Order'), 
        ('confirmed', 'Ready for Delivery'), 
        ('delivered', 'Successfully Delivered')
    ], string='State', required=True, default='draft')
    notes = fields.Text(string='Notes')

    def _get_date(self):
        return fields.Date.context_today(self)

    @api.constrains('quantity')
    def _check_quantity_positive(self):
        for record in self:
            if record.quantity <= 0:
                raise exceptions.ValidationError("Quantity must be greater than 0.")

    @api.constrains('unit_price')
    def _check_unit_price_non_negative(self):
        for record in self:
            if record.unit_price < 0:
                raise exceptions.ValidationError("Unit price cannot be negative.")

    def _get_sequence(self):
        return self.env['ir.sequence'].next_by_code('delivery.order') or 'New'

    @api.depends('delivery_date', 'customer_id')
    def _compute_trip(self):
        """Compute trip number based on delivery date and customer"""
        for record in self:
            if record.delivery_date and record.customer_id:
                # Get all existing trips for the same date and customer
                existing_trips = self.search([
                    ('delivery_date', '=', record.delivery_date),
                    ('customer_id', '=', record.customer_id.id),
                    ('id', '!=', record.id)
                ]).mapped('trip')
                
                # Find the next available trip number
                trip_number = 1
                while str(trip_number) in existing_trips:
                    trip_number += 1
                
                record.trip = str(trip_number)
            else:
                record.trip = False

    @api.depends('delivery_date', 'customer_id')
    def _compute_trip_info(self):
        """Compute trip information for display"""
        for record in self:
            if record.delivery_date and record.customer_id:
                trip_info = self.get_trip_info_for_date(record.delivery_date, record.customer_id.id)
                info_text = f"Date: {record.delivery_date}\n"
                info_text += f"Customer: {record.customer_id.name}\n"
                info_text += f"Total Orders: {trip_info['total_orders']}\n"
                info_text += f"Used Trips: {', '.join(map(str, trip_info['used_trips'])) if trip_info['used_trips'] else 'None'}\n"
                info_text += f"Available Trips: {', '.join(map(str, trip_info['available_trips'])) if trip_info['available_trips'] else 'None'}\n"
                info_text += f"Next Trip: {trip_info['next_trip']}"
                record.trip_info = info_text
            elif record.delivery_date:
                record.trip_info = "Please select a customer"
            else:
                record.trip_info = "Please select a delivery date and customer"

    @api.depends('quantity', 'unit_price')
    def _compute_total_amount(self):
        for record in self:
            quantity = record.quantity or 0.0
            unit_price = record.unit_price or 0.0
            record.total_amount = quantity * unit_price

    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'

    def action_deliver(self):
        for record in self:
            record.state = 'delivered'

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise exceptions.UserError("Only draft delivery orders can be deleted.")
        return super(DeliveryOrder, self).unlink()

    @api.model
    def get_available_trips_for_date(self, delivery_date, customer_id=None):
        """Get available trip numbers for a specific date and customer"""
        if not delivery_date:
            return []
        
        # Build domain based on parameters
        domain = [('delivery_date', '=', delivery_date)]
        if customer_id:
            domain.append(('customer_id', '=', customer_id))
        
        # Get all existing trips for the date and customer
        existing_trips = self.search(domain).mapped('trip')
        
        # Convert to integers for easier comparison
        existing_trip_numbers = []
        for trip in existing_trips:
            if trip and isinstance(trip, str) and trip.isdigit():
                existing_trip_numbers.append(int(trip))
        
        # Find missing trip numbers
        if not existing_trip_numbers:
            return [1]  # If no trips exist, first trip is available
        
        max_trip = max(existing_trip_numbers)
        all_trips = set(range(1, max_trip + 1))
        used_trips = set(existing_trip_numbers)
        available_trips = sorted(list(all_trips - used_trips))
        
        # Add next trip number if all existing numbers are used
        if not available_trips:
            available_trips = [max_trip + 1]
        
        return available_trips

    @api.model
    def get_trip_summary(self, delivery_date=None, customer_id=None):
        """Get trip summary for a specific date/customer or all dates"""
        domain = []
        if delivery_date:
            domain.append(('delivery_date', '=', delivery_date))
        if customer_id:
            domain.append(('customer_id', '=', customer_id))
        
        delivery_orders = self.search(domain)
        
        trip_summary = {}
        for order in delivery_orders:
            date_str = order.delivery_date.strftime('%Y-%m-%d')
            customer_key = f"{date_str}_{order.customer_id.id}"
            
            if customer_key not in trip_summary:
                trip_summary[customer_key] = {
                    'date': date_str,
                    'customer': order.customer_id.name,
                    'customer_id': order.customer_id.id,
                    'used_trips': [],
                    'available_trips': [],
                    'total_orders': 0
                }
            
            trip_summary[customer_key]['used_trips'].append(order.trip)
            trip_summary[customer_key]['total_orders'] += 1
        
        # Calculate available trips for each date-customer combination
        for customer_key, data in trip_summary.items():
            date_obj = fields.Date.from_string(data['date'])
            available_trips = self.get_available_trips_for_date(date_obj, data['customer_id'])
            trip_summary[customer_key]['available_trips'] = available_trips
            trip_summary[customer_key]['used_trips'] = sorted(trip_summary[customer_key]['used_trips'])
        
        return trip_summary

    @api.model
    def get_next_available_trip(self, delivery_date, customer_id=None):
        """Get the next available trip number for a specific date and customer"""
        if not delivery_date:
            return 1
        
        available_trips = self.get_available_trips_for_date(delivery_date, customer_id)
        return available_trips[0] if available_trips else 1

    @api.model
    def get_trip_info_for_date(self, delivery_date, customer_id=None):
        """Get comprehensive trip information for a specific date and customer"""
        if not delivery_date:
            return {
                'used_trips': [],
                'available_trips': [1],
                'next_trip': 1,
                'total_orders': 0
            }
        
        # Build domain based on parameters
        domain = [('delivery_date', '=', delivery_date)]
        if customer_id:
            domain.append(('customer_id', '=', customer_id))
        
        # Get all delivery orders for the date and customer
        orders = self.search(domain)
        
        used_trips = [order.trip for order in orders if order.trip]
        used_trip_numbers = []
        for trip in used_trips:
            if trip and isinstance(trip, str) and trip.isdigit():
                used_trip_numbers.append(int(trip))
        
        available_trips = self.get_available_trips_for_date(delivery_date, customer_id)
        next_trip = available_trips[0] if available_trips else 1
        
        return {
            'used_trips': sorted(used_trip_numbers),
            'available_trips': available_trips,
            'next_trip': next_trip,
            'total_orders': len(orders)
        }

    # Sales Integration Methods
    def action_view_sale_order(self):
        """Open related sale order"""
        self.ensure_one()
        if self.sale_order_id:
            return {
                'name': 'Sale Order',
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'res_id': self.sale_order_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False



    @api.model
    def create_from_sale_order(self, sale_order_id):
        """Create delivery order from sale order"""
        sale_order = self.env['sale.order'].browse(sale_order_id)
        if not sale_order.exists():
            return False
        
        delivery_orders = []
        for line in sale_order.order_line:
            if line.product_id and line.product_uom_qty > 0:
                delivery_order = self.create({
                    'customer_id': sale_order.partner_id.id,
                    'delivery_date': fields.Date.today(),
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty,
                    'unit_price': line.price_unit,
                    'sale_order_id': sale_order.id,
                    'sale_order_line_id': line.id,
                    'notes': f'Created from Sale Order: {sale_order.name}',
                })
                delivery_orders.append(delivery_order)
        
        return delivery_orders

    @api.model
    def create_from_sale_order_line(self, sale_order_line_id):
        """Create delivery order from specific sale order line"""
        sale_line = self.env['sale.order.line'].browse(sale_order_line_id)
        if not sale_line.exists():
            return False
        
        delivery_order = self.create({
            'customer_id': sale_line.order_id.partner_id.id,
            'delivery_date': fields.Date.today(),
            'product_id': sale_line.product_id.id,
            'quantity': sale_line.product_uom_qty,
            'unit_price': sale_line.price_unit,
            'sale_order_id': sale_line.order_id.id,
            'sale_order_line_id': sale_line.id,
            'notes': f'Created from Sale Order Line: {sale_line.order_id.name}',
        })
        
        return delivery_order