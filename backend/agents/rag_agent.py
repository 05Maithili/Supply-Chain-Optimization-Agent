"""
RAG Agent — document retrieval for policy-based queries.
"""
import logging
from agents.state import AgentState
from rag.pipeline import search_supply_chain_documents, build_rag_context

logger = logging.getLogger(__name__)


async def run_rag_agent(state: AgentState) -> AgentState:
    """Search uploaded documents for relevant context."""
    state.agents_used.append("RAG Document Agent")
    try:
        results = search_supply_chain_documents(state.user_query, top_k=5)
        state.retrieved_context = build_rag_context(results)
        state.rag_sources = results
        state.tool_results["rag_retrieval"] = {
            "num_chunks": len(results),
            "sources": [r.get("source", "Unknown") for r in results],
        }
        logger.info(f"RAG agent retrieved {len(results)} chunks")
    except Exception as e:
        logger.error(f"RAG agent error: {e}")
        state.errors.append(f"RAG agent error: {str(e)}")
        state.retrieved_context = "No documents available."

    return state


async def skip_rag(state: AgentState) -> AgentState:
    return state
