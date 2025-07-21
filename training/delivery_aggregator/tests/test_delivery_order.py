from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta


class TestDeliveryOrder(TransactionCase):
    """Unit test for model DeliveryOrder"""
    def setUp(self):
        """Setup method that runs before each test"""
        super(TestDeliveryOrder, self).setUp()
        
        # Create customer for testing
        self.customer = self.env['res.partner'].create({
            'name': 'Test Customer',
        })
        
        # Create product for testing
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
        })
        
        # Base data for delivery order
        self.delivery_data = {
            'customer_id': self.customer.id,
            'delivery_date': date.today(),
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_price': 50.0,
            'notes': 'Test delivery order',
        }

    def test_create_delivery_order(self):
        """Test 1: Create new delivery order"""
        # Create delivery order
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        
        # Memverifikasi bahwa delivery order berhasil dibuat
        self.assertTrue(delivery_order.id, "Delivery order harus berhasil dibuat")
        self.assertEqual(delivery_order.customer_id.name, 'Test Customer')
        self.assertEqual(delivery_order.product_id.name, 'Test Product')
        self.assertEqual(delivery_order.quantity, 10.0)
        self.assertEqual(delivery_order.unit_price, 50.0)
        self.assertEqual(delivery_order.state, 'draft', "State default harus 'draft'")

    def test_02_compute_total_amount(self):
        """
        Test 2: Menghitung total amount
        """
        # Membuat delivery order
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        
        # Memverifikasi perhitungan total amount
        expected_total = 10.0 * 50.0  # quantity * unit_price
        self.assertEqual(delivery_order.total_amount, expected_total, 
                        f"Total amount harus {expected_total}, bukan {delivery_order.total_amount}")
        
        # Test perubahan quantity
        delivery_order.quantity = 5.0
        delivery_order._compute_total_amount()  # Memanggil compute method
        new_expected_total = 5.0 * 50.0
        self.assertEqual(delivery_order.total_amount, new_expected_total)
