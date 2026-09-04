import logging
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from config import SECRET_KEY, SESSION_HTTPS_ONLY, BASE_DIR
from database import init_db
from seed_data import seed
from utils.security import CSRFMiddleware, SecurityHeadersMiddleware

# Import modular routers
from routes.auth import router as auth_router
from routes.dashboard import router as dashboard_router
from routes.orders import router as orders_router
from routes.payments import router as payments_router
from routes.custom_cakes import router as custom_cakes_router
from routes.products import router as products_router
from routes.categories import router as categories_router
from routes.inventory import router as inventory_router
from routes.reports import router as reports_router
from routes.settings import router as settings_router
from routes.staff import router as staff_router
from routes.audit import router as audit_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB and seed demo data if needed
    init_db()
    try:
        from database import SessionLocal
        from models import User
        db = SessionLocal()
        try:
            if db.query(User).count() == 0:
                seed()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Startup check: {e}")
    yield
    # Shutdown logic if any

app = FastAPI(
    title="Cherry Blossom Cake Shop Management System",
    description="Local Cake Shop ERP & Point-of-Sale System",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware runs bottom-up: SessionMiddleware must be added last so that the
# session is already populated when CSRFMiddleware inspects it.
app.add_middleware(SecurityHeadersMiddleware, https_only=SESSION_HTTPS_ONLY)
app.add_middleware(CSRFMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="cherry_session",
    max_age=86400 * 7,   # 7 days
    same_site="lax",     # blocks the cookie on cross-site POSTs
    https_only=SESSION_HTTPS_ONLY
)

# Ensure static directories exist
static_dir = BASE_DIR / "static"
for sub in ("css", "js", "uploads", "uploads/custom_cakes", "uploads/products"):
    (static_dir / sub).mkdir(parents=True, exist_ok=True)

# Copy workspace logo.png to static/ if not present
workspace_logo = BASE_DIR / "logo.png"
static_logo = static_dir / "logo.png"
if workspace_logo.exists() and not static_logo.exists():
    shutil.copy(workspace_logo, static_logo)

# Mount static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Register routers
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(custom_cakes_router)
app.include_router(products_router)
app.include_router(categories_router)
app.include_router(inventory_router)
app.include_router(reports_router)
app.include_router(settings_router)
app.include_router(staff_router)
app.include_router(audit_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
