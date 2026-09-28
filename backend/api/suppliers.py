"""
Suppliers API router.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from database.connection import get_db
from database.models import Supplier, SupplierProduct, Product
from tools.supplier import get_suppliers, compare_suppliers, calculate_supplier_risk

router = APIRouter()


@router.get("/suppliers")
async def get_all_suppliers(db: AsyncSession = Depends(get_db)):
    return await get_suppliers(db)


@router.get("/suppliers/{supplier_id}")
async def get_supplier(supplier_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Supplier).where(Supplier.supplier_id == supplier_id)
    )
    sup = result.scalar_one_or_none()
    if not sup:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    return {
        "supplier_id": sup.supplier_id,
        "supplier_name": sup.supplier_name,
        "country": sup.country,
        "reliability": sup.reliability,
        "quality_score": sup.quality_score,
        "lead_time_days": sup.lead_time_days,
        "capacity": sup.capacity,
        "historical_delays": sup.historical_delays,
        "order_fulfillment_rate": sup.order_fulfillment_rate,
        "active": sup.active,
    }


@router.get("/suppliers/product/{product_id}")
async def get_suppliers_for_product(product_id: str, db: AsyncSession = Depends(get_db)):
    return await get_suppliers(db, product_id)


@router.get("/suppliers/compare/{product_id}")
async def compare_product_suppliers(product_id: str, db: AsyncSession = Depends(get_db)):
    result = await compare_suppliers(db, product_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/suppliers/{supplier_id}/risk")
async def get_supplier_risk(supplier_id: str, db: AsyncSession = Depends(get_db)):
    result = await calculate_supplier_risk(db, supplier_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
