"""
Risk Agent — supply chain risk analysis.
"""
import logging
from agents.state import AgentState
from database.connection import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def run_risk_agent(state: AgentState) -> AgentState:
    from tools.risk import analyze_supply_chain_risk

    product_id = state.extracted_entities.get("product_id")
    state.agents_used.append("Risk Analysis Agent")

    async with AsyncSessionLocal() as session:
        try:
            result = await analyze_supply_chain_risk(session, product_id)
            state.risk_result = result
            state.tool_results["risk_analysis"] = result
            logger.info(f"Risk agent completed for {product_id or 'all'}")
        except Exception as e:
            logger.error(f"Risk agent error: {e}")
            state.errors.append(f"Risk agent error: {str(e)}")

    return state


async def skip_risk(state: AgentState) -> AgentState:
    return state
