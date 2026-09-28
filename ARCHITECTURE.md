# ARCHITECTURE.md — SupplyChainAI System & Agent Architecture

## System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        BROWSER (User)                              │
│   React 18 + Vite + Recharts + Lucide React                       │
│   Pages: Dashboard | Demand | Inventory | Suppliers | Logistics    │
│          Risk | Documents | AI Agent | Reports | Settings          │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ HTTP REST (/api/*)
                           │ Proxy via Vite → localhost:8000
┌──────────────────────────▼─────────────────────────────────────────┐
│                     FastAPI Backend                                │
│   Routers: products | inventory | suppliers | demand | logistics   │
│            risk | documents | agent | dashboard | reports         │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────────┐
           │               │                   │
┌──────────▼───────┐  ┌────▼────────┐  ┌──────▼──────────┐
│  SQLite Database │  │  LangGraph  │  │   RAG Pipeline  │
│  (SQLAlchemy)    │  │  Workflow   │  │  sentence-trans  │
│  - products      │  │  8 Agents   │  │  + NumPy FAISS  │
│  - sales 1200+   │  └────┬────────┘  └──────┬──────────┘
│  - inventory     │       │                  │
│  - suppliers     │  ┌────▼────────┐         │
│  - warehouses    │  │ Ollama LLM  │◄────────┘
│  - shipments     │  │ llama3.2    │
│  - routes        │  └────┬────────┘
└──────────────────┘       │
                           │ Tool calls
           ┌───────────────┼──────────────────────┐
           │               │                      │
┌──────────▼──────┐  ┌────▼──────────┐  ┌────────▼────────┐
│ tools/forecast  │  │ tools/inventor│  │ tools/supplier  │
│ XGBoost model   │  │ Safety stock  │  │ Composite score │
│ Feature eng.    │  │ ROP formula   │  │ Risk classifier │
│ CV evaluation   │  │ EOQ formula   │  └─────────────────┘
└─────────────────┘  └───────────────┘
           │
┌──────────▼──────┐  ┌─────────────────────────────────────┐
│ tools/logistics │  │ tools/risk                          │
│ OR-Tools solver │  │ Multi-factor risk scoring           │
│ Haversine dist  │  │ Inventory + Supplier + Demand +     │
│ Cost breakdown  │  │ Logistics risk composite            │
└─────────────────┘  └─────────────────────────────────────┘
```

---

## LangGraph Multi-Agent Workflow

```
                    ┌──────────────────┐
                    │   orchestrator   │ ← classify_intent() via LLM
                    │  (entry point)   │   extracts: intent, required_agents,
                    └────────┬─────────┘   entities (product_id, horizon, etc.)
                             │
              ┌──────────────┤ conditional_edge(should_run_demand)
              │              │
          ┌───▼───┐    ┌─────▼──────┐
          │demand │    │ skip_demand│
          └───┬───┘    └─────┬──────┘
              └──────┬───────┘
                     │ conditional_edge(should_run_inventory)
              ┌──────▼──────┐    ┌────────────────┐
              │  inventory  │    │ skip_inventory │
              └──────┬──────┘    └───────┬────────┘
                     └────────┬──────────┘
                              │ conditional_edge(should_run_supplier)
                     ┌────────▼───────┐    ┌────────────────┐
                     │    supplier    │    │  skip_supplier │
                     └────────┬───────┘    └───────┬────────┘
                              └────────┬───────────┘
                                       │ conditional_edge(should_run_logistics)
                              ┌────────▼──────┐    ┌──────────────────┐
                              │   logistics   │    │  skip_logistics  │
                              └────────┬──────┘    └─────────┬────────┘
                                       └──────────┬──────────┘
                                                  │ conditional_edge(should_run_risk)
                                         ┌────────▼────┐    ┌───────────┐
                                         │    risk     │    │ skip_risk │
                                         └────────┬────┘    └─────┬─────┘
                                                  └───────┬────────┘
                                                          │ conditional_edge(should_run_rag)
                                                 ┌────────▼──┐    ┌──────────┐
                                                 │    rag    │    │ skip_rag │
                                                 └────────┬──┘    └────┬─────┘
                                                          └────┬───────┘
                                                               │
                                                      ┌────────▼────────┐
                                                      │    decision     │ ← LLM synthesis
                                                      └────────┬────────┘
                                                               │
                                                             [END]
```

---

## AgentState Schema

```python
class AgentState(BaseModel):
    # Input
    user_query: str
    session_id: str

    # Intent (from LLM classification)
    intent: str          # demand_forecast | inventory_check | supplier_analysis |
                         # logistics_optimization | risk_analysis | rag_query |
                         # general_summary | multi_agent
    required_agents: list[str]
    extracted_entities: dict    # product_id, horizon_days, warehouse_id, destination, quantity

    # Tool Results (from Python tools — NOT LLM-generated)
    demand_result: dict | None        # XGBoost forecast output
    inventory_result: dict | None     # Safety stock, ROP, shortage, EOQ
    supplier_result: dict | None      # Composite scores, comparison, trade-offs
    logistics_result: dict | None     # OR-Tools allocation, route costs
    risk_result: dict | None          # Multi-factor risk scores
    retrieved_context: str | None     # RAG chunks as formatted string
    rag_sources: list[dict]           # Source metadata with relevance scores

    # Output
    agents_used: list[str]
    tool_results: dict
    final_answer: str                 # LLM-generated explanation (NOT calculations)
    errors: list[str]
```

---

## Tool Architecture

Each tool is a pure Python async function:

```
tools/
├── forecasting.py
│   ├── get_product_sales_df(session, product_id, warehouse_id) → DataFrame
│   ├── _create_features(df) → DataFrame  [lag features, rolling stats]
│   ├── train_and_forecast(df, horizon) → dict  [XGBoost + CV metrics]
│   └── forecast_demand(session, product_id, horizon, warehouse_id) → dict
│
├── inventory.py
│   ├── calculate_safety_stock(avg_demand, std, lead_time, z=1.65) → int
│   ├── calculate_reorder_point(avg_demand, lead_time, safety_stock) → int
│   ├── calculate_eoq(annual_demand, ordering_cost, holding_rate, unit_cost) → int
│   ├── classify_risk(stock, rop, ss, forecast) → str
│   ├── get_inventory_status(session, product_id, warehouse_id) → dict
│   ├── get_all_inventory_status(session) → list[dict]
│   └── calculate_stockout_risk(session, product_id, horizon) → dict
│
├── supplier.py
│   ├── calculate_supplier_score(...) → float  [weighted composite]
│   ├── classify_supplier_risk(...) → str
│   ├── get_suppliers(session, product_id) → list[dict]
│   ├── compare_suppliers(session, product_id) → dict
│   └── calculate_supplier_risk(session, supplier_id) → dict
│
├── logistics.py
│   ├── haversine_distance(lat1, lon1, lat2, lon2) → float
│   ├── calculate_transportation_cost(distance, quantity, base_cost, weight) → dict
│   ├── optimize_routes(session, destination) → dict  [OR-Tools GLOP]
│   └── optimize_warehouse_allocation(session, product_id, destination, quantity) → dict
│
└── risk.py
    └── analyze_supply_chain_risk(session, product_id) → dict
        ├── Inventory risk (stock vs. safety stock / ROP)
        ├── Demand risk (30d vs 60d demand change %)
        ├── Supplier risk (reliability, delays, fulfillment)
        └── Logistics risk (delayed shipment rate)
```

---

## RAG Pipeline

```
Document Upload (PDF/TXT/DOCX)
        │
        ▼
Text Extraction
  ├── PDF → pypdf PdfReader
  ├── DOCX → python-docx Document
  └── TXT → UTF-8 read
        │
        ▼
Word-based Chunking
  ├── chunk_size = 500 words
  ├── chunk_overlap = 50 words
  └── Metadata: {text, chunk_id, source, word_count}
        │
        ▼
Embedding Generation
  └── sentence-transformers: all-MiniLM-L6-v2
      Output: 384-dim float32 vectors
        │
        ▼
Vector Store (NumPy + Cosine Similarity)
  ├── embeddings.npy  [N × 384 matrix]
  └── metadata.json   [N chunk records]
        │
        ▼
Query → encode query → cosine similarity → top-K chunks
        │
        ▼
Context String → LLM prompt
        │
        ▼
Grounded Answer + Source Citations
```

---

## Key Design Principles

1. **LLM Reasons, Python Calculates**: Every number in the final answer originates from a Python tool function, never from LLM generation.

2. **Conditional Agent Routing**: Not all agents run for every query. The orchestrator uses LLM-based intent classification to select only the necessary agents, keeping latency low.

3. **Modular LLM Client**: The `OllamaClient` in `services/llm_client.py` implements a standard async interface. Swapping to Gemini, OpenAI, or any other provider requires only a new class with the same `chat()`, `generate()`, and `is_available()` methods.

4. **Formula-Based Inventory**: Safety stock = Z × √(LT) × σ, ROP = μ × LT + SS, EOQ = √(2DS/hC). These are not LLM outputs.

5. **OR-Tools for Optimization**: Warehouse allocation uses Google OR-Tools GLOP linear solver to minimize total transportation cost subject to stock availability constraints.

6. **Graceful Degradation**: If Ollama is unavailable, the Decision Agent falls back to a structured template response using only tool result data.

---

*SupplyChainAI — Academic Project — Agentic AI and Large Language Models*
