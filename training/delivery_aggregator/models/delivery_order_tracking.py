from odoo import models, fields, api
from odoo.exceptions import ValidationError

class DeliveryOrderTracking(models.Model):
    _inherit = 'delivery.order'
    _description = 'Delivery Order with Tracking'

    delivery_time = fields.Datetime(string='Delivery Time', help='Waktu pengiriman yang dijadwalkan')
    driver_name = fields.Char(string='Driver Name', help='Nama driver yang mengirim')
    vehicle_number = fields.Char(string='Vehicle Number', help='Nomor kendaraan')
    
    def action_confirm(self):
        super(DeliveryOrderTracking, self).action_confirm()
        
        for record in self:
            if not record.delivery_time:
                record.delivery_time = fields.Datetime.now()
    
    @api.constrains('delivery_time')
    def _check_delivery_time(self):
        """Validasi delivery time tidak boleh di masa lalu"""
        for record in self:
            if record.delivery_time and record.delivery_time < fields.Datetime.now():
                raise ValidationError("Delivery time cannot be in the past!")
    
    def action_open_assign_wizard(self):
        """Buka wizard untuk assign driver, vehicle, dan delivery time"""
        return {
            'name': 'Assign Driver & Schedule',
            'type': 'ir.actions.act_window',
            'res_model': 'delivery.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_delivery_order_ids': [(6, 0, self.ids)],
            }
        }
    
    def action_reset_assign(self):
        """Reset driver, vehicle, and delivery time assignments"""
        for record in self:
            record.driver_name = False
            record.vehicle_number = False
            record.delivery_time = False
            # Reset state to draft if it was confirmed
            if record.state == 'confirmed':
                record.state = 'draft'
            record.notes = (record.notes or '') + f'\n[Reset assignment: {fields.Datetime.now()}]'
        
        # Show notification and reload
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Assignment Reset',
                'message': f'{len(self)} delivery order(s) have been reset.',
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }
    
    def action_mark_ready(self):
        """Mark delivery order as ready to deliver"""
        for record in self:
            if record.driver_name and record.vehicle_number and record.delivery_time:
                record.state = 'confirmed'
                record.notes = (record.notes or '') + f'\n[Marked as ready to deliver: {fields.Datetime.now()}]'
        
        # Show notification and reload
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Ready to Deliver',
                'message': f'{len(self)} delivery order(s) have been marked as ready to deliver.',
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }