from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date
from odoo import fields


class TestPurchasePricingConfig(TransactionCase):
    """Unit test for model PurchasePricingConfig"""
    def setUp(self):
        """Setup method that runs before each test"""
        super(TestPurchasePricingConfig, self).setUp()
        
        # Create customer for testing
        self.vendor = self.env['res.partner'].create({
            'name': 'Test Vendor',
        })
        
        # Create product for testing
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
        })
        
        # Base data for delivery order
        self.purchase_pricing_config_data = {
            'name': 'Test Purchase Pricing Config',
            'product_id': self.product.id,
            'vendor_id': self.vendor.id,
            'pricing_method': 'avg_price',
            'purchase_margin': 10.0,
            'date_range_days': 30,
        }

    def test_create_purchase_pricing_config(self):
        """Test 1: Create new purchase pricing config"""
        # Create purchase pricing config
        purchase_pricing_config = self.env['purchase.pricing.config'].create(self.purchase_pricing_config_data)
        
        # Memverifikasi bahwa purchase pricing config berhasil dibuat
        self.assertTrue(purchase_pricing_config.id, "Purchase pricing config harus berhasil dibuat")
        self.assertEqual(purchase_pricing_config.product_id.name, 'Test Product')
        self.assertEqual(purchase_pricing_config.vendor_id.name, 'Test Vendor')
        self.assertEqual(purchase_pricing_config.pricing_method, 'avg_price')
        self.assertEqual(purchase_pricing_config.purchase_margin, 10.0)
        self.assertEqual(purchase_pricing_config.date_range_days, 30)

    def test_02_compute_test_calculation(self): 
        """
        Test 2: Menghitung test calculation
        """
        # Membuat purchase pricing config
        purchase_pricing_config = self.env['purchase.pricing.config'].create(self.purchase_pricing_config_data)
        
        # Memverifikasi perhitungan test calculation
        expected_test_base_price = 10.0 * 50.0  # quantity * unit_price
        self.assertEqual(purchase_pricing_config.test_base_price, expected_test_base_price, 
                        f"Test base price harus {expected_test_base_price}, bukan {purchase_pricing_config.test_base_price}")
        
        # Test perubahan quantity
        purchase_pricing_config.purchase_margin = 15.0
        purchase_pricing_config._compute_test_calculation()  # Memanggil compute method
        new_expected_test_base_price = 10.0 * 50.0
        self.assertEqual(purchase_pricing_config.test_base_price, new_expected_test_base_price)

    def test_03_compute_display_name(self):
        """Test 3: Test _compute_display_name method"""
        # Create purchase pricing config
        purchase_pricing_config = self.env['purchase.pricing.config'].create(self.purchase_pricing_config_data)
        
        # Verify display name is computed correctly
        expected_display_name = f"{self.purchase_pricing_config_data['name']} - {self.product.name} - {self.vendor.name}"
        self.assertEqual(purchase_pricing_config.display_name, expected_display_name,
                        f"Display name should be '{expected_display_name}', but got '{purchase_pricing_config.display_name}'")
        
        # Test with different name
        purchase_pricing_config.name = 'New Config Name'
        purchase_pricing_config._compute_display_name()
        new_expected_display_name = f"New Config Name - {self.product.name} - {self.vendor.name}"
        self.assertEqual(purchase_pricing_config.display_name, new_expected_display_name,
                        f"Display name should be '{new_expected_display_name}', but got '{purchase_pricing_config.display_name}'")

    def test_04_set_empty_test_values(self):
        """Test 4: Test _set_empty_test_values method"""
        # Create purchase pricing config
        purchase_pricing_config = self.env['purchase.pricing.config'].create(self.purchase_pricing_config_data)
        
        # Set some non-zero values first to verify they get reset
        purchase_pricing_config.test_base_price = 100.0
        purchase_pricing_config.test_margin_amount = 50.0
        purchase_pricing_config.test_final_price = 75.0
        purchase_pricing_config.test_price_count = 5
        
        # Verify initial values are set
        self.assertEqual(purchase_pricing_config.test_base_price, 100.0)
        self.assertEqual(purchase_pricing_config.test_margin_amount, 50.0)
        self.assertEqual(purchase_pricing_config.test_final_price, 75.0)
        self.assertEqual(purchase_pricing_config.test_price_count, 5)
        
        # Call the method to reset values
        purchase_pricing_config._set_empty_test_values()
        
        # Verify all test values are reset to 0.0 or 0
        self.assertEqual(purchase_pricing_config.test_base_price, 0.0,
                        "test_base_price should be reset to 0.0")
        self.assertEqual(purchase_pricing_config.test_margin_amount, 0.0,
                        "test_margin_amount should be reset to 0.0")
        self.assertEqual(purchase_pricing_config.test_final_price, 0.0,
                        "test_final_price should be reset to 0.0")
        self.assertEqual(purchase_pricing_config.test_price_count, 0,
                        "test_price_count should be reset to 0")

    def test_05_calculate_purchase_price(self):
        """Test 5: Test calculate_purchase_price method"""
        # Create purchase pricing config
        purchase_pricing_config = self.env['purchase.pricing.config'].create(self.purchase_pricing_config_data)
        
        # Create a customer for sale orders
        customer = self.env['res.partner'].create({
            'name': 'Test Customer',
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
            'price_unit': 100.0,  # Higher price
        })
        
        self.env['sale.order.line'].create({
            'order_id': sale_order2.id,
            'product_id': self.product.id,
            'name': 'Test Product',
            'product_uom_qty': 5,
            'price_unit': 80.0,   # Lower price
        })
        
        # Test with min_price method (should use lowest price: 80.0)
        purchase_pricing_config.pricing_method = 'min_price'
        calculated_price = purchase_pricing_config.calculate_purchase_price()
        
        # Expected: base_price = 80.0, margin = 80.0 * 10% = 8.0, final_price = 80.0 - 8.0 = 72.0
        expected_price = 72.0
        self.assertEqual(calculated_price, expected_price,
                        f"Purchase price should be {expected_price}, but got {calculated_price}")
        
        # Test with avg_price method (should use average price: (100.0 + 80.0) / 2 = 90.0)
        purchase_pricing_config.pricing_method = 'avg_price'
        calculated_price = purchase_pricing_config.calculate_purchase_price()
        
        # Expected: base_price = 90.0, margin = 90.0 * 10% = 9.0, final_price = 90.0 - 8.0 = 81.0
        expected_price = 81.0
        self.assertEqual(calculated_price, expected_price,
                        f"Purchase price should be {expected_price}, but got {calculated_price}")

    def test_06_action_test_price_calculation(self):
        """Test 6: Test action_test_price_calculation method"""
        # Create purchase pricing config
        purchase_pricing_config = self.env['purchase.pricing.config'].create(self.purchase_pricing_config_data)
        
        # Create a customer for sale orders
        customer = self.env['res.partner'].create({
            'name': 'Test Customer',
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
            'price_unit': 100.0,  # Higher price
        })
        
        self.env['sale.order.line'].create({
            'order_id': sale_order2.id,
            'product_id': self.product.id,
            'name': 'Test Product',
            'product_uom_qty': 5,
            'price_unit': 80.0,   # Lower price
        })
        
        # Test the action method
        result = purchase_pricing_config.action_test_price_calculation()
        
        # Verify the result is a client action
        self.assertEqual(result['type'], 'ir.actions.client',
                        "Result harus berupa client action")
        self.assertEqual(result['tag'], 'display_notification',
                        "Tag harus 'display_notification'")
        self.assertEqual(result['params']['title'], '💰 Price Calculation Test',
                        "Title harus sesuai")
        self.assertEqual(result['params']['type'], 'success',
                        "Type harus 'success'")
        
        # Verify the message contains expected content
        message = result['params']['message']
        self.assertIn('Test Product', message, "Message harus mengandung nama product")
        self.assertIn('Test Vendor', message, "Message harus mengandung nama vendor")
        self.assertIn('Sale Orders Found: 2', message, "Message harus menunjukkan jumlah sale orders")
        self.assertIn('Base Sale Price: 80.00', message, "Message harus menunjukkan base price (min_price method)")
        self.assertIn('Final Purchase Price: 72.00', message, "Message harus menunjukkan final price")

    def test_07_compute_test_calculation(self):
        """Test 7: Test _compute_test_calculation method"""
        # Create purchase pricing config
        purchase_pricing_config = self.env['purchase.pricing.config'].create(self.purchase_pricing_config_data)
        
        # Create a customer for sale orders
        customer = self.env['res.partner'].create({
            'name': 'Test Customer',
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
            'price_unit': 100.0,  # Higher price
        })
        
        self.env['sale.order.line'].create({
            'order_id': sale_order2.id,
            'product_id': self.product.id,
            'name': 'Test Product',
            'product_uom_qty': 5,
            'price_unit': 80.0,   # Lower price
        })
        
        # Trigger the compute method by accessing the computed field
        purchase_pricing_config._compute_test_calculation()
        
        # Verify that test values are computed correctly
        self.assertGreater(purchase_pricing_config.test_base_price, 0.0,
                          "test_base_price harus lebih dari 0.0")
        self.assertGreater(purchase_pricing_config.test_margin_amount, 0.0,
                          "test_margin_amount harus lebih dari 0.0")
        self.assertGreater(purchase_pricing_config.test_final_price, 0.0,
                          "test_final_price harus lebih dari 0.0")
        self.assertEqual(purchase_pricing_config.test_price_count, 2,
                        "test_price_count harus 2 (sesuai jumlah sale orders)")
        
        # Verify status message
        self.assertIn('Calculation ready', purchase_pricing_config.test_status_message,
                     "Status message harus menunjukkan calculation ready")
        
        # Test with no product (should set empty values)
        purchase_pricing_config.product_id = False
        purchase_pricing_config._compute_test_calculation()
        
        # Verify empty values are set
        self.assertEqual(purchase_pricing_config.test_base_price, 0.0,
                        "test_base_price harus 0.0 ketika tidak ada product")
        self.assertEqual(purchase_pricing_config.test_margin_amount, 0.0,
                        "test_margin_amount harus 0.0 ketika tidak ada product")
        self.assertEqual(purchase_pricing_config.test_final_price, 0.0,
                        "test_final_price harus 0.0 ketika tidak ada product")
        self.assertEqual(purchase_pricing_config.test_price_count, 0,
                        "test_price_count harus 0 ketika tidak ada product")
        self.assertEqual(purchase_pricing_config.test_status_message, 'Please select a product first',
                        "Status message harus sesuai ketika tidak ada product")

    def test_08_action_view_calculation_details(self):
        """Test 8: Test action_view_calculation_details method"""
        # Create purchase pricing config
        purchase_pricing_config = self.env['purchase.pricing.config'].create(self.purchase_pricing_config_data)
        
        # Create a customer for sale orders
        customer = self.env['res.partner'].create({
            'name': 'Test Customer',
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
            'price_unit': 100.0,  # Higher price
        })
        
        self.env['sale.order.line'].create({
            'order_id': sale_order2.id,
            'product_id': self.product.id,
            'name': 'Test Product',
            'product_uom_qty': 5,
            'price_unit': 80.0,   # Lower price
        })
        
        # Test the action method
        result = purchase_pricing_config.action_view_calculation_details()
        
        # Verify the result is a window action for the wizard
        self.assertEqual(result['type'], 'ir.actions.act_window',
                        "Result harus berupa window action")
        self.assertEqual(result['res_model'], 'wizard.calculation.details',
                        "Model harus 'wizard.calculation.details'")
        self.assertEqual(result['view_mode'], 'form',
                        "View mode harus 'form'")
        self.assertEqual(result['target'], 'new',
                        "Target harus 'new' (modal)")
        
        # Verify the wizard was created with correct data
        wizard = self.env['wizard.calculation.details'].browse(result['res_id'])
        self.assertEqual(wizard.config_id.id, purchase_pricing_config.id,
                        "Wizard harus terhubung dengan config yang benar")
        self.assertEqual(wizard.product_name, 'Test Product',
                        "Product name harus sesuai")
        self.assertEqual(wizard.vendor_name, 'Test Vendor',
                        "Vendor name harus sesuai")
        self.assertEqual(wizard.pricing_method, 'min_price',
                        "Pricing method harus sesuai")
        self.assertEqual(wizard.purchase_margin, 10.0,
                        "Purchase margin harus sesuai")
        self.assertEqual(wizard.price_count, 2,
                        "Price count harus 2")
        self.assertGreater(wizard.base_price, 0.0,
                          "Base price harus lebih dari 0.0")
        self.assertGreater(wizard.final_price, 0.0,
                          "Final price harus lebih dari 0.0")
        
        # Test with no product (should show warning)
        purchase_pricing_config.product_id = False
        result_no_product = purchase_pricing_config.action_view_calculation_details()
        
        # Verify warning message
        self.assertEqual(result_no_product['type'], 'ir.actions.client',
                        "Result harus berupa client action ketika tidak ada product")
        self.assertEqual(result_no_product['tag'], 'display_notification',
                        "Tag harus 'display_notification'")
        self.assertEqual(result_no_product['params']['title'], 'No Data Found',
                        "Title harus 'No Data Found'")
        self.assertEqual(result_no_product['params']['type'], 'warning',
                        "Type harus 'warning'")

    def test_09_get_no_data_message(self):
        """Test 9: Test _get_no_data_message method"""
        # Create purchase pricing config
        purchase_pricing_config = self.env['purchase.pricing.config'].create(self.purchase_pricing_config_data)
        
        # Test the method
        message = purchase_pricing_config._get_no_data_message()
        
        # Verify the message contains expected content
        self.assertIn('Test Product', message, "Message harus mengandung nama product")
        self.assertIn('Test Vendor', message, "Message harus mengandung nama vendor")
        self.assertIn('30', message, "Message harus menunjukkan date range days (30)")
        
        # Verify the message structure
        self.assertIn('No sale orders found for product', message,
                     "Message harus mengandung teks 'No sale orders found for product'")
        self.assertIn('Date range:', message,
                     "Message harus mengandung teks 'Date range:'")
        self.assertIn('To get pricing calculation:', message,
                     "Message harus mengandung teks 'To get pricing calculation:'")
        self.assertIn('Create confirmed sale orders for this product', message,
                     "Message harus mengandung instruksi untuk membuat sale orders")
        self.assertIn('Ensure order dates are within the date range', message,
                     "Message harus mengandung instruksi untuk date range")
        
        # Test with different date range
        purchase_pricing_config.date_range_days = 60
        message_60_days = purchase_pricing_config._get_no_data_message()
        
        # Verify the new message contains updated date range
        self.assertIn('60', message_60_days, "Message harus menunjukkan date range days yang baru (60)")
        
        # Verify both messages are different
        self.assertNotEqual(message, message_60_days,
                           "Message harus berbeda ketika date range berubah")

    def test_10_action_open_sale_orders(self):
        """Test 10: Test action_open_sale_orders method"""
        # Create purchase pricing config
        purchase_pricing_config = self.env['purchase.pricing.config'].create(self.purchase_pricing_config_data)
        
        # Test the action method with product
        result = purchase_pricing_config.action_open_sale_orders()
        
        # Verify the result is a window action
        self.assertEqual(result['type'], 'ir.actions.act_window',
                        "Result harus berupa window action")
        self.assertEqual(result['res_model'], 'sale.order',
                        "Model harus 'sale.order'")
        self.assertEqual(result['view_mode'], 'list,form',
                        "View mode harus 'list,form'")
        self.assertEqual(result['target'], 'current',
                        "Target harus 'current'")
        
        # Verify the action name
        self.assertEqual(result['name'], 'Sale Orders for Test Product',
                        "Name harus sesuai dengan nama product")
        
        # Verify the domain filters
        domain = result['domain']
        self.assertIn(('order_line.product_id', '=', self.product.id), domain,
                     "Domain harus filter berdasarkan product_id")
        self.assertIn(('state', 'in', ['sale']), domain,
                     "Domain harus filter berdasarkan state 'sale'")
        
        # Verify the context
        context = result['context']
        self.assertEqual(context['search_default_product_id'], self.product.id,
                        "Context harus set search_default_product_id")
        
        # Test with no product (should show warning)
        purchase_pricing_config.product_id = False
        result_no_product = purchase_pricing_config.action_open_sale_orders()
        
        # Verify warning message
        self.assertEqual(result_no_product['type'], 'ir.actions.client',
                        "Result harus berupa client action ketika tidak ada product")
        self.assertEqual(result_no_product['tag'], 'display_notification',
                        "Tag harus 'display_notification'")
        self.assertEqual(result_no_product['params']['title'], 'Validation Error',
                        "Title harus 'Validation Error'")
        self.assertEqual(result_no_product['params']['type'], 'warning',
                        "Type harus 'warning'")
        self.assertIn('Please select a product first', result_no_product['params']['message'],
                     "Message harus menunjukkan bahwa product harus dipilih dulu")

   