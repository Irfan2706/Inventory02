from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

import requests

try:
    from langchain_community.vectorstores import Chroma
except ImportError:  # pragma: no cover - dependency is optional at import time
    Chroma = None

try:
    import chromadb
except ImportError:  # pragma: no cover - dependency is optional at import time
    chromadb = None

try:
    from langchain_ollama import OllamaEmbeddings
except ImportError:  # pragma: no cover - dependency is optional at import time
    OllamaEmbeddings = None

DEFAULT_COLLECTION_NAME = "inventory_manual"
DEFAULT_PERSIST_DIRECTORY = Path(__file__).resolve().parents[1] / "chroma_db"
DEFAULT_MANUAL_PATH = Path(__file__).resolve().parent / "inventory_manual.md"
DEFAULT_CHUNK_SIZE = 600
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_EMBED_MODEL = "nomic-embed-text"
PREFERRED_EMBEDDING_MODELS = ["nomic-embed-text", "mxbai-embed-large"]
_EMBED_PROBE_TEXT = "inventory embedding probe"


class LocalHashEmbeddings:
    def __init__(self, dimensions: int = 16):
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        for index in range(self.dimensions):
            value = digest[index] / 255.0
            vector[index] = round(value, 6)
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


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
            print("Ollama embeddings unavailable. Start server with --embeddings and run: ollama pull nomic-embed-text")
            return self._fallback.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        try:
            return self._ollama.embed_query(text)
        except Exception:
            print("Ollama embeddings unavailable. Start server with --embeddings and run: ollama pull nomic-embed-text")
            return self._fallback.embed_query(text)


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

    # Legacy endpoint fallback for older Ollama APIs.
    payload = {"model": model_name, "prompt": _EMBED_PROBE_TEXT}
    try:
        response = requests.post(f"{base_url}/api/embeddings", json=payload, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


def load_inventory_manual(manual_path: str | Path | None = None) -> str:
    path = Path(manual_path) if manual_path is not None else DEFAULT_MANUAL_PATH
    return path.read_text(encoding="utf-8")


def _split_long_block(block: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    block = block.strip()
    while start < len(block):
        end = min(len(block), start + chunk_size)
        chunk = block[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(block):
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks


def chunk_markdown_document(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", cleaned) if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if current:
            candidate = f"{current}\n\n{paragraph}"
        else:
            candidate = paragraph

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())
            current = ""

        if len(paragraph) <= chunk_size:
            current = paragraph
            continue

        chunks.extend(_split_long_block(paragraph, chunk_size=chunk_size, chunk_overlap=chunk_overlap))

    if current:
        chunks.append(current.strip())

    return [chunk for chunk in chunks if chunk]


def build_chunk_documents(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[dict[str, object]]:
    chunks = chunk_markdown_document(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return [
        {
            "page_content": chunk,
            "metadata": {
                "source": DEFAULT_MANUAL_PATH.name,
                "chunk_index": index + 1,
                "collection": DEFAULT_COLLECTION_NAME,
            },
        }
        for index, chunk in enumerate(chunks)
    ]


def _build_embeddings():
    if OllamaEmbeddings is None:
        return LocalHashEmbeddings()

    base_url = _get_ollama_base_url()
    configured_model = os.getenv("OLLAMA_EMBED_MODEL", DEFAULT_OLLAMA_EMBED_MODEL).strip()
    models = _list_ollama_models(base_url)

    selected_model = configured_model if configured_model else _choose_embedding_model(models)
    installed = {name.lower() for name in models}
    if selected_model and selected_model.lower() not in installed:
        print(
            f"Configured embedding model '{selected_model}' not installed. "
            "Falling back to local deterministic embeddings."
        )
        return LocalHashEmbeddings()

    if selected_model is None:
        print("No compatible Ollama embedding model detected. Falling back to local deterministic embeddings.")
        return LocalHashEmbeddings()

    if not _model_supports_embeddings(base_url, selected_model):
        print(
            f"Configured embedding model '{selected_model}' does not support embeddings in this environment. "
            "Falling back to local deterministic embeddings."
        )
        return LocalHashEmbeddings()

    try:
        return ResilientOllamaEmbeddings(model=selected_model, base_url=base_url)
    except Exception:
        print("Failed to initialize OllamaEmbeddings. Falling back to local deterministic embeddings.")
        return LocalHashEmbeddings()


def ingest_inventory_manual(
    manual_path: str | Path | None = None,
    persist_directory: str | Path = DEFAULT_PERSIST_DIRECTORY,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    reset_collection: bool = True,
) -> dict[str, object]:
    if Chroma is None:
        raise RuntimeError("langchain-community is required to ingest the inventory manual.")

    manual_text = load_inventory_manual(manual_path)
    documents = build_chunk_documents(manual_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    embeddings = _build_embeddings()

    if reset_collection and chromadb is not None:
        client = chromadb.PersistentClient(path=str(persist_directory))
        collection_names = {collection.name for collection in client.list_collections()}
        if collection_name in collection_names:
            client.delete_collection(collection_name)

    vectorstore = Chroma.from_texts(
        texts=[item["page_content"] for item in documents],
        embedding=embeddings,
        metadatas=[item["metadata"] for item in documents],
        collection_name=collection_name,
        persist_directory=str(persist_directory),
    )

    if hasattr(vectorstore, "persist"):
        vectorstore.persist()

    return {
        "collection_name": collection_name,
        "chunk_count": len(documents),
        "persist_directory": str(persist_directory),
    }


def ensure_inventory_collection(
    manual_path: str | Path | None = None,
    persist_directory: str | Path = DEFAULT_PERSIST_DIRECTORY,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> dict[str, object] | None:
    if Chroma is None or chromadb is None:
        return None

    persist_path = Path(persist_directory)
    persist_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_path))
    existing = client.get_collection(collection_name) if collection_name in [c.name for c in client.list_collections()] else None
    if existing is not None and existing.count() >= 20:  # pragma: no cover - depends on runtime data
        return {
            "collection_name": collection_name,
            "chunk_count": existing.count(),
            "persist_directory": str(persist_path),
        }

    return ingest_inventory_manual(
        manual_path=manual_path,
        persist_directory=persist_path,
        collection_name=collection_name,
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        reset_collection=True,
    )
