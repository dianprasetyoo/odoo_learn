from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from odoo import fields
from datetime import timedelta, datetime, time


class TestWizardDeliveryAssign(TransactionCase):
    """Unit test for DeliveryAssignWizard"""

    def setUp(self):
        """Setup method that runs before each test"""
        super(TestWizardDeliveryAssign, self).setUp()
        
        # Create customer for testing
        self.customer = self.env['res.partner'].create({
            'name': 'Test Customer',
        })
        
        # Create product for testing
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
        })
        
        # Create delivery orders for testing
        self.delivery_order1 = self.env['delivery.order'].create({
            'name': 'Test Delivery Order 1',
            'customer_id': self.customer.id,
            'delivery_date': fields.Date.today(),
            'product_id': self.product.id,
            'quantity': 10.0,
            'unit_price': 100.0,
            'notes': 'Initial notes',
        })
        
        self.delivery_order2 = self.env['delivery.order'].create({
            'name': 'Test Delivery Order 2',
            'customer_id': self.customer.id,
            'delivery_date': fields.Date.today(),
            'product_id': self.product.id,
            'quantity': 5.0,
            'unit_price': 50.0,
            'notes': 'Initial notes',
        })
        
        # Base data for wizard
        self.wizard_data = {
            'delivery_order_ids': [(6, 0, [self.delivery_order1.id, self.delivery_order2.id])],
            'driver_name': 'Test Driver',
            'vehicle_number': 'B 1234 ABC',
            'delivery_time': datetime.combine(fields.Date.today() + timedelta(days=1), time(9, 0)),
        }

    def test_01_create_wizard(self):
        """Test 1: Create new delivery assign wizard"""
        # Create wizard
        wizard = self.env['delivery.assign.wizard'].create(self.wizard_data)
        
        # Verify wizard is created successfully
        self.assertTrue(wizard.id, "Wizard harus berhasil dibuat")
        self.assertEqual(wizard.driver_name, 'Test Driver')
        self.assertEqual(wizard.vehicle_number, 'B 1234 ABC')
        self.assertEqual(len(wizard.delivery_order_ids), 2)
        self.assertEqual(wizard.order_count, 2)

    def test_02_compute_order_count(self):
        """Test 2: Test _compute_order_count method"""
        # Create wizard
        wizard = self.env['delivery.assign.wizard'].create(self.wizard_data)
        
        # Initially should have 2 orders
        self.assertEqual(wizard.order_count, 2,
                        "Order count should be 2 initially")
        
        # Add another delivery order
        delivery_order3 = self.env['delivery.order'].create({
            'name': 'Test Delivery Order 3',
            'customer_id': self.customer.id,
            'delivery_date': fields.Date.today(),
            'product_id': self.product.id,
            'quantity': 15.0,
            'unit_price': 75.0,
        })
        
        wizard.delivery_order_ids = [(4, delivery_order3.id)]
        wizard._compute_order_count()
        
        # Should now have 3 orders
        self.assertEqual(wizard.order_count, 3,
                        "Order count should be 3 after adding another order")

    def test_03_default_get(self):
        """Test 3: Test default_get method"""
        # Test with context containing delivery order IDs
        context = {
            'default_delivery_order_ids': [self.delivery_order1.id, self.delivery_order2.id]
        }
        
        wizard = self.env['delivery.assign.wizard'].with_context(context)
        defaults = wizard.default_get(['delivery_time'])
        
        # Should have delivery_time set to tomorrow at 9 AM
        tomorrow = fields.Date.today() + timedelta(days=1)
        expected_time = datetime.combine(tomorrow, time(9, 0))
        
        self.assertEqual(defaults['delivery_time'], expected_time,
                        "Default delivery time should be tomorrow at 9 AM")

    def test_04_action_assign_all_success(self):
        """Test 4: Test action_assign_all method successfully"""
        # Create wizard with future delivery time
        future_time = datetime.combine(fields.Date.today() + timedelta(days=2), time(10, 0))
        wizard_data = self.wizard_data.copy()
        wizard_data['delivery_time'] = future_time
        
        wizard = self.env['delivery.assign.wizard'].create(wizard_data)
        
        # Execute action
        result = wizard.action_assign_all()
        
        # Verify result structure
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'success')
        self.assertIn('Assignment Complete', result['params']['title'])
        
        # Verify delivery orders are updated
        
        self.assertEqual(self.delivery_order1.driver_name, 'Test Driver')
        self.assertEqual(self.delivery_order1.vehicle_number, 'B 1234 ABC')
        self.assertEqual(self.delivery_order1.delivery_time, future_time)
        
        self.assertEqual(self.delivery_order2.driver_name, 'Test Driver')
        self.assertEqual(self.delivery_order2.vehicle_number, 'B 1234 ABC')
        self.assertEqual(self.delivery_order2.delivery_time, future_time)
        
        # Verify notes are updated
        self.assertIn('Tracking updated', self.delivery_order1.notes)
        self.assertIn('Driver: Test Driver', self.delivery_order1.notes)
        self.assertIn('Vehicle: B 1234 ABC', self.delivery_order1.notes)
        self.assertIn('Delivery time:', self.delivery_order1.notes)

    def test_05_action_assign_all_past_time_error(self):
        """Test 5: Test action_assign_all with past delivery time"""
        # Create wizard with past delivery time
        past_time = datetime.combine(fields.Date.today() - timedelta(days=1), time(10, 0))
        wizard_data = self.wizard_data.copy()
        wizard_data['delivery_time'] = past_time
        
        wizard = self.env['delivery.assign.wizard'].create(wizard_data)
        
        # Should raise ValidationError
        with self.assertRaises(ValidationError) as context:
            wizard.action_assign_all()
        
        self.assertIn("Delivery time cannot be in the past", str(context.exception))

    def test_06_action_assign_all_partial_fields(self):
        """Test 6: Test action_assign_all with only some fields filled"""
        # Create wizard with only driver name
        wizard_data = {
            'delivery_order_ids': [(6, 0, [self.delivery_order1.id])],
            'driver_name': 'Test Driver Only',
            'vehicle_number': False,
            'delivery_time': False,
        }
        
        wizard = self.env['delivery.assign.wizard'].create(wizard_data)
        
        # Execute action
        result = wizard.action_assign_all()
        
        # Verify result
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        
        # Verify only driver name is updated
        self.assertEqual(self.delivery_order1.driver_name, 'Test Driver Only')
        self.assertFalse(self.delivery_order1.vehicle_number)
        self.assertFalse(self.delivery_order1.delivery_time)
        
        # Verify notes contain only driver update
        self.assertIn('Driver: Test Driver Only', self.delivery_order1.notes)
        self.assertNotIn('Vehicle:', self.delivery_order1.notes)
        self.assertNotIn('Delivery time:', self.delivery_order1.notes)

    def test_07_action_assign_all_empty_notes(self):
        """Test 7: Test action_assign_all with delivery orders that have no initial notes"""
        # Create delivery order without notes
        delivery_order_no_notes = self.env['delivery.order'].create({
            'name': 'Test Delivery Order No Notes',
            'customer_id': self.customer.id,
            'delivery_date': fields.Date.today(),
            'product_id': self.product.id,
            'quantity': 20.0,
            'unit_price': 200.0,
            'notes': False,
        })
        
        wizard_data = {
            'delivery_order_ids': [(6, 0, [delivery_order_no_notes.id])],
            'driver_name': 'Test Driver',
            'vehicle_number': 'B 5678 DEF',
            'delivery_time': datetime.combine(fields.Date.today() + timedelta(days=1), time(14, 0)),
        }
        
        wizard = self.env['delivery.assign.wizard'].create(wizard_data)
        
        # Execute action
        wizard.action_assign_all()
        
        # Verify notes are created properly
        self.assertIn('Tracking updated', delivery_order_no_notes.notes)
        self.assertIn('Driver: Test Driver', delivery_order_no_notes.notes)
        self.assertIn('Vehicle: B 5678 DEF', delivery_order_no_notes.notes)
        self.assertIn('Delivery time:', delivery_order_no_notes.notes)

    def test_08_action_assign_all_multiple_changes(self):
        """Test 8: Test action_assign_all with multiple changes to same delivery order"""
        # Create wizard
        wizard = self.env['delivery.assign.wizard'].create(self.wizard_data)
        
        # Execute action first time
        wizard.action_assign_all()
        
        # Update wizard with new values
        wizard.driver_name = 'Updated Driver'
        wizard.vehicle_number = 'B 9999 XYZ'
        wizard.delivery_time = datetime.combine(fields.Date.today() + timedelta(days=3), time(16, 0))
        
        # Execute action again
        wizard.action_assign_all()
        
        # Verify delivery orders are updated with new values
        
        self.assertEqual(self.delivery_order1.driver_name, 'Updated Driver')
        self.assertEqual(self.delivery_order1.vehicle_number, 'B 9999 XYZ')
        self.assertEqual(self.delivery_order1.delivery_time, datetime.combine(fields.Date.today() + timedelta(days=3), time(16, 0)))
        
        # Verify notes contain both updates
        self.assertIn('Tracking updated: Driver: Updated Driver, Vehicle: B 9999 XYZ, Delivery time:', self.delivery_order1.notes)
