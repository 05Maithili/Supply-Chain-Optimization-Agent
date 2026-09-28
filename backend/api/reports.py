"""
Reports API router.
"""
import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.connection import get_db
from database.models import Product, Inventory, Supplier, Sale, Shipment
from tools.inventory import get_all_inventory_status
from tools.supplier import get_suppliers
from datetime import date, timedelta

router = APIRouter()


@router.get("/reports/inventory-risk")
async def inventory_risk_report(db: AsyncSession = Depends(get_db)):
    """Inventory risk report with all calculated metrics."""
    statuses = await get_all_inventory_status(db)
    return {
        "report_type": "Inventory Risk Report",
        "generated_at": date.today().isoformat(),
        "summary": {
            "total_products": len(statuses),
            "critical_risk": len([s for s in statuses if s["risk_level"] == "Critical"]),
            "high_risk": len([s for s in statuses if s["risk_level"] == "High"]),
            "medium_risk": len([s for s in statuses if s["risk_level"] == "Medium"]),
            "low_risk": len([s for s in statuses if s["risk_level"] == "Low"]),
        },
        "products": sorted(statuses, key=lambda x: ["Critical", "High", "Medium", "Low"].index(x["risk_level"])),
    }


@router.get("/reports/supplier-performance")
async def supplier_performance_report(db: AsyncSession = Depends(get_db)):
    suppliers = await get_suppliers(db)
    return {
        "report_type": "Supplier Performance Report",
        "generated_at": date.today().isoformat(),
        "suppliers": suppliers,
    }


@router.get("/reports/demand-forecast")
async def demand_forecast_report(
    horizon: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Demand forecast for all products."""
    from tools.forecasting import forecast_demand
    result = await db.execute(select(Product.product_id, Product.product_name))
    products = result.fetchall()

    forecasts = []
    for pid, pname in products:
        fc = await forecast_demand(db, pid, horizon)
        if "error" not in fc:
            forecasts.append({
                "product_id": pid,
                "product_name": pname,
                "total_forecast": fc.get("total_forecast"),
                "avg_daily_forecast": fc.get("avg_daily_forecast"),
                "metrics": fc.get("metrics"),
            })

    return {
        "report_type": "Demand Forecast Report",
        "generated_at": date.today().isoformat(),
        "horizon_days": horizon,
        "products": forecasts,
    }


@router.get("/reports/logistics-cost")
async def logistics_cost_report(db: AsyncSession = Depends(get_db)):
    """Logistics cost summary from shipment data."""
    thirty_days_ago = date.today() - timedelta(days=30)
    result = await db.execute(
        select(
            Shipment.warehouse_id,
            Shipment.destination,
            func.sum(Shipment.transportation_cost).label("total_cost"),
            func.count().label("num_shipments"),
            func.sum(Shipment.quantity).label("total_units"),
        )
        .where(Shipment.ship_date >= thirty_days_ago)
        .group_by(Shipment.warehouse_id, Shipment.destination)
        .order_by(func.sum(Shipment.transportation_cost).desc())
    )
    rows = result.fetchall()

    return {
        "report_type": "Logistics Cost Report",
        "generated_at": date.today().isoformat(),
        "period": "Last 30 days",
        "routes": [
            {
                "warehouse_id": r.warehouse_id,
                "destination": r.destination,
                "total_cost": round(float(r.total_cost or 0), 2),
                "num_shipments": r.num_shipments,
                "total_units": r.total_units,
                "avg_cost_per_unit": round(float(r.total_cost or 0) / max(1, r.total_units), 2),
            }
            for r in rows
        ],
    }


@router.get("/reports/supply-chain-summary")
async def supply_chain_summary_report(db: AsyncSession = Depends(get_db)):
    """Comprehensive supply chain summary report."""
    from tools.risk import analyze_supply_chain_risk
    risk = await analyze_supply_chain_risk(db)
    inventory = await get_all_inventory_status(db)
    suppliers = await get_suppliers(db)

    return {
        "report_type": "Supply Chain Summary Report",
        "generated_at": date.today().isoformat(),
        "risk_overview": {
            "overall_risk": risk.get("overall_risk"),
            "inventory_risk": risk.get("inventory_risk"),
            "supplier_risk": risk.get("supplier_risk"),
            "demand_risk": risk.get("demand_risk"),
            "logistics_risk": risk.get("logistics_risk"),
        },
        "inventory_summary": {
            "total_products": len(inventory),
            "at_risk": len([i for i in inventory if i["risk_level"] in ["High", "Critical"]]),
            "total_value": round(sum(i["inventory_value"] for i in inventory), 2),
        },
        "supplier_summary": {
            "total_active": len(suppliers),
            "high_risk": len([s for s in suppliers if s["risk_level"] == "High"]),
        },
    }


@router.get("/reports/inventory-risk/csv")
async def inventory_risk_csv(db: AsyncSession = Depends(get_db)):
    """Download inventory risk report as CSV."""
    statuses = await get_all_inventory_status(db)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "product_id", "product_name", "total_stock", "safety_stock",
        "reorder_point", "forecast_30_day", "shortage", "risk_level",
        "recommended_order_quantity", "inventory_value",
    ])
    writer.writeheader()
    for s in statuses:
        writer.writerow({k: s.get(k, "") for k in writer.fieldnames})

    output.seek(0)
    return StreamingResponse(
        iter([output.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_risk_report.csv"},
    )
