"""RAG support package for Phase 2 inventory assistance."""

from .ingest import ensure_inventory_collection
from .rag_chain import ask_question, build_rag_chain


def bootstrap_inventory_collection() -> None:
	try:
		ensure_inventory_collection()
	except Exception:
		# Import-time bootstrap should never break the application if optional dependencies are absent.
		return


bootstrap_inventory_collection()

__all__ = ["ask_question", "build_rag_chain", "bootstrap_inventory_collection"]
