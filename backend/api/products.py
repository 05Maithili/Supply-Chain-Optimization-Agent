"""
Products API router.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.connection import get_db
from database.models import Product

router = APIRouter()


@router.get("/products")
async def get_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).order_by(Product.product_id))
    products = result.scalars().all()
    return [
        {
            "id": p.id,
            "product_id": p.product_id,
            "product_name": p.product_name,
            "category": p.category,
            "unit_price": p.unit_price,
            "sku": p.sku,
        }
        for p in products
    ]


@router.get("/products/{product_id}")
async def get_product(product_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).where(Product.product_id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return {
        "id": product.id,
        "product_id": product.product_id,
        "product_name": product.product_name,
        "category": product.category,
        "unit_price": product.unit_price,
        "sku": product.sku,
        "weight_kg": product.weight_kg,
    }
