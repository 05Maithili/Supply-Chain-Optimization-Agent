"""
Demand Forecasting Agent — wraps the forecasting tool.
"""
import logging
from agents.state import AgentState
from database.connection import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def run_demand_agent(state: AgentState) -> AgentState:
    """Invoke the demand forecasting tool and store results in state."""
    from tools.forecasting import forecast_demand

    raw_pid = state.extracted_entities.get("product_id")
    if raw_pid and str(raw_pid).strip().lower() in ["null", "none", "all", "all products", ""]:
        raw_pid = None
    horizon = int(state.extracted_entities.get("horizon_days", 30))
    warehouse_id = state.extracted_entities.get("warehouse_id")

    # If no product specified for demand forecasting, use P101 locally without mutating state.extracted_entities
    product_id = raw_pid or "P101"

    state.agents_used.append("Demand Forecasting Agent")

    async with AsyncSessionLocal() as session:
        try:
            result = await forecast_demand(session, product_id, horizon, warehouse_id)
            state.demand_result = result
            state.tool_results["demand_forecast"] = result
            logger.info(f"Demand agent completed for {product_id}, horizon={horizon}")
        except Exception as e:
            logger.error(f"Demand agent error: {e}")
            state.errors.append(f"Demand forecasting error: {str(e)}")
            state.demand_result = {"error": str(e), "product_id": product_id}

    return state


async def skip_demand(state: AgentState) -> AgentState:
    return state
