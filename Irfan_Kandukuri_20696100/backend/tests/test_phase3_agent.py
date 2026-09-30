def test_agent_selects_low_stock_tool(monkeypatch):
    from agent import agent_executor

    class FakeTool:
        def invoke(self, payload):
            return "SKU-GRO-0001 needs reorder"

    monkeypatch.setattr(agent_executor, "get_low_stock_alerts", FakeTool())

    result = agent_executor.build_agent_executor().invoke({"input": "Which products need reorder?"})

    assert result["tools_used"] == ["get_low_stock_alerts"]
    assert "needs reorder" in result["output"]
    assert "summarized" in result["reasoning"]


def test_agent_selects_policy_search(monkeypatch):
    from agent import agent_executor

    class FakeTool:
        def invoke(self, payload):
            return "Reorder point is the replenishment threshold."

    monkeypatch.setattr(agent_executor, "search_inventory_policy", FakeTool())

    result = agent_executor.build_agent_executor().invoke({"input": "What does reorder point mean?"})

    assert result["tools_used"] == ["search_inventory_policy"]


def test_agent_endpoint_returns_contract(client, auth_headers, monkeypatch):
    from app.routers import agent as agent_router

    monkeypatch.setattr(
        agent_router,
        "answer_question",
        lambda question, authorization: {
            "answer": "Dashboard loaded.",
            "tools_used": ["get_dashboard_stats"],
            "reasoning": "Selected and summarized dashboard statistics.",
        },
    )

    response = client.post(
        "/api/v1/agent/query",
        json={"question": "Show dashboard statistics"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["tools_used"] == ["get_dashboard_stats"]


def test_agent_routes_dashboard_question(monkeypatch):
    from agent import agent_executor

    class FakeTool:
        def invoke(self, payload):
            return "dashboard"

    monkeypatch.setattr(agent_executor, "get_dashboard_stats", FakeTool())
    result = agent_executor.build_agent_executor().invoke({"input": "Show dashboard statistics"})
    assert result["tools_used"] == ["get_dashboard_stats"]


def test_agent_routes_product_question(monkeypatch):
    from agent import agent_executor

    class FakeTool:
        def invoke(self, payload):
            return "product stock"

    monkeypatch.setattr(agent_executor, "get_product_stock", FakeTool())
    result = agent_executor.build_agent_executor().invoke({"input": "What is stock level of Product 7?"})
    assert result["tools_used"] == ["get_product_stock"]


def test_agent_routes_supplier_question(monkeypatch):
    from agent import agent_executor

    class FakeTool:
        def invoke(self, payload):
            return "supplier catalog"

    monkeypatch.setattr(agent_executor, "get_supplier_catalog", FakeTool())
    result = agent_executor.build_agent_executor().invoke({"input": "Show supplier 3 catalog"})
    assert result["tools_used"] == ["get_supplier_catalog"]


def test_agent_falls_back_to_policy_for_unknown_question(monkeypatch):
    from agent import agent_executor

    class FakeTool:
        def invoke(self, payload):
            return "policy"

    monkeypatch.setattr(agent_executor, "search_inventory_policy", FakeTool())
    result = agent_executor.build_agent_executor().invoke({"input": "Explain inventory procedures"})
    assert result["tools_used"] == ["search_inventory_policy"]


def test_agent_endpoint_requires_authentication(client):
    response = client.post("/api/v1/agent/query", json={"question": "Show dashboard statistics"})

    assert response.status_code == 401
