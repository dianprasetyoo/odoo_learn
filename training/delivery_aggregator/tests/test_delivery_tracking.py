from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
from odoo import fields


class TestDeliveryTracking(TransactionCase):
    """Unit test untuk model DeliveryOrderTracking (inherit dari delivery.order)"""
    
    def setUp(self):
        """Setup method yang runs sebelum setiap test"""
        super(TestDeliveryTracking, self).setUp()
        
        # Create customer untuk testing
        self.customer = self.env['res.partner'].create({
            'name': 'Test Customer Tracking',
        })
        
        # Create product untuk testing
        self.product = self.env['product.product'].create({
            'name': 'Test Product Tracking',
        })
        
        # Base data untuk delivery order
        self.delivery_data = {
            'customer_id': self.customer.id,
            'delivery_date': fields.Date.today(),
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_price': 50.0,
            'notes': 'Test delivery order with tracking',
        }

    def test_create_delivery_order_with_tracking(self):
        """Test 1: Create delivery order dengan field tracking baru"""
        # Create delivery order dengan tracking data
        delivery_data = self.delivery_data.copy()
        delivery_data.update({
            'delivery_time': fields.Datetime.now(),
            'driver_name': 'Test Driver',
            'vehicle_number': 'B 1234 TEST'
        })
        
        delivery_order = self.env['delivery.order'].create(delivery_data)
        
        # Verifikasi field tracking
        self.assertTrue(delivery_order.id, "Delivery order harus berhasil dibuat")
        self.assertEqual(delivery_order.driver_name, 'Test Driver')
        self.assertEqual(delivery_order.vehicle_number, 'B 1234 TEST')
        self.assertIsNotNone(delivery_order.delivery_time)

    def test_assign_driver_method(self):
        """Test 2: Test method assign_driver"""
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        
        # Test assign driver
        delivery_order.assign_driver('John Doe', 'B 5678 ABC')
        
        # Verifikasi hasil
        self.assertEqual(delivery_order.driver_name, 'John Doe')
        self.assertEqual(delivery_order.vehicle_number, 'B 5678 ABC')
        self.assertIn('Driver assigned: John Doe - B 5678 ABC', delivery_order.notes)

    def test_schedule_delivery_method(self):
        """Test 3: Test method schedule_delivery"""
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        
        # Test schedule delivery
        scheduled_time = fields.Datetime.now()
        delivery_order.schedule_delivery(scheduled_time)
        
        # Verifikasi hasil
        self.assertEqual(delivery_order.delivery_time, scheduled_time)
        self.assertIn('Delivery scheduled:', delivery_order.notes)

    def test_action_assign_driver_method(self):
        """Test 8: Test method action_assign_driver (button action)"""
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        
        # Test action assign driver
        result = delivery_order.action_assign_driver()
        
        # Verifikasi hasil
        self.assertEqual(delivery_order.driver_name, 'Default Driver')
        self.assertEqual(delivery_order.vehicle_number, 'B 0000 XXX')
        self.assertIn('Driver assigned via button', delivery_order.notes)
        self.assertEqual(result['type'], 'ir.actions.client')

    def test_action_schedule_delivery_method(self):
        """Test 9: Test method action_schedule_delivery (button action)"""
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        
        # Test action schedule delivery
        result = delivery_order.action_schedule_delivery()
        
        # Verifikasi hasil
        self.assertIsNotNone(delivery_order.delivery_time)
        self.assertIn('Delivery scheduled for:', delivery_order.notes)
        self.assertEqual(result['type'], 'ir.actions.client')

    def test_action_confirm_with_tracking(self):
        """Test 4: Test override method action_confirm"""
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        
        # Confirm order tanpa delivery_time
        delivery_order.action_confirm()
        
        # Verifikasi bahwa delivery_time otomatis diisi
        self.assertIsNotNone(delivery_order.delivery_time)
        self.assertEqual(delivery_order.state, 'confirmed')

    def test_get_delivery_status_method(self):
        """Test 5: Test method get_delivery_status"""
        delivery_data = self.delivery_data.copy()
        delivery_data.update({
            'driver_name': 'Test Driver',
            'vehicle_number': 'B 1234 TEST'
        })
        
        delivery_order = self.env['delivery.order'].create(delivery_data)
        
        # Test get delivery status
        status = delivery_order.get_delivery_status()
        
        # Verifikasi hasil
        self.assertEqual(status['order_name'], delivery_order.name)
        self.assertEqual(status['customer'], 'Test Customer Tracking')
        self.assertEqual(status['driver'], 'Test Driver')
        self.assertEqual(status['vehicle'], 'B 1234 TEST')

    def test_get_delivery_status_without_driver(self):
        """Test 6: Test get_delivery_status tanpa driver"""
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        
        # Test get delivery status tanpa driver
        status = delivery_order.get_delivery_status()
        
        # Verifikasi hasil
        self.assertEqual(status['driver'], 'Not assigned')
        self.assertEqual(status['vehicle'], 'Not assigned')

    def test_inherit_field_accessibility(self):
        """Test 7: Test bahwa field original masih bisa diakses"""
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        
        # Test field original
        self.assertEqual(delivery_order.customer_id.name, 'Test Customer Tracking')
        self.assertEqual(delivery_order.product_id.name, 'Test Product Tracking')
        self.assertEqual(delivery_order.quantity, 10.0)
        self.assertEqual(delivery_order.unit_price, 50.0)
        self.assertEqual(delivery_order.total_amount, 500.0)  # 10 * 50 