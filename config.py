import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_secret_key() -> str:
    """
    Resolve the session signing key without ever hardcoding it in source control.

    Order of precedence:
      1. SECRET_KEY environment variable (preferred for real deployments).
      2. A locally generated key persisted in `.secret_key` (git-ignored), so that
         a plain `python app.py` still works and sessions survive restarts.
    """
    env_key = os.environ.get("SECRET_KEY", "").strip()
    if env_key:
        return env_key

    key_file = BASE_DIR / ".secret_key"
    if key_file.exists():
        stored = key_file.read_text(encoding="utf-8").strip()
        if stored:
            return stored

    generated = secrets.token_urlsafe(48)
    key_file.write_text(generated, encoding="utf-8")
    try:
        os.chmod(key_file, 0o600)
    except OSError:
        # Best effort: not all platforms/filesystems support POSIX modes.
        pass
    return generated


SECRET_KEY = _load_secret_key()

# Set SESSION_HTTPS_ONLY=1 when the app is served over HTTPS so the session
# cookie is only ever transmitted on secure connections.
SESSION_HTTPS_ONLY = os.environ.get("SESSION_HTTPS_ONLY", "").strip().lower() in ("1", "true", "yes")

# Local timezone used for "today"/date-range business logic. Timestamps are
# stored in UTC; see utils/time_helper.py.
LOCAL_TIMEZONE = os.environ.get("LOCAL_TIMEZONE", "Asia/Kolkata")

# Uploads directory
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CUSTOM_CAKE_UPLOAD_DIR = UPLOAD_DIR / "custom_cakes"
CUSTOM_CAKE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PRODUCT_UPLOAD_DIR = UPLOAD_DIR / "products"
PRODUCT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Maximum accepted image upload size (bytes).
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# Database configuration.
# MySQL is used only when DATABASE_URL / MYSQL_URL is explicitly provided;
# no credentials are ever embedded in source. Otherwise the app uses SQLite.
MYSQL_URL = os.environ.get("DATABASE_URL", os.environ.get("MYSQL_URL", "")).strip()
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
