from odoo import models, fields, api, exceptions
from datetime import date
import calendar
import logging
from dateutil.relativedelta import relativedelta

# Setup logger untuk tracking dan debugging
_logger = logging.getLogger(__name__)

class MonthlySummary(models.Model):
    _name = 'monthly.summary'
    _description = 'Monthly Summary'
    _sql_constraints = [
        ('unique_month_year', 'unique(month, year)', 'A summary for this month and year combination already exists!')
    ]

    name = fields.Char(string='Name', required=True)
    month = fields.Selection([
        ('january', 'January'),
        ('february', 'February'),
        ('march', 'March'),
        ('april', 'April'),
        ('may', 'May'),
        ('june', 'June'),
        ('july', 'July'),
        ('august', 'August'),
        ('september', 'September'),
        ('october', 'October'),
        ('november', 'November'),
        ('december', 'December')
    ], string='Month', required=True)
    year = fields.Integer(string='Year', required=True)
    delivery_order_ids = fields.One2many('delivery.order', 'monthly_summary_id', string='Delivery Orders')
    total_orders = fields.Integer(string='Total Orders', compute='_compute_total_orders', store=True)
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)
    top_customer_id = fields.Many2one('res.partner', string='Top Customer', compute='_compute_top_customer', store=True)
    average_order_value = fields.Float(string='Average Order Value', compute='_compute_average_order_value', store=True)
    delivered_orders = fields.Integer(string='Delivered Orders', compute='_compute_delivered_orders', store=True)
    confirmed_orders = fields.Integer(string='Confirmed Orders', compute='_compute_confirmed_orders', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    summary_date = fields.Date(string='Summary Date', required=True, default=lambda self: fields.Date.context_today(self))
    date_range = fields.Char(string='Date Range', compute='_compute_date_range', store=True)
    state = fields.Selection([
        ('draft', 'In Preparation'),
        ('confirmed', 'Ready for Processing'),
        ('processed', 'Processing Complete')
    ], string='State', required=True, default='draft', order='draft,confirmed,processed')

    @api.depends('month', 'year')
    def _compute_date_range(self):
        """Compute the date range for display"""
        for record in self:
            if record.month and record.year:
                month_mapping = {
                    'january': 'January', 'february': 'February', 'march': 'March', 'april': 'April',
                    'may': 'May', 'june': 'June', 'july': 'July', 'august': 'August',
                    'september': 'September', 'october': 'October', 'november': 'November', 'december': 'December'
                }
                month_name = month_mapping.get(record.month, record.month.title())
                record.date_range = f"{month_name} {record.year}"
            else:
                record.date_range = ""

    @api.depends('delivery_order_ids')
    def _compute_total_orders(self):
        for record in self:
            record.total_orders = len(record.delivery_order_ids)

    @api.depends('delivery_order_ids', 'delivery_order_ids.total_amount')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(record.delivery_order_ids.mapped('total_amount'))

    @api.depends('delivery_order_ids', 'delivery_order_ids.total_amount', 'delivery_order_ids.customer_id')
    def _compute_top_customer(self):
        for record in self:
            if record.delivery_order_ids:
                # Group by customer and sum their total amounts
                customer_totals = {}
                for order in record.delivery_order_ids:
                    customer_id = order.customer_id.id
                    if customer_id not in customer_totals:
                        customer_totals[customer_id] = 0
                    customer_totals[customer_id] += order.total_amount
                
                # Find customer with highest total
                if customer_totals:
                    top_customer_id = max(customer_totals.items(), key=lambda x: x[1])[0]
                    record.top_customer_id = top_customer_id
                else:
                    record.top_customer_id = False
            else:
                record.top_customer_id = False

    @api.depends('total_orders', 'total_amount')
    def _compute_average_order_value(self):
        for record in self:
            if record.total_orders > 0:
                record.average_order_value = record.total_amount / record.total_orders
            else:
                record.average_order_value = 0.0

    @api.depends('delivery_order_ids', 'delivery_order_ids.state')
    def _compute_delivered_orders(self):
        for record in self:
            record.delivered_orders = len(record.delivery_order_ids.filtered(lambda x: x.state == 'delivered'))

    @api.depends('delivery_order_ids', 'delivery_order_ids.state')
    def _compute_confirmed_orders(self):
        for record in self:
            record.confirmed_orders = len(record.delivery_order_ids.filtered(lambda x: x.state == 'confirmed'))

    @api.onchange('month', 'year')
    def _onchange_month_year(self):
        """Automatically populate delivery orders when month or year changes"""
        if self.month and self.year:
            self._update_delivery_orders()

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically populate delivery orders"""
        records = super().create(vals_list)
        for record in records:
            if record.month and record.year:
                record._update_delivery_orders()
        return records

    def write(self, vals):
        """Override write to automatically populate delivery orders when month/year changes"""
        result = super().write(vals)
        # Check if month or year was updated
        if 'month' in vals or 'year' in vals:
            for record in self:
                if record.month and record.year:
                    record._update_delivery_orders()
        return result

    def _update_delivery_orders(self):
        """Update delivery orders based on selected month and year"""
        if not self.month or not self.year:
            return

        # Get month number from month name
        month_mapping = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        month_num = month_mapping.get(self.month)
        if not month_num:
            return

        # Get the last day of the month
        last_day = calendar.monthrange(self.year, month_num)[1]
        
        # Find delivery orders for the selected month and year
        delivery_orders = self.env['delivery.order'].search([
            ('delivery_date', '>=', f'{self.year}-{month_num:02d}-01'),
            ('delivery_date', '<=', f'{self.year}-{month_num:02d}-{last_day:02d}')
        ])

        # Update the delivery_order_ids field
        self.delivery_order_ids = [(6, 0, delivery_orders.ids)]

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_processed(self):
        self.write({'state': 'processed'})

    def action_refresh_orders(self):
        """Action method for the refresh button"""
        self._update_delivery_orders()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Orders Updated',
                'message': f'Delivery orders for {self.date_range} have been refreshed.',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.constrains('month', 'year')
    def _check_unique_month_year(self):
        """Python constraint to check for duplicate month/year combinations"""
        for record in self:
            if record.month and record.year:
                existing_record = self.search([
                    ('month', '=', record.month),
                    ('year', '=', record.year),
                    ('id', '!=', record.id)
                ])
                if existing_record:
                    raise exceptions.ValidationError(
                        f'A summary for {record.month.title()} {record.year} already exists!'
                    )

    @api.model
    def _auto_generate_monthly_summary(self):
        """
        AUTO GENERATE MONTHLY SUMMARY
        =============================
        
        Method ini dipanggil oleh cron job setiap bulan untuk otomatis membuat
        monthly summary dari bulan sebelumnya.
        
        Returns:
            - MonthlySummary record jika berhasil
            - False jika terjadi error
        """
        try:
            # STEP 1: Ambil tanggal hari ini dan hitung bulan sebelumnya
            current_date = fields.Date.today()  # Contoh: 2024-02-15
            prev_month_date = current_date - relativedelta(months=1)  # Contoh: 2024-01-15
            
            # STEP 2: Mapping angka bulan ke nama bulan (sesuai dengan field selection)
            month_mapping = {
                1: 'january', 2: 'february', 3: 'march', 4: 'april',
                5: 'may', 6: 'june', 7: 'july', 8: 'august',
                9: 'september', 10: 'october', 11: 'november', 12: 'december'
            }
            
            # Ambil nama bulan dan tahun dari tanggal bulan sebelumnya
            month_name = month_mapping.get(prev_month_date.month)  # Contoh: 'january'
            year = prev_month_date.year  # Contoh: 2024
            
            # Validasi: pastikan mapping bulan valid
            if not month_name:
                _logger.error(f"Invalid month number: {prev_month_date.month}")
                return False
            
            # STEP 3: Cek apakah summary untuk bulan dan tahun ini sudah ada
            # Ini mencegah duplikasi jika cron job berjalan berkali-kali
            existing_summary = self.search([
                ('month', '=', month_name),  # Contoh: 'january'
                ('year', '=', year)          # Contoh: 2024
            ])
            
            # STEP 4: Jika summary belum ada, buat yang baru
            if not existing_summary:
                # Buat record monthly summary baru
                summary = self.create({
                    'name': f'Auto Generated - {month_name.title()} {year}',  # Contoh: 'Auto Generated - January 2024'
                    'month': month_name,  # Contoh: 'january'
                    'year': year,         # Contoh: 2024
                    'state': 'confirmed'  # Auto set ke confirmed (tidak perlu draft)
                })
                
                # Log untuk tracking dan monitoring
                _logger.info(f"Auto-generated monthly summary for {month_name.title()} {year}")
                
                return summary
            else:
                # STEP 5: Jika summary sudah ada, return yang ada (mencegah duplikasi)
                _logger.info(f"Monthly summary for {month_name.title()} {year} already exists")
                return existing_summary
                
        except Exception as e:
            # Error handling: log error dan return False
            _logger.error(f"Error in auto-generating monthly summary: {e}")
            return False