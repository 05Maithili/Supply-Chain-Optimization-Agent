"""
LangGraph Workflow — wires all agents into a directed graph.
"""
import logging
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.orchestrator import (
    classify_intent,
    should_run_demand, should_run_inventory, should_run_supplier,
    should_run_logistics, should_run_risk, should_run_rag,
)
from agents.demand_agent import run_demand_agent, skip_demand
from agents.inventory_agent import run_inventory_agent, skip_inventory
from agents.supplier_agent import run_supplier_agent, skip_supplier
from agents.logistics_agent import run_logistics_agent, skip_logistics
from agents.risk_agent import run_risk_agent, skip_risk
from agents.rag_agent import run_rag_agent, skip_rag
from agents.decision_agent import run_decision_agent

logger = logging.getLogger(__name__)


def build_workflow() -> StateGraph:
    """Build and compile the LangGraph multi-agent workflow."""

    workflow = StateGraph(AgentState)

    # ── Nodes ─────────────────────────────────────────────────────────────────
    workflow.add_node("orchestrator", classify_intent)
    workflow.add_node("demand", run_demand_agent)
    workflow.add_node("skip_demand", skip_demand)
    workflow.add_node("inventory", run_inventory_agent)
    workflow.add_node("skip_inventory", skip_inventory)
    workflow.add_node("supplier", run_supplier_agent)
    workflow.add_node("skip_supplier", skip_supplier)
    workflow.add_node("logistics", run_logistics_agent)
    workflow.add_node("skip_logistics", skip_logistics)
    workflow.add_node("risk", run_risk_agent)
    workflow.add_node("skip_risk", skip_risk)
    workflow.add_node("rag", run_rag_agent)
    workflow.add_node("skip_rag", skip_rag)
    workflow.add_node("decision", run_decision_agent)

    # ── Entry point ───────────────────────────────────────────────────────────
    workflow.set_entry_point("orchestrator")

    # ── Conditional routing from orchestrator ─────────────────────────────────
    workflow.add_conditional_edges(
        "orchestrator",
        should_run_demand,
        {"demand": "demand", "skip_demand": "skip_demand"},
    )

    # After demand (or skip) -> inventory
    workflow.add_conditional_edges(
        "demand",
        should_run_inventory,
        {"inventory": "inventory", "skip_inventory": "skip_inventory"},
    )
    workflow.add_conditional_edges(
        "skip_demand",
        should_run_inventory,
        {"inventory": "inventory", "skip_inventory": "skip_inventory"},
    )

    # After inventory (or skip) -> supplier
    workflow.add_conditional_edges(
        "inventory",
        should_run_supplier,
        {"supplier": "supplier", "skip_supplier": "skip_supplier"},
    )
    workflow.add_conditional_edges(
        "skip_inventory",
        should_run_supplier,
        {"supplier": "supplier", "skip_supplier": "skip_supplier"},
    )

    # After supplier (or skip) -> logistics
    workflow.add_conditional_edges(
        "supplier",
        should_run_logistics,
        {"logistics": "logistics", "skip_logistics": "skip_logistics"},
    )
    workflow.add_conditional_edges(
        "skip_supplier",
        should_run_logistics,
        {"logistics": "logistics", "skip_logistics": "skip_logistics"},
    )

    # After logistics (or skip) -> risk
    workflow.add_conditional_edges(
        "logistics",
        should_run_risk,
        {"risk": "risk", "skip_risk": "skip_risk"},
    )
    workflow.add_conditional_edges(
        "skip_logistics",
        should_run_risk,
        {"risk": "risk", "skip_risk": "skip_risk"},
    )

    # After risk (or skip) -> rag
    workflow.add_conditional_edges(
        "risk",
        should_run_rag,
        {"rag": "rag", "skip_rag": "skip_rag"},
    )
    workflow.add_conditional_edges(
        "skip_risk",
        should_run_rag,
        {"rag": "rag", "skip_rag": "skip_rag"},
    )

    # After RAG (or skip) -> decision
    workflow.add_edge("rag", "decision")
    workflow.add_edge("skip_rag", "decision")

    # Decision -> END
    workflow.add_edge("decision", END)

    return workflow.compile()


# Compiled workflow instance
_workflow = None


def get_workflow():
    global _workflow
    if _workflow is None:
        _workflow = build_workflow()
    return _workflow


async def run_agent_query(user_query: str, session_id: str = "") -> AgentState:
    """
    Main entry point: run the full multi-agent workflow for a user query.
    """
    initial_state = AgentState(
        user_query=user_query,
        session_id=session_id,
    )

    workflow = get_workflow()
    try:
        final_state = await workflow.ainvoke(initial_state)
        # Convert dict output back to AgentState if needed
        if isinstance(final_state, dict):
            final_state = AgentState(**final_state)
        return final_state
    except Exception as e:
        logger.error(f"Workflow error: {e}")
        initial_state.errors.append(f"Workflow error: {str(e)}")
        initial_state.final_answer = f"An error occurred during processing: {str(e)}"
        return initial_state
