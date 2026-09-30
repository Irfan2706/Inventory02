from mcp_server import mcp_tools
from mcp_server.chat_interface import process_message, sessions


def test_create_product_through_chat(monkeypatch):
    monkeypatch.setattr(mcp_tools, "list_suppliers", lambda: [])
    monkeypatch.setattr(mcp_tools, "list_products", lambda category=None: [])
    calls = []
    monkeypatch.setattr(mcp_tools, "create_product", lambda payload: calls.append(payload) or {"id": 1, **payload})
    session_id = "ops-product"
    process_message("Create a product", session_id)
    process_message("Basmati Rice", session_id)
    result = process_message("grocery", session_id)
    assert calls and calls[0]["name"] == "Basmati Rice"
    assert calls[0]["category"] == "grocery"
    assert calls[0]["unit_of_measure"] == "kg"
    assert result["tools_used"] == ["create_product"]


def test_create_supplier_through_chat(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools, "create_supplier", lambda payload: calls.append(payload) or {"id": 1, **payload})
    session_id = "ops-supplier"
    process_message("Create supplier", session_id)
    result = process_message("ABC Ltd", session_id)
    assert calls and calls[0]["name"] == "ABC Ltd"
    assert calls[0]["lead_time_days"] == 7
    assert calls[0]["payment_terms_days"] == 30
    assert result["tools_used"] == ["create_supplier"]


def test_supplier_one_shot_with_labeled_details(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools, "create_supplier", lambda payload: calls.append(payload) or {"id": 1, **payload})
    result = process_message("Create supplier ABC Suppliers lead time 7 payment terms 30", "ops-supplier-labeled")
    assert calls and calls[0]["name"] == "ABC Suppliers"
    assert calls[0]["lead_time_days"] == 7
    assert calls[0]["payment_terms_days"] == 30
    assert result["tools_used"] == ["create_supplier"]


def test_reported_supplier_flow_creates_one_shot(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools, "create_supplier", lambda payload: calls.append(payload) or {"id": 1, **payload})
    session_id = "reported-supplier-flow"
    result = process_message("Create supplier ABC Suppliers", session_id)
    assert result["tools_used"] == ["create_supplier"]
    assert calls[0]["name"] == "ABC Suppliers"
    assert calls[0]["lead_time_days"] == 7
    assert calls[0]["payment_terms_days"] == 30


def test_update_stock_through_chat(monkeypatch):
    monkeypatch.setattr(mcp_tools, "update_stock", lambda product_id, movement_type, quantity: {"id": 4, "product_id": product_id, "movement_type": movement_type, "quantity": quantity})
    result = process_message("Update stock for product 12 by 50", "ops-stock")
    assert result["tools_used"] == ["update_stock"]


def test_receive_purchase_order_through_chat(monkeypatch):
    monkeypatch.setattr(mcp_tools, "receive_purchase_order", lambda order_id: {"id": order_id, "status": "received"})
    result = process_message("Mark PO 4 as received", "ops-receive")
    assert result["tools_used"] == ["receive_purchase_order"]


def test_low_stock_po_confirmation_uses_context(monkeypatch):
    monkeypatch.setattr(mcp_tools, "get_low_stock_products", lambda: [{"id": 2, "supplier_id": 9, "reorder_quantity": 10, "cost_price": 3.5}])
    monkeypatch.setattr(mcp_tools, "create_purchase_order", lambda supplier_id, order_date, items: {"id": 8, "supplier_id": supplier_id, "items": items})
    session_id = "ops-po"
    process_message("Show low stock products", session_id)
    process_message("Create PO for those items", session_id)
    result = process_message("yes", session_id)
    assert result["tools_used"] == ["create_purchase_order"]


def test_dashboard_still_routes_through_chat(monkeypatch):
    monkeypatch.setattr(mcp_tools, "_get", lambda path, params=None: {"total_products": 10})
    result = process_message("Show dashboard", "ops-dashboard")
    assert result["tools_used"] == ["get_inventory_dashboard"]


def test_session_history_endpoint_rehydrates_existing_session():
    from app.routers.mcp import session_history
    session_id = "rehydrate-session"
    process_message("Show dashboard", session_id)
    response = session_history(session_id)
    assert response.session_id == session_id
    assert len(response.history) == 2
    assert response.history[0]["role"] == "user"