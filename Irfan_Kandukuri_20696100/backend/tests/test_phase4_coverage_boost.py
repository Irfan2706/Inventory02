"""Targeted tests closing Phase 4 coverage gaps in mcp_tools, mcp_app, and chat_interface."""
from unittest.mock import MagicMock, patch

import pytest

from mcp_server import mcp_tools
from mcp_server.chat_interface import (
    _coerce_numeric_updates,
    _enrich_low_stock_item,
    _reference_products,
    _resolve_supplier_choice,
    discover_local_model,
    process_message,
)


class Response:
    def __init__(self, payload=None, status=200):
        self._payload = payload if payload is not None else {}
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


# ---------------------------------------------------------------------------
# mcp_tools: direct coverage of the new Phase 4 tool functions
# ---------------------------------------------------------------------------

def test_list_suppliers_calls_suppliers_endpoint(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *a, **k: calls.append(a) or Response([{"id": 1}]))
    assert mcp_tools.list_suppliers() == [{"id": 1}]
    assert calls[0][0] == "GET"


def test_list_products_with_and_without_category(monkeypatch):
    captured = []
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *a, **k: captured.append(k.get("params")) or Response([{"id": 1}]))
    mcp_tools.list_products()
    mcp_tools.list_products(category="grocery")
    assert captured[0] == {}
    assert captured[1] == {"category": "grocery"}


def test_update_product_patches_product_endpoint(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *a, **k: calls.append(a) or Response({"id": 7}))
    result = mcp_tools.update_product(7, {"unit_price": 99})
    assert result == {"id": 7}
    assert calls[0][0] == "PATCH"


def test_delete_product_calls_delete_endpoint(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *a, **k: calls.append(a) or Response({"message": "deleted"}))
    result = mcp_tools.delete_product(9)
    assert result == {"message": "deleted"}
    assert calls[0][0] == "DELETE"


def test_update_supplier_patches_supplier_endpoint(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *a, **k: calls.append(a) or Response({"id": 3}))
    result = mcp_tools.update_supplier(3, {"is_active": False})
    assert result == {"id": 3}
    assert calls[0][0] == "PATCH"


def test_generate_inventory_report_combines_dashboard_and_alerts(monkeypatch):
    responses = iter([Response({"total_products": 5}), Response([{"id": 1}])])
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *a, **k: next(responses))
    report = mcp_tools.generate_inventory_report()
    assert report == {"dashboard": {"total_products": 5}, "low_stock_alerts": [{"id": 1}]}


# ---------------------------------------------------------------------------
# mcp_app: wrapper functions for the new Phase 4 tools
# ---------------------------------------------------------------------------

def test_mcp_app_list_suppliers_wrapper():
    with patch("mcp_server.mcp_app.requests.get") as mocked_get:
        mocked_get.return_value = Response([{"id": 1}])
        from mcp_server.mcp_app import list_suppliers
        assert list_suppliers() == [{"id": 1}]


def test_mcp_app_list_products_wrapper():
    with patch("mcp_server.mcp_app.requests.get") as mocked_get:
        mocked_get.return_value = Response([{"id": 2}])
        from mcp_server.mcp_app import list_products
        assert list_products(category="grocery") == [{"id": 2}]


def test_mcp_app_update_product_wrapper():
    with patch("mcp_server.mcp_tools._request") as mocked_request:
        mocked_request.return_value = {"id": 4}
        from mcp_server.mcp_app import update_product
        assert update_product(4, {"unit_price": 10}) == {"id": 4}


def test_mcp_app_delete_product_wrapper():
    with patch("mcp_server.mcp_tools._request") as mocked_request:
        mocked_request.return_value = {"message": "ok"}
        from mcp_server.mcp_app import delete_product
        assert delete_product(4) == {"message": "ok"}


def test_mcp_app_update_supplier_wrapper():
    with patch("mcp_server.mcp_tools._request") as mocked_request:
        mocked_request.return_value = {"id": 8}
        from mcp_server.mcp_app import update_supplier
        assert update_supplier(8, {"is_active": True}) == {"id": 8}


def test_mcp_app_generate_inventory_report_wrapper():
    with patch("mcp_server.mcp_tools._request") as mocked_request:
        mocked_request.return_value = {"ok": True}
        from mcp_server.mcp_app import generate_inventory_report
        assert generate_inventory_report() == {"dashboard": {"ok": True}, "low_stock_alerts": {"ok": True}}


def test_mcp_app_get_purchase_orders_wrapper():
    with patch("mcp_server.mcp_app.requests.get") as mocked_get:
        mocked_get.return_value = Response([{"id": 1}])
        from mcp_server.mcp_app import get_purchase_orders
        assert get_purchase_orders() == [{"id": 1}]


def test_mcp_app_create_product_wrapper():
    with patch("mcp_server.mcp_tools._request") as mocked_request:
        mocked_request.return_value = {"id": 1}
        from mcp_server.mcp_app import create_product
        assert create_product({"name": "X"}) == {"id": 1}


def test_mcp_app_create_supplier_wrapper():
    with patch("mcp_server.mcp_tools._request") as mocked_request:
        mocked_request.return_value = {"id": 1}
        from mcp_server.mcp_app import create_supplier
        assert create_supplier({"name": "X"}) == {"id": 1}


def test_mcp_app_receive_purchase_order_wrapper():
    with patch("mcp_server.mcp_tools._request") as mocked_request:
        mocked_request.return_value = {"status": "received"}
        from mcp_server.mcp_app import receive_purchase_order
        assert receive_purchase_order(3) == {"status": "received"}


def test_mcp_tools_get_and_post_wrappers(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *a, **k: calls.append(a[0]) or Response({"ok": True}))
    assert mcp_tools._get("/products") == {"ok": True}
    assert mcp_tools._post("/products", {"name": "X"}) == {"ok": True}
    assert calls == ["GET", "POST"]


def test_fastmcp_compat_run_raises_when_transport_missing():
    from mcp_server.mcp_app import FastMCP
    compat = FastMCP("test")
    with pytest.raises(RuntimeError):
        compat.run()


def test_fastmcp_compat_tool_decorator_registers_function():
    from mcp_server.mcp_app import FastMCP
    compat = FastMCP("test")

    @compat.tool()
    def sample():
        return "ok"

    assert compat._tools["sample"] is sample


# ---------------------------------------------------------------------------
# chat_interface: helper functions
# ---------------------------------------------------------------------------

def test_discover_local_model_returns_first_model_name(monkeypatch):
    monkeypatch.setattr(
        "mcp_server.chat_interface.requests.get",
        lambda *a, **k: Response({"models": [{"name": "llama3"}]}),
    )
    assert discover_local_model() == "llama3"


def test_discover_local_model_returns_none_when_no_models(monkeypatch):
    monkeypatch.setattr("mcp_server.chat_interface.requests.get", lambda *a, **k: Response({"models": []}))
    assert discover_local_model() is None


def test_coerce_numeric_updates_handles_is_active_and_strings():
    result = _coerce_numeric_updates({"is_active": "false", "name": "Acme"}, {"lead_time_days"})
    assert result == {"is_active": False, "name": "Acme"}


def test_resolve_supplier_choice_matches_by_name():
    options = {"1": "Acme Corp", "2": "Beta Foods"}
    assert _resolve_supplier_choice("please use Beta Foods", options) == 2


def test_resolve_supplier_choice_returns_none_when_no_match():
    options = {"1": "Acme Corp"}
    assert _resolve_supplier_choice("nonexistent", options) is None


def test_reference_products_returns_empty_without_category():
    assert _reference_products(None) == []


def test_reference_products_returns_empty_when_not_a_list(monkeypatch):
    monkeypatch.setattr(mcp_tools, "list_products", lambda category=None: {"error": "boom"})
    assert _reference_products("grocery") == []


def test_enrich_low_stock_item_returns_as_is_when_complete():
    item = {"supplier_id": 1, "cost_price": 1.0, "reorder_quantity": 5, "id": 1}
    assert _enrich_low_stock_item(item) == item


def test_enrich_low_stock_item_returns_none_without_product_id():
    assert _enrich_low_stock_item({}) is None


def test_enrich_low_stock_item_returns_none_when_detail_lookup_fails(monkeypatch):
    monkeypatch.setattr(mcp_tools, "_get", lambda path: {"error": "not found"})
    assert _enrich_low_stock_item({"id": 42}) is None


def test_enrich_low_stock_item_fills_missing_fields_from_detail(monkeypatch):
    monkeypatch.setattr(
        mcp_tools,
        "_get",
        lambda path: {"id": 42, "supplier_id": 7, "cost_price": 12.5, "reorder_quantity": 20},
    )
    enriched = _enrich_low_stock_item({"id": 42})
    assert enriched == {"id": 42, "supplier_id": 7, "cost_price": 12.5, "reorder_quantity": 20}


# ---------------------------------------------------------------------------
# chat_interface: end-to-end conversation flows through process_message
# ---------------------------------------------------------------------------

def test_multiple_suppliers_choice_by_name(monkeypatch):
    monkeypatch.setattr(
        mcp_tools,
        "list_suppliers",
        lambda: [{"id": 1, "name": "Acme", "is_active": True}, {"id": 2, "name": "Beta Foods", "is_active": True}],
    )
    monkeypatch.setattr(mcp_tools, "list_products", lambda category=None: [])
    calls = []
    monkeypatch.setattr(mcp_tools, "create_product", lambda payload: calls.append(payload) or {"id": 9, **payload})
    session_id = "supplier-choice-by-name"
    process_message("Create a grocery product called Basmati Rice", session_id)
    result = process_message("Beta Foods please", session_id)
    assert result["tools_used"] == ["create_product"]
    assert calls[0]["supplier_id"] == 2


def test_multiple_suppliers_invalid_choice_asks_again(monkeypatch):
    monkeypatch.setattr(
        mcp_tools,
        "list_suppliers",
        lambda: [{"id": 1, "name": "Acme", "is_active": True}, {"id": 2, "name": "Beta Foods", "is_active": True}],
    )
    monkeypatch.setattr(mcp_tools, "list_products", lambda category=None: [])
    session_id = "supplier-choice-invalid"
    process_message("Create a grocery product called Basmati Rice", session_id)
    result = process_message("nonexistent supplier", session_id)
    assert "choose one of the listed supplier ids" in result["output"]


def test_low_stock_po_confirmation_declined(monkeypatch):
    monkeypatch.setattr(
        mcp_tools,
        "get_low_stock_products",
        lambda: [{"id": 2, "supplier_id": 9, "reorder_quantity": 10, "cost_price": 3.5}],
    )
    session_id = "ops-po-decline"
    process_message("Create PO for those items", session_id)
    result = process_message("no", session_id)
    assert "did not create" in result["output"].lower()


def test_create_po_for_them_wording_triggers_confirmation(monkeypatch):
    monkeypatch.setattr(
        mcp_tools,
        "get_low_stock_products",
        lambda: [{"id": 2, "supplier_id": 9, "reorder_quantity": 10, "cost_price": 3.5}],
    )
    result = process_message("Create PO for them", "ops-po-them")
    assert result["tools_used"] == ["get_low_stock_products"]


def test_policy_question_routes_to_policy_search(monkeypatch):
    monkeypatch.setattr(
        "mcp_server.chat_interface.search_inventory_policy.func",
        lambda question: "Policy answer",
    )
    result = process_message("What does the approval procedure mean?", "policy-question")
    assert result["tools_used"] == ["search_inventory_policy"]
    assert result["output"] == "Policy answer"


def test_get_purchase_orders_route(monkeypatch):
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *a, **k: Response([{"id": 1}]))
    result = process_message("Show all purchase orders", "po-list")
    assert result["tools_used"] == ["get_purchase_orders"]


def test_get_supplier_catalog_route(monkeypatch):
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *a, **k: Response([{"sku": "A"}]))
    result = process_message("Show supplier 4 catalog", "supplier-catalog")
    assert result["tools_used"] == ["get_supplier_catalog"]


def test_receive_po_without_id_asks_for_it():
    result = process_message("Receive the purchase order", "receive-no-id")
    assert "which purchase order" in result["output"].lower()


def test_update_stock_without_product_id_asks():
    result = process_message("update stock please", "stock-no-id")
    assert "which product id" in result["output"].lower()


def test_update_product_without_id_asks():
    result = process_message("update the product please", "update-product-no-id")
    assert "which product id" in result["output"].lower()


def test_update_product_without_fields_asks():
    result = process_message("update product 4", "update-product-no-fields")
    assert "what field and value" in result["output"].lower()


def test_update_supplier_without_id_asks():
    result = process_message("update the supplier please", "update-supplier-no-id")
    assert "which supplier id" in result["output"].lower()


def test_update_supplier_without_fields_asks():
    result = process_message("update supplier 4", "update-supplier-no-fields")
    assert "what field and value" in result["output"].lower()


def test_delete_product_without_id_asks():
    result = process_message("delete the product please", "delete-product-no-id")
    assert "which product id" in result["output"].lower()


def test_create_supplier_missing_name_asks(monkeypatch):
    result = process_message("Create supplier", "create-supplier-missing-name")
    assert "please provide" in result["output"].lower()


def test_process_message_handles_executor_exception(monkeypatch):
    def boom(*args, **kwargs):
        raise ValueError("kaboom")

    monkeypatch.setattr("mcp_server.chat_interface.build_chat_executor", lambda: type("E", (), {"invoke": staticmethod(boom)})())
    result = process_message("Show dashboard", "process-message-error")
    assert "Error: kaboom" in result["output"]
