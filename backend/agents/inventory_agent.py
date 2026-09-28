"""
Inventory Optimization Agent — wraps inventory tools.
"""
import logging
from agents.state import AgentState
from database.connection import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def run_inventory_agent(state: AgentState) -> AgentState:
    from tools.inventory import get_inventory_status, get_all_inventory_status

    product_id = state.extracted_entities.get("product_id")
    if product_id and str(product_id).strip().lower() in ["null", "none", "all", "all products", ""]:
        product_id = None
    state.agents_used.append("Inventory Optimization Agent")

    async with AsyncSessionLocal() as session:
        try:
            if product_id:
                result = await get_inventory_status(session, product_id)
                state.inventory_result = result
                state.tool_results["inventory_status"] = result
            else:
                result = await get_all_inventory_status(session)
                state.inventory_result = {"all_products": result}
                state.tool_results["inventory_status"] = {"all_products": result}
            logger.info(f"Inventory agent completed for {product_id or 'all products'}")
        except Exception as e:
            logger.error(f"Inventory agent error: {e}")
            state.errors.append(f"Inventory agent error: {str(e)}")

    return state


async def skip_inventory(state: AgentState) -> AgentState:
    return state
