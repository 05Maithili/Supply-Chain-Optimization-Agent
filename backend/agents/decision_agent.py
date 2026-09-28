"""
Decision Agent — combines all tool results and uses the LLM to generate
structured, explainable recommendations. The LLM reasons over tool outputs,
NOT raw supply chain data.
"""
import json
import logging
from agents.state import AgentState
from services.llm_client import get_llm_client, ORCHESTRATOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _build_context_prompt(state: AgentState) -> str:
    """Build the context prompt from all tool results."""
    sections = [f"USER QUERY: {state.user_query}\n"]

    if state.demand_result and "error" not in state.demand_result:
        dr = state.demand_result
        sections.append(
            f"DEMAND FORECAST RESULTS (calculated by XGBoost model):\n"
            f"- Product: {dr.get('product_id')}\n"
            f"- Forecast Horizon: {dr.get('horizon_days')} days\n"
            f"- Total Forecast Demand: {dr.get('total_forecast')} units\n"
            f"- Average Daily Demand: {dr.get('avg_daily_forecast')} units/day\n"
            f"- Model: {dr.get('model')}\n"
            f"- MAE: {dr.get('metrics', {}).get('MAE')}, "
            f"RMSE: {dr.get('metrics', {}).get('RMSE')}, "
            f"MAPE: {dr.get('metrics', {}).get('MAPE')}%\n"
        )

    if state.inventory_result and "error" not in state.inventory_result:
        ir = state.inventory_result
        if "all_products" not in ir:
            sections.append(
                f"INVENTORY STATUS (calculated by inventory optimization tool):\n"
                f"- Product: {ir.get('product_name')} ({ir.get('product_id')})\n"
                f"- Total Stock: {ir.get('total_stock')} units\n"
                f"- Safety Stock (formula-calculated): {ir.get('safety_stock')} units\n"
                f"- Reorder Point (formula-calculated): {ir.get('reorder_point')} units\n"
                f"- 30-Day Forecast Demand: {ir.get('forecast_30_day')} units\n"
                f"- Shortage: {ir.get('shortage')} units\n"
                f"- Risk Level: {ir.get('risk_level')}\n"
                f"- Recommended Order Quantity: {ir.get('recommended_order_quantity')} units\n"
                f"- EOQ: {ir.get('eoq')} units\n"
            )
        else:
            all_prods = ir.get("all_products", [])
            at_risk = [p for p in all_prods if p.get("risk_level") in ["High", "Critical"]]
            details = [
                f"  * {p.get('product_name')} ({p.get('product_id')}): Current Stock = {p.get('total_stock')} units, "
                f"Safety Stock = {p.get('safety_stock')}, Reorder Point = {p.get('reorder_point')}, "
                f"Shortage = {p.get('shortage')} units, Risk Level = {p.get('risk_level')}, "
                f"Recommended Order = {p.get('recommended_order_quantity')} units"
                for p in at_risk[:8]
            ]
            sections.append(
                f"INVENTORY STATUS — ALL PRODUCTS (calculated by inventory tool):\n"
                f"- Total products analyzed: {len(all_prods)}\n"
                f"- Products at High/Critical stockout risk: {len(at_risk)}\n"
                f"- Critical & High risk products breakdown:\n" + ("\n".join(details) if details else "  None") + "\n"
            )

    if state.supplier_result and "error" not in state.supplier_result:
        sr = state.supplier_result
        rec = sr.get("recommended_supplier")
        if rec:
            sections.append(
                f"SUPPLIER ANALYSIS (calculated by supplier scoring model):\n"
                f"- Product: {sr.get('product_id')}\n"
                f"- Recommended Supplier: {rec.get('supplier_name')} ({rec.get('supplier_id')})\n"
                f"- Composite Score: {rec.get('composite_score')}/100\n"
                f"- Unit Cost: {rec.get('unit_cost')}\n"
                f"- Lead Time: {rec.get('lead_time_days')} days\n"
                f"- Reliability: {rec.get('reliability')}%\n"
                f"- Quality Score: {rec.get('quality_score')}/100\n"
                f"- Risk Level: {rec.get('risk_level')}\n"
                f"- Suppliers evaluated: {len(sr.get('suppliers', []))}\n"
            )

    if state.logistics_result and "error" not in state.logistics_result:
        lr = state.logistics_result
        opt = lr.get("optimal_route") or lr.get("allocations", [{}])[0] if lr.get("allocations") else None
        if opt:
            sections.append(
                f"LOGISTICS OPTIMIZATION (calculated by OR-Tools):\n"
                f"- Destination: {lr.get('destination')}\n"
                f"- Optimal Route/Warehouse: {opt.get('origin_warehouse') or opt.get('warehouse_name')}\n"
                f"- Distance: {opt.get('distance_km')} km\n"
                f"- Transit Time: {opt.get('transit_time_days')} days\n"
                f"- Estimated Cost: {opt.get('estimated_cost_100_units') or opt.get('total_cost')}\n"
            )

    if state.risk_result and "error" not in state.risk_result:
        rr = state.risk_result
        risk_prod_details = [
            f"  * {p.get('product_id')} at {p.get('warehouse_id')}: {p.get('issue')} "
            f"(Current Stock: {p.get('current_stock')}, Severity: {p.get('severity')})"
            for p in rr.get("at_risk_products", [])[:8]
        ]
        sections.append(
            f"RISK ANALYSIS (calculated by risk assessment model):\n"
            f"- Inventory Risk: {rr.get('inventory_risk')} (score: {rr.get('inventory_risk_score')})\n"
            f"- Supplier Risk: {rr.get('supplier_risk')} (score: {rr.get('supplier_risk_score')})\n"
            f"- Demand Risk: {rr.get('demand_risk')} (score: {rr.get('demand_risk_score')})\n"
            f"- Logistics Risk: {rr.get('logistics_risk')} (score: {rr.get('logistics_risk_score')})\n"
            f"- Overall Risk: {rr.get('overall_risk')} (score: {rr.get('overall_risk_score')})\n"
            f"- At-risk warehouse locations count: {len(rr.get('at_risk_products', []))}\n"
            f"- At-risk locations breakdown:\n" + ("\n".join(risk_prod_details) if risk_prod_details else "  None") + "\n"
        )

    if state.retrieved_context and state.retrieved_context != "No documents available.":
        sections.append(
            f"RETRIEVED SUPPLY CHAIN POLICY & DOCUMENTATION (from RAG Document Agent):\n"
            f"{state.retrieved_context}\n\n"
            f"INSTRUCTION FOR POLICY QUESTIONS: Answer the query thoroughly and directly by referencing and citing the specific sources and clauses from the retrieved policy documents above."
        )

    sections.append(
        f"\nBased ONLY on the tool-calculated and document-retrieved results above, provide a structured analysis. "
        f"Do NOT invent any numbers or false policy claims. Cite which tool, agent, or document provided each piece of data."
    )

    return "\n\n".join(sections)


async def run_decision_agent(state: AgentState) -> AgentState:
    """Generate final structured recommendation using the LLM."""
    state.agents_used.append("Decision Agent")
    llm = get_llm_client()

    context_prompt = _build_context_prompt(state)

    try:
        response = await llm.chat(
            messages=[
                {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
                {"role": "user", "content": context_prompt},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        state.final_answer = response

    except Exception as e:
        logger.error(f"Decision agent LLM error: {e}")
        state.errors.append(f"LLM error: {str(e)}")
        # Fallback: structured response without LLM
        state.final_answer = _generate_fallback_response(state)

    return state


def _generate_fallback_response(state: AgentState) -> str:
    """Generate a structured response without LLM if it is unavailable."""
    lines = [
        "## Supply Chain Analysis Report",
        f"**Query:** {state.user_query}",
        "",
        "**Note:** AI explanation is temporarily unavailable. Showing raw tool and document retrieval results.",
        "",
    ]

    if state.retrieved_context and state.retrieved_context != "No documents available.":
        lines += [
            "### Retrieved Document Context (RAG)",
            state.retrieved_context,
            "",
        ]

    if state.inventory_result and "error" not in state.inventory_result:
        ir = state.inventory_result
        if "all_products" not in ir:
            lines += [
                "### Inventory Status",
                f"- Product: {ir.get('product_name')} ({ir.get('product_id')})",
                f"- Current Stock: {ir.get('total_stock')} units",
                f"- Risk Level: **{ir.get('risk_level')}**",
                f"- Recommended Order Quantity: {ir.get('recommended_order_quantity')} units",
                "",
            ]

    if state.risk_result and "error" not in state.risk_result:
        rr = state.risk_result
        lines += [
            "### Risk Summary",
            f"- Overall Risk: **{rr.get('overall_risk')}**",
            f"- Inventory Risk: {rr.get('inventory_risk')}",
            f"- Supplier Risk: {rr.get('supplier_risk')}",
            "",
        ]

    if state.errors:
        lines += ["### Errors", *[f"- {e}" for e in state.errors]]

    return "\n".join(lines)
