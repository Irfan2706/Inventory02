from mcp_server.chat_interface import build_chat_executor, discover_local_model, process_message, sessions
from mcp_server.session_manager import ChatSession


def test_session_keeps_last_ten_messages():
    session = ChatSession("x")
    for index in range(12):
        session.add_message("user", str(index))
    assert len(session.get_history_for_llm()) == 10
    assert session.get_history_for_llm()[0]["content"] == "2"


def test_session_manager_reuses_session():
    assert sessions.get("same") is sessions.get("same")


def test_executor_has_six_structured_tools():
    executor = build_chat_executor()
    assert len(executor.tools) == 6
    assert {tool.name for tool in executor.tools} == {"update_stock", "create_purchase_order", "get_low_stock_products", "get_supplier_catalog", "get_purchase_orders", "get_inventory_dashboard"}


def test_executor_has_required_limits():
    executor = build_chat_executor()
    assert executor.max_iterations == 5
    assert executor.handle_parsing_errors is True


def test_executor_routes_reorder_to_mcp_tool(monkeypatch):
    monkeypatch.setattr("mcp_server.mcp_tools._get", lambda path, params=None: [{"sku": "A"}])
    result = build_chat_executor().invoke({"input": "Which products need reorder?"})
    assert result["tools_used"] == ["get_low_stock_products"]


def test_process_message_persists_history(monkeypatch):
    monkeypatch.setattr("mcp_server.mcp_tools.get_inventory_dashboard", lambda: {"total_products": 2})
    result = process_message("Show the dashboard", "phase4-test")
    assert result["session_id"] == "phase4-test"
    assert len(result["history"]) >= 2


def test_model_discovery_degrades_without_ollama(monkeypatch):
    monkeypatch.setattr("mcp_server.chat_interface.requests.get", lambda *args, **kwargs: (_ for _ in ()).throw(discover_local_model.__globals__["requests"].exceptions.ConnectionError()))
    assert discover_local_model() is None


def test_executor_builds():
    assert build_chat_executor() is not None


def test_message_processed():
    from unittest.mock import patch
    with patch("mcp_server.chat_interface.build_chat_executor") as mocked_builder:
        mocked_builder.return_value.invoke.return_value = {"output": "25 products need reorder."}
        assert process_message("Which products need reordering?", session_id="inv-001") is not None


def test_session_id_accepted():
    import uuid
    from unittest.mock import patch
    with patch("mcp_server.chat_interface.build_chat_executor") as mocked_builder:
        mocked_builder.return_value.invoke.return_value = {"output": "OK"}
        assert process_message("Dashboard", session_id=str(uuid.uuid4())) is not None


def test_history_tracking():
    session = ChatSession(session_id="hist-007")
    session.add_message("user", "Show low stock items")
    session.add_message("assistant", "25 products below reorder point.")
    session.add_message("user", "Create a PO for the grocery items")
    assert len(session.history) >= 3


def test_tool_calls_extracted():
    from unittest.mock import patch
    with patch("mcp_server.chat_interface.build_chat_executor") as mocked_builder:
        mocked_builder.return_value.invoke.return_value = {
            "output": "Dashboard loaded.", "intermediate_steps": [("get_inventory_dashboard", {})]}
        process_message("Dashboard", session_id="tool-007")
        mocked_builder.return_value.invoke.assert_called_once()


def test_chat_error_handled():
    from unittest.mock import patch
    with patch("mcp_server.chat_interface.build_chat_executor") as mocked_builder:
        mocked_builder.return_value.invoke.side_effect = Exception("Timeout")
        result = process_message("Show data", session_id="err-007")
        assert result is not None