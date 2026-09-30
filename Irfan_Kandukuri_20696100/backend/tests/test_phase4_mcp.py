from app.main import app
from mcp_server.mcp_app import mcp


def test_mcp_server_name():
    assert mcp.name == "Inventory Management Server"


def test_mcp_registers_all_tools():
    assert {"update_stock", "create_purchase_order", "get_low_stock_products", "get_supplier_catalog", "get_purchase_orders", "get_inventory_dashboard"}.issubset(set(mcp._tools))


def test_mcp_chat_route_exists():
    assert any(route.path == "/api/v1/mcp/chat" for route in app.routes)


def test_chat_request_has_required_message_field():
    from app.routers.mcp import MCPChatRequest
    assert MCPChatRequest(message="hello").session_id == "default"


def test_chat_response_contains_required_contract():
    from app.routers.mcp import MCPChatResponse
    response = MCPChatResponse(output="ok", session_id="x")
    assert response.output == "ok"
    assert response.session_id == "x"


def test_mcp_tools_are_callable():
    assert all(callable(tool) for tool in mcp._tools.values())


def test_server_starts():
    assert mcp is not None
    assert "Inventory" in mcp.name or "Management" in mcp.name


def test_6_tools():
    import mcp_server.mcp_app as app
    for name in ["update_stock", "create_purchase_order", "get_low_stock_products",
                 "get_supplier_catalog", "get_purchase_orders", "get_inventory_dashboard"]:
        assert hasattr(app, name), f"'{name}' not found"


def test_update_stock_official_contract():
    from unittest.mock import MagicMock, patch
    with patch("mcp_server.mcp_app.requests.post") as mocked_post:
        mocked_post.return_value.json.return_value = {"id": 1, "quantity": 100}
        mocked_post.return_value.raise_for_status = MagicMock()
        from mcp_server.mcp_app import update_stock
        result = update_stock(product_id=1, movement_type="receipt", quantity=100)
        assert isinstance(result, dict)
        mocked_post.assert_called_once()


def test_create_purchase_order_official_contract():
    from unittest.mock import MagicMock, patch
    with patch("mcp_server.mcp_app.requests.post") as mocked_post:
        mocked_post.return_value.json.return_value = {"po_number": "PO-2026-0001"}
        mocked_post.return_value.raise_for_status = MagicMock()
        from mcp_server.mcp_app import create_purchase_order
        result = create_purchase_order(1, "2026-06-18", [{"product_id": 1, "quantity_ordered": 100, "unit_cost": 280.0}])
        assert isinstance(result, dict)
        assert result.get("po_number") is not None


def test_get_low_stock_official_contract():
    from unittest.mock import MagicMock, patch
    with patch("mcp_server.mcp_app.requests.get") as mocked_get:
        mocked_get.return_value.json.return_value = [{"sku": "SKU-GRO-0001"}]
        mocked_get.return_value.raise_for_status = MagicMock()
        from mcp_server.mcp_app import get_low_stock_products
        assert isinstance(get_low_stock_products(), (list, dict))


def test_supplier_catalog_official_contract():
    from unittest.mock import MagicMock, patch
    with patch("mcp_server.mcp_app.requests.get") as mocked_get:
        mocked_get.return_value.json.return_value = [{"sku": "SKU-GRO-0001", "cost_price": 280.0}]
        mocked_get.return_value.raise_for_status = MagicMock()
        from mcp_server.mcp_app import get_supplier_catalog
        assert isinstance(get_supplier_catalog(1), (list, dict))


def test_inventory_dashboard_official_contract():
    from unittest.mock import MagicMock, patch
    with patch("mcp_server.mcp_app.requests.get") as mocked_get:
        mocked_get.return_value.json.return_value = {"total_products": 500, "low_stock_count": 25, "open_po_count": 8}
        mocked_get.return_value.raise_for_status = MagicMock()
        from mcp_server.mcp_app import get_inventory_dashboard
        result = get_inventory_dashboard()
        assert isinstance(result, dict)
        assert result.get("total_products") == 500


def test_api_unavailable_error_official_contract():
    import requests as req
    from unittest.mock import patch
    with patch("mcp_server.mcp_app.requests.get", side_effect=req.exceptions.ConnectionError("refused")):
        from mcp_server.mcp_app import get_inventory_dashboard
        result = get_inventory_dashboard()
        assert isinstance(result, dict) and "error" in result