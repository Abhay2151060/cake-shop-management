# Product Requirements Document (PRD)

## Cake Shop Management System

**Document Version:** 1.0  
**Status:** Draft / Development Baseline  
**Project Type:** Local Cake Shop Management Web Application  
**Primary Users:** Cake Shop Owner, Store Staff  
**Recommended Stack:** Laravel + MySQL + Blade + Bootstrap 5 + JavaScript/AJAX

---

# 1. Product Overview

## 1.1 Product Name

**Cake Shop Management System**

The Cake Shop Management System is a web-based internal business management application designed for a local cake shop.

The system will help the shop owner and store staff manage:

- Cake categories
- Cake products
- Inventory
- Regular cake orders
- Multiple products within a single order
- Custom cake orders
- Cash and UPI payments
- Pending/credit transactions
- Order status
- Sales reports
- Inventory status
- Business analytics
- Shop settings

The system is intended primarily for **physical/in-store operations**.

Customers will continue to visit the physical shop and place orders directly with the staff.

The system is **not an online cake ordering platform** in the initial version.

---

# 2. Business Problem

The cake shop currently handles customers and orders physically.

When a customer purchases one or more cakes, staff needs to record the order details so that the owner can monitor business activity.

Without a centralized system, the shop may face problems such as:

- Difficulty tracking daily orders
- Difficulty tracking total sales
- Difficulty identifying pending/credit payments
- Difficulty monitoring inventory
- Difficulty tracking custom cake requirements
- Difficulty knowing which cakes are selling most
- Difficulty reviewing historical orders
- Manual calculation errors
- Lack of centralized business reports
- Difficulty monitoring staff activity

The proposed system will centralize these operations into a single web application.

---

# 3. Product Goals

## 3.1 Primary Goals

The system should:

1. Allow authorized users to log in.
2. Provide different access levels for Owner and Staff.
3. Allow staff to create new orders quickly.
4. Support single-product and multi-product orders.
5. Automatically calculate order totals.
6. Record Cash, UPI, and Pending transactions.
7. Allow the owner to monitor pending/credit payments.
8. Allow staff to create custom cake orders.
9. Allow the owner to manage products and categories.
10. Allow the owner to manage inventory.
11. Provide inventory visibility and low-stock alerts.
12. Provide sales and business reports.
13. Provide an easy-to-use dashboard.
14. Allow the owner to configure basic shop settings.

---

# 4. Product Scope

## 4.1 In Scope

The first version will include:

- Authentication
- Owner module
- Staff module
- Dashboard
- Category management
- Product management
- Inventory management
- Order management
- Multiple items per order
- Payment tracking
- Pending/credit tracking
- Custom cake order management
- Reports and analytics
- Profile management
- Shop settings
- Theme settings
- Shop logo management
- Audit logging

---

## 4.2 Out of Scope

The following features are not required in the initial version:

- Customer management
- Customer accounts
- Customer login
- Online customer ordering
- E-commerce website
- Online payment gateway
- UPI payment API
- UPI QR generation
- Delivery management
- Delivery boy management
- Customer mobile application
- Customer loyalty program
- Email marketing
- SMS marketing
- WhatsApp API integration
- Multi-branch management

These may be considered for future versions.

---

# 5. User Roles

The system will initially support two primary roles.

## 5.1 Owner

The Owner has full access to the system.

### Owner permissions

- Login
- View dashboard
- Manage categories
- Manage products
- Manage inventory
- View all orders
- View order details
- Manage custom cake information
- View pending payments
- Update pending payments
- View reports
- View analytics
- Manage staff
- Manage profile
- Manage shop settings
- Manage logo
- Manage theme
- Logout

---

# 6. Staff

Staff users are responsible for day-to-day shop operations.

### Staff permissions

- Login
- View staff dashboard
- Create new order
- Add multiple products to order
- View current orders
- Update allowed order statuses
- Record Cash payment
- Record UPI payment
- Record Pending/credit transaction
- Create custom cake order
- View custom cake order information
- View available products
- Logout

Staff should not have access to:

- Shop settings
- Owner profile
- Business-level reports
- User management
- Product deletion
- Category deletion
- Manual inventory adjustment unless explicitly permitted
- System configuration

---

# 7. Authentication

## 7.1 Login

Both Owner and Staff will use the login page.

Required fields:

- Username / Email
- Password

System behavior:

1. User enters credentials.
2. System validates credentials.
3. System identifies user role.
4. System creates authenticated session.
5. User is redirected to the appropriate dashboard.

---

## 7.2 Authentication Requirements

- Passwords must never be stored as plain text.
- Password hashing must be used.
- Sessions must be securely managed.
- Unauthorized users must not access protected pages.
- Role-based authorization must be enforced on the server side.
- Logout must invalidate the active session.

---

# 8. Owner Dashboard

The Owner Dashboard will provide a high-level view of the shop's current business activity.

## 8.1 KPI Cards

The dashboard should display:

### Today's Orders

Number of orders created today.

### Today's Sales

Total value of completed/paid orders for the day.

### Cash Collection

Total amount received through Cash.

### UPI Collection

Total amount received through UPI.

### Pending Amount

Total amount currently pending/credit.

### Custom Cake Orders

Number of custom cake orders.

### Current Orders

Number of active orders.

### Low Stock Items

Number of inventory items below the configured minimum stock level.

---

# 9. Dashboard Analytics

The Owner Dashboard should provide visual analytics.

## 9.1 Sales Trend

Display:

- Daily sales
- Weekly sales
- Monthly sales
- Custom date range

Recommended visualization:

**Line Chart**

---

## 9.2 Order Trend

Display the number of orders over time.

Recommended visualization:

**Bar Chart**

---

## 9.3 Payment Analysis

Show:

- Cash
- UPI
- Pending

Recommended visualization:

**Doughnut / Pie Chart**

---

## 9.4 Product Performance

Display:

- Top-selling products
- Lowest-selling products
- Quantity sold
- Revenue generated

---

# 10. Category Management

The Owner can manage cake categories.

## 10.1 Add Category

Fields:

- Category Name
- Description
- Status

Example categories:

- Birthday Cakes
- Anniversary Cakes
- Wedding Cakes
- Chocolate Cakes
- Photo Cakes
- Eggless Cakes
- Pastries

---

## 10.2 Category List

Display:

- Category ID
- Category Name
- Description
- Product Count
- Status
- Created Date
- Actions

Actions:

- View
- Edit
- Delete
- Activate/Deactivate

---

## 10.3 Category Validation

- Category name is required.
- Category name should be unique.
- Empty category names are not allowed.
- Deleted categories should not break existing historical orders.

Recommended approach:

Use soft deletion or prevent deletion when products/orders depend on the category.

---

# 11. Product Management

The Owner can manage cake products.

## 11.1 Add Product

Fields:

- Product Name
- Category
- Product Code / SKU
- Description
- Size / Weight
- Selling Price
- Cost Price
- Available Quantity
- Minimum Stock Level
- Image
- Status

Example:

```text
Product: Chocolate Truffle Cake
Category: Chocolate Cakes
Size: 1 KG
Selling Price: ₹850
Cost Price: ₹500
Minimum Stock: 5
Status: Active
```

---

## 11.2 Product List

Display:

- Product image
- Product name
- Category
- Size
- Selling price
- Available stock
- Status
- Actions

Actions:

- View
- Edit
- Activate/Deactivate
- Delete

---

## 11.3 Product Rules

- Product name is required.
- Category is required.
- Selling price must be greater than or equal to zero.
- Product code should be unique.
- Inactive products cannot be added to new orders.
- Existing orders must retain historical product information.

---

# 12. Order Management

Order Management is the core module of the application.

The system must support:

- Single-product orders
- Multiple-product orders

---

# 13. New Order

Staff will use the New Order screen to create an order.

## 13.1 Order Creation Flow

```text
New Order
   ↓
Select Product
   ↓
Enter Quantity
   ↓
Add Item
   ↓
Add More Items?
   ├── Yes → Select another product
   └── No
   ↓
Calculate Subtotal
   ↓
Apply Discount if applicable
   ↓
Calculate Grand Total
   ↓
Select Payment
   ↓
Save Order
   ↓
Generate Order ID
```

---

# 14. Order Information

The order should contain:

- Order ID
- Order date
- Order time
- Staff ID
- Order status
- Order items
- Quantity
- Unit price
- Subtotal
- Discount
- Grand total
- Payment status
- Payment method
- Paid amount
- Pending amount
- Notes

---

# 15. Multiple Product Orders

A single order can contain multiple products.

Example:

```text
Order ID: ORD-000125

Chocolate Cake 1 KG       × 2
Black Forest Cake 1 KG    × 1
Chocolate Pastry          × 4

Subtotal: ₹2,500
Discount: ₹100

Grand Total: ₹2,400
Payment: UPI
Status: Paid
```

The database must use a separate `order_items` table.

Orders must not store multiple products in a single text field.

---

# 16. Order Calculation

The system should calculate:

```text
Item Total = Quantity × Unit Price

Subtotal = Sum of all Item Totals

Grand Total = Subtotal - Discount
```

Example:

```text
Chocolate Cake
₹800 × 2 = ₹1,600

Black Forest
₹700 × 1 = ₹700

Subtotal = ₹2,300

Discount = ₹100

Grand Total = ₹2,200
```

All calculations should be validated server-side.

---

# 17. Payment Management

Payment handling is intentionally simple because the shop uses physical payments.

## 17.1 Payment Methods

Supported payment methods:

- Cash
- UPI

The system does not directly process UPI payments.

The shop already has a physical UPI QR code displayed in the store.

The staff only needs to record that the customer paid through UPI.

---

# 18. Pending / Credit Transactions

`Pending` represents an **udhaar / credit transaction**.

It is not an online payment method.

Example:

```text
Order Total: ₹1,500

Payment Status: Pending
Paid Amount: ₹0
Pending Amount: ₹1,500
```

The Owner should be able to see all pending transactions.

---

# 19. Payment Status

Payment status:

- Paid
- Pending
- Partially Paid

## Paid

The complete order amount has been received.

## Pending

No payment has been received.

## Partially Paid

Some amount has been received and the remaining amount is pending.

Example:

```text
Grand Total: ₹2,000
Paid: ₹1,000
Pending: ₹1,000
Status: Partially Paid
```

---

# 20. Payment Recording

For a paid order:

```text
Payment Method:
- Cash
- UPI
```

For a pending order:

```text
Payment Status:
Pending
```

When pending payment is later received, the Owner can mark it as paid.

The Owner should record:

- Amount received
- Payment method
- Payment date
- Updated by

---

# 21. Pending Payment Dashboard

The Owner should have a dedicated Pending Payments section.

Display:

- Order ID
- Order Date
- Original Amount
- Paid Amount
- Pending Amount
- Payment Status
- Payment Date
- Action

Actions:

- View
- Record Payment
- Mark as Paid

---

# 22. Order Status

The system should track the operational status of an order.

Recommended statuses:

```text
New
Confirmed
Preparing
Ready
Completed
Cancelled
```

For a normal walk-in sale, the order may move quickly:

```text
New → Completed
```

For pre-orders/custom cakes:

```text
New
 ↓
Confirmed
 ↓
Preparing
 ↓
Ready
 ↓
Completed
```

---

# 23. Current Orders

Staff should have access to current active orders.

Current orders include:

- New
- Confirmed
- Preparing
- Ready

Completed and cancelled orders should not appear in the default Current Orders view.

---

# 24. Order Details

Order details should display:

```text
Order ID
Date / Time
Created By

Products
--------------------------------
Product
Quantity
Unit Price
Total
--------------------------------

Subtotal
Discount
Grand Total

Payment Status
Payment Method
Paid Amount
Pending Amount

Order Status

Notes
```

---

# 25. Custom Cake Management

Custom cakes require a separate workflow because they may contain design requirements that do not exist as standard products.

## 25.1 Staff Custom Cake Order

Staff should be able to enter:

- Custom cake type
- Flavor
- Weight
- Shape
- Design / Theme
- Cake message
- Required date
- Required time
- Special instructions
- Reference image
- Estimated price
- Advance amount
- Pending amount
- Order status

---

# 26. Custom Cake Example

```text
Custom Cake Order

Flavor:
Chocolate

Weight:
2 KG

Shape:
Round

Theme:
Birthday / Cartoon

Message:
Happy Birthday Aryan

Required Date:
25-Aug-2026

Required Time:
06:00 PM

Special Instructions:
Extra chocolate decoration

Reference Image:
Uploaded image

Total:
₹2,400

Advance:
₹1,000

Pending:
₹1,400
```

---

# 27. Custom Cake Management — Owner

Owner can:

- View custom cake orders
- View custom cake details
- Edit custom cake information
- Update status
- View reference image
- View payment information

The Owner should be able to filter custom cake orders by:

- Date
- Status
- Upcoming date
- Completed
- Pending payment

---

# 28. Custom Cake Status

Recommended statuses:

```text
New
Confirmed
Preparing
Ready
Completed
Cancelled
```

---

# 29. Inventory Management

Inventory management will help the owner monitor available stock.

Inventory can represent:

- Finished cakes/products
- Raw materials/ingredients

The initial implementation should prioritize the inventory model actually used by the shop.

---

# 30. Inventory Details

Each inventory item may contain:

- Inventory ID
- Item Name
- Item Type
- Unit
- Current Quantity
- Minimum Quantity
- Purchase Price
- Supplier
- Expiry Date
- Status

Examples:

```text
Cream
Chocolate
Sugar
Flour
Cake Boxes
Candles
Decorations
Ready-made Cakes
```

---

# 31. Inventory Transactions

Inventory changes should be recorded as transactions.

Transaction types:

- Stock In
- Stock Out
- Adjustment

Each transaction should store:

- Item
- Quantity
- Transaction type
- Previous quantity
- New quantity
- Reason
- User
- Date/time

This creates an inventory history.

---

# 32. Low Stock Alert

The system should compare:

```text
Current Stock
        <
Minimum Stock Level
```

If true, the item should be marked as:

**Low Stock**

The Owner Dashboard should display the number of low-stock items.

---

# 33. Inventory and Orders

Where appropriate, completing a product order should reduce inventory automatically.

Example:

```text
Chocolate Cake Stock = 10

Order:
Chocolate Cake × 2

After Order:
Chocolate Cake Stock = 8
```

The exact inventory deduction model should be determined based on the shop's real operational process.

If the shop prepares cakes only after receiving orders, inventory may instead track raw materials rather than finished cakes.

---

# 34. Reports

The Owner should have access to business reports.

## 34.1 Sales Report

Filters:

- Today
- Yesterday
- This Week
- This Month
- Custom Date Range

Display:

- Number of orders
- Total sales
- Cash sales
- UPI sales
- Pending amount
- Discounts

---

# 35. Order Report

Display:

- Total orders
- Completed orders
- Pending orders
- Cancelled orders
- Custom cake orders

Filters:

- Date
- Order status
- Staff
- Payment status

---

# 36. Product Report

Display:

- Product name
- Quantity sold
- Revenue
- Selling price

Analytics:

- Top-selling products
- Least-selling products

---

# 37. Inventory Report

Display:

- Current stock
- Low stock
- Stock in
- Stock out
- Inventory adjustments

---

# 38. Pending Payment Report

Display:

- Total pending orders
- Total pending amount
- Partially paid orders
- Fully pending orders
- Payments received during selected period

---

# 39. Export

Reports should optionally support:

- CSV
- Excel
- PDF

Exported reports should contain the selected date range and relevant filters.

---

# 40. Owner Profile

Owner can manage:

- Name
- Email
- Phone
- Profile photo
- Password

Password change should require:

- Current password
- New password
- Confirm new password

---

# 41. Staff Management

The Owner should be able to manage staff accounts.

Functions:

- Add Staff
- View Staff
- Edit Staff
- Activate/Deactivate Staff
- Reset Password
- Delete/Deactivate Account

Staff information:

- Name
- Username
- Email
- Phone
- Role
- Status
- Created Date

---

# 42. Settings

The Owner can configure shop-level settings.

## 42.1 Shop Information

- Shop Name
- Shop Logo
- Shop Address
- Phone Number
- Email
- GST information if applicable
- Receipt footer

---

# 43. Theme Settings

Owner can select:

- Light Theme
- Dark Theme

Theme preference should be stored and loaded automatically.

---

# 44. Logo Management

Owner can:

- Upload logo
- Replace logo
- Remove logo

The logo should appear on:

- Dashboard
- Navigation
- Receipts
- Reports where appropriate

---

# 45. Audit Logs

Important actions should be logged.

Examples:

- Login
- Logout
- Product created
- Product updated
- Product deleted
- Order created
- Order updated
- Payment recorded
- Inventory adjusted
- Custom cake updated
- Settings changed

Audit log should contain:

- User
- Action
- Module
- Record ID
- Timestamp
- Optional description

This is especially useful for Owner-level monitoring.

---

# 46. Notifications

The system may display internal notifications for:

- Low stock
- Upcoming custom cake
- Pending payments
- Orders ready
- Cancelled orders

Initial notifications can be dashboard-based rather than SMS/email.

---

# 47. Search and Filtering

The system should provide search functionality where appropriate.

## Orders

Search by:

- Order ID
- Date
- Status
- Payment status

## Products

Search by:

- Product name
- Product code
- Category

## Inventory

Search by:

- Item name
- Stock status

## Custom Cakes

Search/filter by:

- Order ID
- Required date
- Status

---

# 48. Data Validation

All forms must perform:

### Client-side validation

For immediate user feedback.

### Server-side validation

For security and data integrity.

Examples:

- Required fields
- Valid numbers
- Positive quantities
- Valid prices
- Valid dates
- Valid image types
- Maximum upload size
- Unique product codes
- Unique usernames/emails where applicable

---

# 49. Error Handling

The system should provide clear messages.

Examples:

```text
"Product added successfully."

"Order created successfully."

"Payment recorded successfully."

"Insufficient stock."

"Invalid login credentials."

"This product cannot be deleted because it is associated with existing orders."

"Please enter a valid quantity."
```

Technical errors should not expose database or server details to users.

---

# 50. Security Requirements

The application must implement:

- Password hashing
- CSRF protection
- Server-side validation
- Authorization checks
- Session security
- SQL injection protection
- XSS protection
- Secure file upload validation
- Access control
- Rate limiting for login where appropriate

Laravel's built-in security mechanisms should be used wherever possible.

---

# 51. Database Requirements

The application will use **MySQL**.

The database should be normalized and maintain referential integrity.

Recommended core tables:

```text
users
roles

categories

products

orders
order_items

payments

custom_cake_orders

inventory_items
inventory_transactions

settings

audit_logs
```

Additional tables may be introduced when required by the final implementation.

---

# 52. Important Database Relationships

## Order → Order Items

One order can contain multiple order items.

```text
orders
   │
   └── order_items
           │
           └── products
```

Relationship:

```text
orders 1 ──── N order_items
products 1 ── N order_items
```

---

# 53. Order → Payment

An order can have one or multiple payment records depending on the implementation.

This is important for partially paid/pending transactions.

```text
orders
   │
   └── payments
```

Example:

```text
Order Total = ₹2,000

Payment 1:
Cash = ₹1,000

Payment 2:
UPI = ₹1,000

Status = Paid
```

For a pending order:

```text
Order Total = ₹2,000

Payment = ₹0

Status = Pending
```

---

# 54. Product → Category

```text
categories
     │
     └── products
```

One category can contain multiple products.

---

# 55. Inventory Relationships

```text
inventory_items
       │
       └── inventory_transactions
```

Each inventory transaction records a stock movement.

---

# 56. Order ID

Each order must have a unique human-readable Order ID.

Example:

```text
ORD-000001
ORD-000002
ORD-000003
```

The Order ID must never be reused.

---

# 57. Custom Cake ID

Custom cake orders should also have a unique identifier.

Example:

```text
CC-000001
CC-000002
```

---

# 58. User Experience Requirements

The application should be designed for fast operation because staff will use it during customer interactions.

The New Order screen should minimize unnecessary clicks.

Priority:

**Speed > visual complexity**

The staff should be able to create a normal order in a few simple steps.

---

# 59. Responsive Design

The system should support:

- Desktop
- Laptop
- Tablet

The primary target is a shop desktop/laptop.

Mobile responsiveness is desirable but not the primary requirement.

---

# 60. UI Design Principles

The interface should be:

- Clean
- Simple
- Professional
- Easy to understand
- Consistent
- Responsive
- Fast

Use:

- Sidebar navigation
- Dashboard cards
- Tables
- Modal forms where appropriate
- Confirmation dialogs
- Toast notifications
- Search/filter controls
- Status badges

---

# 61. Recommended Navigation

## Owner Sidebar

```text
Dashboard

Orders
  ├── All Orders
  ├── Current Orders
  └── Pending Payments

Custom Cakes

Products
  ├── Products
  └── Categories

Inventory

Reports & Analytics

Staff

Profile

Settings

Logout
```

## Staff Sidebar

```text
Dashboard

New Order

Current Orders

Custom Cake Orders

Logout
```

---

# 62. Order Creation UI

The New Order interface should behave like a lightweight POS.

Example:

```text
------------------------------------------------
NEW ORDER
------------------------------------------------

Product        Qty       Price       Total

Chocolate Cake  2        ₹800       ₹1,600
Black Forest    1        ₹700         ₹700

[ + Add Product ]

------------------------------------------------
Subtotal                    ₹2,300
Discount                      ₹100
Grand Total                 ₹2,200

Payment Status:
( ) Paid
( ) Partially Paid
( ) Pending

Payment Method:
( ) Cash
( ) UPI

Paid Amount:               ₹2,200

[ SAVE ORDER ]
------------------------------------------------
```

---

# 63. Receipt

After successfully creating an order, the system should provide a receipt/invoice view.

Receipt should contain:

- Shop logo
- Shop name
- Address
- Order ID
- Date/time
- Items
- Quantity
- Price
- Discount
- Total
- Payment status
- Payment method
- Pending amount
- Footer message

Actions:

- Print
- Download PDF

---

# 64. Business Rules

## Rule 1

Inactive products cannot be added to new orders.

## Rule 2

An order must contain at least one product.

## Rule 3

Quantity must be greater than zero.

## Rule 4

Grand total cannot be negative.

## Rule 5

Paid amount cannot exceed grand total.

## Rule 6

Pending amount is:

```text
Pending Amount = Grand Total - Total Paid
```

## Rule 7

If:

```text
Paid Amount = Grand Total
```

then:

```text
Payment Status = Paid
```

## Rule 8

If:

```text
Paid Amount = 0
```

then:

```text
Payment Status = Pending
```

## Rule 9

If:

```text
0 < Paid Amount < Grand Total
```

then:

```text
Payment Status = Partially Paid
```

## Rule 10

Cancelled orders should not be counted as completed sales.

## Rule 11

Historical orders must preserve the price at the time of purchase even if the product price changes later.

---

# 65. Reporting Business Rules

Sales reports should be calculated from valid business transactions.

Cancelled orders should be excluded from sales totals.

Pending transactions should be included in:

- Total order value
- Pending amount

but should not be counted as received cash/UPI collection until payment is actually recorded.

---

# 66. Performance Requirements

The system should:

- Load normal pages quickly.
- Avoid unnecessary database queries.
- Use pagination for large tables.
- Optimize images.
- Use indexed database columns for frequent searches.
- Use AJAX where it improves usability.
- Avoid loading thousands of records simultaneously.

---

# 67. Backup Requirements

The database should be backed up regularly.

Recommended:

- Daily database backup
- Weekly full backup
- Manual backup option for Owner

Backup functionality can initially be implemented as a database export rather than a complex cloud backup system.

---

# 68. Future Enhancements

The following features may be considered later:

### Version 2

- Customer management
- Customer purchase history
- WhatsApp notifications
- SMS notifications
- Online orders
- Online UPI/payment gateway
- Delivery management
- Customer loyalty
- Coupon/discount system
- Supplier management
- Expense management
- Profit analysis

### Version 3

- Mobile application
- Multi-branch management
- Cloud deployment
- Advanced forecasting
- Inventory demand prediction
- AI-based sales insights

These are outside the initial scope.

---

# 69. MVP Definition

The first production-ready version should include:

## Authentication

- Owner login
- Staff login
- Role-based access

## Owner

- Dashboard
- Categories
- Products
- Inventory
- Orders
- Custom Cakes
- Pending Payments
- Reports
- Profile
- Settings
- Staff Management

## Staff

- Login
- Dashboard
- New Order
- Multiple products per order
- Cash payment
- UPI payment
- Pending payment
- Current Orders
- Custom Cake Orders

---

# 70. MVP Acceptance Criteria

The MVP will be considered functional when:

### Authentication

- Owner can log in.
- Staff can log in.
- Staff cannot access Owner-only pages.
- Logout works correctly.

### Products

- Owner can create products.
- Owner can edit products.
- Owner can deactivate products.
- Staff can view active products.

### Orders

- Staff can create an order.
- Staff can add one product.
- Staff can add multiple products.
- Quantity calculations are correct.
- Order total is calculated correctly.
- Order receives a unique Order ID.

### Payments

- Cash payment can be recorded.
- UPI payment can be recorded.
- Pending payment can be recorded.
- Partial payment can be recorded.
- Pending payment can later be marked as paid.

### Custom Cakes

- Staff can create custom cake orders.
- Reference images can be uploaded.
- Owner can view custom cake orders.
- Owner can edit custom cake information.
- Custom cake status can be updated.

### Inventory

- Owner can view inventory.
- Stock can be added.
- Stock can be reduced.
- Low-stock items can be identified.

### Reports

- Owner can view sales.
- Owner can view order counts.
- Owner can view payment breakdown.
- Owner can view pending amounts.
- Owner can view product performance.

---

# 71. Success Metrics

The system should improve the shop's operational efficiency.

Potential metrics:

- Reduced order-entry time
- Reduced calculation errors
- Accurate daily sales tracking
- Accurate pending-payment tracking
- Improved inventory visibility
- Faster report generation
- Better visibility into best-selling products

---

# 72. Recommended Technology Stack

## Backend

**Laravel / PHP**

Recommended:

- PHP 8.3+
- Laravel
- Laravel Eloquent ORM
- Laravel Validation
- Laravel Authentication
- Laravel Middleware

## Frontend

- Blade
- HTML5
- CSS3
- Bootstrap 5
- JavaScript
- AJAX / Fetch API

## Database

- MySQL 8

## Charts

- Chart.js

## PDF

- Dompdf

## Export

- CSV
- PhpSpreadsheet

## Development

- VS Code
- Git
- GitHub
- Composer
- Node.js / npm
- XAMPP or Laravel development environment

---

# 73. Deployment

The application should initially support deployment on a standard PHP/MySQL hosting environment.

Possible environments:

### Development

```text
Windows
Laravel
MySQL
XAMPP / Laragon
VS Code
Git
```

### Production

```text
Linux Server
Nginx/Apache
PHP
MySQL
Laravel
SSL
```

The application should not depend on a developer's local machine after deployment.

---

# 74. Final Product Vision

The final system should function as a lightweight **Cake Shop ERP/POS Management System** for physical shop operations.

The primary workflow is:

```text
                    OWNER
                      │
        ┌─────────────┼─────────────┐
        │             │             │
    Products      Inventory      Reports
        │             │             │
        └─────────────┼─────────────┘
                      │
                    SYSTEM
                      │
                    STAFF
                      │
              ┌───────┴────────┐
              │                │
          New Order       Custom Cake
              │                │
       ┌──────┼──────┐         │
       │      │      │         │
     Cash    UPI   Pending     │
       │      │      │         │
       └──────┼──────┘         │
              │                │
              └───────┬────────┘
                      │
                    ORDERS
                      │
                 Owner Dashboard
```

The system should remain focused on the actual cake shop workflow rather than becoming a generic e-commerce platform.

The core principle is:

> **Staff records shop activity quickly; the Owner gets centralized visibility and control over the business.**