from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_order_ids = fields.One2many('delivery.order', 'sale_order_id', string='Delivery Orders')
    delivery_order_count = fields.Integer(string='Delivery Orders', compute='_compute_delivery_order_count')

    @api.depends('delivery_order_ids')
    def _compute_delivery_order_count(self):
        for record in self:
            record.delivery_order_count = len(record.delivery_order_ids)

    def action_create_delivery_orders(self):
        """Create delivery orders from sale order"""
        self.ensure_one()
        
        # Check if delivery orders already exist
        if self.delivery_order_ids:
            raise UserError("Delivery orders already exist for this sale order!")
        
        # Warning for draft quotations
        if self.state == 'draft':
            return {
                'name': 'Create Delivery Orders from Quotation',
                'type': 'ir.actions.act_window',
                'res_model': 'delivery.create.from.quotation.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_sale_order_id': self.id,
                    'default_sale_order_name': self.name,
                    'default_partner_id': self.partner_id.id,
                }
            }
        
        # Create delivery orders for confirmed sale orders
        delivery_orders = self.env['delivery.order'].create_from_sale_order(self.id)
        
        if delivery_orders:
            return {
                'name': 'Delivery Orders Created',
                'type': 'ir.actions.act_window',
                'res_model': 'delivery.order',
                'view_mode': 'list,form',
                'domain': [('sale_order_id', '=', self.id)],
                'context': {'default_sale_order_id': self.id},
            }
        else:
            raise UserError("No valid order lines found to create delivery orders!")

    def action_view_delivery_orders(self):
        """View delivery orders for this sale order"""
        self.ensure_one()
        
        if not self.delivery_order_ids:
            return self.action_create_delivery_orders()
        
        return {
            'name': 'Delivery Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'delivery.order',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id},
        }

    def action_create_delivery_from_quotation(self):
        """Create delivery orders from quotation with confirmation"""
        self.ensure_one()
        
        if self.state != 'draft':
            raise UserError("This action is only available for draft quotations!")
        
        # Create delivery orders
        delivery_orders = self.env['delivery.order'].create_from_sale_order(self.id)
        
        if delivery_orders:
            return {
                'name': 'Delivery Orders Created from Quotation',
                'type': 'ir.actions.act_window',
                'res_model': 'delivery.order',
                'view_mode': 'list,form',
                'domain': [('sale_order_id', '=', self.id)],
                'context': {'default_sale_order_id': self.id},
            }
        else:
            raise UserError("No valid order lines found to create delivery orders!")


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    delivery_order_ids = fields.One2many('delivery.order', 'sale_order_line_id', string='Delivery Orders')
    delivery_order_count = fields.Integer(string='Delivery Orders', compute='_compute_delivery_order_count')

    @api.depends('delivery_order_ids')
    def _compute_delivery_order_count(self):
        for record in self:
            record.delivery_order_count = len(record.delivery_order_ids)

    def action_create_delivery_order(self):
        """Create delivery order from sale order line"""
        self.ensure_one()
        
        # Check if delivery order already exists
        if self.delivery_order_ids:
            raise UserError("Delivery order already exists for this line!")
        
        # Warning for draft quotations
        if self.order_id.state == 'draft':
            return {
                'name': 'Create Delivery Order from Quotation Line',
                'type': 'ir.actions.act_window',
                'res_model': 'delivery.create.from.quotation.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_sale_order_id': self.order_id.id,
                    'default_sale_order_line_id': self.id,
                    'default_sale_order_name': self.order_id.name,
                    'default_partner_id': self.order_id.partner_id.id,
                }
            }
        
        # Create delivery order for confirmed sale order lines
        delivery_order = self.env['delivery.order'].create_from_sale_order_line(self.id)
        
        if delivery_order:
            return {
                'name': 'Delivery Order Created',
                'type': 'ir.actions.act_window',
                'res_model': 'delivery.order',
                'res_id': delivery_order.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            raise UserError("Could not create delivery order from this line!")

    def action_view_delivery_orders(self):
        """View delivery orders for this sale order line"""
        self.ensure_one()
        
        if not self.delivery_order_ids:
            return self.action_create_delivery_order()
        
        return {
            'name': 'Delivery Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'delivery.order',
            'view_mode': 'list,form',
            'domain': [('sale_order_line_id', '=', self.id)],
            'context': {'default_sale_order_line_id': self.id},
        } 