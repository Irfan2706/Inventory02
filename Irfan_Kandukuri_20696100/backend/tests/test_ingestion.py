from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("langchain_community.document_loaders")
pytest.importorskip("langchain.text_splitter")
pytest.importorskip("chromadb")

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

ROOT = Path(__file__).resolve().parents[1]
MANUAL_PATH = ROOT / "rag" / "inventory_manual.md"


def test_manual_loads():
    assert MANUAL_PATH.exists()
    docs = TextLoader(str(MANUAL_PATH), encoding="utf-8").load()
    assert len(docs) > 0 and len(docs[0].page_content) > 100


def test_chunks_size():
    docs = TextLoader(str(MANUAL_PATH), encoding="utf-8").load()
    chunks = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=50).split_documents(docs)
    for chunk in chunks:
        assert len(chunk.page_content) <= 600


def test_min_chunks():
    docs = TextLoader(str(MANUAL_PATH), encoding="utf-8").load()
    chunks = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=50).split_documents(docs)
    assert len(chunks) >= 20


def test_chromadb_collection():
    import chromadb

    client = chromadb.PersistentClient(path=str(ROOT / "chroma_db"))
    collections = [collection.name for collection in client.list_collections()]
    assert "inventory_manual" in collections
    assert client.get_collection("inventory_manual").count() >= 20
