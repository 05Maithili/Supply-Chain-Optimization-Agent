from api.products import router as products_router
from api.inventory import router as inventory_router
from api.suppliers import router as suppliers_router
from api.demand import router as demand_router
from api.logistics import router as logistics_router
from api.risk import router as risk_router
from api.documents import router as documents_router
from api.agent import router as agent_router
from api.dashboard import router as dashboard_router
from api.reports import router as reports_router

__all__ = [
    "products_router",
    "inventory_router",
    "suppliers_router",
    "demand_router",
    "logistics_router",
    "risk_router",
    "documents_router",
    "agent_router",
    "dashboard_router",
    "reports_router",
]
