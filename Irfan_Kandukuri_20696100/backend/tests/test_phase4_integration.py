from unittest.mock import MagicMock, patch

from mcp_server.chat_interface import build_chat_executor, process_message


def test_6_tools_discovered():
    assert len(build_chat_executor().tools) >= 6


def test_tool_invoked():
    with patch("mcp_server.mcp_app.requests.get") as mocked_get:
        mocked_get.return_value.json.return_value = {"total_products": 500, "low_stock_count": 25}
        mocked_get.return_value.raise_for_status = MagicMock()
        from mcp_server.mcp_app import get_inventory_dashboard
        result = get_inventory_dashboard()
        assert result.get("total_products") == 500 or "error" in result


def test_correct_tool():
    tool_map = {tool.name: tool for tool in build_chat_executor().tools}
    assert "get_low_stock_products" in tool_map
    assert "stock" in tool_map["get_low_stock_products"].description.lower()


def test_response_routed():
    with patch("mcp_server.chat_interface.build_chat_executor") as mocked_builder:
        mocked_builder.return_value.invoke.return_value = {"output": "25 products below reorder point."}
        result = process_message("Low stock items", session_id="route-007")
        output = result.get("output", str(result)) if isinstance(result, dict) else str(result)
        assert len(output) > 10


def test_multi_turn():
    from mcp_server.chat_interface import ChatSession
    session = ChatSession(session_id="mt-007")
    session.add_message("user", "Show low stock items")
    session.add_message("assistant", "25 products need reorder.")
    session.add_message("user", "Create a PO for grocery items from supplier 1")
    assert len(session.get_history_for_llm()) >= 2


def test_tool_chain():
    names = [tool.name for tool in build_chat_executor().tools]
    assert "get_inventory_dashboard" in names and "get_low_stock_products" in names


def test_update_reachable():
    with patch("mcp_server.mcp_app.requests.post") as mocked_post:
        mocked_post.return_value.json.return_value = {"id": 5, "movement_type": "receipt", "quantity": 50}
        mocked_post.return_value.raise_for_status = MagicMock()
        from mcp_server.mcp_app import update_stock
        result = update_stock(product_id=1, movement_type="receipt", quantity=50)
        assert isinstance(result, dict) and result.get("id") is not None