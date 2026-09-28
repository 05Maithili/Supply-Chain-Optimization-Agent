"""
Orchestrator / Supervisor Agent — intent classification and workflow planning.
Uses the LLM to understand user queries and determine which agents to invoke.
"""
import json
import re
import logging
from agents.state import AgentState
from services.llm_client import get_llm_client, ORCHESTRATOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

INTENT_SYSTEM = """You are a supply-chain AI intent classifier. 
Analyze the user query and return ONLY a valid JSON object with this exact structure:
{
  "intent": "<one of: demand_forecast, inventory_check, supplier_analysis, logistics_optimization, risk_analysis, rag_query, general_summary, multi_agent>",
  "required_agents": ["<list of: demand, inventory, supplier, logistics, risk, rag, decision>"],
  "entities": {
    "product_id": "<extracted product ID like P101, or null>",
    "horizon_days": <integer or 30>,
    "warehouse_id": "<extracted warehouse ID like W001, or null>",
    "destination": "<extracted destination or null>",
    "quantity": <integer or null>,
    "supplier_id": "<extracted supplier ID like S001, or null>"
  }
}

Intent and Agent Selection Rules:
- questions about stockout, stockout risk, stock levels, safety stock, reorder:
  intent: "inventory_check"
  required_agents: ["inventory", "risk", "decision"]
- questions about future demand, sales prediction, forecast:
  intent: "demand_forecast"
  required_agents: ["demand", "decision"]
- questions about supplier comparison, vendor risk, supplier scoring:
  intent: "supplier_analysis"
  required_agents: ["supplier", "decision"]
- questions about logistics, transport cost, delivery, routes, warehouse fulfillment:
  intent: "logistics_optimization"
  required_agents: ["logistics", "decision"]
- questions about why a product is high risk or system-wide disruptions:
  intent: "risk_analysis"
  required_agents: ["inventory", "risk", "decision"]
- questions about policies, manuals, procedures:
  intent: "rag_query"
  required_agents: ["rag", "decision"]
- overview or general status of entire supply chain:
  intent: "general_summary"
  required_agents: ["inventory", "risk", "supplier", "decision"]
- multi-agent scenario (e.g. demand changed by X%, what actions across inventory/supplier/shipping):
  intent: "multi_agent"
  required_agents: ["demand", "inventory", "supplier", "logistics", "decision"]

Always include 'decision' in required_agents.
Return ONLY valid JSON.
"""


async def classify_intent(state: AgentState) -> AgentState:
    """Classify intent and extract entities from the user query."""
    llm = get_llm_client()

    try:
        response = await llm.chat(
            messages=[
                {"role": "system", "content": INTENT_SYSTEM},
                {"role": "user", "content": state.user_query},
            ],
            temperature=0.0,
        )

        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = json.loads(response)

        state.intent = data.get("intent", "general_summary")
        raw_agents = data.get("required_agents", ["decision"])
        state.required_agents = [a.lower().strip() for a in raw_agents if isinstance(a, str)]
        raw_entities = data.get("entities", {})

        # Sanitize entities
        cleaned = {}
        for k, v in raw_entities.items():
            if v is not None and str(v).strip().lower() not in ["null", "none", "n/a", "undefined", ""]:
                cleaned[k] = v

        # Regex extraction for product ID, warehouse, and supplier
        query_upper = state.user_query.upper()
        pid_match = re.search(r'\b(P\d{3})\b', query_upper)
        if pid_match:
            cleaned["product_id"] = pid_match.group(1)
        elif "product_id" in cleaned:
            val = str(cleaned["product_id"]).strip().upper()
            if re.match(r'^P\d{3}$', val) and val in query_upper:
                cleaned["product_id"] = val
            else:
                cleaned.pop("product_id", None)
        else:
            cleaned.pop("product_id", None)

        wid_match = re.search(r'\b(W\d{3})\b', query_upper)
        if wid_match:
            cleaned["warehouse_id"] = wid_match.group(1)

        sid_match = re.search(r'\b(S\d{3})\b', query_upper)
        if sid_match:
            cleaned["supplier_id"] = sid_match.group(1)

        state.extracted_entities = cleaned

        # Heuristic correction for required agents
        q_lower = state.user_query.lower()
        if any(w in q_lower for w in ["stockout", "out of stock", "reorder", "safety stock", "stock level", "inventory"]):
            if "inventory" not in state.required_agents:
                state.required_agents.insert(0, "inventory")
            if "risk" not in state.required_agents:
                state.required_agents.append("risk")
            if "demand" in state.required_agents and not any(w in q_lower for w in ["forecast", "future demand", "predict"]):
                state.required_agents.remove("demand")

        if not state.required_agents:
            state.required_agents = ["inventory", "risk", "decision"]
        elif "decision" not in state.required_agents:
            state.required_agents.append("decision")

        logger.info(f"Intent: {state.intent}, Agents: {state.required_agents}, Entities: {state.extracted_entities}")

    except Exception as e:
        logger.warning(f"Intent classification failed: {e}. Using fallback.")
        state.intent = "general_summary"
        state.required_agents = ["inventory", "risk", "decision"]
        state.errors.append(f"Intent classification error: {str(e)}")

    return state


def should_run_demand(state: AgentState) -> str:
    return "demand" if "demand" in state.required_agents else "skip_demand"


def should_run_inventory(state: AgentState) -> str:
    return "inventory" if "inventory" in state.required_agents else "skip_inventory"


def should_run_supplier(state: AgentState) -> str:
    return "supplier" if "supplier" in state.required_agents else "skip_supplier"


def should_run_logistics(state: AgentState) -> str:
    return "logistics" if "logistics" in state.required_agents else "skip_logistics"


def should_run_risk(state: AgentState) -> str:
    return "risk" if "risk" in state.required_agents else "skip_risk"


def should_run_rag(state: AgentState) -> str:
    return "rag" if "rag" in state.required_agents else "skip_rag"
