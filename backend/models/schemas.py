"""
Pydantic schemas for API request/response validation.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


# ── Agent ─────────────────────────────────────────────────────────────────────
class AgentQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="")

    @validator("query")
    def query_not_blank(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be blank")
        return v.strip()


class AgentQueryResponse(BaseModel):
    answer: str
    agents_used: List[str] = []
    intent: str = ""
    tool_results: Dict[str, Any] = {}
    recommendations: List[Dict] = []
    sources: List[Dict] = []
    errors: List[str] = []
    session_id: str = ""


# ── Demand ────────────────────────────────────────────────────────────────────
class ForecastRequest(BaseModel):
    product_id: str
    horizon: int = Field(default=30, ge=1, le=365)
    warehouse_id: Optional[str] = None


class ForecastMetrics(BaseModel):
    MAE: Optional[float] = None
    RMSE: Optional[float] = None
    MAPE: Optional[float] = None


# ── Inventory ─────────────────────────────────────────────────────────────────
class InventoryStatusResponse(BaseModel):
    product_id: str
    product_name: str
    total_stock: int
    avg_daily_demand: float
    safety_stock: int
    reorder_point: int
    lead_time_days: int
    forecast_30_day: float
    shortage: float
    overstock: float
    risk_level: str
    eoq: int
    recommended_order_quantity: int
    inventory_value: float


# ── Supplier ─────────────────────────────────────────────────────────────────
class SupplierData(BaseModel):
    supplier_id: str
    supplier_name: str
    country: Optional[str] = None
    reliability: float
    quality_score: float
    lead_time_days: int
    capacity: int
    historical_delays: int
    order_fulfillment_rate: float
    unit_cost: Optional[float] = None
    composite_score: Optional[float] = None
    risk_level: str


class SupplierCompareResponse(BaseModel):
    product_id: str
    suppliers: List[SupplierData]
    recommended_supplier: Optional[SupplierData] = None
    trade_offs: List[Dict] = []


# ── Risk ──────────────────────────────────────────────────────────────────────
class RiskReportResponse(BaseModel):
    product_id: str
    inventory_risk: str
    inventory_risk_score: float
    supplier_risk: str
    supplier_risk_score: float
    demand_risk: str
    demand_risk_score: float
    logistics_risk: str
    logistics_risk_score: float
    overall_risk: str
    overall_risk_score: float
    at_risk_products: List[Dict] = []
    demand_volatility: List[Dict] = []
    supplier_risks: List[Dict] = []


# ── Logistics ─────────────────────────────────────────────────────────────────
class LogisticsOptimizeRequest(BaseModel):
    product_id: str
    destination: str
    quantity: int = Field(ge=1)


# ── RAG ───────────────────────────────────────────────────────────────────────
class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class RAGSource(BaseModel):
    source: str
    chunk_id: Optional[int] = None
    relevance_score: float
    excerpt: str


class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[RAGSource] = []
    num_chunks_retrieved: int = 0
