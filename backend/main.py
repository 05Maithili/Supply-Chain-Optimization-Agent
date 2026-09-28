"""
SupplyChainAI - FastAPI Main Application
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from database.connection import engine, Base, init_db
from api import (
    products_router,
    inventory_router,
    suppliers_router,
    demand_router,
    logistics_router,
    risk_router,
    documents_router,
    agent_router,
    dashboard_router,
    reports_router,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    logger.info("Starting SupplyChainAI backend...")
    await init_db()
    logger.info("Database initialized.")
    
    # Create upload directories
    os.makedirs("uploads/documents", exist_ok=True)
    os.makedirs("rag/vector_store", exist_ok=True)
    os.makedirs("ml_models", exist_ok=True)
    
    logger.info("SupplyChainAI backend ready.")
    yield
    logger.info("Shutting down SupplyChainAI backend...")


app = FastAPI(
    title="SupplyChainAI",
    description="Agentic AI-Based Supply Chain Optimization and Decision Support System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(products_router, prefix="/api", tags=["Products"])
app.include_router(inventory_router, prefix="/api", tags=["Inventory"])
app.include_router(suppliers_router, prefix="/api", tags=["Suppliers"])
app.include_router(demand_router, prefix="/api", tags=["Demand"])
app.include_router(logistics_router, prefix="/api", tags=["Logistics"])
app.include_router(risk_router, prefix="/api", tags=["Risk"])
app.include_router(documents_router, prefix="/api", tags=["Documents"])
app.include_router(agent_router, prefix="/api", tags=["Agent"])
app.include_router(dashboard_router, prefix="/api", tags=["Dashboard"])
app.include_router(reports_router, prefix="/api", tags=["Reports"])


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "SupplyChainAI",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "SupplyChainAI"}
# Reload trigger 2



