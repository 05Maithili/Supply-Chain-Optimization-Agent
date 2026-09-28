"""
Inventory API router.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from database.connection import get_db
from database.models import Inventory, Product, Warehouse
from tools.inventory import get_inventory_status, get_all_inventory_status, calculate_stockout_risk

router = APIRouter()


@router.get("/inventory")
async def get_inventory(
    warehouse_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get full inventory status for all products with calculated metrics."""
    statuses = await get_all_inventory_status(db)
    return statuses


@router.get("/inventory/{product_id}")
async def get_product_inventory(
    product_id: str,
    warehouse_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    result = await get_inventory_status(db, product_id, warehouse_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/inventory/{product_id}/stockout-risk")
async def get_stockout_risk(
    product_id: str,
    horizon: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    result = await calculate_stockout_risk(db, product_id, horizon)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/inventory/raw/all")
async def get_raw_inventory(db: AsyncSession = Depends(get_db)):
    """Return raw inventory records joined with product and warehouse info."""
    result = await db.execute(
        select(Inventory, Product, Warehouse)
        .join(Product, Inventory.product_id == Product.product_id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.warehouse_id)
        .order_by(Inventory.product_id)
    )
    rows = result.fetchall()
    return [
        {
            "product_id": inv.product_id,
            "product_name": prod.product_name,
            "category": prod.category,
            "warehouse_id": inv.warehouse_id,
            "warehouse_name": wh.warehouse_name,
            "current_stock": inv.current_stock,
            "safety_stock": inv.safety_stock,
            "reorder_point": inv.reorder_point,
            "last_updated": inv.last_updated.isoformat() if inv.last_updated else None,
        }
        for inv, prod, wh in rows
    ]
