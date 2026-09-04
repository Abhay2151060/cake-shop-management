import datetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import (
    User, Order, OrderItem, Payment, CustomCakeOrder, InventoryItem, Product
)
from utils.auth_helper import require_login, get_shop_settings
from utils.time_helper import local_today, local_day_bounds_utc
from utils.templating import templates

router = APIRouter(tags=["dashboard"])

@router.get("/", response_class=HTMLResponse)
def root_redirect(request: Request, db: Session = Depends(get_db)):
    return RedirectResponse(url="/dashboard")

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    settings = get_shop_settings(db)
    today = local_today()
    today_start, today_end = local_day_bounds_utc(today)

    # 1. Today's metrics (excluding cancelled orders)
    today_orders_query = db.query(Order).filter(
        Order.created_at >= today_start,
        Order.created_at <= today_end,
        Order.order_status != "cancelled"
    )
    today_orders_count = today_orders_query.count()
    today_sales_total = today_orders_query.with_entities(func.sum(Order.grand_total)).scalar() or 0.0

    # Today's Cash & UPI collections from payments table
    today_cash_coll = db.query(func.sum(Payment.amount)).join(Order).filter(
        Payment.payment_date >= today_start,
        Payment.payment_date <= today_end,
        Payment.payment_method == "cash",
        Order.order_status != "cancelled"
    ).scalar() or 0.0

    today_upi_coll = db.query(func.sum(Payment.amount)).join(Order).filter(
        Payment.payment_date >= today_start,
        Payment.payment_date <= today_end,
        Payment.payment_method == "upi",
        Order.order_status != "cancelled"
    ).scalar() or 0.0

    # Total pending/credit amount across all active orders
    total_pending_amount = db.query(func.sum(Order.pending_amount)).filter(
        Order.payment_status.in_(["pending", "partially_paid"]),
        Order.order_status != "cancelled"
    ).scalar() or 0.0


    # Active Custom Cake Orders
    custom_cake_count = db.query(CustomCakeOrder).filter(
        CustomCakeOrder.order_status.in_(["new", "confirmed", "preparing", "ready"])
    ).count()

    # Low Stock Items count (inventory + products)
    low_stock_inv = db.query(InventoryItem).filter(
        InventoryItem.status == "active",
        InventoryItem.current_qty <= InventoryItem.min_qty
    ).all()
    low_stock_prod = db.query(Product).filter(
        Product.status == "active",
        Product.stock_qty <= Product.min_stock_level
    ).all()
    total_low_stock_count = len(low_stock_inv) + len(low_stock_prod)

    # Recent activity feeds
    recent_orders = db.query(Order).order_by(Order.created_at.desc()).limit(6).all()
    upcoming_custom_cakes = db.query(CustomCakeOrder).filter(
        CustomCakeOrder.order_status.in_(["new", "confirmed", "preparing", "ready"])
    ).order_by(CustomCakeOrder.required_date.asc()).limit(5).all()

    kpis = {
        "today_orders": today_orders_count,
        "today_sales": round(today_sales_total, 2),
        "cash_collection": round(today_cash_coll, 2),
        "upi_collection": round(today_upi_coll, 2),
        "pending_amount": round(total_pending_amount, 2),
        "custom_cake_orders": custom_cake_count,
        "low_stock_count": total_low_stock_count
    }

    if user.role == "owner":
        return templates.TemplateResponse(request=request, name="dashboard/owner.html", context={
            "request": request,
            "user": user,
            "settings": settings,
            "kpis": kpis,
            "recent_orders": recent_orders,
            "upcoming_custom_cakes": upcoming_custom_cakes,
            "low_stock_inv": low_stock_inv,
            "low_stock_prod": low_stock_prod
        })
    else:
        # Staff Dashboard
        return templates.TemplateResponse(request=request, name="dashboard/staff.html", context={
            "request": request,
            "user": user,
            "settings": settings,
            "kpis": kpis,
            "recent_orders": recent_orders,
            "upcoming_custom_cakes": upcoming_custom_cakes
        })

@router.get("/api/analytics/charts")
def analytics_charts_data(user: User = Depends(require_login), db: Session = Depends(get_db)):
    # 7-day sales trend
    today = local_today()
    sales_labels = []
    sales_values = []
    order_counts = []

    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_start, day_end = local_day_bounds_utc(day)

        day_total = db.query(func.sum(Order.grand_total)).filter(
            Order.created_at >= day_start,
            Order.created_at <= day_end,
            Order.order_status != "cancelled"
        ).scalar() or 0.0

        day_orders = db.query(Order).filter(
            Order.created_at >= day_start,
            Order.created_at <= day_end,
            Order.order_status != "cancelled"
        ).count()

        sales_labels.append(day.strftime("%a (%d %b)"))
        sales_values.append(round(day_total, 2))
        order_counts.append(day_orders)

    # Payment split across all completed/active orders
    total_cash = db.query(func.sum(Payment.amount)).join(Order).filter(
        Payment.payment_method == "cash",
        Order.order_status != "cancelled"
    ).scalar() or 0.0

    total_upi = db.query(func.sum(Payment.amount)).join(Order).filter(
        Payment.payment_method == "upi",
        Order.order_status != "cancelled"
    ).scalar() or 0.0

    total_pending = db.query(func.sum(Order.pending_amount)).filter(
        Order.payment_status.in_(["pending", "partially_paid"]),
        Order.order_status != "cancelled"
    ).scalar() or 0.0

    # Top 5 Best Selling Products
    top_products_query = db.query(
        OrderItem.product_name,
        func.sum(OrderItem.quantity).label("total_qty"),
        func.sum(OrderItem.subtotal).label("total_revenue")
    ).join(Order).filter(
        Order.order_status != "cancelled"
    ).group_by(OrderItem.product_name).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()

    top_prod_labels = [row[0] for row in top_products_query]
    top_prod_qty = [row[1] for row in top_products_query]
    top_prod_revenue = [round(row[2], 2) for row in top_products_query]

    return JSONResponse({
        "sales_trend": {
            "labels": sales_labels,
            "sales": sales_values,
            "orders": order_counts
        },
        "payment_split": {
            "labels": ["Cash Received", "UPI Received", "Pending (Credit/Udhaar)"],
            "values": [round(total_cash, 2), round(total_upi, 2), round(total_pending, 2)]
        },
        "top_products": {
            "labels": top_prod_labels,
            "quantities": top_prod_qty,
            "revenue": top_prod_revenue
        }
    })
