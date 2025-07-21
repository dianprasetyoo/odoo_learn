from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date
from odoo import fields


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

    def test_03_get_date(self):
        """
        Test 3: Test method _get_date
        """
        # Membuat delivery order
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        
        # Memanggil method _get_date
        result_date = delivery_order._get_date()
        
        # Memverifikasi bahwa _get_date mengembalikan tanggal hari ini
        expected_date = fields.Date.context_today(delivery_order)
        self.assertEqual(result_date, expected_date, 
                        f"_get_date harus mengembalikan {expected_date}, bukan {result_date}")
        
        # Memverifikasi bahwa hasil adalah instance dari date
        self.assertIsInstance(result_date, date, 
                            "_get_date harus mengembalikan instance dari date")

    def test_check_quantity_positive(self):
        """
        Test 4: Check quantity positive constraint
        """
        # Test case 1: Quantity positif (harus berhasil)
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        self.assertGreater(delivery_order.quantity, 0, "Quantity harus positif")
        
        # Test case 2: Quantity = 0 (harus gagal dengan ValidationError)
        invalid_data = self.delivery_data.copy()
        invalid_data['quantity'] = 0.0
        
        with self.assertRaises(ValidationError) as context:
            self.env['delivery.order'].create(invalid_data)
        
        self.assertIn("Quantity must be greater than 0", str(context.exception))
        
        # Test case 3: Quantity negatif (harus gagal dengan ValidationError)
        invalid_data['quantity'] = -5.0
        
        with self.assertRaises(ValidationError) as context:
            self.env['delivery.order'].create(invalid_data)
        
        self.assertIn("Quantity must be greater than 0", str(context.exception))
        
        # Test case 4: Update quantity menjadi 0 (harus gagal dengan ValidationError)
        with self.assertRaises(ValidationError) as context:
            delivery_order.quantity = 0.0
        
        self.assertIn("Quantity must be greater than 0", str(context.exception))

    def test_check_unit_price_non_negative(self):
        """
        Test 5: Check unit price non-negative constraint
        """
        # Test case 1: Unit price positif (harus berhasil)
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        self.assertGreaterEqual(delivery_order.unit_price, 0, "Unit price harus non-negatif")
        
        # Test case 2: Unit price = 0 (harus berhasil)
        valid_data = self.delivery_data.copy()
        valid_data['unit_price'] = 0.0
        delivery_order_zero = self.env['delivery.order'].create(valid_data)
        self.assertEqual(delivery_order_zero.unit_price, 0.0, "Unit price 0 harus berhasil dibuat")
        
        # Test case 3: Unit price negatif (harus gagal dengan ValidationError)
        invalid_data = self.delivery_data.copy()
        invalid_data['unit_price'] = -10.0
        
        with self.assertRaises(ValidationError) as context:
            self.env['delivery.order'].create(invalid_data)
        
        self.assertIn("Unit price cannot be negative", str(context.exception))
        
        # Test case 4: Update unit price menjadi negatif (harus gagal dengan ValidationError)
        with self.assertRaises(ValidationError) as context:
            delivery_order.unit_price = -5.0
        
        self.assertIn("Unit price cannot be negative", str(context.exception))

    def test_action_confirm(self):
        """
        Test 6: Test action_confirm method
        """
        # Membuat delivery order dengan state draft
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        self.assertEqual(delivery_order.state, 'draft', "State awal harus 'draft'")
        
        # Memanggil action_confirm
        delivery_order.action_confirm()
        
        # Memverifikasi bahwa state berubah menjadi 'confirmed'
        self.assertEqual(delivery_order.state, 'confirmed', 
                        "State harus berubah menjadi 'confirmed' setelah action_confirm")

    def test_action_deliver(self):
        """
        Test 7: Test action_deliver method
        """
        # Membuat delivery order dengan state draft
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        self.assertEqual(delivery_order.state, 'draft', "State awal harus 'draft'")
        
        # Memanggil action_deliver
        delivery_order.action_deliver()
        
        # Memverifikasi bahwa state berubah menjadi 'delivered'
        self.assertEqual(delivery_order.state, 'delivered', 
                        "State harus berubah menjadi 'delivered' setelah action_deliver")

    def test_unlink_draft_order(self):
        """
        Test 8: Test unlink method untuk draft order
        """
        # Membuat delivery order dengan state draft
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        self.assertEqual(delivery_order.state, 'draft', "State harus 'draft'")
        
        # Menyimpan ID untuk verifikasi
        delivery_order_id = delivery_order.id
        
        # Memanggil unlink (delete)
        delivery_order.unlink()
        
        # Memverifikasi bahwa record berhasil dihapus
        deleted_order = self.env['delivery.order'].browse(delivery_order_id)
        self.assertFalse(deleted_order.exists(), "Draft order harus berhasil dihapus")

    def test_unlink_confirmed_order(self):
        """
        Test 9: Test unlink method untuk confirmed order (harus gagal)
        """
        # Membuat delivery order dan mengkonfirmasi
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        delivery_order.action_confirm()
        self.assertEqual(delivery_order.state, 'confirmed', "State harus 'confirmed'")
        
        # Mencoba menghapus confirmed order (harus gagal)
        with self.assertRaises(UserError) as context:
            delivery_order.unlink()
        
        self.assertIn("Only draft delivery orders can be deleted", str(context.exception))

    def test_unlink_delivered_order(self):
        """
        Test 10: Test unlink method untuk delivered order (harus gagal)
        """
        # Membuat delivery order dan mengirim
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        delivery_order.action_deliver()
        self.assertEqual(delivery_order.state, 'delivered', "State harus 'delivered'")
        
        # Mencoba menghapus delivered order (harus gagal)
        with self.assertRaises(UserError) as context:
            delivery_order.unlink()
        
        self.assertIn("Only draft delivery orders can be deleted", str(context.exception))