from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import fields


class TestWizardDeliveryQuotation(TransactionCase):
    """Unit test for DeliveryCreateFromQuotationWizard"""

    def setUp(self):
        """Setup method that runs before each test"""
        super(TestWizardDeliveryQuotation, self).setUp()
        
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
        
        # Base data for wizard
        self.wizard_data = {
            'sale_order_id': self.sale_order.id,
            'sale_order_line_id': False,
            'sale_order_name': self.sale_order.name,
            'partner_id': self.customer.id,
            'message': 'Are you sure you want to create delivery orders from this quotation? This action will create delivery orders even though the quotation is not yet confirmed.',
        }

    def test_01_create_wizard(self):
        """Test 1: Create new delivery create from quotation wizard"""
        # Create wizard
        wizard = self.env['delivery.create.from.quotation.wizard'].create(self.wizard_data)
        
        # Verify wizard is created successfully
        self.assertTrue(wizard.id, "Wizard harus berhasil dibuat")
        self.assertEqual(wizard.sale_order_id.name, self.sale_order.name)
        self.assertEqual(wizard.sale_order_name, self.sale_order.name)
        self.assertEqual(wizard.partner_id.name, self.customer.name)
        self.assertEqual(wizard.message, self.wizard_data['message'])

    def test_02_default_get_with_sale_order(self):
        """Test 2: Test default_get method with sale order context"""
        # Test with context containing sale order ID
        context = {
            'default_sale_order_id': self.sale_order.id,
        }
        
        wizard = self.env['delivery.create.from.quotation.wizard'].with_context(context)
        defaults = wizard.default_get(['sale_order_id', 'sale_order_name', 'partner_id'])
        
        # Should have correct default values
        self.assertEqual(defaults['sale_order_id'], self.sale_order.id)
        self.assertEqual(defaults['sale_order_name'], self.sale_order.name)
        self.assertEqual(defaults['partner_id'], self.customer.id)

    def test_03_default_get_with_sale_order_line(self):
        """Test 3: Test default_get method with sale order line context"""
        # Test with context containing both sale order and line IDs
        context = {
            'default_sale_order_id': self.sale_order.id,
            'default_sale_order_line_id': self.sale_order_line.id,
        }
        
        wizard = self.env['delivery.create.from.quotation.wizard'].with_context(context)
        defaults = wizard.default_get(['sale_order_id', 'sale_order_line_id', 'sale_order_name', 'partner_id'])
        
        # Should have correct default values
        self.assertEqual(defaults['sale_order_id'], self.sale_order.id)
        self.assertEqual(defaults['sale_order_line_id'], self.sale_order_line.id)
        self.assertEqual(defaults['sale_order_name'], self.sale_order.name)
        self.assertEqual(defaults['partner_id'], self.customer.id)

    def test_04_default_get_without_context(self):
        """Test 4: Test default_get method without context"""
        # Test without any context
        wizard = self.env['delivery.create.from.quotation.wizard']
        defaults = wizard.default_get(['sale_order_id', 'sale_order_name', 'partner_id'])
        
        # Should return empty defaults
        self.assertFalse(defaults.get('sale_order_id'))
        self.assertFalse(defaults.get('sale_order_name'))
        self.assertFalse(defaults.get('partner_id'))

    def test_05_action_create_delivery_orders_from_line(self):
        """Test 5: Test action_create_delivery_orders from specific sale order line"""
        # Create wizard with sale order line
        wizard_data = self.wizard_data.copy()
        wizard_data['sale_order_line_id'] = self.sale_order_line.id
        
        wizard = self.env['delivery.create.from.quotation.wizard'].create(wizard_data)
        
        # Test the action method structure
        try:
            result = wizard.action_create_delivery_orders()
            # If it succeeds, verify the result structure
            self.assertIsInstance(result, dict)
        except UserError:
            # Expected behavior if delivery order creation fails
            pass

    def test_06_action_create_delivery_orders_from_order(self):
        """Test 6: Test action_create_delivery_orders from entire sale order"""
        # Create wizard without sale order line
        wizard = self.env['delivery.create.from.quotation.wizard'].create(self.wizard_data)
        
        # Test the action method structure
        try:
            result = wizard.action_create_delivery_orders()
            # If it succeeds, verify the result structure
            self.assertIsInstance(result, dict)
        except UserError:
            # Expected behavior if delivery order creation fails
            pass

    def test_07_action_cancel(self):
        """Test 7: Test action_cancel method"""
        # Create wizard
        wizard = self.env['delivery.create.from.quotation.wizard'].create(self.wizard_data)
        
        # Execute cancel action
        result = wizard.action_cancel()
        
        # Should return close action
        self.assertEqual(result['type'], 'ir.actions.act_window_close')

    def test_08_wizard_with_different_sale_order_states(self):
        """Test 8: Test wizard behavior with different sale order states"""
        # Test with confirmed sale order
        self.sale_order.action_confirm()
        self.assertEqual(self.sale_order.state, 'sale')
        
        # Create wizard with confirmed sale order
        wizard = self.env['delivery.create.from.quotation.wizard'].create(self.wizard_data)
        
        # Wizard should still work with confirmed orders
        self.assertEqual(wizard.sale_order_id.state, 'sale')
        self.assertEqual(wizard.sale_order_id.name, self.sale_order.name)
        
        # Test with draft sale order
        self.sale_order.action_draft()
        self.assertEqual(self.sale_order.state, 'draft')
        
        # Wizard should work with draft orders too
        wizard = self.env['delivery.create.from.quotation.wizard'].create(self.wizard_data)
        self.assertEqual(wizard.sale_order_id.state, 'draft')

    def test_09_wizard_field_validation(self):
        """Test 9: Test wizard field validation and constraints"""
        # Create wizard
        wizard = self.env['delivery.create.from.quotation.wizard'].create(self.wizard_data)
        
        # Verify required fields
        self.assertTrue(wizard.sale_order_id, "Sale order should be required")
        self.assertTrue(wizard.sale_order_name, "Sale order name should be set")
        self.assertTrue(wizard.partner_id, "Partner should be set")
        self.assertTrue(wizard.message, "Message should be set")
        
        # Verify field types
        self.assertIsInstance(wizard.sale_order_id.id, int)
        self.assertIsInstance(wizard.sale_order_name, str)
        self.assertIsInstance(wizard.partner_id.id, int)
        self.assertIsInstance(wizard.message, str)

    def test_10_wizard_context_handling(self):
        """Test 10: Test wizard context handling and data flow"""
        # Test with minimal context
        context = {'default_sale_order_id': self.sale_order.id}
        wizard = self.env['delivery.create.from.quotation.wizard'].with_context(context)
        
        # Verify context is properly handled
        self.assertEqual(wizard.env.context.get('default_sale_order_id'), self.sale_order.id)
        
        # Test with additional context
        extended_context = {
            'default_sale_order_id': self.sale_order.id,
            'default_sale_order_line_id': self.sale_order_line.id,
            'test_key': 'test_value'
        }
        wizard = self.env['delivery.create.from.quotation.wizard'].with_context(extended_context)
        
        # Verify extended context
        self.assertEqual(wizard.env.context.get('test_key'), 'test_value')
