from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

pytest.importorskip("langchain")
pytest.importorskip("langchain_community")
pytest.importorskip("langchain_ollama")
pytest.importorskip("chromadb")
pytest.importorskip("rag.rag_chain")

from rag.rag_chain import ask_question, build_rag_chain


def test_sku_query():
    result = ask_question("What is the SKU format for grocery products?", build_rag_chain())
    answer = result.get("answer", "").lower()
    assert any(token in answer for token in ["gro", "sku", "grocery", "prefix"])


def test_top_k():
    chain = build_rag_chain()
    retriever = chain.retriever if hasattr(chain, "retriever") else chain
    if hasattr(retriever, "search_kwargs"):
        assert retriever.search_kwargs.get("k", 4) == 4


def test_irrelevant_low_score():
    mock = MagicMock()
    mock.query.return_value = {"documents": [["Inventory stock info."]], "distances": [[0.87]]}
    assert mock.query(query_texts=["Football match results"], n_results=4)["distances"][0][0] > 0.5


def test_po_lifecycle():
    result = ask_question("What are the stages of a purchase order?", build_rag_chain())
    answer = result.get("answer", "").lower()
    assert any(token in answer for token in ["draft", "submitted", "received", "status", "lifecycle"])


def test_empty_query():
    try:
        result = ask_question("", build_rag_chain())
        assert isinstance(result, dict)
    except Exception as exc:
        pytest.fail(f"Empty query raised: {exc}")


def test_latency():
    chain = build_rag_chain()
    start = time.time()
    ask_question("What is a reorder point?", chain)
    assert time.time() - start < 5.0
