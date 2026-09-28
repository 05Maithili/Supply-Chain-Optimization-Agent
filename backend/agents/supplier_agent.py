"""
Supplier Agent — wraps supplier analysis tools.
"""
import logging
from agents.state import AgentState
from database.connection import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def run_supplier_agent(state: AgentState) -> AgentState:
    from tools.supplier import compare_suppliers, get_suppliers

    product_id = state.extracted_entities.get("product_id")
    state.agents_used.append("Supplier Analysis Agent")

    async with AsyncSessionLocal() as session:
        try:
            if product_id:
                result = await compare_suppliers(session, product_id)
            else:
                result = {"suppliers": await get_suppliers(session)}
            state.supplier_result = result
            state.tool_results["supplier_analysis"] = result
            logger.info(f"Supplier agent completed for {product_id or 'all'}")
        except Exception as e:
            logger.error(f"Supplier agent error: {e}")
            state.errors.append(f"Supplier agent error: {str(e)}")

    return state


async def skip_supplier(state: AgentState) -> AgentState:
    return state
