from odoo import models, fields, api
from odoo.exceptions import UserError

class DeliveryCreateFromQuotationWizard(models.TransientModel):
    _name = 'delivery.create.from.quotation.wizard'
    _description = 'Wizard untuk membuat delivery order dari quotation'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True)
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
    sale_order_name = fields.Char(string='Quotation Name', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    message = fields.Text(string='Message', readonly=True, default="Are you sure you want to create delivery orders from this quotation? This action will create delivery orders even though the quotation is not yet confirmed.")

    @api.model
    def default_get(self, fields_list):
        """Set default values"""
        res = super(DeliveryCreateFromQuotationWizard, self).default_get(fields_list)
        sale_order_id = self.env.context.get('default_sale_order_id')
        sale_order_line_id = self.env.context.get('default_sale_order_line_id')
        
        if sale_order_id:
            sale_order = self.env['sale.order'].browse(sale_order_id)
            res.update({
                'sale_order_id': sale_order.id,
                'sale_order_name': sale_order.name,
                'partner_id': sale_order.partner_id.id,
            })
        
        if sale_order_line_id:
            res['sale_order_line_id'] = sale_order_line_id
        
        return res

    def action_create_delivery_orders(self):
        """Create delivery orders from quotation"""
        self.ensure_one()
        
        if self.sale_order_line_id:
            # Create delivery order from specific line
            delivery_order = self.env['delivery.order'].create_from_sale_order_line(self.sale_order_line_id.id)
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
            # Create delivery orders from entire sale order
            delivery_orders = self.env['delivery.order'].create_from_sale_order(self.sale_order_id.id)
            if delivery_orders:
                return {
                    'name': 'Delivery Orders Created from Quotation',
                    'type': 'ir.actions.act_window',
                    'res_model': 'delivery.order',
                    'view_mode': 'list,form',
                    'domain': [('sale_order_id', '=', self.sale_order_id.id)],
                    'context': {'default_sale_order_id': self.sale_order_id.id},
                }
        
        raise UserError("Could not create delivery orders from this quotation!")

    def action_cancel(self):
        """Cancel the wizard"""
        return {'type': 'ir.actions.act_window_close'} 