"""
Risk Analysis Tool — comprehensive supply-chain risk assessment.
"""
import math
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Inventory, Sale, Supplier, SupplierProduct, Shipment
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


def _risk_score_to_level(score: float) -> str:
    if score >= 7:
        return "Critical"
    elif score >= 5:
        return "High"
    elif score >= 3:
        return "Medium"
    else:
        return "Low"


async def analyze_supply_chain_risk(
    session: AsyncSession,
    product_id: Optional[str] = None,
) -> dict:
    """
    Comprehensive risk analysis across inventory, suppliers, demand, logistics.
    """
    if product_id and str(product_id).strip().lower() in ["null", "none", "all", "all products", ""]:
        product_id = None

    # ── Inventory Risk ────────────────────────────────────────────────────────
    inv_query = select(Inventory)
    if product_id:
        inv_query = inv_query.where(Inventory.product_id == product_id)
    inv_result = await session.execute(inv_query)
    inventories = inv_result.scalars().all()

    inventory_risk_score = 0
    at_risk_products = []
    total_inv_value = 0.0

    for inv in inventories:
        if inv.current_stock <= inv.safety_stock:
            inventory_risk_score += 3
            at_risk_products.append({
                "product_id": inv.product_id,
                "warehouse_id": inv.warehouse_id,
                "issue": "Below safety stock",
                "current_stock": inv.current_stock,
                "safety_stock": inv.safety_stock,
                "severity": "Critical",
            })
        elif inv.current_stock <= inv.reorder_point:
            inventory_risk_score += 2
            at_risk_products.append({
                "product_id": inv.product_id,
                "warehouse_id": inv.warehouse_id,
                "issue": "Below reorder point",
                "current_stock": inv.current_stock,
                "reorder_point": inv.reorder_point,
                "severity": "High",
            })
        elif inv.current_stock > inv.reorder_point * 3:
            inventory_risk_score += 1
            at_risk_products.append({
                "product_id": inv.product_id,
                "warehouse_id": inv.warehouse_id,
                "issue": "Potential overstock",
                "current_stock": inv.current_stock,
                "severity": "Medium",
            })

    inv_risk_normalized = min(10, inventory_risk_score / max(1, len(inventories)) * 5)

    # ── Demand Risk ───────────────────────────────────────────────────────────
    sixty_days_ago = date.today() - timedelta(days=60)
    thirty_days_ago = date.today() - timedelta(days=30)

    demand_query = select(
        Sale.product_id,
        func.sum(Sale.quantity_sold).label("qty"),
    ).group_by(Sale.product_id)

    # Compare last 30 days vs previous 30 days for volatility
    recent_q = demand_query.where(Sale.sale_date >= thirty_days_ago)
    prev_q = demand_query.where(
        Sale.sale_date >= sixty_days_ago,
        Sale.sale_date < thirty_days_ago,
    )

    if product_id:
        recent_q = recent_q.where(Sale.product_id == product_id)
        prev_q = prev_q.where(Sale.product_id == product_id)

    recent_result = await session.execute(recent_q)
    prev_result = await session.execute(prev_q)

    recent_map = {r.product_id: r.qty for r in recent_result.fetchall()}
    prev_map = {r.product_id: r.qty for r in prev_result.fetchall()}

    demand_volatility = []
    for pid, recent_qty in recent_map.items():
        prev_qty = prev_map.get(pid, 0)
        if prev_qty > 0:
            change_pct = abs(recent_qty - prev_qty) / prev_qty * 100
            if change_pct > 30:
                demand_volatility.append({
                    "product_id": pid,
                    "recent_qty": recent_qty,
                    "prev_qty": prev_qty,
                    "change_percent": round(change_pct, 1),
                    "direction": "Increasing" if recent_qty > prev_qty else "Decreasing",
                })

    demand_risk_score = min(10, len(demand_volatility) * 2)

    # ── Supplier Risk ─────────────────────────────────────────────────────────
    sup_query = select(Supplier).where(Supplier.active == True)
    if product_id:
        sup_query = select(Supplier).join(
            SupplierProduct, Supplier.supplier_id == SupplierProduct.supplier_id
        ).where(SupplierProduct.product_id == product_id, Supplier.active == True)

    sup_result = await session.execute(sup_query)
    suppliers = sup_result.scalars().all()

    supplier_risks = []
    supplier_risk_score = 0
    for sup in suppliers:
        if sup.reliability < 75 or sup.historical_delays > 10:
            supplier_risk_score += 3
            supplier_risks.append({
                "supplier_id": sup.supplier_id,
                "supplier_name": sup.supplier_name,
                "issue": "Low reliability or high delays",
                "reliability": sup.reliability,
                "delays": sup.historical_delays,
                "severity": "High",
            })
        elif sup.lead_time_days > 21:
            supplier_risk_score += 2
            supplier_risks.append({
                "supplier_id": sup.supplier_id,
                "supplier_name": sup.supplier_name,
                "issue": "Long lead time",
                "lead_time_days": sup.lead_time_days,
                "severity": "Medium",
            })

    sup_risk_normalized = min(10, supplier_risk_score / max(1, len(suppliers)) * 5)

    # ── Logistics Risk ────────────────────────────────────────────────────────
    delayed_query = select(func.count()).select_from(Shipment).where(
        Shipment.status == "Delayed"
    )
    total_ship_query = select(func.count()).select_from(Shipment).where(
        Shipment.status.in_(["Pending", "In Transit", "Delayed"])
    )
    delayed_result = await session.execute(delayed_query)
    total_result = await session.execute(total_ship_query)
    delayed_count = delayed_result.scalar() or 0
    total_active = total_result.scalar() or 1

    delay_rate = delayed_count / total_active
    logistics_risk_score = min(10, delay_rate * 10 * 3)

    # ── Overall Risk ──────────────────────────────────────────────────────────
    overall = (
        0.30 * inv_risk_normalized
        + 0.25 * demand_risk_score
        + 0.25 * sup_risk_normalized
        + 0.20 * logistics_risk_score
    )

    return {
        "product_id": product_id or "All Products",
        "inventory_risk": _risk_score_to_level(inv_risk_normalized),
        "inventory_risk_score": round(inv_risk_normalized, 1),
        "supplier_risk": _risk_score_to_level(sup_risk_normalized),
        "supplier_risk_score": round(sup_risk_normalized, 1),
        "demand_risk": _risk_score_to_level(demand_risk_score),
        "demand_risk_score": round(demand_risk_score, 1),
        "logistics_risk": _risk_score_to_level(logistics_risk_score),
        "logistics_risk_score": round(logistics_risk_score, 1),
        "overall_risk": _risk_score_to_level(overall),
        "overall_risk_score": round(overall, 1),
        "at_risk_products": at_risk_products[:10],
        "demand_volatility": demand_volatility[:5],
        "supplier_risks": supplier_risks[:5],
        "delayed_shipments": delayed_count,
        "active_shipments": total_active,
    }
