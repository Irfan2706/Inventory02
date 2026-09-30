from __future__ import annotations

import pytest

pytest.importorskip("langchain")
pytest.importorskip("langchain_community")
pytest.importorskip("langchain_ollama")
pytest.importorskip("chromadb")
pytest.importorskip("rag.rag_chain")

from rag.rag_chain import ask_question, build_rag_chain


def test_reorder_formula():
    result = ask_question("How do I calculate a reorder point?", build_rag_chain())
    answer = result.get("answer", "").lower()
    assert any(token in answer for token in ["lead time", "daily", "demand", "safety", "reorder"])


def test_po_approval():
    result = ask_question("When does a PO need Store Manager approval?", build_rag_chain())
    answer = result.get("answer", "")
    assert "50,000" in answer or "50000" in answer or "₹" in answer


def test_movement_types():
    result = ask_question("What are the stock movement types?", build_rag_chain())
    answer = result.get("answer", "").lower()
    assert any(token in answer for token in ["receipt", "sale", "adjustment", "transfer", "return"])


def test_out_of_scope():
    result = ask_question("What is the weather forecast for Mumbai?", build_rag_chain())
    answer = result.get("answer", "").lower()
    assert any(token in answer for token in ["don't have", "not in", "no information", "cannot"])


def test_non_empty():
    for question in ["What is SKU?", "What is FIFO?", "What is a stockout?"]:
        assert len(ask_question(question, build_rag_chain()).get("answer", "")) > 10


def test_category_management():
    result = ask_question("How do grocery products differ from electronics in inventory management?", build_rag_chain())
    answer = result.get("answer", "").lower()
    assert any(token in answer for token in ["grocery", "electronic", "shelf life", "velocity", "cost"])
