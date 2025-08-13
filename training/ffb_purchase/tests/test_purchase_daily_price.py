from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class TestPurchaseDailyPrice(TransactionCase):

    def setUp(self):
        super(TestPurchaseDailyPrice, self).setUp()
        
        # Create test data
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'purchase_ok': True,
        })
        
        self.supplier = self.env['res.partner'].create({
            'name': 'Test Supplier',
            'supplier_rank': 1,
        })
        
        self.company = self.env.company
        self.currency = self.company.currency_id
        
        # Create daily price
        self.daily_price = self.env['purchase.daily.price'].create({
            'product_id': self.product.id,
            'supplier_id': self.supplier.id,
            'date': date.today(),
            'unit_price': 100.0,
            'currency_id': self.currency.id,
        })

    def test_daily_price_creation(self):
        """Test that daily price is created correctly"""
        self.assertEqual(self.daily_price.product_id, self.product)
        self.assertEqual(self.daily_price.supplier_id, self.supplier)
        self.assertEqual(self.daily_price.unit_price, 100.0)
        self.assertTrue(self.daily_price.name.startswith('New'))

    def test_daily_price_uniqueness(self):
        """Test that duplicate daily prices are not allowed"""
        with self.assertRaises(ValidationError):
            self.env['purchase.daily_price'].create({
                'product_id': self.product.id,
                'supplier_id': self.supplier.id,
                'date': date.today(),
                'unit_price': 150.0,
                'currency_id': self.currency.id,
            })

    def test_purchase_order_with_daily_price(self):
        """Test that purchase order line gets daily price automatically"""
        # Create purchase order
        po = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'date_planned': date.today(),
        })
        
        # Add line
        po_line = self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product.id,
            'product_uom_qty': 10.0,
            'product_uom': self.product.uom_po_id.id,
        })
        
        # Check that daily price is applied
        self.assertEqual(po_line.price_unit, 100.0)

    def test_quantity_change_maintains_daily_price(self):
        """Test that changing quantity maintains daily price"""
        # Create purchase order
        po = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'date_planned': date.today(),
        })
        
        # Add line
        po_line = self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product.id,
            'product_uom_qty': 10.0,
            'product_uom': self.product.uom_po_id.id,
        })
        
        # Change quantity
        po_line.product_uom_qty = 20.0
        
        # Check that daily price is maintained
        self.assertEqual(po_line.price_unit, 100.0)

    def test_uom_change_maintains_daily_price(self):
        """Test that changing UoM maintains daily price"""
        # Create purchase order
        po = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'date_planned': date.today(),
        })
        
        # Add line
        po_line = self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product.id,
            'product_uom_qty': 10.0,
            'product_uom': self.product.uom_po_id.id,
        })
        
        # Change UoM (if different UoM exists)
        if self.product.uom_po_id != self.product.uom_id:
            po_line.product_uom = self.product.uom_id.id
            
            # Check that daily price is maintained
            self.assertEqual(po_line.price_unit, 100.0)

    def test_manual_price_change_reverts_to_daily_price(self):
        """Test that manually changing price reverts to daily price"""
        # Create purchase order
        po = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'date_planned': date.today(),
        })
        
        # Add line
        po_line = self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product.id,
            'product_uom_qty': 10.0,
            'product_uom': self.product.uom_po_id.id,
        })
        
        # Manually change price
        po_line.price_unit = 150.0
        
        # Check that daily price is reverted
        self.assertEqual(po_line.price_unit, 100.0)

    def test_date_change_updates_daily_price(self):
        """Test that changing date updates daily price"""
        # Create daily price for tomorrow
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_price = self.env['purchase.daily.price'].create({
            'product_id': self.product.id,
            'supplier_id': self.supplier.id,
            'date': tomorrow,
            'unit_price': 120.0,
            'currency_id': self.currency.id,
        })
        
        # Create purchase order
        po = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'date_planned': date.today(),
        })
        
        # Add line
        po_line = self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product.id,
            'product_uom_qty': 10.0,
            'product_uom': self.product.uom_po_id.id,
        })
        
        # Change date to tomorrow
        po.date_planned = tomorrow
        
        # Check that daily price is updated
        self.assertEqual(po_line.price_unit, 120.0)

    def test_supplier_change_updates_daily_price(self):
        """Test that changing supplier updates daily price"""
        # Create another supplier with different price
        supplier2 = self.env['res.partner'].create({
            'name': 'Test Supplier 2',
            'supplier_rank': 1,
        })
        
        supplier2_price = self.env['purchase.daily.price'].create({
            'product_id': self.product.id,
            'supplier_id': supplier2.id,
            'date': date.today(),
            'unit_price': 80.0,
            'currency_id': self.currency.id,
        })
        
        # Create purchase order
        po = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'date_planned': date.today(),
        })
        
        # Add line
        po_line = self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product.id,
            'product_uom_qty': 10.0,
            'product_uom': self.product.uom_po_id.id,
        })
        
        # Change supplier
        po.partner_id = supplier2
        
        # Check that daily price is updated
        self.assertEqual(po_line.price_unit, 80.0)

    def test_copy_line_maintains_daily_price(self):
        """Test that copying line maintains daily price"""
        # Create purchase order
        po = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'date_planned': date.today(),
        })
        
        # Add line
        po_line = self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product.id,
            'product_uom_qty': 10.0,
            'product_uom': self.product.uom_po_id.id,
        })
        
        # Copy line
        copied_line = po_line.copy()
        
        # Check that daily price is maintained
        self.assertEqual(copied_line.price_unit, 100.0)
        self.assertEqual(copied_line.product_uom_qty, 10.0)
