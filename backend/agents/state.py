"""
Agent State — shared state schema for the LangGraph workflow.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    """
    Shared state passed between all agents in the LangGraph workflow.
    """
    # Input
    user_query: str = ""
    session_id: str = ""

    # Intent classification
    intent: str = ""
    required_agents: list[str] = Field(default_factory=list)
    extracted_entities: dict = Field(default_factory=dict)  # product_id, horizon, etc.

    # Agent results
    demand_result: Optional[dict] = None
    inventory_result: Optional[dict] = None
    supplier_result: Optional[dict] = None
    logistics_result: Optional[dict] = None
    risk_result: Optional[dict] = None
    retrieved_context: Optional[str] = None
    rag_sources: list[dict] = Field(default_factory=list)

    # Decision output
    situation_summary: str = ""
    identified_problems: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    recommended_actions: list[dict] = Field(default_factory=list)
    risk_considerations: list[str] = Field(default_factory=list)
    expected_impact: str = ""

    # Metadata
    agents_used: list[str] = Field(default_factory=list)
    tool_results: dict = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    final_answer: str = ""

    class Config:
        arbitrary_types_allowed = True
