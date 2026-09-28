"""
Inventory Optimization Tool — formula-based calculations.
All computations done in Python; LLM receives results, NOT raw numbers to compute.
"""
import math
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Inventory, Sale, Product, Warehouse
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

# ── Core Formulas ─────────────────────────────────────────────────────────────

def calculate_safety_stock(
    avg_demand: float,
    demand_std: float,
    lead_time_days: int,
    service_level_z: float = 1.65,   # 95% service level
) -> int:
    """
    Safety Stock = Z * sqrt(lead_time) * demand_std
    """
    ss = service_level_z * math.sqrt(lead_time_days) * demand_std
    return max(0, math.ceil(ss))


def calculate_reorder_point(
    avg_demand: float,
    lead_time_days: int,
    safety_stock: int,
) -> int:
    """
    ROP = (Avg Daily Demand * Lead Time) + Safety Stock
    """
    rop = (avg_demand * lead_time_days) + safety_stock
    return max(0, math.ceil(rop))


def calculate_eoq(
    annual_demand: float,
    ordering_cost: float = 200.0,
    holding_cost_rate: float = 0.20,
    unit_cost: float = 100.0,
) -> int:
    """
    EOQ = sqrt(2 * D * S / (h * C))
    """
    h = holding_cost_rate * unit_cost
    if h <= 0 or annual_demand <= 0:
        return 0
    eoq = math.sqrt(2 * annual_demand * ordering_cost / h)
    return max(1, math.ceil(eoq))


def classify_risk(
    current_stock: int,
    reorder_point: int,
    safety_stock: int,
    forecast_demand: float,
) -> str:
    """Classify inventory risk level."""
    if current_stock <= safety_stock:
        return "Critical"
    elif current_stock <= reorder_point:
        return "High"
    elif current_stock < reorder_point * 1.5:
        return "Medium"
    else:
        return "Low"


# ── Async Inventory Calculations ─────────────────────────────────────────────

async def get_inventory_status(
    session: AsyncSession,
    product_id: str,
    warehouse_id: Optional[str] = None,
) -> dict:
    """
    Get full inventory status with calculated metrics.
    """
    # Fetch inventory record(s)
    query = select(Inventory, Product, Warehouse).join(
        Product, Inventory.product_id == Product.product_id
    ).join(
        Warehouse, Inventory.warehouse_id == Warehouse.warehouse_id
    ).where(Inventory.product_id == product_id)

    if warehouse_id:
        query = query.where(Inventory.warehouse_id == warehouse_id)

    result = await session.execute(query)
    rows = result.fetchall()

    if not rows:
        return {"error": f"No inventory found for product {product_id}"}

    # Calculate 30-day average demand from sales
    thirty_days_ago = date.today() - timedelta(days=30)
    sales_query = select(
        func.sum(Sale.quantity_sold).label("total"),
        func.count().label("days"),
    ).where(
        Sale.product_id == product_id,
        Sale.sale_date >= thirty_days_ago,
    )
    if warehouse_id:
        sales_query = sales_query.where(Sale.warehouse_id == warehouse_id)

    sales_result = await session.execute(sales_query)
    sales_row = sales_result.first()
    total_sold = float(sales_row.total or 0)
    avg_daily_demand = total_sold / 30.0

    # Standard deviation from last 30-day individual day sums
    daily_query = select(
        Sale.sale_date,
        func.sum(Sale.quantity_sold).label("daily_qty"),
    ).where(
        Sale.product_id == product_id,
        Sale.sale_date >= thirty_days_ago,
    ).group_by(Sale.sale_date)

    daily_result = await session.execute(daily_query)
    daily_rows = daily_result.fetchall()
    daily_demands = [float(r.daily_qty) for r in daily_rows] if daily_rows else [avg_daily_demand]

    import numpy as np
    demand_std = float(np.std(daily_demands)) if len(daily_demands) > 1 else avg_daily_demand * 0.2

    # Aggregate inventory across warehouses if no warehouse specified
    total_stock = sum(r[0].current_stock for r in rows)
    stored_safety_stock = rows[0][0].safety_stock
    stored_rop = rows[0][0].reorder_point

    # Lead time (default 7 days if not from supplier)
    lead_time = 7

    # Recalculate with formulas
    safety_stock = calculate_safety_stock(avg_daily_demand, demand_std, lead_time)
    reorder_point = calculate_reorder_point(avg_daily_demand, lead_time, safety_stock)

    # 30-day forecast demand
    forecast_30 = avg_daily_demand * 30

    # Shortage calculation
    shortage = max(0, forecast_30 - total_stock)
    overstock = max(0, total_stock - forecast_30 * 2)

    risk_level = classify_risk(total_stock, reorder_point, safety_stock, forecast_30)

    # EOQ
    product_row = rows[0][1]
    eoq = calculate_eoq(avg_daily_demand * 365, unit_cost=product_row.unit_price)

    # Recommended order quantity
    rec_order = max(0, math.ceil(reorder_point + safety_stock + forecast_30 - total_stock))
    rec_order = max(rec_order, eoq) if shortage > 0 else 0

    inventory_records = []
    for inv, prod, wh in rows:
        inventory_records.append({
            "warehouse_id": inv.warehouse_id,
            "warehouse_name": wh.warehouse_name,
            "current_stock": inv.current_stock,
            "safety_stock": inv.safety_stock,
            "reorder_point": inv.reorder_point,
        })

    return {
        "product_id": product_id,
        "product_name": product_row.product_name,
        "total_stock": total_stock,
        "avg_daily_demand": round(avg_daily_demand, 2),
        "demand_std": round(demand_std, 2),
        "safety_stock": safety_stock,
        "reorder_point": reorder_point,
        "lead_time_days": lead_time,
        "forecast_30_day": round(forecast_30, 1),
        "shortage": round(shortage, 1),
        "overstock": round(overstock, 1),
        "risk_level": risk_level,
        "eoq": eoq,
        "recommended_order_quantity": rec_order,
        "inventory_value": round(total_stock * product_row.unit_price, 2),
        "warehouses": inventory_records,
    }


async def get_all_inventory_status(session: AsyncSession) -> list:
    """Get inventory status for all products."""
    query = select(Product.product_id)
    result = await session.execute(query)
    product_ids = [row[0] for row in result.fetchall()]

    statuses = []
    for pid in product_ids:
        status = await get_inventory_status(session, pid)
        if "error" not in status:
            statuses.append(status)
    return statuses


async def calculate_stockout_risk(
    session: AsyncSession,
    product_id: str,
    horizon_days: int = 7,
) -> dict:
    """Calculate stockout probability over given horizon."""
    status = await get_inventory_status(session, product_id)
    if "error" in status:
        return status

    avg_daily = status["avg_daily_demand"]
    std = status["demand_std"]
    stock = status["total_stock"]

    expected_demand = avg_daily * horizon_days
    demand_uncertainty = std * math.sqrt(horizon_days)

    # Probability that demand > stock (simplified normal approximation)
    if demand_uncertainty > 0:
        import scipy.stats as stats
        z = (stock - expected_demand) / demand_uncertainty
        prob_stockout = 1 - stats.norm.cdf(z)
    else:
        prob_stockout = 1.0 if expected_demand > stock else 0.0

    return {
        "product_id": product_id,
        "horizon_days": horizon_days,
        "current_stock": stock,
        "expected_demand": round(expected_demand, 1),
        "demand_uncertainty": round(demand_uncertainty, 1),
        "probability_stockout": round(float(prob_stockout) * 100, 1),
        "risk_level": status["risk_level"],
        "days_of_supply": round(stock / avg_daily, 1) if avg_daily > 0 else float("inf"),
    }
