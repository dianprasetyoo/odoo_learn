from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import fields


class TestSaleOrderIntegration(TransactionCase):
    """Unit test for SaleOrder integration with delivery orders"""

    def setUp(self):
        """Setup method that runs before each test"""
        super(TestSaleOrderIntegration, self).setUp()
        
        # Create customer for testing
        self.customer = self.env['res.partner'].create({
            'name': 'Test Customer',
        })
        
        # Create product for testing
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
        })
        
        # Create sale order for testing
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'date_order': fields.Date.today(),
            'state': 'draft',
        })
        
        # Create sale order line
        self.sale_order_line = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': self.product.id,
            'name': 'Test Product',
            'product_uom_qty': 10,
            'price_unit': 100.0,
        })

    def test_01_compute_delivery_order_count(self):
        """Test 1: Test _compute_delivery_order_count for SaleOrder"""
        # Initially no delivery orders
        self.assertEqual(self.sale_order.delivery_order_count, 0,
                        "Initial delivery order count should be 0")
        
        # Create a delivery order
        delivery_order = self.env['delivery.order'].create({
            'name': 'Test Delivery Order',
            'customer_id': self.customer.id,
            'delivery_date': fields.Date.today(),
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_price': 100.0,
            'sale_order_id': self.sale_order.id,
        })
        
        # Trigger compute
        self.sale_order._compute_delivery_order_count()
        
        # Verify count is updated
        self.assertEqual(self.sale_order.delivery_order_count, 1,
                        "Delivery order count should be 1 after creating delivery order")

    def test_02_compute_delivery_order_count_line(self):
        """Test 2: Test _compute_delivery_order_count for SaleOrderLine"""
        # Initially no delivery orders
        self.assertEqual(self.sale_order_line.delivery_order_count, 0,
                        "Initial delivery order count should be 0")
        
        # Create a delivery order for the line
        delivery_order = self.env['delivery.order'].create({
            'name': 'Test Delivery Order Line',
            'customer_id': self.customer.id,
            'delivery_date': fields.Date.today(),
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_price': 100.0,
            'sale_order_line_id': self.sale_order_line.id,
        })
        
        # Trigger compute
        self.sale_order_line._compute_delivery_order_count()
        
        # Verify count is updated
        self.assertEqual(self.sale_order_line.delivery_order_count, 1,
                        "Delivery order count should be 1 after creating delivery order")

    def test_03_action_create_delivery_orders_draft(self):
        """Test 3: Test action_create_delivery_orders for draft quotation"""
        # Sale order is in draft state
        self.assertEqual(self.sale_order.state, 'draft')
        
        # Call the action
        result = self.sale_order.action_create_delivery_orders()
        
        # Should return wizard action for draft quotations
        self.assertEqual(result['res_model'], 'delivery.create.from.quotation.wizard')
        self.assertEqual(result['target'], 'new')
        self.assertEqual(result['context']['default_sale_order_id'], self.sale_order.id)

    def test_04_action_create_delivery_orders_existing(self):
        """Test 4: Test action_create_delivery_orders with existing delivery orders"""
        # Create existing delivery order
        self.env['delivery.order'].create({
            'name': 'Existing Delivery Order',
            'customer_id': self.customer.id,
            'delivery_date': fields.Date.today(),
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_price': 100.0,
            'sale_order_id': self.sale_order.id,
        })
        
        # Should raise UserError
        with self.assertRaises(UserError) as context:
            self.sale_order.action_create_delivery_orders()
        
        self.assertIn("Delivery orders already exist", str(context.exception))

    def test_05_action_view_delivery_orders(self):
        """Test 5: Test action_view_delivery_orders"""
        # No delivery orders exist, should call create action
        result = self.sale_order.action_view_delivery_orders()
        
        # Should return create delivery orders action
        self.assertEqual(result['res_model'], 'delivery.create.from.quotation.wizard')
        
        # Create delivery order and test view action
        self.env['delivery.order'].create({
            'name': 'Existing Delivery Order',
            'customer_id': self.customer.id,
            'delivery_date': fields.Date.today(),
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_price': 100.0,
            'sale_order_id': self.sale_order.id,
        })
        
        result = self.sale_order.action_view_delivery_orders()
        
        # Should return delivery order list view
        self.assertEqual(result['res_model'], 'delivery.order')
        self.assertEqual(result['view_mode'], 'list,form')

    def test_06_action_create_delivery_from_quotation(self):
        """Test 6: Test action_create_delivery_from_quotation"""
        # Sale order is in draft state
        self.assertEqual(self.sale_order.state, 'draft')
        
        # Call the action
        result = self.sale_order.action_create_delivery_from_quotation()
        
        # Should return delivery order list view
        self.assertEqual(result['res_model'], 'delivery.order')
        self.assertEqual(result['view_mode'], 'list,form')

    def test_07_action_create_delivery_from_quotation_confirmed(self):
        """Test 7: Test action_create_delivery_from_quotation for confirmed order"""
        # Confirm the sale order
        self.sale_order.action_confirm()
        
        # Should raise UserError for confirmed orders
        with self.assertRaises(UserError) as context:
            self.sale_order.action_create_delivery_from_quotation()
        
        self.assertIn("only available for draft quotations", str(context.exception))

    def test_08_action_create_delivery_order_line_draft(self):
        """Test 8: Test action_create_delivery_order for draft quotation line"""
        # Sale order is in draft state
        self.assertEqual(self.sale_order.state, 'draft')
        
        # Call the action
        result = self.sale_order_line.action_create_delivery_order()
        
        # Should return wizard action for draft quotations
        self.assertEqual(result['res_model'], 'delivery.create.from.quotation.wizard')
        self.assertEqual(result['target'], 'new')
        self.assertEqual(result['context']['default_sale_order_line_id'], self.sale_order_line.id)

    def test_09_action_create_delivery_order_line_existing(self):
        """Test 9: Test action_create_delivery_order with existing delivery order"""
        # Create existing delivery order for the line
        self.env['delivery.order'].create({
            'name': 'Existing Delivery Order Line',
            'customer_id': self.customer.id,
            'delivery_date': fields.Date.today(),
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_price': 100.0,
            'sale_order_line_id': self.sale_order_line.id,
        })
        
        # Should raise UserError
        with self.assertRaises(UserError) as context:
            self.sale_order_line.action_create_delivery_order()
        
        self.assertIn("Delivery order already exists", str(context.exception))

    def test_10_action_view_delivery_orders_line(self):
        """Test 10: Test action_view_delivery_orders for sale order line"""
        # No delivery orders exist, should call create action
        result = self.sale_order_line.action_view_delivery_orders()
        
        # Should return create delivery order action
        self.assertEqual(result['res_model'], 'delivery.create.from.quotation.wizard')
        
        # Create delivery order and test view action
        self.env['delivery.order'].create({
            'name': 'Existing Delivery Order Line',
            'customer_id': self.customer.id,
            'delivery_date': fields.Date.today(),
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_price': 100.0,
            'sale_order_line_id': self.sale_order_line.id,
        })
        
        result = self.sale_order_line.action_view_delivery_orders()
        
        # Should return delivery order list view
        self.assertEqual(result['res_model'], 'delivery.order')
        self.assertEqual(result['view_mode'], 'list,form')
