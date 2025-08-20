from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
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

    def test_get_available_trips_for_date_no_existing_trips(self):
        """
        Test 11: Test get_available_trips_for_date ketika tidak ada trip yang ada
        """
        # Test tanpa customer_id
        available_trips = self.env['delivery.order'].get_available_trips_for_date(date.today())
        self.assertEqual(available_trips, [1], "Ketika tidak ada trip, harus mengembalikan [1]")
        
        # Test dengan customer_id
        available_trips = self.env['delivery.order'].get_available_trips_for_date(date.today(), self.customer.id)
        self.assertEqual(available_trips, [1], "Ketika tidak ada trip untuk customer, harus mengembalikan [1]")

    def test_get_available_trips_for_date_with_existing_trips(self):
        """
        Test 12: Test get_available_trips_for_date dengan trip yang sudah ada
        """
        # Membuat beberapa delivery order dengan trip yang berbeda
        delivery_data_1 = self.delivery_data.copy()
        delivery_data_1['delivery_date'] = date.today()
        delivery_order_1 = self.env['delivery.order'].create(delivery_data_1)
        
        delivery_data_2 = self.delivery_data.copy()
        delivery_data_2['delivery_date'] = date.today()
        delivery_order_2 = self.env['delivery.order'].create(delivery_data_2)
        
        delivery_data_3 = self.delivery_data.copy()
        delivery_data_3['delivery_date'] = date.today()
        delivery_order_3 = self.env['delivery.order'].create(delivery_data_3)
        
        # Trip akan otomatis di-compute: 1, 2, 3
        self.assertEqual(delivery_order_1.trip, '1')
        self.assertEqual(delivery_order_2.trip, '2')
        self.assertEqual(delivery_order_3.trip, '3')
        
        # Test get available trips
        available_trips = self.env['delivery.order'].get_available_trips_for_date(date.today(), self.customer.id)
        self.assertEqual(available_trips, [4], "Trip berikutnya yang tersedia harus 4")
    
    def test_get_available_trips_for_date_no_delivery_date(self):
        """
        Test 16: Test get_available_trips_for_date tanpa delivery_date
        """
        # Test dengan delivery_date = None
        available_trips = self.env['delivery.order'].get_available_trips_for_date(None)
        self.assertEqual(available_trips, [], "Ketika delivery_date None, harus mengembalikan list kosong")
        
        # Test dengan delivery_date = False
        available_trips = self.env['delivery.order'].get_available_trips_for_date(False)
        self.assertEqual(available_trips, [], "Ketika delivery_date False, harus mengembalikan list kosong")

    def test_compute_trip_info(self):
        """
        Test 17: Test _compute_trip_info method
        """
        # Test case 1: Dengan delivery_date dan customer_id
        delivery_order = self.env['delivery.order'].create(self.delivery_data)
        
        # Memanggil _compute_trip_info
        delivery_order._compute_trip_info()
        
        # Memverifikasi bahwa trip_info berhasil di-compute
        self.assertTrue(delivery_order.trip_info, "Trip info harus berhasil di-compute")
        
        # Memverifikasi format trip_info
        trip_info = delivery_order.trip_info
        self.assertIn("Date:", trip_info, "Trip info harus mengandung informasi tanggal")
        self.assertIn("Customer:", trip_info, "Trip info harus mengandung informasi customer")
        self.assertIn("Total Orders:", trip_info, "Trip info harus mengandung total orders")
        self.assertIn("Used Trips:", trip_info, "Trip info harus mengandung used trips")
        self.assertIn("Available Trips:", trip_info, "Trip info harus mengandung available trips")
        self.assertIn("Next Trip:", trip_info, "Trip info harus mengandung next trip")
        
        # Test case 2: Hanya dengan delivery_date (tanpa customer_id)
        delivery_order_no_customer = self.env['delivery.order'].create({
            'delivery_date': date.today(),
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_price': 50.0,
        })
        
        delivery_order_no_customer._compute_trip_info()
        self.assertEqual(delivery_order_no_customer.trip_info, "Please select a customer", 
                        "Trip info harus menampilkan pesan untuk memilih customer")
        
        # Test case 3: Tanpa delivery_date dan customer_id
        delivery_order_no_date = self.env['delivery.order'].create({
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_price': 50.0,
        })
        
        delivery_order_no_date._compute_trip_info()
        self.assertEqual(delivery_order_no_date.trip_info, "Please select a delivery date and customer", 
                        "Trip info harus menampilkan pesan untuk memilih tanggal dan customer")

    def test_get_trip_summary(self):
        """
        Test 18: Test get_trip_summary method
        """
        from datetime import timedelta
        
        # Membuat customer kedua untuk testing
        customer_2 = self.env['res.partner'].create({
            'name': 'Test Customer 2',
        })
        
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Membuat beberapa delivery orders untuk testing
        # Customer 1, hari ini: 2 orders
        delivery_data_1 = self.delivery_data.copy()
        delivery_data_1['delivery_date'] = today
        delivery_order_1 = self.env['delivery.order'].create(delivery_data_1)
        
        delivery_data_2 = self.delivery_data.copy()
        delivery_data_2['delivery_date'] = today
        delivery_order_2 = self.env['delivery.order'].create(delivery_data_2)
        
        # Customer 2, hari ini: 1 order
        delivery_data_3 = self.delivery_data.copy()
        delivery_data_3['customer_id'] = customer_2.id
        delivery_data_3['delivery_date'] = today
        delivery_order_3 = self.env['delivery.order'].create(delivery_data_3)
        
        # Customer 1, besok: 1 order
        delivery_data_4 = self.delivery_data.copy()
        delivery_data_4['delivery_date'] = tomorrow
        delivery_order_4 = self.env['delivery.order'].create(delivery_data_4)
        
        # Test case 1: Get trip summary untuk semua data
        trip_summary_all = self.env['delivery.order'].get_trip_summary()
        
        # Verifikasi struktur dan data
        self.assertIsInstance(trip_summary_all, dict, "Trip summary harus berupa dictionary")
        self.assertGreater(len(trip_summary_all), 0, "Trip summary tidak boleh kosong")
        
        # Verifikasi customer key format
        for customer_key in trip_summary_all.keys():
            self.assertIn('_', customer_key, "Customer key harus dalam format 'date_customer_id'")
        
        # Test case 2: Get trip summary untuk tanggal tertentu
        trip_summary_today = self.env['delivery.order'].get_trip_summary(delivery_date=today)
        
        # Verifikasi data untuk hari ini
        self.assertGreater(len(trip_summary_today), 0, "Trip summary untuk hari ini tidak boleh kosong")
        
        # Verifikasi data untuk customer 1 hari ini
        customer_1_today_key = f"{today.strftime('%Y-%m-%d')}_{self.customer.id}"
        if customer_1_today_key in trip_summary_today:
            customer_1_data = trip_summary_today[customer_1_today_key]
            self.assertEqual(customer_1_data['date'], today.strftime('%Y-%m-%d'))
            self.assertEqual(customer_1_data['customer'], 'Test Customer')
            self.assertEqual(customer_1_data['customer_id'], self.customer.id)
            self.assertEqual(customer_1_data['total_orders'], 2)
            self.assertIn('1', customer_1_data['used_trips'])
            self.assertIn('2', customer_1_data['used_trips'])
            self.assertIsInstance(customer_1_data['available_trips'], list)
        
        # Test case 3: Get trip summary untuk customer tertentu
        trip_summary_customer_1 = self.env['delivery.order'].get_trip_summary(customer_id=self.customer.id)
        
        # Verifikasi data untuk customer 1
        self.assertGreater(len(trip_summary_customer_1), 0, "Trip summary untuk customer 1 tidak boleh kosong")
        
        # Verifikasi bahwa semua data adalah untuk customer 1
        for customer_key, data in trip_summary_customer_1.items():
            self.assertEqual(data['customer_id'], self.customer.id)
            self.assertEqual(data['customer'], 'Test Customer')
        
        # Test case 4: Get trip summary untuk kombinasi tanggal dan customer
        trip_summary_specific = self.env['delivery.order'].get_trip_summary(
            delivery_date=today, 
            customer_id=self.customer.id
        )
        
        # Verifikasi data spesifik
        self.assertGreater(len(trip_summary_specific), 0, "Trip summary spesifik tidak boleh kosong")
        
        # Verifikasi bahwa hanya ada satu entry untuk kombinasi ini
        customer_1_today_key = f"{today.strftime('%Y-%m-%d')}_{self.customer.id}"
        self.assertIn(customer_1_today_key, trip_summary_specific)
        
        specific_data = trip_summary_specific[customer_1_today_key]
        self.assertEqual(specific_data['total_orders'], 2)
        self.assertEqual(len(specific_data['used_trips']), 2)
        self.assertIsInstance(specific_data['available_trips'], list)