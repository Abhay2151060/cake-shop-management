import os
import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import (
    User, Category, Product, Order, OrderItem, Payment,
    CustomCakeOrder, InventoryItem, InventoryTransaction, Setting, AuditLog
)
from config import DEFAULT_SHOP_SETTINGS

def seed():
    init_db()
    db: Session = SessionLocal()

    try:
        # 1. Seed Shop Settings
        for key, val in DEFAULT_SHOP_SETTINGS.items():
            existing = db.query(Setting).filter(Setting.key == key).first()
            if not existing:
                db.add(Setting(key=key, value=str(val)))
        db.commit()

        # 2. Seed Default Users
        owner = db.query(User).filter(User.username == "owner").first()
        if not owner:
            owner = User(
                name="Aarav Sharma",
                username="owner",
                email="owner@cherryblossom.com",
                role="owner",
                phone="+91 98765 00001",
                status="active"
            )
            owner.set_password("admin123")
            db.add(owner)

        staff = db.query(User).filter(User.username == "staff").first()
        if not staff:
            staff = User(
                name="Priya Patel",
                username="staff",
                email="staff@cherryblossom.com",
                role="staff",
                phone="+91 98765 00002",
                status="active"
            )
            staff.set_password("staff123")
            db.add(staff)

        db.commit()
        owner = db.query(User).filter(User.username == "owner").first()
        staff = db.query(User).filter(User.username == "staff").first()

        # 3. Seed Categories
        categories_data = [
            ("Birthday Cakes", "Delicious handcrafted cakes for memorable birthday moments."),
            ("Anniversary Cakes", "Romantic & elegant themed cakes for special milestone celebrations."),
            ("Chocolate Special", "Decadent Dutch chocolate, truffles, and rich cocoa creations."),
            ("Pastries & Desserts", "Single-portion pastries, cupcakes, mousse cups, and tarts."),
            ("Eggless & Vegan", "100% vegetarian egg-free cakes with irresistible soft sponge."),
            ("Fruit & Floral", "Fresh fruit toppings, strawberry delights, and exotic berry cakes.")
        ]

        cat_map = {}
        for cat_name, cat_desc in categories_data:
            cat = db.query(Category).filter(Category.name == cat_name).first()
            if not cat:
                cat = Category(name=cat_name, description=cat_desc, status="active")
                db.add(cat)
                db.flush()
            cat_map[cat_name] = cat.id
        db.commit()

        # 4. Seed Products
        products_data = [
            ("Belgian Dark Chocolate Truffle", "Chocolate Special", "CB-TRUF-01", "Rich dark chocolate ganache with moist sponge", "1 KG", 850.0, 450.0, 12, 4),
            ("Dutch Chocolate Bliss", "Chocolate Special", "CB-DUTCH-02", "Layered Dutch cocoa with choco curls", "500g", 480.0, 240.0, 15, 5),
            ("Classic Black Forest", "Birthday Cakes", "CB-BF-01", "Whipped cream, cherries, and shaved dark chocolate", "1 KG", 750.0, 380.0, 8, 3),
            ("Golden Butterscotch Delight", "Birthday Cakes", "CB-BS-01", "Crunchy butterscotch praline with vanilla sponge", "1 KG", 700.0, 350.0, 10, 4),
            ("Royal Red Velvet with Cream Cheese", "Anniversary Cakes", "CB-RV-01", "Velvety red sponge with silky cream cheese frosting", "1 KG", 950.0, 520.0, 6, 3),
            ("Heart-shaped Strawberry Rose", "Anniversary Cakes", "CB-STR-01", "Fresh strawberry compote layered in heart shape", "1.5 KG", 1200.0, 600.0, 4, 2),
            ("Pineapple Cream Pastry", "Pastries & Desserts", "CB-PAS-PIN", "Juicy tropical pineapple slice pastry", "Piece", 80.0, 35.0, 25, 10),
            ("Choco Lava Cupcake", "Pastries & Desserts", "CB-PAS-LAV", "Warm gooey molten chocolate lava center", "Piece", 95.0, 40.0, 20, 8),
            ("Eggless Mango Mango Surprise", "Eggless & Vegan", "CB-EGG-MNG", "Alphonso mango pulp infused eggless sponge", "1 KG", 800.0, 400.0, 7, 3),
            ("Eggless Blueberry Cheesecake", "Eggless & Vegan", "CB-EGG-BLU", "Rich creamy baked eggless cheesecake", "1 KG", 1100.0, 580.0, 5, 2),
            ("Fresh Exotic Mixed Fruit Cake", "Fruit & Floral", "CB-FRT-01", "Loaded with kiwi, dragonfruit, grapes & apples", "1 KG", 900.0, 460.0, 6, 3),
            ("Cherry Blossom Signature Cake", "Fruit & Floral", "CB-SIG-01", "Shop specialty: Sakura floral cream with cherry jam", "1 KG", 990.0, 480.0, 9, 3)
        ]

        prod_map = {}
        for name, cat_name, sku, desc, size, sell_p, cost_p, stock, min_s in products_data:
            prod = db.query(Product).filter(Product.sku == sku).first()
            if not prod:
                prod = Product(
                    category_id=cat_map[cat_name],
                    name=name,
                    sku=sku,
                    description=desc,
                    size_weight=size,
                    selling_price=sell_p,
                    cost_price=cost_p,
                    stock_qty=stock,
                    min_stock_level=min_s,
                    status="active"
                )
                db.add(prod)
                db.flush()
            prod_map[name] = prod
        db.commit()

        # 5. Seed Inventory Items
        inventory_data = [
            ("Whipped Dairy Cream", "raw_material", "Litre", 24.0, 8.0, 180.0, "Amul Dairy Supplies"),
            ("Dark Chocolate Compound (55%)", "raw_material", "KG", 18.5, 6.0, 280.0, "Morde Confectionery"),
            ("Refined Cake Flour", "raw_material", "KG", 50.0, 15.0, 45.0, "Metro Wholesale"),
            ("Caster Sugar", "raw_material", "KG", 40.0, 10.0, 48.0, "Metro Wholesale"),
            ("Madagascar Vanilla Extract", "raw_material", "Litre", 3.0, 1.0, 1200.0, "Sprig Flavours"),
            ("Fresh Red Cherries", "raw_material", "KG", 4.0, 5.0, 320.0, "City Market Vendors"),  # Low stock
            ("1 KG Premium Cake Box", "packaging", "Piece", 85.0, 20.0, 18.0, "Shree Packaging"),
            ("500g Cake Box", "packaging", "Piece", 60.0, 15.0, 14.0, "Shree Packaging"),
            ("Birthday Sparkler Candles (Pack of 6)", "accessory", "Packet", 45.0, 10.0, 25.0, "Party Planet"),
            ("Golden Number Candles (0-9)", "accessory", "Box", 8.0, 10.0, 35.0, "Party Planet")  # Low stock
        ]

        for name, itype, unit, cqty, mqty, price, supp in inventory_data:
            inv = db.query(InventoryItem).filter(InventoryItem.name == name).first()
            if not inv:
                inv = InventoryItem(
                    name=name,
                    item_type=itype,
                    unit=unit,
                    current_qty=cqty,
                    min_qty=mqty,
                    purchase_price=price,
                    supplier=supp,
                    status="active"
                )
                db.add(inv)
                db.flush()
                # Record initial transaction
                db.add(InventoryTransaction(
                    inventory_item_id=inv.id,
                    user_id=owner.id,
                    transaction_type="stock_in",
                    quantity=cqty,
                    prev_qty=0.0,
                    new_qty=cqty,
                    reason="Initial stock setup"
                ))
        db.commit()

        # 6. Seed Sample Orders
        today = datetime.date.today()
        sample_orders = [
            {
                "order_number": "ORD-000101",
                "customer_name": "Rohan Gupta",
                "customer_phone": "+91 98234 11223",
                "items": [
                    ("Belgian Dark Chocolate Truffle", 1, 850.0),
                    ("Choco Lava Cupcake", 2, 95.0)
                ],
                "discount": 0.0,
                "payment_method": "upi",
                "paid_amount": 1040.0,
                "payment_status": "paid",
                "order_status": "completed",
                "notes": "Fast walk-in customer"
            },
            {
                "order_number": "ORD-000102",
                "customer_name": "Ananya Sharma",
                "customer_phone": "+91 98345 22334",
                "items": [
                    ("Classic Black Forest", 1, 750.0),
                    ("Pineapple Cream Pastry", 3, 80.0)
                ],
                "discount": 0.0,
                "payment_method": "cash",
                "paid_amount": 990.0,
                "payment_status": "paid",
                "order_status": "completed",
                "notes": "Paid via exact cash"
            },
            {
                "order_number": "ORD-000103",
                "customer_name": "Vikram Desai (Local Regular)",
                "customer_phone": "+91 98456 33445",
                "items": [
                    ("Royal Red Velvet with Cream Cheese", 1, 950.0),
                    ("Golden Butterscotch Delight", 1, 700.0)
                ],
                "discount": 0.0,
                "payment_method": "pending",
                "paid_amount": 600.0,
                "payment_status": "partially_paid",
                "order_status": "completed",
                "notes": "Paid ₹600 cash advance, balance ₹1050 promised tomorrow (Udhaar account)"
            },
            {
                "order_number": "ORD-000104",
                "customer_name": "Kavita Verma",
                "customer_phone": "+91 98567 44556",
                "items": [
                    ("Fresh Exotic Mixed Fruit Cake", 1, 900.0)
                ],
                "discount": 0.0,
                "payment_method": "pending",
                "paid_amount": 0.0,
                "payment_status": "pending",
                "order_status": "preparing",
                "notes": "Office bulk delivery order; payment on delivery invoice"
            }
        ]

        for s_ord in sample_orders:
            existing = db.query(Order).filter(Order.order_number == s_ord["order_number"]).first()
            subtotal = sum(q * p for _, q, p in s_ord["items"])
            grand_total = subtotal
            pending_amount = max(0.0, grand_total - s_ord["paid_amount"])

            if not existing:
                order = Order(
                    order_number=s_ord["order_number"],
                    user_id=staff.id,
                    customer_name=s_ord["customer_name"],
                    customer_phone=s_ord["customer_phone"],
                    subtotal=subtotal,
                    discount=0.0,
                    grand_total=grand_total,
                    paid_amount=s_ord["paid_amount"],
                    pending_amount=pending_amount,
                    payment_status=s_ord["payment_status"],
                    payment_method=s_ord["payment_method"],
                    order_status=s_ord["order_status"],
                    notes=s_ord["notes"],
                    created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=2)
                )
                db.add(order)
                db.flush()

                for p_name, qty, price in s_ord["items"]:
                    p_obj = prod_map.get(p_name)
                    p_id = p_obj.id if p_obj else None
                    db.add(OrderItem(
                        order_id=order.id,
                        product_id=p_id,
                        product_name=p_name,
                        size_weight=p_obj.size_weight if p_obj else "1 KG",
                        unit_price=price,
                        quantity=qty,
                        subtotal=qty * price
                    ))

                if s_ord["paid_amount"] > 0:
                    db.add(Payment(
                        order_id=order.id,
                        user_id=staff.id,
                        amount=s_ord["paid_amount"],
                        payment_method="cash" if s_ord["payment_method"] == "cash" else "upi",
                        notes="Initial order payment"
                    ))
            else:
                existing.discount = 0.0
                existing.grand_total = existing.subtotal
                existing.pending_amount = max(0.0, existing.grand_total - existing.paid_amount)
                db.flush()
        db.commit()

        # 7. Seed Custom Cake Orders
        custom_cakes = [
            {
                "custom_order_number": "CC-000101",
                "customer_name": "Meera Joshi",
                "customer_phone": "+91 98111 22334",
                "flavor": "Chocolate Hazelnut Truffle",
                "weight": "2 KG",
                "shape": "Multi-tier Round",
                "theme_design": "Princess Unicorn Pastel Pink & Gold",
                "cake_message": "Happy 5th Birthday Anaya!",
                "required_date": (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
                "required_time": "17:30",
                "instructions": "Add edible fondant unicorn horn, minimal food coloring, extra glitter sprinkles",
                "estimated_price": 2400.0,
                "advance_paid": 1000.0,
                "payment_method": "upi",
                "payment_status": "partially_paid",
                "order_status": "confirmed"
            },
            {
                "custom_order_number": "CC-000102",
                "customer_name": "Karan Singhania",
                "customer_phone": "+91 98222 33445",
                "flavor": "Pure Belgian Dark Chocolate",
                "weight": "3 KG",
                "shape": "Square 2-Tier",
                "theme_design": "25th Silver Jubilee Anniversary Floral Cascade",
                "cake_message": "Celebrating 25 Sweet Years - Rita & Karan",
                "required_date": (today + datetime.timedelta(days=4)).strftime("%Y-%m-%d"),
                "required_time": "19:00",
                "instructions": "Silver leaf accents, sugar cherry blossoms draping from top to base",
                "estimated_price": 3800.0,
                "advance_paid": 2000.0,
                "payment_method": "cash",
                "payment_status": "partially_paid",
                "order_status": "preparing"
            }
        ]

        for cc in custom_cakes:
            existing = db.query(CustomCakeOrder).filter(CustomCakeOrder.custom_order_number == cc["custom_order_number"]).first()
            if not existing:
                pending = max(0.0, cc["estimated_price"] - cc["advance_paid"])
                db.add(CustomCakeOrder(
                    custom_order_number=cc["custom_order_number"],
                    user_id=staff.id,
                    customer_name=cc["customer_name"],
                    customer_phone=cc["customer_phone"],
                    flavor=cc["flavor"],
                    weight=cc["weight"],
                    shape=cc["shape"],
                    theme_design=cc["theme_design"],
                    cake_message=cc["cake_message"],
                    required_date=cc["required_date"],
                    required_time=cc["required_time"],
                    special_instructions=cc["instructions"],
                    estimated_price=cc["estimated_price"],
                    advance_paid=cc["advance_paid"],
                    pending_amount=pending,
                    payment_status=cc["payment_status"],
                    payment_method=cc["payment_method"],
                    order_status=cc["order_status"]
                ))
        db.commit()

        # 8. Seed Audit Log entries
        db.add(AuditLog(
            user_id=owner.id,
            user_name=owner.name,
            role="owner",
            action="System Initialized",
            module="System",
            details="Initial database seeding and shop configuration completed.",
            ip_address="127.0.0.1"
        ))
        db.commit()

        print("Database seeding completed successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
