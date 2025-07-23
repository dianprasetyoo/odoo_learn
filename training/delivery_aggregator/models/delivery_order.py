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