from odoo import models, fields, api, exceptions

class DeliveryOrder(models.Model):
    _name = 'delivery.order'
    _description = 'Delivery Order'

    name = fields.Char(string='Name', required=True, default=lambda self: self._get_sequence())
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    delivery_date = fields.Date(string='Delivery Date', required=True)
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