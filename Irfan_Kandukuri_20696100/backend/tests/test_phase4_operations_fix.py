"""Regression tests for the reported MCP Chat Mode bug: action requests routed to read-only tools."""
from mcp_server import mcp_tools
from mcp_server.chat_interface import process_message


def test_reported_bug_creates_product_instead_of_dashboard(monkeypatch):
    """'Create a grocery product called Basmati Rice' must invoke create_product, not the dashboard."""
    monkeypatch.setattr(mcp_tools, "list_suppliers", lambda: [{"id": 3, "name": "Fresh Farms", "is_active": True}])
    monkeypatch.setattr(mcp_tools, "list_products", lambda category=None: [])
    calls = []
    monkeypatch.setattr(mcp_tools, "create_product", lambda payload: calls.append(payload) or {"id": 1, **payload})
    monkeypatch.setattr(mcp_tools, "get_inventory_dashboard", lambda: {"total_products": 999})

    result = process_message("Create a grocery product called Basmati Rice", "bug-report-product")

    assert result["tools_used"] == ["create_product"]
    assert calls, "create_product tool was never invoked"
    assert calls[0]["name"] == "Basmati Rice"
    assert calls[0]["category"] == "grocery"
    assert calls[0]["unit_of_measure"] == "kg"
    assert calls[0]["supplier_id"] == 3
    assert calls[0]["cost_price"] == 50.0
    assert calls[0]["unit_price"] == 70.0
    assert "total_products" not in result["output"]
    assert "auto-estimated" in result["output"]
    assert "auto-selected" in result["output"]


def test_create_product_uses_same_category_reference_pricing(monkeypatch):
    monkeypatch.setattr(mcp_tools, "list_suppliers", lambda: [])
    monkeypatch.setattr(
        mcp_tools,
        "list_products",
        lambda category=None: [
            {"cost_price": 40.0, "unit_price": 60.0, "reorder_point": 8, "reorder_quantity": 40},
            {"cost_price": 60.0, "unit_price": 80.0, "reorder_point": 12, "reorder_quantity": 60},
        ],
    )
    calls = []
    monkeypatch.setattr(mcp_tools, "create_product", lambda payload: calls.append(payload) or {"id": 2, **payload})

    process_message("Create a grocery product called Basmati Rice", "reference-pricing")

    assert calls[0]["cost_price"] == 50.0
    assert calls[0]["unit_price"] == 70.0
    assert calls[0]["reorder_point"] == 10
    assert calls[0]["reorder_quantity"] == 50


def test_create_product_asks_when_multiple_active_suppliers(monkeypatch):
    monkeypatch.setattr(
        mcp_tools,
        "list_suppliers",
        lambda: [
            {"id": 1, "name": "Acme", "is_active": True},
            {"id": 2, "name": "Beta Foods", "is_active": True},
        ],
    )
    monkeypatch.setattr(mcp_tools, "list_products", lambda category=None: [])
    calls = []
    monkeypatch.setattr(mcp_tools, "create_product", lambda payload: calls.append(payload) or {"id": 5, **payload})

    session_id = "supplier-choice"
    ask = process_message("Create a grocery product called Basmati Rice", session_id)
    assert "Beta Foods" in ask["output"]

    result = process_message("2", session_id)
    assert result["tools_used"] == ["create_product"]
    assert calls[0]["supplier_id"] == 2


def test_add_stock_for_product_asks_for_quantity_instead_of_guessing(monkeypatch):
    calls = []
    monkeypatch.setattr(
        mcp_tools,
        "update_stock",
        lambda product_id, movement_type, quantity: calls.append((product_id, movement_type, quantity)) or {"id": 1},
    )
    session_id = "stock-single-number"
    ask = process_message("Add stock for product 1", session_id)
    assert "how many units" in ask["output"].lower()
    assert not calls

    result = process_message("25", session_id)
    assert result["tools_used"] == ["update_stock"]
    assert calls[0] == (1, "receipt", 25)


def test_delete_product_routes_to_delete_tool(monkeypatch):
    monkeypatch.setattr(mcp_tools, "delete_product", lambda product_id: {"message": "Product deleted", "product_id": product_id})
    result = process_message("Delete product 5", "delete-product")
    assert result["tools_used"] == ["delete_product"]


def test_update_product_routes_to_update_tool(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools, "update_product", lambda product_id, payload: calls.append((product_id, payload)) or {"id": product_id, **payload})
    result = process_message("Update product 5 unit_price to 150", "update-product")
    assert result["tools_used"] == ["update_product"]
    assert calls[0] == (5, {"unit_price": 150})


def test_update_supplier_routes_to_update_tool(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools, "update_supplier", lambda supplier_id, payload: calls.append((supplier_id, payload)) or {"id": supplier_id, **payload})
    result = process_message("Update supplier 3 lead_time_days to 10", "update-supplier")
    assert result["tools_used"] == ["update_supplier"]
    assert calls[0] == (3, {"lead_time_days": 10})


def test_generate_report_routes_to_report_tool(monkeypatch):
    monkeypatch.setattr(mcp_tools, "generate_inventory_report", lambda: {"dashboard": {"total_products": 4}, "low_stock_alerts": []})
    result = process_message("Generate an inventory report", "generate-report")
    assert result["tools_used"] == ["generate_inventory_report"]


def test_create_po_for_low_stock_items_generates_po_immediately(monkeypatch):
    monkeypatch.setattr(
        mcp_tools,
        "get_low_stock_products",
        lambda: [{"id": 2, "supplier_id": 9, "reorder_quantity": 10, "cost_price": 3.5}],
    )
    calls = []
    monkeypatch.setattr(
        mcp_tools,
        "create_purchase_order",
        lambda supplier_id, order_date, items: calls.append((supplier_id, items)) or {"po_number": "PO-2026-0099", "supplier_id": supplier_id},
    )
    result = process_message("Create PO for low stock items", "low-stock-po")
    assert result["tools_used"] == ["create_purchase_order"]
    assert calls[0][0] == 9
    assert "PO-2026-0099" in result["output"]


def test_create_supplier_still_works_with_descriptive_wording(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools, "create_supplier", lambda payload: calls.append(payload) or {"id": 1, **payload})
    result = process_message("Create a new supplier called ABC Suppliers", "supplier-descriptive")
    assert calls and calls[0]["name"] == "ABC Suppliers"
    assert calls[0]["lead_time_days"] == 7
    assert calls[0]["payment_terms_days"] == 30
    assert result["tools_used"] == ["create_supplier"]
