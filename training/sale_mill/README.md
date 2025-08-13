# Sale Mill Module - Daily Price Management

## Overview
The Sale Mill module provides comprehensive daily price management functionality within the Sales and Purchase modules. This module has been simplified to focus on daily price input per product-customer/supplier-date combination.

## Key Features

### Simplified Daily Price Structure
- **Direct Price Input**: Each daily price record contains the price directly, eliminating the need for complex price line management
- **Unique Constraints**: One price per product-customer/supplier-date combination to avoid duplicates
- **Simple Interface**: Clean form view with essential fields only

### Core Functionality
- **Daily Price Creation**: Create daily prices for specific product-customer/supplier-date combinations
- **Price Validation**: Ensures prices are positive and unique
- **Copy to Next Day**: Quickly copy today's price to tomorrow
- **Sales Integration**: Automatic price application in sale orders
- **Purchase Integration**: Automatic price application in purchase orders
- **Data Cleanup**: Manage old prices using date-based filtering

### User Interface
- **List View**: Shows all daily prices with key information (product, customer/supplier, date, price, notes)
- **Form View**: Simple form for creating/editing daily prices
- **Search & Filter**: Advanced filtering by date ranges, products, customers/suppliers
- **Grouping**: Group by product, customer/supplier, or date for better organization

## Model Structure

### DailyPrice Model
- `name`: Reference number (auto-generated)
- `product_id`: Product reference
- `customer_id`: Customer/Supplier reference (used for both sales and purchases)
- `date`: Price date
- `unit_price`: Price per unit
- `currency_id`: Currency for the price
- `company_id`: Company (multi-company support)
- `notes`: Additional notes

### Key Methods
- `action_copy_to_next_day()`: Copy price to next day
- `get_price_for_date()`: Get price for specific date
- `check_price_exists()`: Check if price exists for date
- `validate_before_create()`: Validate before creation

## Usage

### Creating Daily Prices
1. Navigate to Sales > Products > Daily Prices
2. Click "Create" button
3. Select product, customer/supplier, and date
4. Enter unit price and currency
5. Add optional notes
6. Save the record

### Copying to Next Day
1. Open an existing daily price record
2. Click "Copy to Next Day" button
3. The system will create a new record for tomorrow with the same price

### Sales Order Integration
- When creating sale orders, the system automatically checks for daily prices
- If a daily price exists for the order date, it's automatically applied
- Validation ensures required daily prices are set before order creation

### Purchase Order Integration
- When creating purchase orders, the system automatically checks for daily prices
- If a daily price exists for the order date, it's automatically applied
- Validation ensures required daily prices are set before order creation
- Works with suppliers (partners) just like customers

## Technical Details

### Constraints
- Unique constraint on (product_id, customer_id, date)
- Positive unit price validation
- Date validation (not more than 1 year in future)

### Security
- Sales users can read/write/create daily prices
- Sales managers have full access including deletion
- Multi-company record rules for data isolation

### Dependencies
- `base`: Core Odoo functionality
- `sale`: Sales module
- `sale_management`: Sales management features
- `purchase`: Purchase module

## Integration Points

### Sales Orders
- **SaleOrderLine**: Automatic price application when product changes
- **Validation**: Ensures daily prices exist before order creation
- **Warning**: Shows message if daily price is missing

### Purchase Orders
- **PurchaseOrderLine**: Automatic price application when product changes
- **Validation**: Ensures daily prices exist before order creation
- **Warning**: Shows message if daily price is missing

### Products
- **ProductProduct**: Methods to check and get daily prices
- **Supplier Support**: Methods for both customer and supplier pricing
- **Action Views**: Quick access to daily prices from product forms

### Partners
- **ResPartner**: Methods for both customer and supplier scenarios
- **Action Views**: Quick access to daily prices from partner forms

## Migration Notes

This module has been simplified from a previous version that used daily price lines. The new structure:
- Eliminates the need for daily price line management
- Provides direct price input per record
- Maintains backward compatibility where possible
- Simplifies the user interface and data model
- Extends functionality to both sales and purchase operations

## Future Enhancements
- Bulk price creation for date ranges
- Price history tracking
- Advanced reporting and analytics
- Integration with other pricing modules
- Supplier-specific pricing rules
- Cost analysis and margin calculations
