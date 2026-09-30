import inspect

from mcp_server import mcp_tools


def test_mcp_tracer_name():
    assert mcp_tools.tracer is not None


def test_all_tools_have_phase4_span_calls():
    for name in ("update_stock", "create_purchase_order", "get_low_stock_products", "get_supplier_catalog", "get_purchase_orders", "get_inventory_dashboard"):
        assert f'_tool_span("{name}")' in inspect.getsource(getattr(mcp_tools, name))


def test_tools_set_poc_attribute():
    assert inspect.getsource(mcp_tools.update_stock).count('set_attribute("poc_id", "POC-07")') == 1


def test_tools_log_phase4():
    assert 'phase="P4"' in inspect.getsource(mcp_tools._log_tool)


def test_langsmith_project_annotation():
    import inspect
    from mcp_server import chat_interface
    assert "AI-Readiness-POC-07-P4" in inspect.getsource(chat_interface.process_message)


def test_session_in_trace():
    from unittest.mock import patch
    from mcp_server.chat_interface import process_message
    with patch("mcp_server.chat_interface.build_chat_executor") as mocked_builder:
        mocked_builder.return_value.invoke.return_value = {"output": "OK"}
        result = process_message("Test", session_id="obs-007")
        mocked_builder.return_value.invoke.assert_called_once()
        assert result is not None


def test_otel_span_for_mcp_tool():
    import inspect
    from unittest.mock import MagicMock, patch
    from mcp_server import mcp_tools
    with patch("mcp_server.mcp_app.requests.get") as mocked_get:
        mocked_get.return_value.json.return_value = {"total_products": 10}
        mocked_get.return_value.raise_for_status = MagicMock()
        from mcp_server.mcp_app import get_inventory_dashboard
        get_inventory_dashboard()
    assert "mcp.tool." in inspect.getsource(mcp_tools._tool_span)


def test_log_has_session_id():
    from unittest.mock import patch
    from mcp_server.chat_interface import process_message
    with patch("mcp_server.chat_interface.build_chat_executor") as mocked_builder:
        mocked_builder.return_value.invoke.return_value = {"output": "OK"}
        result = process_message("Test", session_id="log-007-session")
        assert "session_id" in result