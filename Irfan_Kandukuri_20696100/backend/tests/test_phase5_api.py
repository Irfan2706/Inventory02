def _fake_state(product_id: int) -> dict:
    return {
        "product_id": product_id,
        "product_data": {"sku": "SKU-GRO-0001"},
        "demand_forecast": {
            "avg_daily_demand": 4.5,
            "demand_trend": "increasing",
            "days_of_stock_remaining": 2.2,
            "stockout_risk": "high",
            "forecast_notes": "Demand is rising.",
        },
        "reorder_recommendation": {
            "reorder_required": True,
            "recommended_quantity": 125,
            "urgency": "immediate",
            "reason": "Below reorder point.",
        },
        "supplier_quote": {
            "supplier_id": 5,
            "quoted_unit_cost": 22.0,
            "total_order_cost": 2750.0,
            "estimated_lead_time_days": 4,
            "quote_notes": "Best available quote.",
        },
        "audit_report": "Product is at high stockout risk; reorder immediately.",
        "analysis_status": "complete",
        "errors": [],
        "messages": ["Demand Forecaster: risk=high, trend=increasing"],
    }


def test_multi_agent_analyze_returns_contract(client, auth_headers, monkeypatch):
    from multi_agent import api as multi_agent_api

    monkeypatch.setattr(multi_agent_api, "analyze_product", lambda product_id: _fake_state(product_id))

    response = client.post(
        "/api/v1/multi-agent/analyze",
        json={"product_id": 1},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == 1
    assert body["analysis_status"] == "complete"
    assert body["demand_forecast"]["stockout_risk"] == "high"
    assert body["reorder_recommendation"]["reorder_required"] is True
    assert body["supplier_quote"]["supplier_id"] == 5
    assert "immediately" in body["audit_report"]


def test_multi_agent_analyze_requires_authentication(client):
    response = client.post("/api/v1/multi-agent/analyze", json={"product_id": 1})
    assert response.status_code == 401


def test_multi_agent_analyze_rejects_invalid_product_id(client, auth_headers):
    response = client.post(
        "/api/v1/multi-agent/analyze",
        json={"product_id": 0},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_multi_agent_analyze_forwards_authorization_token(client, auth_headers, monkeypatch):
    from multi_agent import api as multi_agent_api

    captured = {}

    def fake_set_api_token(token):
        captured["token"] = token
        return "token-state"

    monkeypatch.setattr(multi_agent_api, "set_api_token", fake_set_api_token)
    monkeypatch.setattr(multi_agent_api, "reset_api_token", lambda state: None)
    monkeypatch.setattr(multi_agent_api, "analyze_product", lambda product_id: _fake_state(product_id))

    client.post("/api/v1/multi-agent/analyze", json={"product_id": 1}, headers=auth_headers)

    assert captured["token"] == auth_headers["Authorization"]


def test_multi_agent_analyze_resets_token_on_failure(monkeypatch):
    from fastapi import Request

    from multi_agent import api as multi_agent_api
    from multi_agent.schemas import MultiAgentAnalyzeRequest

    reset_called = {}

    def fake_reset(state):
        reset_called["done"] = True

    def failing_analyze(product_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(multi_agent_api, "reset_api_token", fake_reset)
    monkeypatch.setattr(multi_agent_api, "analyze_product", failing_analyze)

    scope = {"type": "http", "headers": [(b"authorization", b"Bearer abc")]}
    request = Request(scope)

    try:
        multi_agent_api.analyze(MultiAgentAnalyzeRequest(product_id=1), request, _user=None)
    except RuntimeError:
        pass

    assert reset_called.get("done") is True
