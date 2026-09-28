"""
Agent API router — main interface for the multi-agent LangGraph system.
"""
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agents.workflow import run_agent_query

router = APIRouter()


class AgentQueryRequest(BaseModel):
    query: str
    session_id: str = ""


@router.post("/agent/query")
async def query_agent(request: AgentQueryRequest):
    """
    Run a natural-language query through the full multi-agent pipeline.
    The LangGraph orchestrator selects appropriate agents, calls tools,
    and the Decision Agent generates an explainable recommendation.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    session_id = request.session_id or str(uuid.uuid4())

    final_state = await run_agent_query(request.query, session_id)

    # Build tool results summary for frontend
    tool_results_summary = {}
    if final_state.demand_result:
        dr = final_state.demand_result
        tool_results_summary["demand_forecast"] = {
            "product_id": dr.get("product_id"),
            "total_forecast": dr.get("total_forecast"),
            "avg_daily_forecast": dr.get("avg_daily_forecast"),
            "horizon_days": dr.get("horizon_days"),
            "metrics": dr.get("metrics"),
        }

    if final_state.inventory_result and "all_products" not in final_state.inventory_result:
        ir = final_state.inventory_result
        tool_results_summary["inventory"] = {
            "product_id": ir.get("product_id"),
            "product_name": ir.get("product_name"),
            "total_stock": ir.get("total_stock"),
            "safety_stock": ir.get("safety_stock"),
            "reorder_point": ir.get("reorder_point"),
            "shortage": ir.get("shortage"),
            "risk_level": ir.get("risk_level"),
            "recommended_order_quantity": ir.get("recommended_order_quantity"),
        }
    elif final_state.inventory_result and "all_products" in final_state.inventory_result:
        all_inv = final_state.inventory_result["all_products"]
        at_risk = [p for p in all_inv if p.get("risk_level") in ["High", "Critical"]]
        tool_results_summary["inventory_summary"] = {
            "total_products": len(all_inv),
            "at_risk_count": len(at_risk),
            "at_risk_products": [
                {
                    "product_id": p["product_id"],
                    "product_name": p["product_name"],
                    "risk_level": p["risk_level"],
                    "total_stock": p["total_stock"],
                    "shortage": p["shortage"],
                    "recommended_order_quantity": p["recommended_order_quantity"],
                }
                for p in at_risk[:5]
            ],
        }

    if final_state.supplier_result:
        sr = final_state.supplier_result
        rec = sr.get("recommended_supplier")
        if rec:
            tool_results_summary["supplier_recommendation"] = {
                "product_id": sr.get("product_id"),
                "recommended": rec.get("supplier_name"),
                "composite_score": rec.get("composite_score"),
                "risk_level": rec.get("risk_level"),
            }

    if final_state.risk_result:
        rr = final_state.risk_result
        tool_results_summary["risk_summary"] = {
            "overall_risk": rr.get("overall_risk"),
            "inventory_risk": rr.get("inventory_risk"),
            "supplier_risk": rr.get("supplier_risk"),
            "demand_risk": rr.get("demand_risk"),
            "logistics_risk": rr.get("logistics_risk"),
        }

    if final_state.rag_sources:
        tool_results_summary["rag_retrieval"] = {
            "num_chunks_retrieved": len(final_state.rag_sources),
            "documents": list(dict.fromkeys(r.get("source", "Unknown") for r in final_state.rag_sources)),
        }

    # RAG sources
    rag_sources = [
        {
            "source": r.get("source", "Unknown"),
            "chunk_id": r.get("chunk_id"),
            "relevance_score": round(r.get("score", 0), 3),
            "excerpt": (r.get("text", "")[:160] + "...") if r.get("text") else "",
        }
        for r in final_state.rag_sources[:5]
    ]

    return {
        "answer": final_state.final_answer,
        "agents_used": final_state.agents_used,
        "intent": final_state.intent,
        "tool_results": tool_results_summary,
        "recommendations": final_state.recommended_actions,
        "sources": rag_sources,
        "errors": final_state.errors,
        "session_id": session_id,
    }


@router.get("/agent/demo-queries")
async def get_demo_queries():
    """Return pre-configured demonstration queries."""
    return [
        {"id": 1, "query": "Which products are at risk of stockout?", "category": "Inventory"},
        {"id": 2, "query": "Forecast demand for Product P101 for the next 30 days.", "category": "Demand"},
        {"id": 3, "query": "Which supplier should be considered for Product P102?", "category": "Supplier"},
        {"id": 4, "query": "How can transportation cost be reduced?", "category": "Logistics"},
        {"id": 5, "query": "Which warehouse should fulfill the order?", "category": "Logistics"},
        {"id": 6, "query": "Why is Product P111 classified as high risk?", "category": "Risk"},
        {"id": 7, "query": "Summarize the current supply chain situation.", "category": "General"},
        {"id": 8, "query": "What does the procurement policy say about safety stock?", "category": "Policy"},
        {"id": 9, "query": "Product P105 demand increased by 20%. What action should be taken?", "category": "Multi-Agent"},
    ]
