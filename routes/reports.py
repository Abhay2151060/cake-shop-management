import io
import datetime
import pandas as pd
from fastapi import APIRouter, Request, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import User, Order, OrderItem, Payment, Product, InventoryItem
from utils.auth_helper import require_owner, get_shop_settings
from utils.templating import templates

router = APIRouter(prefix="/reports", tags=["reports"])

def parse_date_range(period: str, start_date_str: str, end_date_str: str):
    now = datetime.datetime.now()
    today = datetime.date.today()

    if period == "today":
        start = datetime.datetime(today.year, today.month, today.day, 0, 0, 0)
        end = datetime.datetime(today.year, today.month, today.day, 23, 59, 59)
    elif period == "yesterday":
        y = today - datetime.timedelta(days=1)
        start = datetime.datetime(y.year, y.month, y.day, 0, 0, 0)
        end = datetime.datetime(y.year, y.month, y.day, 23, 59, 59)
    elif period == "week":
        start_day = today - datetime.timedelta(days=today.weekday())
        start = datetime.datetime(start_day.year, start_day.month, start_day.day, 0, 0, 0)
        end = datetime.datetime(today.year, today.month, today.day, 23, 59, 59)
    elif period == "month":
        start = datetime.datetime(today.year, today.month, 1, 0, 0, 0)
        end = datetime.datetime(today.year, today.month, today.day, 23, 59, 59)
    elif period == "custom" and start_date_str and end_date_str:
        s_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        e_dt = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
        start = datetime.datetime(s_dt.year, s_dt.month, s_dt.day, 0, 0, 0)
        end = datetime.datetime(e_dt.year, e_dt.month, e_dt.day, 23, 59, 59)
    else:
        # Default to this month
        start = datetime.datetime(today.year, today.month, 1, 0, 0, 0)
        end = datetime.datetime(today.year, today.month, today.day, 23, 59, 59)
        period = "month"

    return start, end, period

@router.get("", response_class=HTMLResponse)
def reports_index(
    request: Request,
    tab: str = "sales",
    period: str = "month",
    start_date: str = "",
    end_date: str = "",
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    settings = get_shop_settings(db)
    start_dt, end_dt, period = parse_date_range(period, start_date, end_date)

    # 1. Sales Report Data
    orders_query = db.query(Order).filter(
        Order.created_at >= start_dt,
        Order.created_at <= end_dt,
        Order.order_status != "cancelled"
    ).order_by(Order.created_at.desc())
    orders = orders_query.all()

    total_orders_count = len(orders)
    total_gross_sales = sum(o.subtotal for o in orders)
    total_net_sales = sum(o.grand_total for o in orders)
    total_received_amount = sum(o.paid_amount for o in orders)
    total_pending_amount = sum(o.pending_amount for o in orders)

    # Cash vs UPI collections in period
    cash_collected = db.query(func.sum(Payment.amount)).join(Order).filter(
        Payment.payment_date >= start_dt,
        Payment.payment_date <= end_dt,
        Payment.payment_method == "cash",
        Order.order_status != "cancelled"
    ).scalar() or 0.0

    upi_collected = db.query(func.sum(Payment.amount)).join(Order).filter(
        Payment.payment_date >= start_dt,
        Payment.payment_date <= end_dt,
        Payment.payment_method == "upi",
        Order.order_status != "cancelled"
    ).scalar() or 0.0

    # 2. Product Performance
    product_stats = db.query(
        OrderItem.product_name,
        func.sum(OrderItem.quantity).label("total_qty"),
        func.sum(OrderItem.subtotal).label("total_revenue")
    ).join(Order).filter(
        Order.created_at >= start_dt,
        Order.created_at <= end_dt,
        Order.order_status != "cancelled"
    ).group_by(OrderItem.product_name).order_by(func.sum(OrderItem.subtotal).desc()).all()

    # 3. Inventory Status
    inventory_items = db.query(InventoryItem).order_by(InventoryItem.name.asc()).all()

    # 4. Pending Payments
    pending_orders = db.query(Order).filter(
        Order.payment_status.in_(["pending", "partially_paid"]),
        Order.order_status != "cancelled"
    ).order_by(Order.created_at.desc()).all()

    summary = {
        "total_orders": total_orders_count,
        "gross_sales": round(total_gross_sales, 2),
        "discounts": 0.0,
        "net_sales": round(total_net_sales, 2),
        "received": round(total_received_amount, 2),
        "pending": round(total_pending_amount, 2),
        "cash_collected": round(cash_collected, 2),
        "upi_collected": round(upi_collected, 2),
        "start_formatted": start_dt.strftime("%d %b %Y"),
        "end_formatted": end_dt.strftime("%d %b %Y")
    }

    return templates.TemplateResponse(request=request, name="reports/index.html", context={
        "request": request,
        "user": user,
        "settings": settings,
        "tab": tab,
        "period": period,
        "start_date": start_date or start_dt.strftime("%Y-%m-%d"),
        "end_date": end_date or end_dt.strftime("%Y-%m-%d"),
        "summary": summary,
        "orders": orders,
        "product_stats": product_stats,
        "inventory_items": inventory_items,
        "pending_orders": pending_orders
    })

@router.get("/export/csv")
def export_csv(
    report_type: str = "sales",
    period: str = "month",
    start_date: str = "",
    end_date: str = "",
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    start_dt, end_dt, period = parse_date_range(period, start_date, end_date)

    if report_type == "sales":
        orders = db.query(Order).filter(
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.order_status != "cancelled"
        ).order_by(Order.created_at.desc()).all()

        data = [{
            "Order ID": o.order_number,
            "Date": o.created_at.strftime("%Y-%m-%d %H:%M"),
            "Customer Name": o.customer_name,
            "Customer Phone": o.customer_phone or "",
            "Subtotal (₹)": o.subtotal,
            "Grand Total (₹)": o.grand_total,
            "Paid Amount (₹)": o.paid_amount,
            "Pending Amount (₹)": o.pending_amount,
            "Payment Status": o.payment_status.title(),
            "Payment Method": o.payment_method.upper(),
            "Order Status": o.order_status.title()
        } for o in orders]
        df = pd.DataFrame(data)

    elif report_type == "products":
        product_stats = db.query(
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("qty"),
            func.sum(OrderItem.subtotal).label("revenue")
        ).join(Order).filter(
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.order_status != "cancelled"
        ).group_by(OrderItem.product_name).order_by(func.sum(OrderItem.subtotal).desc()).all()

        data = [{
            "Product Name": row[0],
            "Quantity Sold": row[1],
            "Total Revenue (₹)": round(row[2], 2)
        } for row in product_stats]
        df = pd.DataFrame(data)

    elif report_type == "inventory":
        inv = db.query(InventoryItem).all()
        data = [{
            "Item Name": i.name,
            "Type": i.item_type.replace("_", " ").title(),
            "Current Stock": i.current_qty,
            "Min Stock Alert": i.min_qty,
            "Unit": i.unit,
            "Purchase Price (₹)": i.purchase_price,
            "Supplier": i.supplier or "",
            "Status": "Low Stock" if i.is_low_stock else "Adequate"
        } for i in inv]
        df = pd.DataFrame(data)

    else:
        raise HTTPException(status_code=400, detail="Invalid report type.")

    stream = io.StringIO()
    df.to_csv(stream, index=False)
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=cherry_blossom_{report_type}_report_{datetime.date.today()}.csv"
    return response

@router.get("/export/excel")
def export_excel(
    report_type: str = "sales",
    period: str = "month",
    start_date: str = "",
    end_date: str = "",
    user: User = Depends(require_owner),
    db: Session = Depends(get_db)
):
    start_dt, end_dt, period = parse_date_range(period, start_date, end_date)

    if report_type == "sales":
        orders = db.query(Order).filter(
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.order_status != "cancelled"
        ).order_by(Order.created_at.desc()).all()

        data = [{
            "Order ID": o.order_number,
            "Date": o.created_at.strftime("%Y-%m-%d %H:%M"),
            "Customer": o.customer_name,
            "Phone": o.customer_phone or "",
            "Subtotal (₹)": o.subtotal,
            "Grand Total (₹)": o.grand_total,
            "Paid (₹)": o.paid_amount,
            "Pending (₹)": o.pending_amount,
            "Payment Status": o.payment_status.title(),
            "Payment Method": o.payment_method.upper(),
            "Order Status": o.order_status.title()
        } for o in orders]
        df = pd.DataFrame(data)

    elif report_type == "products":
        product_stats = db.query(
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("qty"),
            func.sum(OrderItem.subtotal).label("revenue")
        ).join(Order).filter(
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.order_status != "cancelled"
        ).group_by(OrderItem.product_name).order_by(func.sum(OrderItem.subtotal).desc()).all()

        data = [{
            "Product Name": row[0],
            "Quantity Sold": row[1],
            "Total Revenue (₹)": round(row[2], 2)
        } for row in product_stats]
        df = pd.DataFrame(data)

    elif report_type == "inventory":
        inv = db.query(InventoryItem).all()
        data = [{
            "Item Name": i.name,
            "Type": i.item_type.replace("_", " ").title(),
            "Current Stock": i.current_qty,
            "Min Alert Level": i.min_qty,
            "Unit": i.unit,
            "Purchase Price (₹)": i.purchase_price,
            "Supplier": i.supplier or "",
            "Status": "Low Stock" if i.is_low_stock else "Adequate"
        } for i in inv]
        df = pd.DataFrame(data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=report_type.title())

    output.seek(0)
    response = Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response.headers["Content-Disposition"] = f"attachment; filename=cherry_blossom_{report_type}_report_{datetime.date.today()}.xlsx"
    return response
