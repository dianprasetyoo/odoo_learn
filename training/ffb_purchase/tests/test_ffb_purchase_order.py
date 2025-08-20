from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
from odoo import fields


class TestFfbPurchaseOrder(TransactionCase):
    """Unit test for model PurchaseOrder (FFB Purchase)"""
    
    def setUp(self):
        """Setup method that runs before each test"""
        super(TestFfbPurchaseOrder, self).setUp()
        
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
        
        # Create purchase order base data
        self.purchase_order_data = {
            'partner_id': self.vendor.id,
            'date_order': fields.Date.today(),
            'use_pricing_config': True,
            'pricing_date_from': fields.Date.today() - timedelta(days=30),
            'pricing_date_to': fields.Date.today(),
        }

    def test_create_purchase_order(self):
        """Test 1: Create new purchase order with pricing configuration"""
        # Create purchase order
        purchase_order = self.env['purchase.order'].create(self.purchase_order_data)
        
        # Verify that purchase order was created successfully
        self.assertTrue(purchase_order.id, "Purchase order harus berhasil dibuat")
        self.assertEqual(purchase_order.partner_id.name, 'Test Vendor')
        self.assertTrue(purchase_order.use_pricing_config, "use_pricing_config harus True")
        self.assertIsInstance(purchase_order.pricing_date_from, date, "pricing_date_from harus berupa date")
        self.assertIsInstance(purchase_order.pricing_date_to, date, "pricing_date_to harus berupa date")

    def test_default_pricing_dates(self):
        """Test 2: Test default pricing dates when use_pricing_config is True"""
        # Create purchase order without specifying pricing dates
        data_without_dates = self.purchase_order_data.copy()
        del data_without_dates['pricing_date_from']
        del data_without_dates['pricing_date_to']
        
        purchase_order = self.env['purchase.order'].create(data_without_dates)
        
        # Verify default dates are set correctly
        expected_date_from = fields.Date.today() - timedelta(days=30)
        expected_date_to = fields.Date.today()
        
        self.assertEqual(purchase_order.pricing_date_from, expected_date_from,
                        f"pricing_date_from harus {expected_date_from}, bukan {purchase_order.pricing_date_from}")
        self.assertEqual(purchase_order.pricing_date_to, expected_date_to,
                        f"pricing_date_to harus {expected_date_to}, bukan {purchase_order.pricing_date_to}")

    def test_onchange_use_pricing_config(self):
        """Test 3: Test _onchange_use_pricing_config method"""
        # Create purchase order with pricing config disabled
        data_disabled = self.purchase_order_data.copy()
        data_disabled['use_pricing_config'] = False
        data_disabled['pricing_date_from'] = False
        data_disabled['pricing_date_to'] = False
        
        purchase_order = self.env['purchase.order'].create(data_disabled)
        
        # Verify initial state
        self.assertFalse(purchase_order.use_pricing_config)
        self.assertFalse(purchase_order.pricing_date_from)
        self.assertFalse(purchase_order.pricing_date_to)
        
        # Enable pricing config
        purchase_order.use_pricing_config = True
        purchase_order._onchange_use_pricing_config()
        
        # Verify dates are set when enabling pricing config
        expected_date_from = fields.Date.today() - timedelta(days=30)
        expected_date_to = fields.Date.today()
        
        self.assertEqual(purchase_order.pricing_date_from, expected_date_from,
                        "pricing_date_from harus diset saat enable pricing config")
        self.assertEqual(purchase_order.pricing_date_to, expected_date_to,
                        "pricing_date_to harus diset saat enable pricing config")

    def test_onchange_partner_id_pricing_config(self):
        """Test 4: Test _onchange_partner_id_pricing_config method"""
        # Create purchase order
        purchase_order = self.env['purchase.order'].create(self.purchase_order_data)
        
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create({
            'order_id': purchase_order.id,
            'product_id': self.product.id,
            'name': 'Test Product',
            'product_qty': 10.0,
            'product_uom': self.product.uom_id.id,
        })
        
        # Verify initial state
        self.assertEqual(order_line.order_id.partner_id.name, 'Test Vendor')
        
        # Change partner (this should trigger the onchange)
        new_vendor = self.env['res.partner'].create({
            'name': 'New Test Vendor',
            'supplier_rank': 1,
        })
        
        purchase_order.partner_id = new_vendor.id
        purchase_order._onchange_partner_id_pricing_config()
        
        # Verify partner changed
        self.assertEqual(purchase_order.partner_id.name, 'New Test Vendor',
                        "Partner harus berubah ke vendor baru")

    def test_write_partner_change(self):
        """Test 5: Test write method when partner changes"""
        # Create purchase order
        purchase_order = self.env['purchase.order'].create(self.purchase_order_data)
        
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create({
            'order_id': purchase_order.id,
            'product_id': self.product.id,
            'name': 'Test Product',
            'product_qty': 10.0,
            'product_uom': self.product.uom_id.id,
        })
        
        # Create new vendor
        new_vendor = self.env['res.partner'].create({
            'name': 'New Test Vendor',
            'supplier_rank': 1,
        })
        
        # Change partner using write method
        purchase_order.write({'partner_id': new_vendor.id})
        
        # Verify partner changed
        self.assertEqual(purchase_order.partner_id.name, 'New Test Vendor',
                        "Partner harus berubah setelah write")

    def test_action_apply_pricing_config(self):
        """Test 6: Test action_apply_pricing_config method"""
        # Create purchase order
        purchase_order = self.env['purchase.order'].create(self.purchase_order_data)
        
        # Create purchase order line
        order_line = self.env['purchase.order.line'].create({
            'order_id': purchase_order.id,
            'product_id': self.product.id,
            'name': 'Test Product',
            'product_qty': 10.0,
            'product_uom': self.product.uom_id.id,
        })
        
        # Call the action method
        result = purchase_order.action_apply_pricing_config()
        
        # Verify the result is a client action
        self.assertEqual(result['type'], 'ir.actions.client',
                        "Result harus berupa client action")
        self.assertEqual(result['tag'], 'display_notification',
                        "Tag harus 'display_notification'")
        self.assertEqual(result['params']['title'], 'Success',
                        "Title harus 'Success'")
        self.assertEqual(result['params']['message'], 'Pricing configuration re-applied to all lines.',
                        "Message harus sesuai")

    def test_pricing_date_validation(self):
        """Test 7: Test pricing date validation"""
        # Test with valid date range
        valid_data = self.purchase_order_data.copy()
        valid_data['pricing_date_from'] = fields.Date.today() - timedelta(days=10)
        valid_data['pricing_date_to'] = fields.Date.today()
        
        purchase_order = self.env['purchase.order'].create(valid_data)
        self.assertTrue(purchase_order.id, "Purchase order dengan date range valid harus berhasil dibuat")
        
        # Test with invalid date range (from > to)
        invalid_data = self.purchase_order_data.copy()
        invalid_data['pricing_date_from'] = fields.Date.today()
        invalid_data['pricing_date_to'] = fields.Date.today() - timedelta(days=10)
        
        # This should still work as there's no validation constraint in the model
        purchase_order_invalid = self.env['purchase.order'].create(invalid_data)
        self.assertTrue(purchase_order_invalid.id, "Purchase order dengan date range invalid tetap bisa dibuat")

    def test_pricing_config_flag_behavior(self):
        """Test 8: Test behavior of use_pricing_config flag"""
        # Test with pricing config enabled
        purchase_order_enabled = self.env['purchase.order'].create(self.purchase_order_data)
        self.assertTrue(purchase_order_enabled.use_pricing_config)
        
        # Test with pricing config disabled
        data_disabled = self.purchase_order_data.copy()
        data_disabled['use_pricing_config'] = False
        
        purchase_order_disabled = self.env['purchase.order'].create(data_disabled)
        self.assertFalse(purchase_order_disabled.use_pricing_config)
        
        # Verify that both have the same structure
        self.assertTrue(hasattr(purchase_order_enabled, 'pricing_date_from'))
        self.assertTrue(hasattr(purchase_order_enabled, 'pricing_date_to'))
        self.assertTrue(hasattr(purchase_order_disabled, 'pricing_date_from'))
        self.assertTrue(hasattr(purchase_order_disabled, 'pricing_date_to'))
