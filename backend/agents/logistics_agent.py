"""
Logistics Agent — route optimization and warehouse allocation.
"""
import logging
from agents.state import AgentState
from database.connection import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def run_logistics_agent(state: AgentState) -> AgentState:
    from tools.logistics import optimize_routes, optimize_warehouse_allocation

    destination = state.extracted_entities.get("destination")
    product_id = state.extracted_entities.get("product_id")
    quantity = int(state.extracted_entities.get("quantity", 100))
    state.agents_used.append("Logistics Optimization Agent")

    async with AsyncSessionLocal() as session:
        try:
            if product_id and destination:
                result = await optimize_warehouse_allocation(
                    session, product_id, destination, quantity
                )
            else:
                result = await optimize_routes(session, destination)
            state.logistics_result = result
            state.tool_results["logistics_optimization"] = result
            logger.info(f"Logistics agent completed: dest={destination}, product={product_id}")
        except Exception as e:
            logger.error(f"Logistics agent error: {e}")
            state.errors.append(f"Logistics agent error: {str(e)}")

    return state


async def skip_logistics(state: AgentState) -> AgentState:
    return state
