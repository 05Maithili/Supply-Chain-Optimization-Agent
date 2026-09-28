"""
Risk Analysis API router.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from database.connection import get_db
from tools.risk import analyze_supply_chain_risk

router = APIRouter()


@router.get("/risk")
async def get_risk_analysis(
    product_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Comprehensive supply chain risk analysis."""
    return await analyze_supply_chain_risk(db, product_id)


@router.get("/risk/product/{product_id}")
async def get_product_risk(product_id: str, db: AsyncSession = Depends(get_db)):
    return await analyze_supply_chain_risk(db, product_id)
