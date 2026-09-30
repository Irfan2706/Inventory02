from unittest.mock import Mock


def test_api_get_additional_failure_paths(monkeypatch):
    from agent import tools

    class Response:
        status_code = 500

        def raise_for_status(self):
            error = tools.requests.HTTPError("server error")
            error.response = self
            raise error

    monkeypatch.setattr(tools.requests, "get", lambda *args, **kwargs: Response())
    assert "server error" in tools._api_get("/dashboard")["error"]

    monkeypatch.setattr(tools.requests, "get", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("bad json")))
    assert tools._api_get("/dashboard") == {"error": "bad json"}


def test_api_get_forwards_bearer_token(monkeypatch):
    from agent import tools

    response = Mock()
    response.json.return_value = {"ok": True}
    response.raise_for_status.return_value = None
    request = Mock(return_value=response)
    monkeypatch.setattr(tools.requests, "get", request)
    state = tools.set_api_token("token-value")
    try:
        assert tools._api_get("/dashboard", {"page": 1}) == {"ok": True}
    finally:
        tools.reset_api_token(state)
    assert request.call_args.kwargs["headers"] == {"Authorization": "Bearer token-value"}


def test_tools_handle_empty_and_error_results(monkeypatch):
    from agent import tools

    monkeypatch.setattr(tools, "_api_get", lambda path: {"error": "offline"})
    assert "offline" in tools.get_low_stock_alerts.invoke("")
    assert "offline" in tools.get_dashboard_stats.invoke("")
    assert "unavailable" in tools.get_supplier_catalog.invoke("7").lower()
    assert "offline" in tools.get_product_stock.invoke("7")

    monkeypatch.setattr(tools, "_api_get", lambda path: [])
    assert "No low stock" in tools.get_low_stock_alerts.invoke("")
    assert "no products" in tools.get_supplier_catalog.invoke("7").lower()


def test_policy_tool_handles_missing_answer_and_errors(monkeypatch):
    from agent import tools

    monkeypatch.setattr("rag.rag_chain.ask_question", lambda question: {})
    assert tools.search_inventory_policy.invoke("policy") == "No answer found."
    monkeypatch.setattr("rag.rag_chain.ask_question", lambda question: (_ for _ in ()).throw(RuntimeError("rag down")))
    assert "rag down" in tools.search_inventory_policy.invoke("policy")


def test_agent_executor_string_and_identifier_paths(monkeypatch):
    from agent import agent_executor

    class FakeTool:
        def invoke(self, payload):
            return str(payload)

    monkeypatch.setattr(agent_executor, "get_product_stock", FakeTool())
    result = agent_executor.build_agent_executor().invoke("What is stock level of item ID: 12?")
    assert result["tools_used"] == ["get_product_stock"]
    assert "12" in result["output"]

    monkeypatch.setattr(agent_executor, "get_supplier_catalog", FakeTool())
    result = agent_executor.build_agent_executor().invoke({"question": "Show supplier #8 catalog"})
    assert result["tools_used"] == ["get_supplier_catalog"]
    assert "8" in result["output"]


def test_summarizer_local_fallbacks(monkeypatch):
    from agent import summarizer

    long_text = "word " * 600
    monkeypatch.setattr(summarizer, "load_summarize_chain", lambda: None)
    fallback = summarizer._summarize_if_long(long_text)
    assert len(fallback) < len(long_text)
    monkeypatch.setattr(summarizer, "load_summarize_chain", lambda: (_ for _ in ()).throw(RuntimeError("unavailable")))
    assert summarizer._summarize_if_long(long_text).endswith("...")


def test_agent_service_maps_executor_result(monkeypatch):
    from agent import agent_service

    executor = Mock()
    executor.invoke.return_value = {"output": "answer", "tools_used": ["tool"], "reasoning": "reason"}
    monkeypatch.setattr(agent_service, "build_agent_executor", lambda: executor)
    result = agent_service.answer_question("question", "Bearer token")
    assert result == {"answer": "answer", "tools_used": ["tool"], "reasoning": "reason"}
    executor.invoke.assert_called_once_with({"input": "question"})


def test_database_operation_extraction_branches():
    from app.database import _extract_operation_and_table

    assert _extract_operation_and_table("") == ("unknown", "unknown")
    assert _extract_operation_and_table("INSERT INTO products VALUES (1)") == ("insert", "products")
    assert _extract_operation_and_table("UPDATE products SET name='x'") == ("update", "products")
    assert _extract_operation_and_table("SELECT * FROM products") == ("select", "products")
    assert _extract_operation_and_table("DELETE FROM products") == ("delete", "products")
