from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from odoo import exceptions, fields
from datetime import date, datetime


class TestMonthlySummary(TransactionCase):
    """Unit test for model MonthlySummary"""
    def setUp(self):
        """Setup method that runs before each test"""
        super(TestMonthlySummary, self).setUp()
        
        # Create customer for testing
        self.customer = self.env['res.partner'].create({
            'name': 'Test Customer',
            'is_company': True,
        })
        
        # Create additional customers for testing
        self.customer2 = self.env['res.partner'].create({
            'name': 'Test Customer 2',
            'is_company': True,
        })
        
        # Create product for testing
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
            'list_price': 50.0,
        })
        
        # Create additional product for testing
        self.product2 = self.env['product.product'].create({
            'name': 'Test Product 2',
            'type': 'consu',
            'list_price': 75.0,
        })
        
        # Create delivery orders for testing
        self.delivery_order1 = self.env['delivery.order'].create({
            'customer_id': self.customer.id,
            'delivery_date': date(2024, 1, 15),
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_price': 50.0,
            'notes': 'Test delivery order 1',
            'state': 'confirmed',
        })
        
        self.delivery_order2 = self.env['delivery.order'].create({
            'customer_id': self.customer.id,
            'delivery_date': date(2024, 1, 20),
            'product_id': self.product2.id,
            'quantity': 5.0,
            'unit_price': 75.0,
            'notes': 'Test delivery order 2',
            'state': 'delivered',
        })
        
        self.delivery_order3 = self.env['delivery.order'].create({
            'customer_id': self.customer2.id,
            'delivery_date': date(2024, 1, 25),
            'product_id': self.product.id,
            'quantity': 8.0,
            'unit_price': 50.0,
            'notes': 'Test delivery order 3',
            'state': 'draft',
        })
        
        # Create monthly summary for testing
        self.monthly_summary = self.env['monthly.summary'].create({
            'name': 'January 2024 Summary',
            'month': 'january',
            'year': 2024,
            'summary_date': date(2024, 1, 31),
            'state': 'draft',
        })
        
        # Base data for creating new delivery orders
        self.delivery_data = {
            'customer_id': self.customer.id,
            'delivery_date': date.today(),
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_price': 50.0,
            'notes': 'Test delivery order',
        }

    def test_create_monthly_summary(self):
        """Test 1: Create new monthly summary"""
        # Create monthly summary
        monthly_summary = self.env['monthly.summary'].create({
            'name': 'February 2024 Summary',
            'month': 'february',
            'year': 2024,
            'summary_date': date(2024, 2, 28),
        })
        
        # Verify that monthly summary was created successfully
        self.assertTrue(monthly_summary.id, "Monthly summary harus berhasil dibuat")
        self.assertEqual(monthly_summary.name, 'February 2024 Summary')
        self.assertEqual(monthly_summary.month, 'february')
        self.assertEqual(monthly_summary.year, 2024)
        self.assertEqual(monthly_summary.state, 'draft', "State default harus 'draft'")
        self.assertEqual(monthly_summary.date_range, 'February 2024')

    def test_compute_total_orders(self):
        """Test 2: Compute total orders"""
        # Link delivery orders to monthly summary
        self.monthly_summary.delivery_order_ids = [(6, 0, [
            self.delivery_order1.id,
            self.delivery_order2.id,
            self.delivery_order3.id
        ])]
        
        # Trigger computation
        self.monthly_summary._compute_total_orders()
        
        # Verify total orders
        self.assertEqual(self.monthly_summary.total_orders, 3, "Total orders harus 3")

    def test_compute_total_amount(self):
        """Test 3: Compute total amount"""
        # Link delivery orders to monthly summary
        self.monthly_summary.delivery_order_ids = [(6, 0, [
            self.delivery_order1.id,
            self.delivery_order2.id,
            self.delivery_order3.id
        ])]
        
        # Trigger computation
        self.monthly_summary._compute_total_amount()
        
        # Calculate expected total amount
        # delivery_order1: 10.0 * 50.0 = 500.0
        # delivery_order2: 5.0 * 75.0 = 375.0  
        # delivery_order3: 8.0 * 50.0 = 400.0
        # Total: 500.0 + 375.0 + 400.0 = 1275.0
        expected_total = 500.0 + 375.0 + 400.0
        
        # Verify total amount
        self.assertEqual(self.monthly_summary.total_amount, expected_total, 
                        f"Total amount harus {expected_total}, bukan {self.monthly_summary.total_amount}")

    def test_compute_top_customer(self):
        """Test 4: Compute top customer"""
        # Link delivery orders to monthly summary
        self.monthly_summary.delivery_order_ids = [(6, 0, [
            self.delivery_order1.id,
            self.delivery_order2.id,
            self.delivery_order3.id
        ])]
        
        # Trigger computation
        self.monthly_summary._compute_top_customer()
        
        # Calculate expected top customer
        # customer (delivery_order1 + delivery_order2): 500.0 + 375.0 = 875.0
        # customer2 (delivery_order3): 400.0
        # customer should be top customer since 875.0 > 400.0
        
        # Verify top customer
        self.assertEqual(self.monthly_summary.top_customer_id, self.customer, 
                        f"Top customer harus {self.customer.name}, bukan {self.monthly_summary.top_customer_id.name if self.monthly_summary.top_customer_id else 'None'}")

    def test_compute_top_customer_no_orders(self):
        """Test 5: Compute top customer with no delivery orders"""
        # Create monthly summary without delivery orders
        empty_monthly_summary = self.env['monthly.summary'].create({
            'name': 'Empty Summary',
            'month': 'february',
            'year': 2024,
            'summary_date': date(2024, 2, 28),
        })
        
        # Trigger computation
        empty_monthly_summary._compute_top_customer()
        
        # Verify top customer is False when no orders
        self.assertFalse(empty_monthly_summary.top_customer_id, 
                        "Top customer harus False ketika tidak ada delivery orders")

    def test_compute_average_order_value(self):
        """Test 7: Compute average order value with multiple orders"""
        # Link delivery orders to monthly summary
        self.monthly_summary.delivery_order_ids = [(6, 0, [
            self.delivery_order1.id,
            self.delivery_order2.id,
            self.delivery_order3.id
        ])]
        
        # Trigger computation
        self.monthly_summary._compute_average_order_value()
        
        # Calculate expected average order value
        # delivery_order1: 10.0 * 50.0 = 500.0
        # delivery_order2: 5.0 * 75.0 = 375.0  
        # delivery_order3: 8.0 * 50.0 = 400.0
        # Total: 500.0 + 375.0 + 400.0 = 1275.0
        # Average: 1275.0 / 3 = 425.0
        expected_total = 500.0 + 375.0 + 400.0
        expected_average = expected_total / 3
        
        # Verify average order value
        self.assertEqual(self.monthly_summary.average_order_value, expected_average, 
                        f"Average order value harus {expected_average}, bukan {self.monthly_summary.average_order_value}")

    def test_compute_average_order_value_no_orders(self):
        """Test 8: Compute average order value with no delivery orders"""
        # Create monthly summary without delivery orders
        empty_monthly_summary = self.env['monthly.summary'].create({
            'name': 'Empty Summary',
            'month': 'february',
            'year': 2024,
            'summary_date': date(2024, 2, 28),
        })
        
        # Trigger computation
        empty_monthly_summary._compute_average_order_value()
        
        # Verify average order value is 0.0 when no orders
        self.assertEqual(empty_monthly_summary.average_order_value, 0.0, 
                        "Average order value harus 0.0 ketika tidak ada delivery orders")

    def test_compute_average_order_value_single_order(self):
        """Test 9: Compute average order value with single order"""
        # Create delivery order for single order only
        self.monthly_summary.delivery_order_ids = [(6, 0, [
            self.delivery_order1.id
        ])]
        
        # Trigger computation
        self.monthly_summary._compute_average_order_value()
        
        # Calculate expected average order value
        # delivery_order1: 10.0 * 50.0 = 500.0
        # Average: 500.0 / 1 = 500.0
        expected_average = 500.0
        
        # Verify average order value
        self.assertEqual(self.monthly_summary.average_order_value, expected_average, 
                        f"Average order value harus {expected_average}, bukan {self.monthly_summary.average_order_value}")

    def test_compute_delivered_orders(self):
        """Test 11: Compute delivered orders with mixed states"""
        # Link delivery orders to monthly summary
        self.monthly_summary.delivery_order_ids = [(6, 0, [
            self.delivery_order1.id,  # state: 'confirmed'
            self.delivery_order2.id,  # state: 'delivered'
            self.delivery_order3.id   # state: 'draft'
        ])]
        
        # Trigger computation
        self.monthly_summary._compute_delivered_orders()
        
        # Expected delivered orders: only delivery_order2 (state: 'delivered')
        expected_delivered_orders = 1
        
        # Verify delivered orders count
        self.assertEqual(self.monthly_summary.delivered_orders, expected_delivered_orders, 
                        f"Delivered orders harus {expected_delivered_orders}, bukan {self.monthly_summary.delivered_orders}")

    def test_compute_confirmed_orders(self):
        """Test 12: Compute confirmed orders with mixed states"""
        # Link delivery orders to monthly summary
        self.monthly_summary.delivery_order_ids = [(6, 0, [
            self.delivery_order1.id,  # state: 'confirmed'
            self.delivery_order2.id,  # state: 'delivered'
            self.delivery_order3.id   # state: 'draft'
        ])]
        
        # Trigger computation
        self.monthly_summary._compute_confirmed_orders()
        
        # Expected confirmed orders: only delivery_order1 (state: 'confirmed')
        expected_confirmed_orders = 1
        
        # Verify confirmed orders count
        self.assertEqual(self.monthly_summary.confirmed_orders, expected_confirmed_orders, 
                        f"Confirmed orders harus {expected_confirmed_orders}, bukan {self.monthly_summary.confirmed_orders}")

    def test_onchange_month_year_logic(self):
        """Test 14: Test onchange month year logic"""
        # Create monthly summary for February 2024
        feb_summary = self.env['monthly.summary'].create({
            'name': 'February 2024 Summary',
            'month': 'february',
            'year': 2024,
            'summary_date': date(2024, 2, 28),
        })
        
        try:
            feb_summary._onchange_month_year()
            # If no exception is raised, the method executed successfully
            self.assertTrue(True, "Onchange method harus berhasil dieksekusi")
        except Exception as e:
            self.fail(f"Onchange method gagal dieksekusi: {str(e)}")

    def test_update_delivery_orders_february_boundary(self):
        """Test 14: Test _update_delivery_orders with February (28 days)"""
        # Create delivery orders for February 2024 (28 days)
        feb_first_order = self.env['delivery.order'].create({
            'customer_id': self.customer.id,
            'delivery_date': date(2024, 2, 1),  # First day of February
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_price': 50.0,
            'notes': 'February 1st order',
            'state': 'confirmed',
        })
        
        feb_last_order = self.env['delivery.order'].create({
            'customer_id': self.customer2.id,
            'delivery_date': date(2024, 2, 28),  # Last day of February (28 days)
            'product_id': self.product2.id,
            'quantity': 5.0,
            'unit_price': 75.0,
            'notes': 'February 28th order',
            'state': 'delivered',
        })
        
        # Create monthly summary for February 2024
        feb_summary = self.env['monthly.summary'].create({
            'name': 'February 2024 Summary',
            'month': 'february',
            'year': 2024,
            'summary_date': date(2024, 2, 28),
        })
        
        # Trigger the update method
        feb_summary._update_delivery_orders()
        
        # Verify that both boundary orders are included (should not cause date overflow error)
        self.assertIn(feb_first_order.id, feb_summary.delivery_order_ids.ids, 
                     "February 1st order harus ter-populate")
        self.assertIn(feb_last_order.id, feb_summary.delivery_order_ids.ids, 
                     "February 28th order harus ter-populate")
        self.assertEqual(len(feb_summary.delivery_order_ids), 2, 
                        "Harus ada 2 delivery orders untuk February 2024 (28 days)")

    def test_update_delivery_orders_missing_month_or_year(self):
        """Test 15: Test _update_delivery_orders when month or year is missing"""
        
        # Create monthly summary with valid values first (using different month/year to avoid unique constraint)
        summary_test = self.env['monthly.summary'].create({
            'name': 'Test Summary',
            'month': 'march',
            'year': 2025,
            'summary_date': date(2025, 3, 31),
        })
        
        # Test missing month by temporarily setting it to None
        original_month = summary_test.month
        summary_test.month = None
        
        # Test that method returns early without error when month is missing
        try:
            summary_test._update_delivery_orders()
            self.assertEqual(len(summary_test.delivery_order_ids), 0, 
                           "Delivery orders harus kosong ketika month missing")
        except Exception as e:
            self.fail(f"Method harus return early tanpa error ketika month missing: {str(e)}")
        
        # Restore month and test missing year
        summary_test.month = original_month
        original_year = summary_test.year
        summary_test.year = None
        
        # Test that method returns early without error when year is missing
        try:
            summary_test._update_delivery_orders()
            self.assertEqual(len(summary_test.delivery_order_ids), 0, 
                           "Delivery orders harus kosong ketika year missing")
        except Exception as e:
            self.fail(f"Method harus return early tanpa error ketika year missing: {str(e)}")
        
        # Restore year and test both missing
        summary_test.year = original_year
        summary_test.month = None
        summary_test.year = None
        
        # Test that method returns early without error when both are missing
        try:
            summary_test._update_delivery_orders()
            self.assertEqual(len(summary_test.delivery_order_ids), 0, 
                           "Delivery orders harus kosong ketika month dan year missing")
        except Exception as e:
            self.fail(f"Method harus return early tanpa error ketika month dan year missing: {str(e)}")

    def test_action_confirm(self):
        """Test 16: Test action_confirm method"""
        # Create monthly summary in draft state
        summary_test = self.env['monthly.summary'].create({
            'name': 'Test Summary for Confirm',
            'month': 'april',
            'year': 2025,
            'summary_date': date(2025, 4, 30),
            'state': 'draft',
        })
        
        # Verify initial state is draft
        self.assertEqual(summary_test.state, 'draft', "Initial state harus 'draft'")
        
        # Call action_confirm
        summary_test.action_confirm()
        
        # Verify state changed to confirmed
        self.assertEqual(summary_test.state, 'confirmed', 
                        f"State harus berubah ke 'confirmed', bukan '{summary_test.state}'")

    def test_action_processed(self):
        """Test 17: Test action_processed method"""
        # Create monthly summary in confirmed state
        summary_test = self.env['monthly.summary'].create({
            'name': 'Test Summary for Process',
            'month': 'may',
            'year': 2025,
            'summary_date': date(2025, 5, 31),
            'state': 'confirmed',
        })
        
        # Verify initial state is confirmed
        self.assertEqual(summary_test.state, 'confirmed', "Initial state harus 'confirmed'")
        
        # Call action_processed
        summary_test.action_processed()
        
        # Verify state changed to processed
        self.assertEqual(summary_test.state, 'processed', 
                        f"State harus berubah ke 'processed', bukan '{summary_test.state}'")

    def test_action_refresh_orders(self):
        """Test 18: Test action_refresh_orders method"""
        # Create delivery orders for June 2025
        june_order1 = self.env['delivery.order'].create({
            'customer_id': self.customer.id,
            'delivery_date': date(2025, 6, 10),
            'product_id': self.product.id,
            'quantity': 15.0,
            'unit_price': 50.0,
            'notes': 'June order 1',
            'state': 'confirmed',
        })
        
        june_order2 = self.env['delivery.order'].create({
            'customer_id': self.customer2.id,
            'delivery_date': date(2025, 6, 20),
            'product_id': self.product2.id,
            'quantity': 8.0,
            'unit_price': 75.0,
            'notes': 'June order 2',
            'state': 'delivered',
        })
        
        # Create monthly summary for June 2025
        summary_test = self.env['monthly.summary'].create({
            'name': 'Test Summary for Refresh',
            'month': 'june',
            'year': 2025,
            'summary_date': date(2025, 6, 30),
            'state': 'draft',
        })
        
        # Verify initial state has no delivery orders
        self.assertEqual(len(summary_test.delivery_order_ids), 0, 
                        "Initial delivery orders harus kosong")
        
        # Call action_refresh_orders
        result = summary_test.action_refresh_orders()
        
        # Verify delivery orders are populated
        self.assertIn(june_order1.id, summary_test.delivery_order_ids.ids, 
                     "June order 1 harus ter-populate")
        self.assertIn(june_order2.id, summary_test.delivery_order_ids.ids, 
                     "June order 2 harus ter-populate")
        self.assertEqual(len(summary_test.delivery_order_ids), 2, 
                        "Harus ada 2 delivery orders untuk June 2025")
        
        # Verify the action returns correct notification
        self.assertEqual(result['type'], 'ir.actions.client', 
                        "Action harus return ir.actions.client")
        self.assertEqual(result['tag'], 'display_notification', 
                        "Action tag harus 'display_notification'")
        self.assertEqual(result['params']['title'], 'Orders Updated', 
                        "Notification title harus 'Orders Updated'")
        self.assertIn('June 2025', result['params']['message'], 
                     "Notification message harus mengandung 'June 2025'")
        self.assertEqual(result['params']['type'], 'success', 
                        "Notification type harus 'success'")
        self.assertFalse(result['params']['sticky'], 
                        "Notification sticky harus False")
