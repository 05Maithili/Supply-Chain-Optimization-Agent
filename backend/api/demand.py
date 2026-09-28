"""
Demand Forecasting API router.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from database.connection import get_db
from tools.forecasting import forecast_demand

router = APIRouter()


@router.get("/demand/forecast/{product_id}")
async def get_demand_forecast(
    product_id: str,
    horizon: int = Query(30, ge=1, le=365),
    warehouse_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Run XGBoost demand forecast for a product."""
    result = await forecast_demand(db, product_id, horizon, warehouse_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
