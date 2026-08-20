import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, Enum
)
from sqlalchemy.orm import relationship
from database import Base
from werkzeug.security import generate_password_hash, check_password_hash

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="staff", nullable=False)  # 'owner', 'staff'
    phone = Column(String(20), nullable=True)
    status = Column(String(20), default="active", nullable=False)  # 'active', 'inactive'
    avatar_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    orders = relationship("Order", back_populates="creator")
    custom_orders = relationship("CustomCakeOrder", back_populates="creator")
    audit_logs = relationship("AuditLog", back_populates="user")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="active", nullable=False)  # 'active', 'inactive'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    name = Column(String(150), nullable=False, index=True)
    sku = Column(String(50), unique=True, index=True, nullable=True)
    description = Column(Text, nullable=True)
    size_weight = Column(String(50), default="1 KG")  # e.g., '500g', '1 KG', '2 KG', 'Piece'
    selling_price = Column(Float, nullable=False, default=0.0)
    cost_price = Column(Float, nullable=False, default=0.0)
    stock_qty = Column(Integer, default=0)
    min_stock_level = Column(Integer, default=5)
    image_path = Column(String(255), nullable=True)
    status = Column(String(20), default="active", nullable=False)  # 'active', 'inactive'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")

    @property
    def is_low_stock(self) -> bool:
        return self.stock_qty <= self.min_stock_level


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)  # e.g., ORD-000101
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_name = Column(String(100), default="Walk-in Customer")
    customer_phone = Column(String(20), nullable=True)
    subtotal = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    grand_total = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    pending_amount = Column(Float, default=0.0)
    payment_status = Column(String(30), default="paid")  # 'paid', 'partially_paid', 'pending'
    payment_method = Column(String(30), default="cash")  # 'cash', 'upi', 'pending'
    order_status = Column(String(30), default="completed")  # 'new', 'confirmed', 'preparing', 'ready', 'completed', 'cancelled'
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    creator = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name = Column(String(150), nullable=False)
    size_weight = Column(String(50), nullable=True)
    unit_price = Column(Float, nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    subtotal = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(30), default="cash")  # 'cash', 'upi'
    payment_date = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(String(255), nullable=True)

    order = relationship("Order", back_populates="payments")
    collector = relationship("User")


class CustomCakeOrder(Base):
    __tablename__ = "custom_cake_orders"

    id = Column(Integer, primary_key=True, index=True)
    custom_order_number = Column(String(50), unique=True, index=True, nullable=False)  # e.g., CC-000101
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_name = Column(String(100), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    flavor = Column(String(100), nullable=False)
    weight = Column(String(50), default="1 KG")
    shape = Column(String(50), default="Round")  # Round, Square, Heart, Multi-tier, Custom
    theme_design = Column(String(150), nullable=True)
    cake_message = Column(String(255), nullable=True)
    required_date = Column(String(30), nullable=False)  # YYYY-MM-DD
    required_time = Column(String(30), nullable=True)   # HH:MM
    special_instructions = Column(Text, nullable=True)
    reference_image = Column(String(255), nullable=True)
    estimated_price = Column(Float, default=0.0)
    advance_paid = Column(Float, default=0.0)
    pending_amount = Column(Float, default=0.0)
    payment_status = Column(String(30), default="pending")  # 'paid', 'partially_paid', 'pending'
    payment_method = Column(String(30), default="cash")
    order_status = Column(String(30), default="new")  # 'new', 'confirmed', 'preparing', 'ready', 'completed', 'cancelled'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    creator = relationship("User", back_populates="custom_orders")


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), unique=True, nullable=False)
    item_type = Column(String(50), default="raw_material")  # 'finished_cake', 'raw_material', 'packaging', 'accessory'
    unit = Column(String(30), default="KG")  # 'KG', 'Gram', 'Litre', 'Piece', 'Box', 'Packet'
    current_qty = Column(Float, default=0.0)
    min_qty = Column(Float, default=5.0)
    purchase_price = Column(Float, default=0.0)
    supplier = Column(String(100), nullable=True)
    expiry_date = Column(String(30), nullable=True)
    status = Column(String(20), default="active")  # 'active', 'inactive'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    transactions = relationship("InventoryTransaction", back_populates="item", cascade="all, delete-orphan")

    @property
    def is_low_stock(self) -> bool:
        return self.current_qty <= self.min_qty


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transaction_type = Column(String(30), nullable=False)  # 'stock_in', 'stock_out', 'adjustment'
    quantity = Column(Float, nullable=False)
    prev_qty = Column(Float, nullable=False)
    new_qty = Column(Float, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    item = relationship("InventoryItem", back_populates="transactions")
    actor = relationship("User")


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_name = Column(String(100), nullable=True)
    role = Column(String(30), nullable=True)
    action = Column(String(100), nullable=False)
    module = Column(String(50), nullable=False)
    record_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")
