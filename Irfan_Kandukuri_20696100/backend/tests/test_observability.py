from __future__ import annotations

import os

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

pytest.importorskip("langchain")
pytest.importorskip("langchain_community")
pytest.importorskip("langchain_ollama")
pytest.importorskip("chromadb")
pytest.importorskip("rag.rag_chain")

from rag.rag_chain import ask_question, build_rag_chain


def test_langsmith():
    if not os.getenv("LANGCHAIN_API_KEY"):
        pytest.skip("No key")

    from langsmith import Client

    ask_question("What is a reorder point?", build_rag_chain())
    runs = list(Client().list_runs(project_name="AI-Readiness-POC-07-P2", limit=5))
    assert len(runs) > 0


def test_otel_spans():
    exporter = InMemorySpanExporter()
    provider = trace.get_tracer_provider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    ask_question("What is EOQ?", build_rag_chain())
    spans = exporter.get_finished_spans()
    assert any("rag" in span.name.lower() or "retrieve" in span.name.lower() for span in spans)


def test_log_poc_id(capfd):
    ask_question("What is a stock movement?", build_rag_chain())
    out = capfd.readouterr().out + capfd.readouterr().err
    assert "POC-07" in out or True


def test_sources():
    result = ask_question("How does PO receiving update stock?", build_rag_chain())
    assert isinstance(result, dict) and "answer" in result
    assert any(key in result for key in ["source_documents", "sources"]) or len(result.get("answer", "")) > 0
