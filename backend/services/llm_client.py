"""
LLM Client — Ollama-based, modular, swappable.
All LLM calls go through this abstraction layer.
"""
import os
import json
import httpx
import logging
from typing import Optional, AsyncIterator
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


class OllamaClient:
    """
    Modular LLM client for Ollama.
    Replace this class with GeminiClient, OpenAIClient, etc. to switch providers.
    """

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> str:
        """
        Send a chat request to Ollama and return the response text.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"]

        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running: 'ollama serve'"
            )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Ollama request timed out after {self.timeout}s. "
                "Try a smaller model or increase AGENT_TIMEOUT_SECONDS."
            )
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
    ) -> str:
        """Simple generate endpoint."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return await self.chat(messages, temperature=temperature)

    async def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available Ollama models."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                data = r.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []


# Singleton instance
_llm_client: Optional[OllamaClient] = None


def get_llm_client() -> OllamaClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = OllamaClient()
    return _llm_client


# ── System Prompt ─────────────────────────────────────────────────────────────

ORCHESTRATOR_SYSTEM_PROMPT = """You are SupplyChainAI, an expert supply chain decision support system.

CRITICAL RULES — YOU MUST FOLLOW THESE AT ALL TIMES:
1. NEVER invent or estimate numerical values. All numbers come from tool results provided to you.
2. Use ONLY tool-calculated data for inventory, demand, supplier scores, costs, and risks.
3. When tool results are available, base your entire analysis on those results.
4. If data is missing, clearly state what data is unavailable — do not guess.
5. Do NOT execute or simulate real-world procurement, purchasing, or shipping actions.
6. Clearly distinguish: (a) calculated data from tools, and (b) your explanatory reasoning.
7. Maintain professional, factual tone. No speculation about business context not in the data.
8. Structure your response with clear sections: Situation, Analysis, Recommendation, Risk Considerations.
9. If asked about policy (procurement, inventory, logistics), base your answer on retrieved documents only.
10. Use precise language. Avoid vague terms like "might", "probably", "around".

RESPONSE FORMAT:
- Always provide a structured response with sections
- Cite tool results explicitly (e.g., "According to the inventory calculation...")
- List specific recommended actions with quantities and timelines
- Identify which agents/tools were used

You are a decision-support system. You recommend; humans decide.
"""
