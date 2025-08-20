from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
from odoo import fields


class TestFfbPurchaseOrderLine(TransactionCase):
    """Unit test for model PurchaseOrderLine (FFB Purchase)"""
    
    def setUp(self):
        """Setup method that runs before each test"""
        super(TestFfbPurchaseOrderLine, self).setUp()
        
        # Create vendor for testing
        self.vendor = self.env['res.partner'].create({
            'name': 'Test Vendor',
            'supplier_rank': 1,
        })
        
        # Create product for testing
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
            'standard_price': 50.0,
            'list_price': 100.0,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        
        # Create purchase order for testing
        self.purchase_order = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'date_order': fields.Date.today(),
            'use_pricing_config': True,
            'pricing_date_from': fields.Date.today() - timedelta(days=30),
            'pricing_date_to': fields.Date.today(),
        })
        
        # Create purchase order line base data
        self.purchase_order_line_data = {
            'order_id': self.purchase_order.id,
            'product_id': self.product.id,
            'name': 'Test Product',
            'product_qty': 10.0,
            'product_uom': self.product.uom_id.id,
        }

    def test_create_purchase_order_line(self):
        """Test 1: Create new purchase order line"""
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create(self.purchase_order_line_data)
        
        # Verify that purchase order line was created successfully
        self.assertTrue(order_line.id, "Purchase order line harus berhasil dibuat")
        self.assertEqual(order_line.order_id.id, self.purchase_order.id)
        self.assertEqual(order_line.product_id.name, 'Test Product')
        self.assertEqual(order_line.product_qty, 10.0)
        self.assertEqual(order_line.product_uom.id, self.product.uom_id.id)

    def test_compute_pricing_config_available(self):
        """Test 2: Test _compute_pricing_config_available method"""
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create(self.purchase_order_line_data)
        
        # Initially, no pricing config should be available
        self.assertFalse(order_line.pricing_config_available)
        
        # Create a pricing configuration
        pricing_config = self.env['purchase.pricing.config'].create({
            'name': 'Test Config',
            'product_id': self.product.id,
            'vendor_id': self.vendor.id,
            'pricing_method': 'avg_price',
            'purchase_margin': 10.0,
            'date_range_days': 30,
        })
        
        # Trigger compute method
        order_line._compute_pricing_config_available()
        
        # Now pricing config should be available
        self.assertTrue(order_line.pricing_config_available)

    def test_compute_pricing_status(self):
        """Test 3: Test _compute_pricing_status method"""
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create(self.purchase_order_line_data)
        
        # Test status when no product
        order_line.product_id = False
        order_line._compute_pricing_status()
        self.assertEqual(order_line.pricing_status, "No Product")
        
        # Test status when no vendor
        order_line.product_id = self.product
        order_line.order_id.partner_id = False
        order_line._compute_pricing_status()
        self.assertEqual(order_line.pricing_status, "No Vendor")
        
        # Test status when no pricing config available
        order_line.order_id.partner_id = self.vendor
        order_line._compute_pricing_status()
        self.assertEqual(order_line.pricing_status, "Manual Pricing")
        
        # Test status when pricing config is available but no price set
        pricing_config = self.env['purchase.pricing.config'].create({
            'name': 'Test Config',
            'product_id': self.product.id,
            'vendor_id': self.vendor.id,
            'pricing_method': 'avg_price',
            'purchase_margin': 10.0,
            'date_range_days': 30,
        })
        order_line._compute_pricing_status()
        self.assertEqual(order_line.pricing_status, "Config Available")
        
        # Test status when auto-priced
        order_line.price_unit = 80.0
        order_line._compute_pricing_status()
        self.assertEqual(order_line.pricing_status, "Auto-priced")

    def test_onchange_product_id_pricing_config(self):
        """Test 4: Test _onchange_product_id_pricing_config method"""
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create(self.purchase_order_line_data)
        
        # Create pricing configuration
        pricing_config = self.env['purchase.pricing.config'].create({
            'name': 'Test Config',
            'product_id': self.product.id,
            'vendor_id': self.vendor.id,
            'pricing_method': 'avg_price',
            'purchase_margin': 10.0,
            'date_range_days': 30,
        })
        
        # Test onchange when product changes
        result = order_line._onchange_product_id_pricing_config()
        
        # Verify the method returns None (no warning)
        self.assertIsNone(result)

    def test_onchange_quantity_pricing_config(self):
        """Test 5: Test _onchange_quantity_pricing_config method"""
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create(self.purchase_order_line_data)
        
        # Create pricing configuration
        pricing_config = self.env['purchase.pricing.config'].create({
            'name': 'Test Config',
            'product_id': self.product.id,
            'vendor_id': self.vendor.id,
            'pricing_method': 'avg_price',
            'purchase_margin': 10.0,
            'date_range_days': 30,
        })
        
        # Test onchange when quantity changes
        result = order_line._onchange_quantity_pricing_config()
        
        # Verify the method returns None (no warning)
        self.assertIsNone(result)

    def test_create_with_pricing_config(self):
        """Test 6: Test create method override with pricing config"""
        # Create pricing configuration first
        pricing_config = self.env['purchase.pricing.config'].create({
            'name': 'Test Config',
            'product_id': self.product.id,
            'vendor_id': self.vendor.id,
            'pricing_method': 'avg_price',
            'purchase_margin': 10.0,
            'date_range_days': 30,
        })
        
        # Create purchase order line (should trigger pricing config)
        order_line = self.env['purchase.order.line'].create(self.purchase_order_line_data)
        
        # Verify that pricing config was applied
        self.assertTrue(order_line.id, "Purchase order line harus berhasil dibuat")

    def test_write_with_pricing_config(self):
        """Test 7: Test write method override with pricing config"""
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create(self.purchase_order_line_data)
        
        # Create pricing configuration
        pricing_config = self.env['purchase.pricing.config'].create({
            'name': 'Test Config',
            'product_id': self.product.id,
            'vendor_id': self.vendor.id,
            'pricing_method': 'avg_price',
            'purchase_margin': 10.0,
            'date_range_days': 30,
        })
        
        # Test write when product changes
        order_line.write({'product_id': self.product.id})
        
        # Verify the line still exists
        self.assertTrue(order_line.id)

    def test_apply_pricing_config(self):
        """Test 8: Test _apply_pricing_config method"""
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create(self.purchase_order_line_data)
        
        # Create pricing configuration
        pricing_config = self.env['purchase.pricing.config'].create({
            'name': 'Test Config',
            'product_id': self.product.id,
            'vendor_id': self.vendor.id,
            'pricing_method': 'avg_price',
            'purchase_margin': 10.0,
            'date_range_days': 30,
        })
        
        # Apply pricing config
        order_line._apply_pricing_config()
        
        # Verify that pricing config was applied
        self.assertEqual(order_line.pricing_config_id.id, pricing_config.id)

    def test_clear_pricing_info(self):
        """Test 9: Test _clear_pricing_info method"""
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create(self.purchase_order_line_data)
        
        # Set some pricing info first
        order_line.pricing_config_id = self.env['purchase.pricing.config'].create({
            'name': 'Test Config',
            'product_id': self.product.id,
            'vendor_id': self.vendor.id,
            'pricing_method': 'avg_price',
            'purchase_margin': 10.0,
            'date_range_days': 30,
        })
        order_line.base_sale_price = 100.0
        order_line.margin_amount = 10.0
        order_line.price_calculation_info = 'Test info'
        
        # Clear pricing info
        order_line._clear_pricing_info()
        
        # Verify all pricing info is cleared
        self.assertFalse(order_line.pricing_config_id)
        self.assertEqual(order_line.base_sale_price, 0.0)
        self.assertEqual(order_line.margin_amount, 0.0)
        self.assertEqual(order_line.price_calculation_info, 'Product or vendor not specified.')

    def test_apply_fallback_pricing(self):
        """Test 10: Test _apply_fallback_pricing method"""
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create(self.purchase_order_line_data)
        
        # Apply fallback pricing
        order_line._apply_fallback_pricing()
        
        # Verify fallback pricing was applied (should use standard_price = 50.0)
        self.assertEqual(order_line.price_unit, 50.0)
        self.assertIn('Using product standard cost: 50.00', order_line.price_calculation_info)

    def test_action_view_pricing_details(self):
        """Test 11: Test action_view_pricing_details method"""
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create(self.purchase_order_line_data)
        
        # Test when no pricing config available
        result = order_line.action_view_pricing_details()
        
        # Verify warning message
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['title'], 'Warning')
        self.assertIn('No pricing configuration available', result['params']['message'])

    def test_action_recalculate_price(self):
        """Test 12: Test action_recalculate_price method"""
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create(self.purchase_order_line_data)
        
        # Test recalculate price action
        result = order_line.action_recalculate_price()
        
        # Verify success message
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['title'], 'Success')
        self.assertEqual(result['params']['message'], 'Price recalculated successfully.')

    def test_pricing_config_with_sale_data(self):
        """Test 13: Test pricing config with actual sale data"""
        # Create customer for sale orders
        customer = self.env['res.partner'].create({
            'name': 'Test Customer',
            'customer_rank': 1,
        })
        
        # Create sale orders with the test product
        sale_order1 = self.env['sale.order'].create({
            'partner_id': customer.id,
            'date_order': fields.Date.today(),
            'state': 'sale',
        })
        
        sale_order2 = self.env['sale.order'].create({
            'partner_id': customer.id,
            'date_order': fields.Date.today(),
            'state': 'sale',
        })
        
        # Create sale order lines with different prices
        self.env['sale.order.line'].create({
            'order_id': sale_order1.id,
            'product_id': self.product.id,
            'name': 'Test Product',
            'product_uom_qty': 10,
            'price_unit': 100.0,
        })
        
        self.env['sale.order.line'].create({
            'order_id': sale_order2.id,
            'product_id': self.product.id,
            'name': 'Test Product',
            'product_uom_qty': 5,
            'price_unit': 80.0,
        })
        
        # Create pricing configuration
        pricing_config = self.env['purchase.pricing.config'].create({
            'name': 'Test Config',
            'product_id': self.product.id,
            'vendor_id': self.vendor.id,
            'pricing_method': 'min_price',
            'purchase_margin': 10.0,
            'date_range_days': 30,
        })
        
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create(self.purchase_order_line_data)
        
        # Apply pricing config
        order_line._apply_pricing_config()
        
        # Verify that pricing was calculated from sale data
        self.assertEqual(order_line.pricing_config_id.id, pricing_config.id)
        self.assertGreater(order_line.base_sale_price, 0.0)
        self.assertGreater(order_line.margin_amount, 0.0)
        self.assertGreater(order_line.price_unit, 0.0)
