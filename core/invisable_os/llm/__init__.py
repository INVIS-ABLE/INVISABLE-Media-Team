"""LLM access layer.

Two backends are supported:

* **Claude** — for the highest-stakes reasoning and final selection/judging.
* **Ollama** (Qwen / DeepSeek) — for high-volume local generation.

Both are wrapped so that when no backend is configured the platform degrades to a
deterministic stub. This keeps the whole system testable and demonstrable offline,
and means a missing API key never takes the agency OS down.
"""

from invisable_os.llm.client import LLMClient, LLMResponse, get_llm

__all__ = ["LLMClient", "LLMResponse", "get_llm"]
