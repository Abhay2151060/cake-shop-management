from database import SessionLocal, init_db
from seed_data import seed
from models import User, Category, Product, Order, OrderItem, Payment, CustomCakeOrder, InventoryItem

def run_checks():
    print("--- Starting System Verification ---")
    init_db()
    seed()
    db = SessionLocal()

    # 1. Verify Users
    owner = db.query(User).filter(User.username == "owner").first()
    staff = db.query(User).filter(User.username == "staff").first()
    assert owner is not None, "Owner user missing"
    assert staff is not None, "Staff user missing"
    assert owner.check_password("admin123"), "Owner password check failed"
    assert staff.check_password("staff123"), "Staff password check failed"
    print("[OK] Auth check passed: Owner and Staff accounts verified")

    # 2. Verify Categories and Products
    categories = db.query(Category).all()
    products = db.query(Product).all()
    assert len(categories) >= 6, f"Expected >=6 categories, got {len(categories)}"
    assert len(products) >= 12, f"Expected >=12 products, got {len(products)}"
    print(f"[OK] Menu catalog check passed: {len(categories)} categories, {len(products)} products")

    # 3. Verify Inventory
    inventory = db.query(InventoryItem).all()
    assert len(inventory) >= 10, f"Expected >=10 inventory items, got {len(inventory)}"
    low_stock = [i for i in inventory if i.is_low_stock]
    print(f"[OK] Inventory check passed: {len(inventory)} items, {len(low_stock)} low stock alerts detected")

    # 4. Verify Orders & Math
    orders = db.query(Order).all()
    assert len(orders) >= 4, f"Expected >=4 sample orders, got {len(orders)}"
    for o in orders:
        calculated_subtotal = sum(item.subtotal for item in o.items)
        assert abs(o.subtotal - calculated_subtotal) < 0.01, f"Subtotal mismatch on {o.order_number}"
        calculated_grand = max(0.0, o.subtotal)
        assert abs(o.grand_total - calculated_grand) < 0.01, f"Grand total mismatch on {o.order_number}"
        assert abs(o.pending_amount - max(0.0, o.grand_total - o.paid_amount)) < 0.01, f"Pending mismatch on {o.order_number}"
    print(f"[OK] Order financial integrity check passed across {len(orders)} orders")

    # 5. Verify Custom Cakes
    custom_cakes = db.query(CustomCakeOrder).all()
    assert len(custom_cakes) >= 2, f"Expected >=2 custom cakes, got {len(custom_cakes)}"
    print(f"[OK] Custom cake bookings check passed: {len(custom_cakes)} active bookings")

    db.close()
    print("--- ALL VERIFICATION TESTS PASSED SUCCESSFULLY! ---")

if __name__ == "__main__":
    run_checks()
