import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from config import SECRET_KEY, BASE_DIR
from database import init_db
from seed_data import seed

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB and seed demo data if needed
    init_db()
    try:
        from database import SessionLocal
        from models import User
        db = SessionLocal()
        if db.query(User).count() == 0:
            seed()
        db.close()
    except Exception as e:
        print(f"Startup check: {e}")
    yield
    # Shutdown logic if any

app = FastAPI(
    title="Cherry Blossom Cake Shop Management System",
    description="Local Cake Shop ERP & Point-of-Sale System",
    version="1.0.0",
    lifespan=lifespan
)

# Enable signed session cookies
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="cherry_session",
    max_age=86400 * 7  # 7 days
)

# Ensure static directories exist
static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "css").mkdir(parents=True, exist_ok=True)
(static_dir / "js").mkdir(parents=True, exist_ok=True)
(static_dir / "uploads").mkdir(parents=True, exist_ok=True)
(static_dir / "uploads" / "custom_cakes").mkdir(parents=True, exist_ok=True)
(static_dir / "uploads" / "products").mkdir(parents=True, exist_ok=True)

# Copy workspace logo.png to static/ if not present
workspace_logo = BASE_DIR / "logo.png"
static_logo = static_dir / "logo.png"
if workspace_logo.exists() and not static_logo.exists():
    import shutil
    shutil.copy(workspace_logo, static_logo)

# Mount static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory="templates")

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
