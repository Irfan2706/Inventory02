"""Local-only model abstraction for Phase 5 multi-agent narratives.

Reuses the Phase 2 Ollama selection strategy (backend/rag/rag_chain.py) so the
multi-agent pipeline runs entirely on the existing local model, with no
Gemini dependency and no new model downloads. If no local chat model is
available, callers fall back to deterministic, rule-based text.
"""
from __future__ import annotations

from typing import Any

from app.logging_config import get_logger

try:
    from langchain_ollama import ChatOllama
except ImportError:  # pragma: no cover - dependency is optional at import time
    ChatOllama = None

logger = get_logger("multi_agent")

_cached_llm: Any = None
_llm_checked = False


def reset_llm_cache() -> None:
    """Test hook to force re-selection of the local model."""
    global _cached_llm, _llm_checked
    _cached_llm = None
    _llm_checked = False


def get_local_llm() -> Any:
    global _cached_llm, _llm_checked
    if _llm_checked:
        return _cached_llm
    _llm_checked = True

    if ChatOllama is None:
        return None

    try:
        from rag.rag_chain import _get_ollama_base_url, _list_ollama_models, _select_chat_model

        base_url = _get_ollama_base_url()
        available_models = _list_ollama_models(base_url)
        selected_model = _select_chat_model(available_models)
        if not selected_model:
            logger.warning("multi_agent_llm_unavailable", reason="no local Ollama chat model found; using deterministic narratives")
            return None
        _cached_llm = ChatOllama(model=selected_model, base_url=base_url, temperature=0.2)
    except Exception:
        logger.warning("multi_agent_llm_unavailable", reason="local Ollama service unreachable; using deterministic narratives")
        _cached_llm = None

    return _cached_llm
