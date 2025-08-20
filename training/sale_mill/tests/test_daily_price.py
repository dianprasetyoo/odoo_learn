from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from odoo import fields
from datetime import timedelta


class TestDailyPrice(TransactionCase):
    """Unit test for DailyPrice model"""

    def setUp(self):
        """Setup method that runs before each test"""
        super(TestDailyPrice, self).setUp()
        
        # Create customer for testing
        self.customer = self.env['res.partner'].create({
            'name': 'Test Customer',
        })
        
        # Create product for testing
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
        })
        
        # Create currency for testing
        self.currency = self.env['res.currency'].create({
            'name': 'Test Currency',
            'symbol': 'TST',
        })
        
        # Base data for daily price
        self.daily_price_data = {
            'product_id': self.product.id,
            'customer_id': self.customer.id,
            'date': fields.Date.today(),
            'unit_price': 100.0,
            'currency_id': self.currency.id,
            'notes': 'Test daily price',
        }

    def test_01_create_daily_price(self):
        """Test 1: Create new daily price"""
        # Create daily price
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Verify daily price is created successfully
        self.assertTrue(daily_price.id, "Daily price harus berhasil dibuat")
        self.assertEqual(daily_price.product_id.name, 'Test Product')
        self.assertEqual(daily_price.customer_id.name, 'Test Customer')
        self.assertEqual(daily_price.unit_price, 100.0)
        self.assertEqual(daily_price.currency_id.name, 'Test Currency')
        self.assertEqual(daily_price.notes, 'Test daily price')

    def test_02_compute_display_name(self):
        """Test 2: Test _compute_display_name method"""
        # Create daily price
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Verify display name is computed correctly
        expected_display_name = f"{daily_price.date} - {self.product.name} - {self.customer.name}"
        self.assertEqual(daily_price.display_name, expected_display_name,
                        f"Display name should be '{expected_display_name}', but got '{daily_price.display_name}'")
        
        # Test with different date
        daily_price.date = fields.Date.today() + timedelta(days=1)
        daily_price._compute_display_name()
        new_expected_display_name = f"{daily_price.date} - {self.product.name} - {self.customer.name}"
        self.assertEqual(daily_price.display_name, new_expected_display_name)

    def test_03_check_unit_price_positive(self):
        """Test 3: Test unit price positive constraint"""
        # Test case 1: Unit price positive (should succeed)
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        self.assertGreater(daily_price.unit_price, 0, "Unit price should be positive")
        
        # Test case 2: Unit price = 0 (should fail with ValidationError)
        invalid_data = self.daily_price_data.copy()
        invalid_data['unit_price'] = 0.0
        
        with self.assertRaises(ValidationError) as context:
            self.env['daily.price'].create(invalid_data)
        
        self.assertIn("Unit price must be greater than zero", str(context.exception))
        
        # Test case 3: Unit price negative (should fail with ValidationError)
        invalid_data['unit_price'] = -50.0
        
        with self.assertRaises(ValidationError) as context:
            self.env['daily.price'].create(invalid_data)
        
        self.assertIn("Unit price must be greater than zero", str(context.exception))

    def test_04_check_date_not_future(self):
        """Test 4: Test date not future constraint"""
        # Test case 1: Date today (should succeed)
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        self.assertEqual(daily_price.date, fields.Date.today())
        
        # Test case 2: Date in future but within 1 year (should succeed)
        future_data = self.daily_price_data.copy()
        future_data['date'] = fields.Date.today() + timedelta(days=30)
        future_daily_price = self.env['daily.price'].create(future_data)
        self.assertEqual(future_daily_price.date, fields.Date.today() + timedelta(days=30))
        
        # Test case 3: Date more than 1 year in future (should fail)
        far_future_data = self.daily_price_data.copy()
        far_future_data['date'] = fields.Date.today() + timedelta(days=400)
        
        with self.assertRaises(ValidationError) as context:
            self.env['daily.price'].create(far_future_data)
        
        self.assertIn("Price date cannot be more than 1 year in the future", str(context.exception))

    def test_05_check_unique_product_customer_date(self):
        """Test 5: Test unique product-customer-date constraint"""
        # Create first daily price
        daily_price1 = self.env['daily.price'].create(self.daily_price_data)
        
        # Try to create second daily price with same product-customer-date (should fail)
        duplicate_data = self.daily_price_data.copy()
        
        with self.assertRaises(ValidationError) as context:
            self.env['daily.price'].create(duplicate_data)
        
        self.assertIn("already exists", str(context.exception))
        
        # Create daily price with different date (should succeed)
        different_date_data = self.daily_price_data.copy()
        different_date_data['date'] = fields.Date.today() + timedelta(days=1)
        daily_price2 = self.env['daily.price'].create(different_date_data)
        self.assertTrue(daily_price2.id)

    def test_06_check_record_exists(self):
        """Test 6: Test check_record_exists method"""
        # Initially no record exists
        exists = self.env['daily.price'].check_record_exists(
            self.product.id, self.customer.id, fields.Date.today()
        )
        self.assertFalse(exists, "Record should not exist initially")
        
        # Create daily price
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Now record should exist
        exists = self.env['daily.price'].check_record_exists(
            self.product.id, self.customer.id, fields.Date.today()
        )
        self.assertTrue(exists, "Record should exist after creation")

    def test_07_get_existing_record(self):
        """Test 7: Test get_existing_record method"""
        # Initially no record exists
        existing_record = self.env['daily.price'].get_existing_record(
            self.product.id, self.customer.id, fields.Date.today()
        )
        self.assertFalse(existing_record, "No existing record should be found")
        
        # Create daily price
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Now should find existing record
        existing_record = self.env['daily.price'].get_existing_record(
            self.product.id, self.customer.id, fields.Date.today()
        )
        self.assertEqual(existing_record.id, daily_price.id, "Should find the created record")

    def test_08_add_price_line_to_existing(self):
        """Test 8: Test add_price_line_to_existing method"""
        # Create daily price
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Try to add price line for same date (should fail)
        with self.assertRaises(ValidationError) as context:
            self.env['daily.price'].add_price_line_to_existing(
                self.product.id, self.customer.id, fields.Date.today(), 150.0
            )
        
        self.assertIn("already exists", str(context.exception))
        
        # Add price line for different date (should succeed)
        new_date = fields.Date.today() + timedelta(days=1)
        new_price = self.env['daily.price'].add_price_line_to_existing(
            self.product.id, self.customer.id, new_date, 150.0
        )
        self.assertTrue(new_price.id, "New price should be created")
        self.assertEqual(new_price.unit_price, 150.0)

    def test_09_get_price_for_date(self):
        """Test 9: Test get_price_for_date method"""
        # Initially no price exists
        price = self.env['daily.price'].get_price_for_date(
            self.product.id, self.customer.id, fields.Date.today()
        )
        self.assertEqual(price, 0.0, "Price should be 0.0 initially")
        
        # Create daily price
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Now should get the price
        price = self.env['daily.price'].get_price_for_date(
            self.product.id, self.customer.id, fields.Date.today()
        )
        self.assertEqual(price, 100.0, "Price should be 100.0")

    def test_10_get_price_for_date_range(self):
        """Test 10: Test get_price_for_date_range method"""
        # Create multiple daily prices
        dates = [
            fields.Date.today(),
            fields.Date.today() + timedelta(days=1),
            fields.Date.today() + timedelta(days=2),
        ]
        
        for i, date in enumerate(dates):
            self.env['daily.price'].create({
                'product_id': self.product.id,
                'customer_id': self.customer.id,
                'date': date,
                'unit_price': 100.0 + (i * 10),
                'currency_id': self.currency.id,
            })
        
        # Get prices for date range
        start_date = fields.Date.today()
        end_date = fields.Date.today() + timedelta(days=2)
        price_records = self.env['daily.price'].get_price_for_date_range(
            self.product.id, self.customer.id, start_date, end_date
        )
        
        self.assertEqual(len(price_records), 3, "Should find 3 price records")

    def test_11_action_copy_to_next_day(self):
        """Test 11: Test action_copy_to_next_day method"""
        # Create daily price
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Copy to next day
        result = daily_price.action_copy_to_next_day()
        
        # Verify result structure
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'success')
        
        # Verify new record was created
        next_day = daily_price.date + timedelta(days=1)
        next_day_record = self.env['daily.price'].search([
            ('product_id', '=', self.product.id),
            ('customer_id', '=', self.customer.id),
            ('date', '=', next_day)
        ])
        self.assertTrue(next_day_record, "Next day record should be created")

    def test_12_action_copy_to_next_day_existing(self):
        """Test 12: Test action_copy_to_next_day when next day already exists"""
        # Create daily price
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Create record for next day
        next_day = daily_price.date + timedelta(days=1)
        self.env['daily.price'].create({
            'product_id': self.product.id,
            'customer_id': self.customer.id,
            'date': next_day,
            'unit_price': 150.0,
            'currency_id': self.currency.id,
        })
        
        # Try to copy (should show warning)
        result = daily_price.action_copy_to_next_day()
        
        # Verify warning result
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'warning')

    def test_13_product_inheritance(self):
        """Test 13: Test ProductProduct inheritance"""
        # Create daily price
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Check product has daily pricing
        self.assertTrue(self.product.has_daily_pricing, "Product should have daily pricing")
        
        # Get daily price from product
        price = self.product.get_daily_price(self.customer.id, fields.Date.today())
        self.assertEqual(price, 100.0, "Product should return correct daily price")
        
        # Check if daily price exists
        exists = self.product.check_daily_price_exists(self.customer.id, fields.Date.today())
        self.assertTrue(exists, "Product should have daily price for this date")

    def test_14_customer_inheritance(self):
        """Test 14: Test ResPartner inheritance"""
        # Create daily price
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Get daily price from customer
        price = self.customer.get_daily_price_for_product(self.product.id, fields.Date.today())
        self.assertEqual(price, 100.0, "Customer should return correct daily price")
        
        # Check if daily price exists
        exists = self.customer.check_daily_price_record_exists(self.product.id, fields.Date.today())
        self.assertTrue(exists, "Customer should have daily price for this product and date")

    def test_15_daily_price_line_model(self):
        """Test 15: Test DailyPriceLine model"""
        # Create daily price first
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Create daily price line
        line_data = {
            'daily_price_id': daily_price.id,
            'date': fields.Date.today() + timedelta(days=1),
            'unit_price': 120.0,
            'currency_id': self.currency.id,
            'notes': 'Test line',
        }
        
        line = self.env['daily.price.line'].create(line_data)
        
        # Verify line is created
        self.assertTrue(line.id, "Daily price line should be created")
        self.assertEqual(line.unit_price, 120.0, "Line should have correct price")
        
        # Test line constraint
        with self.assertRaises(ValidationError) as context:
            self.env['daily.price.line'].create(line_data)
        
        self.assertIn("already exists", str(context.exception))

    def test_16_sequence_generation(self):
        """Test 16: Test sequence generation for daily price"""
        # Create daily price
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Verify name is generated
        self.assertNotEqual(daily_price.name, 'New', "Name should be generated automatically")
        self.assertTrue(daily_price.name.startswith('DP'), "Name should start with DP")

    def test_17_copy_method(self):
        """Test 17: Test copy method"""
        # Create daily price
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Copy the record
        copied_price = daily_price.copy()
        
        # Verify copy is created
        self.assertTrue(copied_price.id, "Copied record should be created")
        self.assertNotEqual(copied_price.id, daily_price.id, "Copied record should have different ID")
        self.assertEqual(copied_price.product_id.id, daily_price.product_id.id, "Product should be copied")
        self.assertEqual(copied_price.customer_id.id, daily_price.customer_id.id, "Customer should be copied")

    def test_18_action_create_or_open_existing(self):
        """Test 18: Test action_create_or_open method with existing record"""
        # Create daily price first
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Test action_create_or_open with existing record
        result = self.env['daily.price'].action_create_or_open(
            product_id=self.product.id,
            customer_id=self.customer.id,
            date=fields.Date.today()
        )
        
        # Should return existing record view
        self.assertEqual(result['res_model'], 'daily.price')
        self.assertEqual(result['view_mode'], 'form')
        self.assertEqual(result['res_id'], daily_price.id)
        self.assertEqual(result['target'], 'current')
        self.assertIn('Daily Price -', result['name'])

    def test_19_action_create_or_open_new(self):
        """Test 19: Test action_create_or_open method for new record"""
        # Test action_create_or_open without existing record
        result = self.env['daily.price'].action_create_or_open(
            product_id=self.product.id,
            customer_id=self.customer.id,
            date=fields.Date.today() + timedelta(days=5)
        )
        
        # Should return create new record action
        self.assertEqual(result['res_model'], 'daily.price')
        self.assertEqual(result['view_mode'], 'form')
        self.assertEqual(result['target'], 'current')
        self.assertEqual(result['name'], 'Create Daily Price')

    def test_20_action_create_or_open_partial_params(self):
        """Test 20: Test action_create_or_open method with partial parameters"""
        # Test with only product_id
        result = self.env['daily.price'].action_create_or_open(product_id=self.product.id)
        
        # Should return create new record action
        self.assertEqual(result['res_model'], 'daily.price')
        self.assertEqual(result['view_mode'], 'form')
        self.assertEqual(result['target'], 'current')
        
        # Test with only customer_id
        result = self.env['daily.price'].action_create_or_open(customer_id=self.customer.id)
        
        # Should return create new record action
        self.assertEqual(result['res_model'], 'daily.price')
        self.assertEqual(result['view_mode'], 'form')
        self.assertEqual(result['target'], 'current')
        
        # Test with no parameters
        result = self.env['daily.price'].action_create_or_open()
        
        # Should return create new record action
        self.assertEqual(result['res_model'], 'daily.price')
        self.assertEqual(result['view_mode'], 'form')
        self.assertEqual(result['target'], 'current')

    def test_21_validate_before_create_success(self):
        """Test 21: Test validate_before_create method - success case"""
        # Test validation when no record exists (should succeed)
        result = self.env['daily.price'].validate_before_create(
            product_id=self.product.id,
            customer_id=self.customer.id,
            date=fields.Date.today() + timedelta(days=10)
        )
        
        # Should return True if validation passes
        self.assertTrue(result, "Validation should pass when no record exists")

    def test_22_validate_before_create_failure(self):
        """Test 22: Test validate_before_create method - failure case"""
        # Create a daily price first
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Test validation when record already exists (should fail)
        with self.assertRaises(ValidationError) as context:
            self.env['daily.price'].validate_before_create(
                product_id=self.product.id,
                customer_id=self.customer.id,
                date=fields.Date.today()
            )
        
        # Should raise ValidationError with appropriate message
        self.assertIn("already exists", str(context.exception))
        self.assertIn("product", str(context.exception))
        self.assertIn("customer", str(context.exception))
        self.assertIn("date", str(context.exception))

    def test_23_onchange_product_customer_date_check_existing(self):
        """Test 23: Test _onchange_product_customer_date_check_existing method"""
        # Create a daily price first
        daily_price = self.env['daily.price'].create(self.daily_price_data)
        
        # Create a new daily price record for onchange testing
        new_daily_price = self.env['daily.price'].new({
            'product_id': self.product.id,
            'customer_id': self.customer.id,
            'date': fields.Date.today(),
            'unit_price': 200.0,
            'currency_id': self.currency.id,
        })
        
        # Trigger the onchange method
        result = new_daily_price._onchange_product_customer_date_check_existing()
        
        # Should return warning since record already exists
        self.assertIsNotNone(result, "Result should not be None when record exists")
        self.assertIsInstance(result, dict)
        
        # Now we know result is a dict, so we can safely access it
        if result is not None:  # This satisfies the type checker
            warning_data = result['warning']
            self.assertIn('title', warning_data)
            self.assertIn('message', warning_data)
            self.assertEqual(warning_data['title'], 'Record Already Exists')
            self.assertIn("already exists", warning_data['message'])

    def test_24_onchange_product_customer_date_no_existing(self):
        """Test 24: Test _onchange_product_customer_date_check_existing method - no existing record"""
        # Create a new daily price record with different date (no existing record)
        new_daily_price = self.env['daily.price'].new({
            'product_id': self.product.id,
            'customer_id': self.customer.id,
            'date': fields.Date.today() + timedelta(days=15),
            'unit_price': 200.0,
            'currency_id': self.currency.id,
        })
        
        # Trigger the onchange method
        result = new_daily_price._onchange_product_customer_date_check_existing()
        
        # Should return None since no existing record
        self.assertIsNone(result, "Should return None when no existing record")

    def test_25_onchange_product_customer_date_partial_fields(self):
        """Test 25: Test _onchange_product_customer_date_check_existing method with partial fields"""
        # Test with missing product_id
        new_daily_price = self.env['daily.price'].new({
            'customer_id': self.customer.id,
            'date': fields.Date.today(),
            'unit_price': 200.0,
            'currency_id': self.currency.id,
        })
        
        result = new_daily_price._onchange_product_customer_date_check_existing()
        self.assertIsNone(result, "Should return None when product_id is missing")
        
        # Test with missing customer_id
        new_daily_price = self.env['daily.price'].new({
            'product_id': self.product.id,
            'date': fields.Date.today(),
            'unit_price': 200.0,
            'currency_id': self.currency.id,
        })
        
        result = new_daily_price._onchange_product_customer_date_check_existing()
        self.assertIsNone(result, "Should return None when customer_id is missing")
        
        # Test with missing date
        new_daily_price = self.env['daily.price'].new({
            'product_id': self.product.id,
            'customer_id': self.customer.id,
            'unit_price': 200.0,
            'currency_id': self.currency.id,
        })
        
        result = new_daily_price._onchange_product_customer_date_check_existing()
        self.assertIsNone(result, "Should return None when date is missing")
