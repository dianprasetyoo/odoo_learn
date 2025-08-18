# FFB Purchase - Purchase Pricing Configuration

## Fitur Utama

Modul ini menambahkan fitur otomatis pricing untuk purchase order berdasarkan harga sale dari modul `sale_mill` (daily price).

## Cara Penggunaan

### 1. Setup Konfigurasi Pricing

1. **Masuk ke menu**: Purchase > FFB Purchase > Configuration > Purchase Pricing Configuration
2. **Buat konfigurasi baru** dengan parameter:
   - **Name**: Nama konfigurasi (contoh: "FFB Pricing - Vendor A")
   - **Product**: Pilih produk (contoh: Fresh Fruit Bunches)
   - **Vendor**: Pilih vendor/supplier
   - **Pricing Method**: 
     - "Minimum Sale Price": Menggunakan harga minimum dari daily price
     - "Average Sale Price": Menggunakan harga rata-rata dari daily price
   - **Discount Percentage**: Persentase diskon dari harga sale (contoh: 10%)
   - **Date Range (Days)**: Rentang hari untuk mencari data daily price (default: 30 hari)

### 2. Membuat Purchase Order

1. **Buat Purchase Order** baru
2. **Pilih vendor** yang sudah dikonfigurasi
3. **Aktifkan "Use Pricing Configuration"** (default aktif)
4. **Set tanggal range** untuk perhitungan harga (optional)
5. **Tambahkan product line**:
   - Ketika memilih product yang sudah dikonfigurasi, harga akan otomatis dihitung
   - System akan menampilkan informasi:
     - Base Sale Price
     - Discount Amount  
     - Final Purchase Price
     - Detail perhitungan

### 3. Cara Kerja Sistem

#### Contoh Perhitungan:
Jika ada daily price untuk FFB:
- Tanggal 1-10: Harga 10,000
- Tanggal 11-20: Harga 12,000  
- Tanggal 21-30: Harga 11,000

**Dengan Method "Minimum Price" + Discount 10%:**
- Base Price = 10,000 (minimum)
- Discount = 10,000 × 10% = 1,000
- **Final Purchase Price = 9,000**

**Dengan Method "Average Price" + Discount 10%:**
- Base Price = (10,000 + 12,000 + 11,000) ÷ 3 = 11,000
- Discount = 11,000 × 10% = 1,100  
- **Final Purchase Price = 9,900**

### 4. Fitur Tambahan

- **Recalculate Price**: Button untuk menghitung ulang harga
- **Pricing Details**: Button untuk melihat detail perhitungan
- **Apply Pricing Config**: Button untuk apply konfigurasi ke semua line
- **Price Calculation Info**: Field yang menampilkan informasi detail perhitungan

## Syarat

1. **Daily Price harus sudah ada** di modul `sale_mill` untuk produk yang bersangkutan
2. **Konfigurasi pricing** harus dibuat untuk kombinasi product-vendor
3. **Date range** yang dipilih harus mengandung data daily price

## Troubleshooting

### Harga tidak ter-calculate otomatis:
1. Check apakah ada konfigurasi untuk product-vendor tersebut
2. Check apakah ada daily price data dalam rentang tanggal yang dipilih
3. Check apakah "Use Pricing Configuration" diaktifkan

### Error saat save konfigurasi:
1. Pastikan tidak ada duplikasi konfigurasi untuk product-vendor yang sama
2. Pastikan discount percentage dalam range 0-100%
3. Pastikan date range > 0

## Dependencies

- `purchase`: Modul purchase standar Odoo
- `sale_mill`: Modul untuk daily price management
