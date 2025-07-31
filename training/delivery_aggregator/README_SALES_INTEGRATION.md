# Sales Integration dengan Delivery Order

## Overview
Modul ini menyediakan integrasi sederhana antara modul Sales (Sale Order) dengan modul Delivery Order yang telah dibuat. Integrasi ini memungkinkan pengguna untuk membuat Delivery Order secara otomatis dari Sale Order yang sudah ada.

## Fitur Integrasi

### 1. Link antara Sale Order dan Delivery Order
- Field `sale_order_id` pada model `delivery.order` untuk menghubungkan dengan Sale Order
- Field `sale_order_line_id` untuk menghubungkan dengan Sale Order Line
- Field `delivery_order_ids` pada model `sale.order` untuk melihat semua Delivery Order terkait
- Field `delivery_order_count` untuk menghitung jumlah Delivery Order

### 2. Pembuatan Otomatis Delivery Order
- **Dari Sale Order**: Membuat Delivery Order untuk semua line dalam Sale Order
- **Dari Sale Order Line**: Membuat Delivery Order untuk line tertentu saja
- **Validasi**: Mencegah pembuatan duplikat Delivery Order

### 3. UI Integration
- Tombol "Create Delivery Orders" pada form Sale Order
- Tombol "View Delivery Orders" untuk melihat Delivery Order yang sudah dibuat
- Tab "Delivery Orders" pada form Sale Order
- Field counter untuk menampilkan jumlah Delivery Order
- Tombol "View Sale Order" pada form Delivery Order

### 4. Filter dan Grouping
- Filter "From Sales" untuk Delivery Order yang dibuat dari Sale Order
- Filter "Manual" untuk Delivery Order yang dibuat manual
- Grouping berdasarkan Sale Order

## Cara Penggunaan

### Membuat Delivery Order dari Sale Order (Confirmed)
1. Buka Sale Order yang sudah dikonfirmasi (status 'sale')
2. Klik tombol "Create Delivery Orders" di header
3. Sistem akan membuat Delivery Order untuk setiap line dalam Sale Order
4. Delivery Order akan otomatis terisi dengan data dari Sale Order

### Membuat Delivery Order dari Quotation (Draft)
1. Buka Quotation yang masih dalam status draft
2. Klik tombol "Create Delivery Orders" di header
3. Sistem akan menampilkan wizard konfirmasi
4. Klik "Create Delivery Orders" untuk melanjutkan
5. Delivery Order akan dibuat meskipun quotation belum dikonfirmasi

### Membuat Delivery Order dari Sale Order Line (Confirmed)
1. Buka Sale Order yang sudah dikonfirmasi
2. Pada tab Order Lines, klik tombol "Create DO" pada line tertentu
3. Sistem akan membuat Delivery Order untuk line tersebut saja

### Membuat Delivery Order dari Quotation Line (Draft)
1. Buka Quotation yang masih dalam status draft
2. Pada tab Order Lines, klik tombol "Create DO" pada line tertentu
3. Sistem akan menampilkan wizard konfirmasi
4. Klik "Create Delivery Orders" untuk melanjutkan

### Melihat Delivery Order dari Sale Order
1. Buka Sale Order
2. Klik tombol "View Delivery Orders" atau buka tab "Delivery Orders"
3. Sistem akan menampilkan semua Delivery Order terkait

### Melihat Sale Order dari Delivery Order
1. Buka Delivery Order yang dibuat dari Sale Order
2. Klik tombol "View Sale Order" di header
3. Sistem akan membuka Sale Order terkait

## Model dan Method

### Delivery Order Model
```python
# Fields tambahan
sale_order_id = fields.Many2one('sale.order', string='Sale Order')
sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')

# Methods
def action_view_sale_order(self):
    """Open related sale order"""

@api.model
def create_from_sale_order(self, sale_order_id):
    """Create delivery order from sale order"""

@api.model
def create_from_sale_order_line(self, sale_order_line_id):
    """Create delivery order from specific sale order line"""
```

### Sale Order Model
```python
# Fields tambahan
delivery_order_ids = fields.One2many('delivery.order', 'sale_order_id', string='Delivery Orders')
delivery_order_count = fields.Integer(string='Delivery Orders', compute='_compute_delivery_order_count')

# Methods
def action_create_delivery_orders(self):
    """Create delivery orders from sale order"""

def action_view_delivery_orders(self):
    """View delivery orders for this sale order"""
```

## Testing
Modul ini dilengkapi dengan unit test yang mencakup:
- Pembuatan Delivery Order dari Sale Order
- Pembuatan Delivery Order dari Sale Order Line
- Perhitungan counter Delivery Order
- Validasi duplikasi
- Action methods

## Demo Data
Modul ini menyediakan demo data yang mencakup:
- Sale Order dengan multiple lines
- Delivery Order yang dibuat dari Sale Order
- Contoh berbagai state Delivery Order

## Keuntungan Integrasi
1. **Otomatisasi**: Mengurangi input manual data
2. **Konsistensi**: Data customer, product, quantity, dan price otomatis terisi
3. **Tracking**: Mudah melacak Delivery Order dari Sale Order
4. **Efisiensi**: Workflow yang lebih smooth dari Sales ke Delivery
5. **Fleksibilitas**: Tetap bisa membuat Delivery Order manual jika diperlukan
6. **Quotation Support**: Bisa membuat Delivery Order dari quotation yang belum dikonfirmasi
7. **Validasi**: Wizard konfirmasi untuk quotation mencegah kesalahan

## Workflow dengan Quotation

### Scenario 1: Normal Flow
```
Quotation (Draft) → Confirm Sale Order → Create Delivery Orders → Delivery
```

### Scenario 2: Early Delivery Planning
```
Quotation (Draft) → Create Delivery Orders (with confirmation) → Confirm Sale Order → Delivery
```

### Scenario 3: Partial Delivery
```
Quotation (Draft) → Create Delivery Orders for specific lines → Confirm Sale Order → Delivery
``` 