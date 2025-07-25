from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta, datetime, time


class DeliveryAssignWizard(models.TransientModel):
    _name = 'delivery.assign.wizard'
    _description = 'Wizard untuk assign driver, vehicle, dan delivery time'

    delivery_order_ids = fields.Many2many('delivery.order', string='Delivery Orders', required=True)
    driver_name = fields.Char(string='Driver Name', required=True)
    vehicle_number = fields.Char(string='Vehicle Number', required=True)
    delivery_time = fields.Datetime(string='Delivery Time', required=True, default=lambda self: datetime.combine(fields.Date.today() + timedelta(days=1), time(9, 0)))
    order_count = fields.Integer(string='Number of Orders', compute='_compute_order_count')

    @api.depends('delivery_order_ids')
    def _compute_order_count(self):
        """Compute the number of selected delivery orders"""
        for record in self:
            record.order_count = len(record.delivery_order_ids)

    @api.model
    def default_get(self, fields_list):
        """Set default values"""
        res = super(DeliveryAssignWizard, self).default_get(fields_list)
        delivery_order_ids = self.env.context.get('default_delivery_order_ids')
        if delivery_order_ids and len(delivery_order_ids) > 0:
            # Set default delivery time to tomorrow at 9 AM
            tomorrow = fields.Date.today() + timedelta(days=1)
            res.update({
                'delivery_time': datetime.combine(tomorrow, time(9, 0)),
            })
        return res

    def action_assign_all(self):
        """Assign driver, vehicle, dan delivery time ke semua delivery order"""
        # Validasi delivery time tidak boleh di masa lalu
        if self.delivery_time < fields.Datetime.now():
            raise ValidationError("Delivery time cannot be in the past!")
        
        for delivery_order in self.delivery_order_ids:
            # Update tracking info
            if self.delivery_time:
                delivery_order.delivery_time = self.delivery_time
            if self.driver_name:
                delivery_order.driver_name = self.driver_name
            if self.vehicle_number:
                delivery_order.vehicle_number = self.vehicle_number
            
            # Log perubahan
            changes = []
            if self.delivery_time:
                changes.append(f"Delivery time: {self.delivery_time}")
            if self.driver_name:
                changes.append(f"Driver: {self.driver_name}")
            if self.vehicle_number:
                changes.append(f"Vehicle: {self.vehicle_number}")
            
            if changes:
                delivery_order.notes = (delivery_order.notes or '') + f'\n[Tracking updated: {", ".join(changes)}]'
        
        # Show notification and reload
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Assignment Complete',
                'message': f'Driver, vehicle, and delivery time have been assigned to {len(self.delivery_order_ids)} delivery order(s).',
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        } 