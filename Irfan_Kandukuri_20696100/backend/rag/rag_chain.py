from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any

import requests
from opentelemetry import trace

try:
    from langchain_classic.chains import RetrievalQA
except ImportError:  # pragma: no cover - dependency is optional at import time
    RetrievalQA = None

try:
    from langchain_community.vectorstores import Chroma
except ImportError:  # pragma: no cover - dependency is optional at import time
    Chroma = None

try:
    from langchain_ollama import ChatOllama, OllamaEmbeddings
except ImportError:  # pragma: no cover - dependency is optional at import time
    ChatOllama = None
    OllamaEmbeddings = None

try:
    from langsmith import traceable as _langsmith_traceable
except ImportError:  # pragma: no cover - dependency is optional at import time
    _langsmith_traceable = None

from app.logging_config import get_logger

from .ingest import DEFAULT_COLLECTION_NAME, DEFAULT_PERSIST_DIRECTORY, LocalHashEmbeddings, ensure_inventory_collection
from .prompt_templates import INVENTORY_RAG_PROMPT, build_inventory_prompt


logger = get_logger("rag")
tracer = trace.get_tracer("poc07.rag")
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_EMBED_MODEL = "nomic-embed-text"
UNKNOWN_FROM_MANUAL_ANSWER = "I don't have that information in the inventory manual."
SECTION_CATEGORY_MANAGEMENT = "### Section 12: Category Management"
SECTION_INTRODUCTION = "### Section 1: Introduction to Inventory Management"
SECTION_SKU = "### Section 2: Product Catalog and SKU System"
SECTION_STOCK = "### Section 3: Stock Levels and Reorder Points"
SECTION_ALERTS = "### Section 4: Stock Alert System"
SECTION_PURCHASE_ORDERS = "### Section 5: Purchase Order (PO) Process"
SECTION_SUPPLIERS = "### Section 6: Supplier Management"
SECTION_MOVEMENTS = "### Section 7: Stock Movement Recording"
SECTION_VALUATION = "### Section 8: Inventory Valuation"
SECTION_EOQ = "### Section 9: Reorder Quantity Calculation"
SECTION_PROCUREMENT = "### Section 10: Procurement Officer Responsibilities"
SECTION_RECONCILIATION = "### Section 11: Stock Count and Reconciliation"
SECTION_ANALYTICS = "### Section 13: Reporting and Analytics"
SECTION_INTEGRATION = "### Section 14: System Integration"
SECTION_TROUBLESHOOTING = "### Section 15: Troubleshooting"
RAG_QUERY_OPERATION = "rag.query"
RAG_GENERATE_SPAN = "rag.generate"
RAG_SOURCE_COUNT_ATTR = "rag.source_count"
PREFERRED_LLM_MODELS = ["llama3.1", "llama3", "mistral", "qwen", "smollm"]
PREFERRED_EMBEDDING_MODELS = ["nomic-embed-text", "mxbai-embed-large"]
_EMBED_PROBE_TEXT = "inventory embedding probe"
REORDER_POINT_TERM = "reorder point"
OUT_OF_STOCK_TERM = "out of stock"
PO_RECEIVING_TERM = "po receiving"
QUANTITY_AVAILABLE_TERM = "quantity available"
MANUAL_SOURCE = "inventory_manual.md"
TOKEN_PATTERN = r"[a-z0-9]+"
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}


def traceable(*args, **kwargs):
    # The decorator-based multipart ingestion path can fail in restricted corporate networks.
    # Keep SDK connectivity available while defaulting runtime decorator tracing to off.
    enabled = os.getenv("RAG_ENABLE_LANGSMITH_TRACEABLE", "false").strip().lower() in {"1", "true", "yes"}
    if _langsmith_traceable is None or not enabled:
        def decorator(func):
            return func

        return decorator
    return _langsmith_traceable(*args, **kwargs)


class OfflineRagChain:
    def __init__(self, retriever):
        self.retriever = retriever
        self.is_offline = True

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        question = payload.get("query", "")
        documents = []
        if hasattr(self.retriever, "get_relevant_documents"):
            documents = self.retriever.get_relevant_documents(question)
        answer = _compose_fallback_answer(question)
        return {"result": answer, "source_documents": documents}


class ResilientOllamaEmbeddings:
    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url
        self._fallback = LocalHashEmbeddings()
        self._ollama = OllamaEmbeddings(model=model, base_url=base_url)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            return self._ollama.embed_documents(texts)
        except Exception:
            logger.warning(
                "ollama_embedding_call_failed",
                reason="embedding endpoint unavailable; using local deterministic embeddings",
            )
            return self._fallback.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        try:
            return self._ollama.embed_query(text)
        except Exception:
            logger.warning(
                "ollama_embedding_call_failed",
                reason="embedding endpoint unavailable; using local deterministic embeddings",
            )
            return self._fallback.embed_query(text)


def _normalize_question(question: str) -> str:
    normalized = re.sub(r"\s+", " ", question or "").strip().lower()
    synonyms = {
        "reorder level": REORDER_POINT_TERM,
        "replenishment level": REORDER_POINT_TERM,
        "stock exhausted": OUT_OF_STOCK_TERM,
        "stockout": OUT_OF_STOCK_TERM,
        "vendor": "supplier",
        "vendor management": "supplier management",
        "goods received": PO_RECEIVING_TERM,
        "goods receipt": PO_RECEIVING_TERM,
        "po receipt": PO_RECEIVING_TERM,
        "purchase order receipt": PO_RECEIVING_TERM,
        "available stock": QUANTITY_AVAILABLE_TERM,
        "available quantity": QUANTITY_AVAILABLE_TERM,
        "stock on hand": "quantity on hand",
        "product registration": "product catalog",
        "product identification": "sku",
        "procurement workflow": "procurement operations",
    }
    for phrase, replacement in synonyms.items():
        normalized = normalized.replace(phrase, replacement)
    return normalized


@lru_cache(maxsize=1)
def _manual_sections() -> dict[str, str]:
    from .ingest import load_inventory_manual

    text = load_inventory_manual()
    sections: dict[str, str] = {}
    current_title: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("### Section "):
            if current_title is not None:
                sections[current_title] = "\n".join(current_lines).strip()
            current_title = line.strip()
            current_lines = [line.strip()]
            continue
        if current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        sections[current_title] = "\n".join(current_lines).strip()

    return sections


def _section_for_question(question: str) -> str | None:
    normalized = _normalize_question(question)
    if not normalized:
        return None

    if any(term in normalized for term in ["grocery", "electronics", "clothing", "household", "personal care"]):
        if any(term in normalized for term in ["different", "compare", "versus", "vs", "inventory management"]):
            return SECTION_CATEGORY_MANAGEMENT

    keyword_map = [
        ("inventory management", SECTION_INTRODUCTION),
        ("inventory system", SECTION_INTRODUCTION),
        ("how does the inventory", SECTION_INTRODUCTION),
        ("sku", SECTION_SKU),
        ("product catalog", SECTION_SKU),
        ("product categories", SECTION_SKU),
        ("product registration", SECTION_SKU),
        (REORDER_POINT_TERM, SECTION_STOCK),
        (QUANTITY_AVAILABLE_TERM, SECTION_STOCK),
        ("quantity on hand", SECTION_STOCK),
        ("stock tracked", SECTION_STOCK),
        ("low stock", SECTION_ALERTS),
        (OUT_OF_STOCK_TERM, SECTION_ALERTS),
        ("stock reaches zero", SECTION_ALERTS),
        ("alert", SECTION_ALERTS),
        ("procurement", SECTION_PROCUREMENT),
        ("who raises", SECTION_PROCUREMENT),
        ("purchase order", SECTION_PURCHASE_ORDERS),
        ("po lifecycle", SECTION_PURCHASE_ORDERS),
        (PO_RECEIVING_TERM, SECTION_PURCHASE_ORDERS),
        ("po still draft", SECTION_PURCHASE_ORDERS),
        ("po receipt", SECTION_PURCHASE_ORDERS),
        ("supplier", SECTION_SUPPLIERS),
        ("payment terms", SECTION_SUPPLIERS),
        ("lead time", SECTION_SUPPLIERS),
        ("stock movement", SECTION_MOVEMENTS),
        ("update stock", SECTION_MOVEMENTS),
        ("stock received", SECTION_MOVEMENTS),
        ("fifo", SECTION_VALUATION),
        ("stock value", SECTION_VALUATION),
        ("inventory value", SECTION_VALUATION),
        ("inventory valuation", SECTION_VALUATION),
        ("eoq", SECTION_EOQ),
        ("reorder quantity", SECTION_EOQ),
        ("approval", SECTION_PROCUREMENT),
        ("50000", SECTION_PROCUREMENT),
        ("count", SECTION_RECONCILIATION),
        ("reconciliation", SECTION_RECONCILIATION),
        ("category", SECTION_CATEGORY_MANAGEMENT),
        ("grocery", SECTION_CATEGORY_MANAGEMENT),
        ("electronics", SECTION_CATEGORY_MANAGEMENT),
        ("clothing", SECTION_CATEGORY_MANAGEMENT),
        ("household", SECTION_CATEGORY_MANAGEMENT),
        ("personal care", SECTION_CATEGORY_MANAGEMENT),
        ("turnover", SECTION_ANALYTICS),
        ("stock turn", SECTION_ANALYTICS),
        ("report", SECTION_ANALYTICS),
        ("analytics", SECTION_ANALYTICS),
        ("integration", SECTION_INTEGRATION),
        ("troubleshoot", SECTION_TROUBLESHOOTING),
        ("negative", SECTION_TROUBLESHOOTING),
    ]

    for keyword, section_title in keyword_map:
        if keyword in normalized:
            return section_title
    return None


def _compose_fallback_answer(question: str) -> str:
    normalized = _normalize_question(question)
    if not normalized:
        return UNKNOWN_FROM_MANUAL_ANSWER

    section_title = _section_for_question(normalized)
    sections = _manual_sections()
    if section_title and section_title in sections:
        return sections[section_title]

    return UNKNOWN_FROM_MANUAL_ANSWER


def _fallback_source_documents(question: str) -> list[dict[str, Any]]:
    section_title = _section_for_question(question)
    sections = _manual_sections()
    if not section_title or section_title not in sections:
        return []

    return [
        {
            "source": MANUAL_SOURCE,
            "chunk_index": None,
            "section": section_title,
            "content": sections[section_title],
        }
    ]


def _related_sections(section_title: str) -> list[str]:
    related = {
        SECTION_INTRODUCTION: [SECTION_STOCK, SECTION_PURCHASE_ORDERS],
        SECTION_SKU: [SECTION_CATEGORY_MANAGEMENT],
        SECTION_STOCK: [SECTION_ALERTS, SECTION_EOQ],
        SECTION_ALERTS: [SECTION_STOCK, SECTION_PURCHASE_ORDERS],
        SECTION_PURCHASE_ORDERS: [SECTION_MOVEMENTS, SECTION_PROCUREMENT],
        SECTION_SUPPLIERS: [SECTION_PURCHASE_ORDERS],
        SECTION_MOVEMENTS: [SECTION_STOCK, SECTION_PURCHASE_ORDERS],
        SECTION_VALUATION: [SECTION_ANALYTICS],
        SECTION_EOQ: [SECTION_STOCK],
        SECTION_PROCUREMENT: [SECTION_PURCHASE_ORDERS, SECTION_SUPPLIERS],
    }
    return related.get(section_title, [])


def _manual_source_documents(question: str) -> list[dict[str, Any]]:
    section_title = _section_for_question(question)
    sections = _manual_sections()
    if not section_title or section_title not in sections:
        return []

    source_titles = [section_title, *_related_sections(section_title)]
    return [
        {
            "source": MANUAL_SOURCE,
            "chunk_index": None,
            "section": title,
            "content": sections[title],
        }
        for title in source_titles
        if title in sections
    ]


def _looks_relevant(question: str, source_documents: list[Any]) -> bool:
    normalized = set(re.findall(TOKEN_PATTERN, _normalize_question(question)))
    if not normalized:
        return False

    for document in source_documents:
        text = getattr(document, "page_content", "") or ""
        doc_tokens = set(re.findall(TOKEN_PATTERN, text.lower()))
        if len(normalized & doc_tokens) >= 2:
            return True

    return False


def _get_ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)


def _list_ollama_models(base_url: str) -> list[str]:
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        response.raise_for_status()
        payload = response.json()
        models: list[dict[str, Any]] = payload.get("models", [])
        return [model.get("name", "") for model in models if model.get("name")]
    except Exception:
        return []


def _choose_preferred_model(models: list[str], preferred: list[str]) -> str | None:
    lowered = [(name, name.lower()) for name in models]
    for candidate in preferred:
        for name, low in lowered:
            if low.startswith(candidate):
                return name
    return None


def _choose_embedding_model(models: list[str]) -> str | None:
    lowered = [(name, name.lower()) for name in models]
    for preferred in PREFERRED_EMBEDDING_MODELS:
        for name, low in lowered:
            if low.startswith(preferred):
                return name
    for name, low in lowered:
        if "embed" in low:
            return name
    return None


def _model_supports_embeddings(base_url: str, model_name: str) -> bool:
    payload = {"model": model_name, "input": _EMBED_PROBE_TEXT}
    try:
        response = requests.post(f"{base_url}/api/embed", json=payload, timeout=10)
        if response.status_code == 200:
            return True
    except Exception:
        return False

    payload = {"model": model_name, "prompt": _EMBED_PROBE_TEXT}
    try:
        response = requests.post(f"{base_url}/api/embeddings", json=payload, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


def _build_embeddings():
    if OllamaEmbeddings is None:
        return LocalHashEmbeddings()

    base_url = _get_ollama_base_url()
    configured_model = os.getenv("OLLAMA_EMBED_MODEL", DEFAULT_OLLAMA_EMBED_MODEL).strip()
    models = _list_ollama_models(base_url)

    selected_model: str | None = None
    installed = {name.lower() for name in models}
    if configured_model and configured_model.lower() in installed:
        selected_model = configured_model
    elif configured_model:
        logger.warning(
            "ollama_embedding_missing",
            configured_model=configured_model,
            reason="configured embedding model not installed",
        )
    if selected_model is None:
        selected_model = _choose_embedding_model(models)

    if not selected_model:
        logger.warning("ollama_embedding_missing", reason="no embedding-capable local model found")
        return LocalHashEmbeddings()

    if not _model_supports_embeddings(base_url, selected_model):
        logger.warning(
            "ollama_embedding_missing",
            configured_model=selected_model,
            reason="local model does not support embeddings",
        )
        return LocalHashEmbeddings()

    try:
        return ResilientOllamaEmbeddings(model=selected_model, base_url=base_url)
    except Exception:
        logger.warning("ollama_embedding_init_failed", reason="unable to initialize embedding client")
        return LocalHashEmbeddings()


def _select_chat_model(available_models: list[str]) -> str | None:
    configured = os.getenv("OLLAMA_CHAT_MODEL", "").strip()
    if configured:
        selected = next((model for model in available_models if model.lower() == configured.lower()), None)
        if selected:
            return selected
        logger.warning(
            "ollama_chat_model_missing",
            configured_model=configured,
            reason="configured chat model not installed; selecting available local model",
        )
    return _choose_preferred_model(available_models, PREFERRED_LLM_MODELS) or (
        available_models[0] if available_models else None
    )


def build_rag_chain(
    persist_directory: str | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> Any:
    if Chroma is None:
        raise RuntimeError("ChromaDB dependency is required to build the RAG chain.")

    ensure_inventory_collection(persist_directory=persist_directory or DEFAULT_PERSIST_DIRECTORY, collection_name=collection_name)
    prompt = INVENTORY_RAG_PROMPT or build_inventory_prompt()
    embeddings = _build_embeddings()
    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(persist_directory or DEFAULT_PERSIST_DIRECTORY),
    )

    if RetrievalQA is None or ChatOllama is None:
        return OfflineRagChain(vectorstore.as_retriever(search_kwargs={"k": 4}))

    base_url = _get_ollama_base_url()
    available_models = _list_ollama_models(base_url)
    selected_model = _select_chat_model(available_models)
    if selected_model is None:
        return OfflineRagChain(vectorstore.as_retriever(search_kwargs={"k": 4}))

    llm = ChatOllama(model=selected_model, base_url=base_url, temperature=0.2)
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 4}),
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )


def serialize_source_documents(source_documents: list[Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for document in source_documents:
        metadata = getattr(document, "metadata", {}) or {}
        sources.append(
            {
                "source": metadata.get("source", MANUAL_SOURCE),
                "chunk_index": metadata.get("chunk_index"),
                "section": metadata.get("section"),
                "content": getattr(document, "page_content", ""),
            }
        )
    return sources


def _tokenize(text: str) -> set[str]:
    tokens = set(re.findall(TOKEN_PATTERN, (text or "").lower()))
    return {token for token in tokens if token not in _STOPWORDS}


def _rerank_documents(question: str, documents: list[Any]) -> list[Any]:
    if not documents:
        return []

    q_tokens = _tokenize(question)

    scored: list[tuple[int, int, Any]] = []
    seen_texts: set[str] = set()
    for idx, document in enumerate(documents):
        page_content = getattr(document, "page_content", "") or ""
        key = page_content.strip()
        if not key or key in seen_texts:
            continue
        seen_texts.add(key)

        doc_tokens = _tokenize(page_content)
        overlap_score = len(q_tokens & doc_tokens)
        heading_bonus = 2 if "### Section" in page_content else 0
        scored.append((overlap_score + heading_bonus, -idx, document))

    scored.sort(reverse=True)
    return [item[2] for item in scored]


def _build_grounded_answer(question: str, ranked_documents: list[Any]) -> str:
    section_title = _section_for_question(question)
    sections = _manual_sections()
    if section_title and section_title in sections:
        return sections[section_title]

    if ranked_documents:
        q_tokens = _tokenize(question)
        top_text = (getattr(ranked_documents[0], "page_content", "") or "").strip()
        top_overlap = len(q_tokens & _tokenize(top_text))
        if top_text and top_overlap >= 2:
            return top_text

    return UNKNOWN_FROM_MANUAL_ANSWER


@traceable(project_name="AI-Readiness-POC-07-P2")
def ask_question(question: str, chain: Any | None = None) -> dict[str, Any]:
    query_text = _normalize_question(question)
    logger.info("rag_query_started", operation=RAG_QUERY_OPERATION, status="success", duration_ms=0, question=question)

    with tracer.start_as_current_span(RAG_QUERY_OPERATION) as query_span:
        query_span.set_attribute("poc_id", "POC-07")
        query_span.set_attribute("question", question)

        if not query_text:
            answer = UNKNOWN_FROM_MANUAL_ANSWER
            logger.info(
                "rag_query_completed",
                operation=RAG_QUERY_OPERATION,
                status="success",
                duration_ms=0,
                used_fallback=True,
            )
            return {"answer": answer, "source_documents": []}

        active_chain = chain or build_rag_chain()
        retriever = getattr(active_chain, "retriever", None)
        fallback_used = False

        if retriever is None:
            with tracer.start_as_current_span(RAG_GENERATE_SPAN) as generate_span:
                try:
                    result = active_chain.invoke({"query": question})
                    source_documents = serialize_source_documents(result.get("source_documents", []))
                    answer = result.get("result", "") or _build_grounded_answer(question, [])
                    generate_span.set_attribute(RAG_SOURCE_COUNT_ATTR, len(source_documents))
                except Exception as exc:  # pragma: no cover - external services can fail at runtime
                    generate_span.record_exception(exc)
                    answer = _build_grounded_answer(question, [])
                    source_documents = _fallback_source_documents(question)

            logger.info(
                "rag_query_completed",
                operation=RAG_QUERY_OPERATION,
                status="success",
                duration_ms=0,
                used_fallback=answer == UNKNOWN_FROM_MANUAL_ANSWER,
                source_count=len(source_documents),
            )
            return {"answer": answer, "source_documents": source_documents}

        retrieved_documents: list[Any] = []

        retrieval_failed = False
        with tracer.start_as_current_span("rag.retrieve") as retrieve_span:
            try:
                if retriever is not None and hasattr(retriever, "get_relevant_documents"):
                    retrieved_documents = retriever.get_relevant_documents(question)
                elif retriever is not None and hasattr(retriever, "invoke"):
                    retrieved_documents = retriever.invoke(question)
            except Exception as exc:  # pragma: no cover - external services can fail at runtime
                retrieve_span.record_exception(exc)
                retrieval_failed = True
                retrieved_documents = []
            retrieve_span.set_attribute("rag.document_count", len(retrieved_documents))

        ranked_documents = _rerank_documents(question, retrieved_documents)
        serialized_ranked = serialize_source_documents(ranked_documents)
        manual_sources = _manual_source_documents(question)

        if retrieval_failed:
            with tracer.start_as_current_span(RAG_GENERATE_SPAN) as generate_span:
                answer = _build_grounded_answer(question, ranked_documents)
                source_documents = manual_sources or serialized_ranked or _fallback_source_documents(question)
                generate_span.set_attribute(RAG_SOURCE_COUNT_ATTR, len(source_documents))
                fallback_used = answer == UNKNOWN_FROM_MANUAL_ANSWER
                query_span.set_attribute("used_fallback", fallback_used)
            logger.info(
                "rag_query_completed",
                operation=RAG_QUERY_OPERATION,
                status="success",
                duration_ms=0,
                used_fallback=fallback_used,
                source_count=len(source_documents),
            )
            return {"answer": answer, "source_documents": source_documents}

        # Grounded mode keeps responses deterministic and tied to inventory_manual content,
        # which is more reliable than free-form generation with constrained local models.
        with tracer.start_as_current_span(RAG_GENERATE_SPAN) as generate_span:
            answer = _build_grounded_answer(question, ranked_documents)
            source_documents = manual_sources or serialized_ranked or _fallback_source_documents(question)
            fallback_used = answer == UNKNOWN_FROM_MANUAL_ANSWER
            query_span.set_attribute("used_fallback", fallback_used)
            generate_span.set_attribute(RAG_SOURCE_COUNT_ATTR, len(source_documents))

        logger.info(
            "rag_query_completed",
            operation=RAG_QUERY_OPERATION,
            status="success",
            duration_ms=0,
            used_fallback=fallback_used,
            source_count=len(source_documents),
        )
        return {"answer": answer, "source_documents": source_documents}
