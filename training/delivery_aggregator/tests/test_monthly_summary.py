from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime
from odoo import fields


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

    def test_compute_top_customer_single_customer(self):
        """Test 6: Compute top customer with single customer"""
        # Create delivery order for customer2 only
        self.monthly_summary.delivery_order_ids = [(6, 0, [
            self.delivery_order3.id
        ])]
        
        # Trigger computation
        self.monthly_summary._compute_top_customer()
        
        # Verify top customer is customer2
        self.assertEqual(self.monthly_summary.top_customer_id, self.customer2, 
                        f"Top customer harus {self.customer2.name}, bukan {self.monthly_summary.top_customer_id.name if self.monthly_summary.top_customer_id else 'None'}")

    