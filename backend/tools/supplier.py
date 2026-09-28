"""
Supplier Analysis Tool — scoring, comparison, and risk assessment.
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Supplier, SupplierProduct, Product
import logging

logger = logging.getLogger(__name__)


def calculate_supplier_score(
    reliability: float,
    quality_score: float,
    lead_time_days: int,
    unit_cost: float,
    order_fulfillment_rate: float,
    historical_delays: int,
    cost_weight: float = 0.25,
    quality_weight: float = 0.25,
    reliability_weight: float = 0.20,
    lead_time_weight: float = 0.15,
    fulfillment_weight: float = 0.15,
) -> float:
    """
    Composite supplier score (0–100). Higher is better.
    Cost component: inverted (lower cost = higher score).
    Lead time: inverted (shorter = better).
    """
    # Normalize cost: assume max cost ~5000, min ~10
    cost_score = max(0, min(100, 100 * (1 - (unit_cost / 5000))))

    # Lead time score: 1 day = 100, 30 days = 0
    lead_time_score = max(0, min(100, 100 * (1 - (lead_time_days - 1) / 29)))

    # Penalty for delays
    delay_penalty = min(20, historical_delays * 2)
    adjusted_reliability = max(0, reliability - delay_penalty)

    score = (
        cost_weight * cost_score
        + quality_weight * quality_score
        + reliability_weight * adjusted_reliability
        + lead_time_weight * lead_time_score
        + fulfillment_weight * order_fulfillment_rate
    )
    return round(score, 2)


def classify_supplier_risk(
    reliability: float,
    lead_time_days: int,
    historical_delays: int,
    order_fulfillment_rate: float,
) -> str:
    risk_score = 0
    if reliability < 70:
        risk_score += 3
    elif reliability < 85:
        risk_score += 1
    if lead_time_days > 21:
        risk_score += 3
    elif lead_time_days > 14:
        risk_score += 2
    elif lead_time_days > 7:
        risk_score += 1
    if historical_delays > 10:
        risk_score += 3
    elif historical_delays > 5:
        risk_score += 2
    elif historical_delays > 0:
        risk_score += 1
    if order_fulfillment_rate < 85:
        risk_score += 3
    elif order_fulfillment_rate < 92:
        risk_score += 1

    if risk_score >= 6:
        return "High"
    elif risk_score >= 3:
        return "Medium"
    else:
        return "Low"


async def get_suppliers(
    session: AsyncSession,
    product_id: Optional[str] = None,
) -> list:
    """Retrieve suppliers, optionally filtered by product."""
    if product_id:
        query = select(Supplier, SupplierProduct).join(
            SupplierProduct, Supplier.supplier_id == SupplierProduct.supplier_id
        ).where(SupplierProduct.product_id == product_id, Supplier.active == True)
    else:
        query = select(Supplier)

    result = await session.execute(query)
    rows = result.fetchall()

    suppliers = []
    for row in rows:
        if product_id:
            sup, sp = row
            unit_cost = sp.unit_cost
            moq = sp.min_order_quantity
        else:
            sup = row[0]
            unit_cost = None
            moq = None

        score = calculate_supplier_score(
            sup.reliability,
            sup.quality_score,
            sup.lead_time_days,
            unit_cost or 500,
            sup.order_fulfillment_rate,
            sup.historical_delays,
        ) if unit_cost else None

        suppliers.append({
            "supplier_id": sup.supplier_id,
            "supplier_name": sup.supplier_name,
            "country": sup.country,
            "reliability": sup.reliability,
            "quality_score": sup.quality_score,
            "lead_time_days": sup.lead_time_days,
            "capacity": sup.capacity,
            "historical_delays": sup.historical_delays,
            "order_fulfillment_rate": sup.order_fulfillment_rate,
            "unit_cost": unit_cost,
            "min_order_quantity": moq,
            "composite_score": score,
            "risk_level": classify_supplier_risk(
                sup.reliability,
                sup.lead_time_days,
                sup.historical_delays,
                sup.order_fulfillment_rate,
            ),
        })

    # Sort by composite score descending
    suppliers.sort(key=lambda x: x["composite_score"] or 0, reverse=True)
    return suppliers


async def compare_suppliers(
    session: AsyncSession,
    product_id: str,
) -> dict:
    """Compare all suppliers for a given product and recommend the best."""
    suppliers = await get_suppliers(session, product_id)
    if not suppliers:
        return {"error": f"No suppliers found for product {product_id}"}

    ranked = sorted(suppliers, key=lambda x: x["composite_score"] or 0, reverse=True)

    trade_offs = []
    for sup in ranked:
        trade_offs.append({
            "supplier_id": sup["supplier_id"],
            "supplier_name": sup["supplier_name"],
            "rank": ranked.index(sup) + 1,
            "composite_score": sup["composite_score"],
            "strengths": _get_strengths(sup),
            "weaknesses": _get_weaknesses(sup),
        })

    return {
        "product_id": product_id,
        "suppliers": ranked,
        "recommended_supplier": ranked[0] if ranked else None,
        "trade_offs": trade_offs,
    }


def _get_strengths(sup: dict) -> list:
    strengths = []
    if sup["reliability"] >= 90:
        strengths.append("High reliability")
    if sup["quality_score"] >= 90:
        strengths.append("Excellent quality")
    if sup["lead_time_days"] <= 7:
        strengths.append("Short lead time")
    if sup["order_fulfillment_rate"] >= 97:
        strengths.append("High fulfillment rate")
    if sup["unit_cost"] and sup["unit_cost"] < 200:
        strengths.append("Competitive pricing")
    return strengths or ["Average performance"]


def _get_weaknesses(sup: dict) -> list:
    weaknesses = []
    if sup["reliability"] < 80:
        weaknesses.append("Below-average reliability")
    if sup["quality_score"] < 80:
        weaknesses.append("Below-average quality")
    if sup["lead_time_days"] > 14:
        weaknesses.append("Long lead time")
    if sup["historical_delays"] > 5:
        weaknesses.append(f"{sup['historical_delays']} historical delays")
    if sup["unit_cost"] and sup["unit_cost"] > 1000:
        weaknesses.append("High unit cost")
    return weaknesses or ["No significant weaknesses"]


async def calculate_supplier_risk(
    session: AsyncSession,
    supplier_id: str,
) -> dict:
    """Calculate detailed risk report for a specific supplier."""
    result = await session.execute(
        select(Supplier).where(Supplier.supplier_id == supplier_id)
    )
    sup = result.scalar_one_or_none()
    if not sup:
        return {"error": f"Supplier {supplier_id} not found"}

    risk_level = classify_supplier_risk(
        sup.reliability, sup.lead_time_days,
        sup.historical_delays, sup.order_fulfillment_rate
    )

    return {
        "supplier_id": supplier_id,
        "supplier_name": sup.supplier_name,
        "reliability_risk": "Low" if sup.reliability >= 90 else ("Medium" if sup.reliability >= 75 else "High"),
        "lead_time_risk": "Low" if sup.lead_time_days <= 7 else ("Medium" if sup.lead_time_days <= 14 else "High"),
        "delay_risk": "Low" if sup.historical_delays == 0 else ("Medium" if sup.historical_delays <= 5 else "High"),
        "fulfillment_risk": "Low" if sup.order_fulfillment_rate >= 95 else ("Medium" if sup.order_fulfillment_rate >= 85 else "High"),
        "overall_risk": risk_level,
        "risk_factors": {
            "reliability": sup.reliability,
            "quality_score": sup.quality_score,
            "lead_time_days": sup.lead_time_days,
            "historical_delays": sup.historical_delays,
            "order_fulfillment_rate": sup.order_fulfillment_rate,
        },
    }
