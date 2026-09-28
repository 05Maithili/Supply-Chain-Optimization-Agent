"""
Dashboard summary API — aggregated KPIs for the main dashboard.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.connection import get_db
from database.models import Product, Inventory, Supplier, Shipment, Sale, TransportRoute
from tools.risk import analyze_supply_chain_risk
from datetime import date, timedelta

router = APIRouter()


@router.get("/dashboard/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Aggregated KPIs for the main dashboard."""
    # Total products
    prod_count = (await db.execute(select(func.count()).select_from(Product))).scalar()

    # Total inventory value
    inv_result = await db.execute(
        select(Inventory.current_stock, Product.unit_price)
        .join(Product, Inventory.product_id == Product.product_id)
    )
    inv_rows = inv_result.fetchall()
    total_inventory_value = sum(row.current_stock * row.unit_price for row in inv_rows)

    # Active suppliers
    sup_count = (await db.execute(
        select(func.count()).select_from(Supplier).where(Supplier.active == True)
    )).scalar()

    # Pending/In-Transit shipments
    pending_shipments = (await db.execute(
        select(func.count()).select_from(Shipment).where(
            Shipment.status.in_(["Pending", "In Transit"])
        )
    )).scalar()

    # Products at risk (below reorder point)
    at_risk = await db.execute(
        select(func.count()).select_from(Inventory).where(
            Inventory.current_stock <= Inventory.reorder_point
        )
    )
    products_at_risk = at_risk.scalar()

    # Total transportation cost (last 30 days)
    thirty_days_ago = date.today() - timedelta(days=30)
    transport_cost = (await db.execute(
        select(func.sum(Shipment.transportation_cost)).where(
            Shipment.ship_date >= thirty_days_ago
        )
    )).scalar() or 0

    # Recent revenue (last 30 days)
    recent_revenue = (await db.execute(
        select(func.sum(Sale.total_revenue)).where(
            Sale.sale_date >= thirty_days_ago
        )
    )).scalar() or 0

    # Monthly sales trend (last 6 months)
    monthly_sales = []
    for i in range(5, -1, -1):
        month_start = date.today().replace(day=1) - timedelta(days=i * 30)
        month_end = month_start + timedelta(days=30)
        month_revenue = (await db.execute(
            select(func.sum(Sale.total_revenue)).where(
                Sale.sale_date >= month_start,
                Sale.sale_date < month_end,
            )
        )).scalar() or 0
        monthly_sales.append({
            "month": month_start.strftime("%b %Y"),
            "revenue": round(float(month_revenue), 2),
        })

    # Top 5 products by revenue (last 30 days)
    top_products_result = await db.execute(
        select(
            Sale.product_id,
            Product.product_name,
            func.sum(Sale.total_revenue).label("revenue"),
        )
        .join(Product, Sale.product_id == Product.product_id)
        .where(Sale.sale_date >= thirty_days_ago)
        .group_by(Sale.product_id, Product.product_name)
        .order_by(func.sum(Sale.total_revenue).desc())
        .limit(5)
    )
    top_products = [
        {"product_id": r.product_id, "product_name": r.product_name, "revenue": round(float(r.revenue), 2)}
        for r in top_products_result.fetchall()
    ]

    # Inventory risk distribution
    inv_risk_result = await db.execute(
        select(Inventory.product_id, Inventory.current_stock,
               Inventory.safety_stock, Inventory.reorder_point)
    )
    inv_items = inv_risk_result.fetchall()
    risk_dist = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for item in inv_items:
        if item.current_stock <= item.safety_stock:
            risk_dist["Critical"] += 1
        elif item.current_stock <= item.reorder_point:
            risk_dist["High"] += 1
        elif item.current_stock <= item.reorder_point * 1.5:
            risk_dist["Medium"] += 1
        else:
            risk_dist["Low"] += 1

    # Recent alerts
    alerts = []
    alert_items = await db.execute(
        select(Inventory, Product)
        .join(Product, Inventory.product_id == Product.product_id)
        .where(Inventory.current_stock <= Inventory.reorder_point)
        .order_by(Inventory.current_stock.asc())
        .limit(8)
    )
    for inv, prod in alert_items.fetchall():
        if inv.current_stock <= inv.safety_stock:
            risk = "Critical"
            issue = "Stock below safety level"
            action = f"Immediate reorder of {max(0, inv.reorder_point - inv.current_stock + inv.safety_stock)} units required"
        else:
            risk = "High"
            issue = "Stock below reorder point"
            action = f"Initiate reorder of approximately {inv.reorder_point - inv.current_stock} units"

        alerts.append({
            "product_id": prod.product_id,
            "product_name": prod.product_name,
            "warehouse_id": inv.warehouse_id,
            "issue": issue,
            "risk_level": risk,
            "current_stock": inv.current_stock,
            "reorder_point": inv.reorder_point,
            "recommended_action": action,
            "date": date.today().isoformat(),
        })

    return {
        "kpis": {
            "total_products": prod_count,
            "total_inventory_value": round(total_inventory_value, 2),
            "products_at_risk": products_at_risk,
            "active_suppliers": sup_count,
            "pending_shipments": pending_shipments,
            "transportation_cost_30d": round(float(transport_cost), 2),
            "revenue_30d": round(float(recent_revenue), 2),
        },
        "monthly_sales_trend": monthly_sales,
        "top_products": top_products,
        "inventory_risk_distribution": [
            {"risk_level": k, "count": v} for k, v in risk_dist.items()
        ],
        "recent_alerts": alerts,
    }
