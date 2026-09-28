"""
Logistics API router.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel
from database.connection import get_db
from database.models import TransportRoute, Warehouse, Shipment
from tools.logistics import optimize_routes, optimize_warehouse_allocation, calculate_transportation_cost
from sqlalchemy import select

router = APIRouter()


class AllocationRequest(BaseModel):
    product_id: str
    destination: str
    quantity: int


@router.get("/logistics/routes")
async def get_routes(
    destination: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await optimize_routes(db, destination)


@router.post("/logistics/optimize")
async def optimize_logistics(
    request: AllocationRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await optimize_warehouse_allocation(
        db, request.product_id, request.destination, request.quantity
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/logistics/warehouses")
async def get_warehouses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Warehouse))
    warehouses = result.scalars().all()
    return [
        {
            "warehouse_id": w.warehouse_id,
            "warehouse_name": w.warehouse_name,
            "location": w.location,
            "latitude": w.latitude,
            "longitude": w.longitude,
            "capacity": w.capacity,
            "current_utilization": w.current_utilization,
        }
        for w in warehouses
    ]


@router.get("/logistics/shipments")
async def get_shipments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Shipment).order_by(Shipment.created_at.desc()).limit(50)
    )
    shipments = result.scalars().all()
    return [
        {
            "shipment_id": s.shipment_id,
            "product_id": s.product_id,
            "warehouse_id": s.warehouse_id,
            "destination": s.destination,
            "quantity": s.quantity,
            "status": s.status,
            "ship_date": s.ship_date.isoformat() if s.ship_date else None,
            "estimated_delivery": s.estimated_delivery.isoformat() if s.estimated_delivery else None,
            "transportation_cost": s.transportation_cost,
        }
        for s in shipments
    ]
