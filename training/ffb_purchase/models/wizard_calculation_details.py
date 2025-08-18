from odoo import models, fields, api, _


class WizardCalculationDetails(models.TransientModel):
    _name = 'wizard.calculation.details'
    _description = 'Calculation Details Wizard'

    # Configuration fields
    config_id = fields.Many2one('purchase.pricing.config', string='Configuration', readonly=True)
    product_name = fields.Char(string='Product', readonly=True)
    vendor_name = fields.Char(string='Vendor', readonly=True)
    pricing_method = fields.Selection([
        ('min_price', 'Minimum Sale Price'),
        ('avg_price', 'Average Sale Price'),
    ], string='Pricing Method', readonly=True)
    purchase_margin = fields.Float(string='Purchase Margin (%)', readonly=True)
    date_range_days = fields.Integer(string='Date Range (Days)', readonly=True)
    date_from = fields.Date(string='Date From', readonly=True)
    date_to = fields.Date(string='Date To', readonly=True)
    
    # Calculation results
    price_count = fields.Integer(string='Sale Orders Found', readonly=True)
    base_price = fields.Float(string='Base Sale Price', readonly=True)
    margin_amount = fields.Float(string='Purchase Margin Amount', readonly=True)
    final_price = fields.Float(string='Final Purchase Price', readonly=True)
    profit_margin = fields.Float(string='Expected Profit (%)', readonly=True)
    
    # Sale order lines
    sale_order_line_ids = fields.One2many('wizard.calculation.details.line', 'wizard_id', 
                                         string='Sale Order Details', readonly=True)


class WizardCalculationDetailsLine(models.TransientModel):
    _name = 'wizard.calculation.details.line'
    _description = 'Calculation Details Sale Order Line'

    wizard_id = fields.Many2one('wizard.calculation.details', string='Wizard', ondelete='cascade')
    customer_name = fields.Char(string='Customer', readonly=True)
    order_name = fields.Char(string='Sale Order', readonly=True)
    order_date = fields.Date(string='Order Date', readonly=True)
    unit_price = fields.Float(string='Unit Price', readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)
    subtotal = fields.Float(string='Subtotal', readonly=True)
