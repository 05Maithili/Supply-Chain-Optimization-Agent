# SupplyChainAI
## Agentic AI-Based Supply Chain Optimization and Decision Support System

> Academic Project — Agentic AI and Large Language Models (LLMs)

---

## 1. Project Overview

SupplyChainAI is a full-stack, AI-powered supply chain decision-support platform. It uses a **LangGraph multi-agent architecture** where a local LLM (Ollama / llama3.2) orchestrates specialized agents that call Python tools for demand forecasting, inventory optimization, supplier analysis, logistics route optimization, and risk assessment.

The system is a **decision-support** platform: it recommends actions based on data and analysis, but does not autonomously execute real-world procurement or shipment actions.

---

## 2. Problem Statement

Modern supply chains face:
- Demand uncertainty and forecast inaccuracy
- Stockout and overstock risk
- Complex supplier trade-offs (cost vs. quality vs. lead time)
- High logistics costs due to suboptimal routing
- Lack of explainable, data-driven decision support

Traditional ERP systems provide data but lack intelligent, natural-language interaction and automated multi-factor analysis.

---

## 3. Objectives

1. Analyze historical sales and forecast future demand (XGBoost)
2. Calculate safety stock, reorder points, and EOQ from formulae
3. Score and compare suppliers using a composite model
4. Optimize warehouse-to-customer allocation (Google OR-Tools)
5. Detect and quantify supply chain risks
6. Enable RAG-based Q&A over policy documents
7. Orchestrate all agents with LangGraph + Ollama LLM
8. Provide a professional enterprise dashboard

---

## 4. System Architecture

```
User (Browser)
     |
     v
React Frontend (Vite + Recharts + Lucide)
     |
     v  REST API
FastAPI Backend
     |
     v
LangGraph Orchestrator
     |
  [Intent Classification via LLM]
     |
  +--+--+--+--+--+--+
  |  |  |  |  |  |  |
 D   I  S  L  R Rg  Dec
 e   n  u  o  i a   i
 m   v  p  g  s g   s
 a   .  p  .  k .   i
 n      l     .     o
 d      i           n
        e           A
        r           g
                    e
                    n
                    t
     |
     v
LLM (llama3.2) — Reasoning Layer
     |
     v
Structured JSON Recommendation
```

**Agents:**
- **Demand Agent** → XGBoost forecasting tool
- **Inventory Agent** → Safety stock, ROP, EOQ formulas
- **Supplier Agent** → Composite scoring model
- **Logistics Agent** → OR-Tools warehouse allocation
- **Risk Agent** → Multi-factor risk scoring
- **RAG Agent** → FAISS vector search + sentence-transformers
- **Decision Agent** → LLM synthesis over tool results

---

## 5. Agent Architecture (LangGraph)

```
orchestrator (classify_intent)
      |
   [conditional routing]
      |
   demand ──> inventory ──> supplier ──> logistics ──> risk ──> rag ──> decision ──> END
      |              |            |            |          |        |
   skip_demand  skip_inv   skip_sup   skip_log  skip_risk skip_rag
```

**AgentState fields:**
```python
user_query, intent, required_agents, extracted_entities,
demand_result, inventory_result, supplier_result,
logistics_result, risk_result, retrieved_context,
rag_sources, agents_used, tool_results, final_answer, errors
```

---

## 6. Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Recharts + Lucide React |
| Backend | Python 3.11 + FastAPI |
| LLM | Ollama (llama3.2) — local, no API key needed |
| Agent Framework | LangGraph |
| Forecasting | XGBoost + scikit-learn |
| Optimization | Google OR-Tools |
| RAG Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector Store | NumPy-based FAISS-style cosine similarity |
| Database | SQLite (async via aiosqlite) / MySQL supported |
| ORM | SQLAlchemy 2.0 async |
| Validation | Pydantic v2 |
| Document Parsing | pypdf, python-docx |

---

## 7. Dataset Description

| Table | Records |
|-------|---------|
| products | 12 industrial products |
| warehouses | 3 (Delhi, Mumbai, Chennai) |
| suppliers | 5 (India, Germany, China, USA) |
| supplier_products | 24 product-supplier mappings |
| sales | 1,200+ records (18 months) with seasonal trends |
| inventory | 36 product-warehouse combinations |
| customers | 5 customer accounts |
| transport_routes | 10 warehouse-to-city routes |
| shipments | 30 sample shipments |

Sales data includes:
- Seasonal variation (Q4 uplift, summer dip)
- Upward trend component
- Gaussian noise for realism

---

## 8. Database Schema

```sql
-- Products
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    product_id VARCHAR(20) UNIQUE,
    product_name VARCHAR(200),
    category VARCHAR(100),
    unit_price FLOAT,
    sku VARCHAR(50),
    weight_kg FLOAT
);

-- Sales (1,200+ rows)
CREATE TABLE sales (
    id INTEGER PRIMARY KEY,
    product_id VARCHAR(20) REFERENCES products(product_id),
    warehouse_id VARCHAR(20) REFERENCES warehouses(warehouse_id),
    sale_date DATE,
    quantity_sold INTEGER,
    unit_price FLOAT,
    total_revenue FLOAT
);

-- Inventory
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY,
    product_id VARCHAR(20),
    warehouse_id VARCHAR(20),
    current_stock INTEGER,
    safety_stock INTEGER,
    reorder_point INTEGER,
    max_stock INTEGER
);

-- Suppliers
CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY,
    supplier_id VARCHAR(20) UNIQUE,
    supplier_name VARCHAR(200),
    country VARCHAR(100),
    reliability FLOAT,        -- 0-100
    quality_score FLOAT,      -- 0-100
    lead_time_days INTEGER,
    capacity INTEGER,
    historical_delays INTEGER,
    order_fulfillment_rate FLOAT
);

-- See database/models.py for complete schema
```

---

## 9. Installation

### Prerequisites
- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com) installed and running

### Step 1 — Clone / Navigate to project
```bash
cd "E:\Projects\Supply Chain"
```

### Step 2 — Start Ollama and pull model
```bash
ollama serve
ollama pull llama3.2
```

### Step 3 — Backend setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
```

### Step 4 — Frontend setup
```bash
cd frontend
npm install
```

---

## 10. Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# LLM (Ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Database
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///./supplychain.db

# MySQL (optional)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=supplychain_ai
MYSQL_USER=root
MYSQL_PASSWORD=

# Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:5173

# RAG
CHUNK_SIZE=500
CHUNK_OVERLAP=50
RAG_TOP_K=5
```

---

## 11. Running the Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On first start, the database is auto-created and seeded with sample data.

API docs: http://localhost:8000/docs

---

## 12. Running the Frontend

```bash
cd frontend
npm run dev
```

Open: http://localhost:5173

The frontend proxies `/api` requests to the backend at `localhost:8000`.

---

## 13. LLM Configuration

The LLM client is in `backend/services/llm_client.py`.

To switch to a different model:
```python
# In .env
OLLAMA_MODEL=llama3.1
# or
OLLAMA_MODEL=mistral
# or
OLLAMA_MODEL=deepseek-r1
```

To switch to a different provider, implement a new client class with the same interface as `OllamaClient`:
```python
class GeminiClient:
    async def chat(self, messages, temperature, max_tokens, stream) -> str: ...
    async def generate(self, prompt, system, temperature) -> str: ...
    async def is_available(self) -> bool: ...
```

---

## 14. RAG Pipeline

```
Upload (PDF/TXT/DOCX)
    |
Text Extraction (pypdf / python-docx / plaintext)
    |
Chunking (500 words, 50 overlap)
    |
Embedding (sentence-transformers all-MiniLM-L6-v2)
    |
NumPy Vector Store (cosine similarity)
    |
Query → Top-K Retrieval
    |
Context String → LLM
    |
Grounded Answer + Source Citations
```

Files stored in: `backend/rag/vector_store/global/`
- `embeddings.npy` — numpy embedding matrix
- `metadata.json` — chunk text + source info

---

## 15. Agent Workflow

**Example: "Which products are at risk of stockout?"**

1. **Orchestrator** calls LLM → intent: `inventory_check`, required_agents: `[inventory, risk, decision]`
2. **Inventory Agent** calls `get_all_inventory_status()` → iterates all products, computes safety stock, ROP, shortage for each
3. **Risk Agent** calls `analyze_supply_chain_risk()` → scores inventory, demand, supplier, logistics risks
4. **Decision Agent** builds a context string from tool results → sends to LLM → LLM generates structured recommendation citing specific calculated values
5. **Response** returned to frontend with `agents_used`, `tool_results`, `answer`

**Key principle:** The LLM only *reasons* — it never *calculates*. All numbers come from Python tool functions.

---

## 16. API Documentation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/products` | GET | List all products |
| `/api/inventory` | GET | All inventory with computed metrics |
| `/api/inventory/{pid}` | GET | Single product inventory |
| `/api/inventory/{pid}/stockout-risk` | GET | Stockout probability |
| `/api/suppliers` | GET | All suppliers |
| `/api/suppliers/compare/{pid}` | GET | Compare suppliers for product |
| `/api/demand/forecast/{pid}` | GET | XGBoost forecast |
| `/api/risk` | GET | System-wide risk analysis |
| `/api/logistics/routes` | GET | All transport routes |
| `/api/logistics/optimize` | POST | OR-Tools warehouse allocation |
| `/api/logistics/shipments` | GET | Recent shipments |
| `/api/agent/query` | POST | Multi-agent LLM query |
| `/api/agent/demo-queries` | GET | Pre-configured demo queries |
| `/api/documents/upload` | POST | Upload document for RAG |
| `/api/rag/query` | POST | Query uploaded documents |
| `/api/dashboard/summary` | GET | Dashboard KPIs |
| `/api/reports/inventory-risk` | GET | Inventory risk report |
| `/api/reports/inventory-risk/csv` | GET | CSV download |
| `/api/reports/supplier-performance` | GET | Supplier report |
| `/api/reports/demand-forecast` | GET | Forecast report |
| `/api/reports/logistics-cost` | GET | Logistics cost report |

Full Swagger UI: http://localhost:8000/docs

---

## 17. Example Queries (AI Agent)

```
1. "Which products are at risk of stockout?"
   → Triggers: Inventory Agent + Risk Agent + Decision Agent

2. "Forecast demand for Product P101 for the next 30 days."
   → Triggers: Demand Agent + Decision Agent

3. "Which supplier should be considered for Product P102?"
   → Triggers: Supplier Agent + Decision Agent

4. "How can transportation cost be reduced?"
   → Triggers: Logistics Agent + Decision Agent

5. "Which warehouse should fulfill the order?"
   → Triggers: Logistics Agent + Inventory Agent + Decision Agent

6. "Why is Product P111 classified as high risk?"
   → Triggers: Inventory Agent + Risk Agent + Decision Agent

7. "Summarize the current supply chain situation."
   → Triggers: Inventory Agent + Risk Agent + Supplier Agent + Decision Agent

8. "What does the procurement policy say about safety stock?"
   → Triggers: RAG Agent + Decision Agent (requires uploaded document)

9. "Product P105 demand increased by 20%. What action should be taken?"
   → Triggers: ALL agents (multi-agent reasoning demonstration)
```

---

## 18. Evaluation Methodology

### Demand Forecasting
- **MAE** (Mean Absolute Error) — average absolute forecast error in units
- **RMSE** (Root Mean Square Error) — penalizes large errors
- **MAPE** (Mean Absolute Percentage Error) — error as % of actual demand
- Method: 3-fold time-series cross-validation (TimeSeriesSplit)

### Inventory Metrics
- **Service Level** = 1 - Stockout Rate
- **Reorder Point Accuracy** — actual stockouts vs. predicted
- **Safety Stock Formula**: Z × √(LT) × σ(demand) where Z=1.65 (95% service level)

### Supplier Scoring
- Composite score: cost (25%) + quality (25%) + reliability (20%) + lead time (15%) + fulfillment (15%)
- Risk classification based on reliability, delays, fulfillment rate thresholds

### Logistics
- OR-Tools minimizes: Σ(cost_per_unit × allocated_quantity)
- Subject to: Σ(allocation) = total_demand, allocation ≤ available_stock per warehouse

### RAG
- Cosine similarity score (0-1) for each retrieved chunk
- Source citations with chunk ID and relevance score

### Agent
- **Tool Selection**: LLM correctly identifies required agents for query type
- **Task Completion**: Final answer references tool-calculated numbers
- **Response Latency**: Measured per query in agent page

---

## 19. Future Enhancements

1. **Automated Reorder Triggers** — email/webhook alerts when stock hits ROP
2. **Prophet Time-Series** — seasonal decomposition for products with clear seasonality
3. **Multi-Model LLM** — A/B testing between Ollama models
4. **Real-Time Data Integration** — ERP/SAP connector via REST
5. **MySQL Production Mode** — full MySQL support (schema-compatible)
6. **Map Visualization** — Leaflet.js warehouse/route map
7. **Authentication** — JWT-based multi-user access
8. **Evaluation Dashboard** — Live MAE/MAPE tracking with historical model performance
9. **Batch Forecasting** — Scheduled nightly forecast refresh
10. **Multi-Language** — Internationalization for global deployments

---

## Project Structure

```
Supply Chain/
├── backend/
│   ├── agents/           # LangGraph agent nodes
│   │   ├── state.py      # AgentState schema
│   │   ├── workflow.py   # LangGraph graph definition
│   │   ├── orchestrator.py
│   │   ├── demand_agent.py
│   │   ├── inventory_agent.py
│   │   ├── supplier_agent.py
│   │   ├── logistics_agent.py
│   │   ├── risk_agent.py
│   │   ├── rag_agent.py
│   │   └── decision_agent.py
│   ├── api/              # FastAPI routers
│   ├── database/         # SQLAlchemy models, seed, connection
│   ├── models/           # Pydantic schemas
│   ├── rag/              # RAG pipeline
│   ├── services/         # LLM client (Ollama)
│   ├── tools/            # Calculation engines (no LLM)
│   ├── utils/            # Helpers
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # Sidebar, UI components
│   │   ├── pages/        # 10 dashboard pages
│   │   └── services/     # API client
│   └── vite.config.js
├── data/                 # CSV sample data
├── docs/
├── .env
├── .env.example
├── docker-compose.yml
├── README.md
└── ARCHITECTURE.md
```

---

*SupplyChainAI — Academic Project — Agentic AI and Large Language Models*
