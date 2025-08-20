from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
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

    def test_action_open_assign_wizard(self):
        """Test 2: Test method action_open_assign_wizard"""
        delivery_order = self.env['delivery.order'].create(self.delivery_data)

        # Test action open assign wizard
        result = delivery_order.action_open_assign_wizard()

        # Verifikasi hasil
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'delivery.assign.wizard')
        self.assertEqual(result['view_mode'], 'form')
        self.assertEqual(result['target'], 'new')

    def test_action_reset_assign(self):
        """Test 3: Test method action_reset_assign"""
        delivery_data = self.delivery_data.copy()
        delivery_data.update({
            'driver_name': 'Test Driver',
            'vehicle_number': 'B 1234 TEST',
            'delivery_time': fields.Datetime.now(),
            'state': 'confirmed'
        })
        
        delivery_order = self.env['delivery.order'].create(delivery_data)

        # Test action reset assign
        result = delivery_order.action_reset_assign()

        # Verifikasi hasil
        self.assertFalse(delivery_order.driver_name)
        self.assertFalse(delivery_order.vehicle_number)
        self.assertFalse(delivery_order.delivery_time)
        self.assertEqual(delivery_order.state, 'draft')
        self.assertIn('Reset assignment', delivery_order.notes)
        self.assertEqual(result['type'], 'ir.actions.client')

    def test_action_mark_ready(self):
        """Test 4: Test method action_mark_ready"""
        delivery_data = self.delivery_data.copy()
        delivery_data.update({
            'driver_name': 'Test Driver',
            'vehicle_number': 'B 1234 TEST',
            'delivery_time': fields.Datetime.now()
        })
        
        delivery_order = self.env['delivery.order'].create(delivery_data)

        # Test action mark ready
        result = delivery_order.action_mark_ready()

        # Verifikasi hasil
        self.assertEqual(delivery_order.state, 'confirmed')
        self.assertIn('Marked as ready to deliver', delivery_order.notes)
        self.assertEqual(result['type'], 'ir.actions.client')

    def test_action_mark_ready_incomplete_data(self):
        """Test 5: Test action_mark_ready dengan data tidak lengkap"""
        delivery_order = self.env['delivery.order'].create(self.delivery_data)

        # Test action mark ready tanpa driver, vehicle, atau delivery time
        result = delivery_order.action_mark_ready()

        # Verifikasi bahwa state tidak berubah
        self.assertEqual(delivery_order.state, 'draft')
        self.assertEqual(result['type'], 'ir.actions.client')

    def test_action_confirm_with_tracking(self):
        """Test 6: Test override method action_confirm"""
        delivery_order = self.env['delivery.order'].create(self.delivery_data)

        # Confirm order tanpa delivery_time
        delivery_order.action_confirm()

        # Verifikasi bahwa delivery_time otomatis diisi
        self.assertIsNotNone(delivery_order.delivery_time)
        self.assertEqual(delivery_order.state, 'confirmed')

    def test_delivery_time_validation(self):
        """Test 7: Test validasi delivery time tidak boleh di masa lalu"""
        delivery_data = self.delivery_data.copy()
        past_time = fields.Datetime.now() - timedelta(days=1)
        delivery_data['delivery_time'] = past_time

        # Test bahwa validasi error muncul saat delivery time di masa lalu
        with self.assertRaises(ValidationError):
            self.env['delivery.order'].create(delivery_data)

    def test_inherit_field_accessibility(self):
        """Test 8: Test bahwa field original masih bisa diakses"""
        delivery_order = self.env['delivery.order'].create(self.delivery_data)

        # Test field original
        self.assertEqual(delivery_order.customer_id.name, 'Test Customer Tracking')
        self.assertEqual(delivery_order.product_id.name, 'Test Product Tracking')
        self.assertEqual(delivery_order.quantity, 10.0)
        self.assertEqual(delivery_order.unit_price, 50.0)
        self.assertEqual(delivery_order.total_amount, 500.0)  # 10 * 50

    def test_tracking_fields_default_values(self):
        """Test 9: Test default values untuk field tracking"""
        delivery_order = self.env['delivery.order'].create(self.delivery_data)

        # Verifikasi default values
        self.assertFalse(delivery_order.driver_name)
        self.assertFalse(delivery_order.vehicle_number)
        self.assertFalse(delivery_order.delivery_time)
        self.assertEqual(delivery_order.state, 'draft') 