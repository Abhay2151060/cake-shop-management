import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Secret key for session signing
SECRET_KEY = os.environ.get("SECRET_KEY", "cherry-blossom-secret-key-2026-super-secure")

# Uploads directory
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CUSTOM_CAKE_UPLOAD_DIR = UPLOAD_DIR / "custom_cakes"
CUSTOM_CAKE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PRODUCT_UPLOAD_DIR = UPLOAD_DIR / "products"
PRODUCT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Database configuration
# Set MYSQL_URL in environment if MySQL is running, otherwise uses SQLite fallback
MYSQL_URL = os.environ.get("MYSQL_URL", "mysql+pymysql://root:@localhost:3306/cherry_blossom")
SQLITE_URL = f"sqlite:///{BASE_DIR / 'cherry_blossom.db'}"

# Shop Default Information
DEFAULT_SHOP_SETTINGS = {
    "shop_name": "Cherry Blossom Cake Shop",
    "shop_tagline": "Freshly Baked with Love & Passion",
    "shop_address": "Shop No. 12, Blossom Avenue, Near City Centre, Pune, MH - 411001",
    "shop_phone": "+91 98765 43210",
    "shop_email": "orders@cherryblossomcakes.com",
    "shop_gstin": "27AAAAA0000A1Z5",
    "currency_symbol": "₹",
    "receipt_footer": "Thank you for choosing Cherry Blossom! Have a sweet day!",
    "theme": "light",
    "low_stock_threshold_default": 5
}
