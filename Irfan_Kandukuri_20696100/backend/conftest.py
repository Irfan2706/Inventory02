from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def bootstrap_rag_collection():
    try:
        from rag import bootstrap_inventory_collection
    except Exception:
        return

    bootstrap_inventory_collection()
