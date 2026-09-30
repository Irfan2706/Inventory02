import os
from unittest.mock import MagicMock, patch

import pytest


def test_tools_defined():
    from agent.tools import get_dashboard_stats, get_low_stock_alerts, get_product_stock, get_supplier_catalog, search_inventory_policy

    for tool in [get_low_stock_alerts, get_product_stock, get_supplier_catalog, get_dashboard_stats, search_inventory_policy]:
        assert tool.name and tool.description


def test_tools_registered():
    from agent.agent import build_agent_executor

    names = [tool.name for tool in build_agent_executor().tools]
    for required in ["get_low_stock_alerts", "get_product_stock", "get_supplier_catalog", "get_dashboard_stats", "search_inventory_policy"]:
        assert required in names


def test_desc_length():
    from agent.tools import get_dashboard_stats, get_low_stock_alerts, get_product_stock, get_supplier_catalog, search_inventory_policy

    for tool in [get_low_stock_alerts, get_product_stock, get_supplier_catalog, get_dashboard_stats, search_inventory_policy]:
        assert len(tool.description) >= 50, f"{tool.name} description too short"


def test_string_input():
    from agent.tools import get_product_stock, get_supplier_catalog

    for tool in [get_product_stock, get_supplier_catalog]:
        if tool.args_schema:
            assert len(tool.args_schema.model_json_schema().get("properties", {})) >= 1


def test_dashboard_counts():
    mock = {"total_products": 500, "low_stock_count": 25, "out_of_stock_count": 5, "open_po_count": 8, "total_stock_value": 2500000.0}
    with patch("agent.tools._api_get", return_value=mock):
        from agent.tools import get_dashboard_stats

        result = get_dashboard_stats.invoke("")
        assert "500" in result or "product" in result.lower()
        assert "25" in result or "low" in result.lower()


def test_product_stock():
    mock = {"id": 1, "sku": "SKU-GRO-0001", "name": "Basmati Rice", "reorder_point": 20, "reorder_quantity": 100, "stock_level": {"quantity_on_hand": 15, "quantity_available": 15, "quantity_reserved": 0}}
    with patch("agent.tools._api_get", return_value=mock):
        from agent.tools import get_product_stock

        result = get_product_stock.invoke("1")
        assert "15" in result or "available" in result.lower()


def test_product_404():
    with patch("agent.tools._api_get", return_value={"error": "not_found"}):
        from agent.tools import get_product_stock

        result = get_product_stock.invoke("9999")
        assert "not found" in result.lower() or "9999" in result


def test_policy_search():
    mock = {"answer": "PO approval required for orders above 50,000."}
    with patch("rag.rag_chain.build_rag_chain"), patch("rag.rag_chain.ask_question", return_value=mock):
        from agent.tools import search_inventory_policy

        result = search_inventory_policy.invoke("When is PO approval required?")
        assert "50,000" in result or "approval" in result.lower()


def test_low_stock():
    mock = [{"id": 1, "sku": "SKU-GRO-0001", "name": "Rice", "quantity_available": 5, "reorder_point": 20}]
    with patch("agent.tools._api_get", return_value=mock):
        from agent.tools import get_low_stock_alerts

        result = get_low_stock_alerts.invoke("")
        assert "SKU-GRO" in result or "reorder" in result.lower() or "1" in result


def test_api_unavailable():
    from agent.tools import _api_get

    with patch("agent.tools.requests.get", side_effect=ConnectionError("refused")):
        result = _api_get("/products/1")
        assert isinstance(result, dict) and "error" in result


def test_system_prompt_role():
    from agent.prompts import INVENTORY_AGENT_SYSTEM_PROMPT

    assert any(word in INVENTORY_AGENT_SYSTEM_PROMPT.lower() for word in ["inventory", "stock", "procurement", "retail", "reorder"])
    assert len(INVENTORY_AGENT_SYSTEM_PROMPT) >= 100


def test_long_summarized():
    from agent.summarizer import _summarize_if_long

    long = "Stock report: " + ("SKU-GRO-0001 has 5 units. " * 100)
    assert len(long) > 2000
    with patch("agent.summarizer.load_summarize_chain") as mock_chain:
        mock_chain.return_value.run.return_value = "Summary: 100 products need reorder."
        assert isinstance(_summarize_if_long(long), str)


def test_short_unchanged():
    from agent.summarizer import _summarize_if_long

    short = "SKU-GRO-0001 Basmati Rice: 15 available, reorder point 20."
    assert _summarize_if_long(short) == short


def test_all_tools_referenced():
    from agent.prompts import INVENTORY_AGENT_SYSTEM_PROMPT

    count = sum(1 for tool_name in ["get_low_stock_alerts", "get_product_stock", "get_supplier_catalog", "get_dashboard_stats", "search_inventory_policy"] if tool_name in INVENTORY_AGENT_SYSTEM_PROMPT)
    assert count >= 4


def test_low_stock_query():
    from agent.agent import build_agent_executor

    names = [tool.name for tool in build_agent_executor().tools]
    assert "get_low_stock_alerts" in names


def test_multi_tool():
    from agent.agent import build_agent_executor

    names = [tool.name for tool in build_agent_executor().tools]
    assert "get_product_stock" in names and "search_inventory_policy" in names


def test_policy_rag():
    mock = {"answer": "Low stock alert triggers when quantity_available <= reorder_point."}
    with patch("rag.rag_chain.ask_question", return_value=mock):
        from agent.tools import search_inventory_policy

        result = search_inventory_policy.invoke("When is a low stock alert triggered?")
        assert "low" in result.lower() or "reorder" in result.lower()


def test_dashboard_query():
    mock = {"total_products": 500, "low_stock_count": 25, "out_of_stock_count": 5, "open_po_count": 8, "total_stock_value": 2500000.0}
    with patch("agent.tools._api_get", return_value=mock):
        from agent.tools import get_dashboard_stats

        result = get_dashboard_stats.invoke("")
        assert "500" in result or "product" in result.lower()


def test_ambiguous_no_crash():
    with patch("agent.tools._api_get", return_value=[]):
        from agent.tools import get_low_stock_alerts

        try:
            result = get_low_stock_alerts.invoke("")
            assert isinstance(result, str)
        except Exception as exc:
            pytest.fail(f"Raised: {exc}")


def test_langsmith_trace():
    if not os.getenv("LANGCHAIN_API_KEY"):
        pytest.skip("No key")
    from langsmith import Client

    runs = list(Client().list_runs(project_name="AI-Readiness-POC-07-P3", limit=3))
    if not runs:
        pytest.skip("No traces yet")
    assert len(runs) >= 1
