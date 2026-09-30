import requests

from multi_agent import agents
from multi_agent.state import initial_state


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError("request failed")
            error.response = self
            raise error

    def json(self):
        return self.payload


PRODUCT = {
    "id": 1,
    "sku": "SKU-GRO-0001",
    "name": "Rice",
    "reorder_point": 20,
    "reorder_quantity": 100,
    "supplier_id": 5,
    "cost_price": 25.0,
    "stock_level": {"quantity_on_hand": 15, "quantity_available": 10, "quantity_reserved": 5},
    "movements": [
        {"movement_type": "sale", "quantity": 5, "recorded_at": "2026-08-25T00:00:00"},
        {"movement_type": "sale", "quantity": 4, "recorded_at": "2026-08-20T00:00:00"},
    ],
}
CATALOG = [{"product_id": 1, "sku": "SKU-GRO-0001", "name": "Rice", "unit_cost": 22.0}]
SUPPLIER = {"id": 5, "lead_time_days": 4}
HEALTHY_PRODUCT = {**PRODUCT, "stock_level": {"quantity_on_hand": 100, "quantity_available": 95, "quantity_reserved": 5}}


def _fake_get_factory(product=PRODUCT, catalog=CATALOG, supplier=SUPPLIER):
    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/products/1"):
            return FakeResponse(product)
        if url.endswith("/suppliers/5/catalog"):
            return FakeResponse(catalog)
        if url.endswith("/suppliers/5"):
            return FakeResponse(supplier)
        return FakeResponse({}, 404)

    return fake_get


def test_demand_forecaster_returns_required_fields(monkeypatch):
    monkeypatch.setattr(agents, "requests", requests)
    monkeypatch.setattr(requests, "get", _fake_get_factory())
    state = agents.demand_forecaster(initial_state(1))
    forecast = state["demand_forecast"]
    assert set(forecast.keys()) == {
        "avg_daily_demand",
        "demand_trend",
        "days_of_stock_remaining",
        "stockout_risk",
        "forecast_notes",
    }
    assert forecast["stockout_risk"] == "high"
    assert state["product_data"]["sku"] == "SKU-GRO-0001"


def test_demand_forecaster_handles_product_fetch_error(monkeypatch):
    def fail(url, headers=None, timeout=None):
        raise requests.exceptions.ConnectionError("offline")

    monkeypatch.setattr(requests, "get", fail)
    state = agents.demand_forecaster(initial_state(1))
    assert state["errors"]
    assert state["analysis_status"] == "error"
    assert state["product_data"] == {}


def test_demand_forecaster_handles_invalid_product_payload(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse(["unexpected"]))
    state = agents.demand_forecaster(initial_state(1))
    assert state["analysis_status"] == "error"
    assert state["product_data"] == {}


def test_demand_forecaster_healthy_stock_is_low_risk(monkeypatch):
    monkeypatch.setattr(requests, "get", _fake_get_factory(product=HEALTHY_PRODUCT))
    state = agents.demand_forecaster(initial_state(1))
    assert state["demand_forecast"]["stockout_risk"] in {"low", "medium"}


def test_reorder_agent_flags_reorder_when_below_reorder_point(monkeypatch):
    monkeypatch.setattr(requests, "get", _fake_get_factory())
    state = agents.demand_forecaster(initial_state(1))
    state = agents.reorder_agent(state)
    reco = state["reorder_recommendation"]
    assert set(reco.keys()) == {"reorder_required", "recommended_quantity", "urgency", "reason"}
    assert reco["reorder_required"] is True
    assert reco["recommended_quantity"] > 0
    assert state["analysis_status"] == "reorder_required"


def test_reorder_agent_no_reorder_when_stock_healthy(monkeypatch):
    monkeypatch.setattr(requests, "get", _fake_get_factory(product=HEALTHY_PRODUCT))
    state = agents.demand_forecaster(initial_state(1))
    state = agents.reorder_agent(state)
    assert state["reorder_recommendation"]["reorder_required"] is False
    assert state["reorder_recommendation"]["urgency"] == "not_required"


def test_reorder_agent_handles_missing_product_data():
    state = initial_state(1)
    state = agents.reorder_agent(state)
    assert state["reorder_recommendation"]["reorder_required"] is False
    assert "unavailable" in state["reorder_recommendation"]["reason"]


def test_supplier_coordinator_generates_quote(monkeypatch):
    monkeypatch.setattr(requests, "get", _fake_get_factory())
    state = agents.demand_forecaster(initial_state(1))
    state = agents.reorder_agent(state)
    state = agents.supplier_coordinator(state)
    quote = state["supplier_quote"]
    assert set(quote.keys()) == {
        "supplier_id",
        "quoted_unit_cost",
        "total_order_cost",
        "estimated_lead_time_days",
        "quote_notes",
    }
    assert quote["supplier_id"] == 5
    assert quote["quoted_unit_cost"] == 22.0
    assert quote["total_order_cost"] > 0
    assert quote["estimated_lead_time_days"] == 4


def test_supplier_coordinator_handles_catalog_fetch_error(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/products/1"):
            return FakeResponse(PRODUCT)
        raise requests.exceptions.ConnectionError("offline")

    monkeypatch.setattr(requests, "get", fake_get)
    state = agents.demand_forecaster(initial_state(1))
    state = agents.reorder_agent(state)
    state = agents.supplier_coordinator(state)
    assert state["errors"]
    assert state["supplier_quote"]["supplier_id"] == 5


def test_supplier_coordinator_ignores_invalid_catalog_entries(monkeypatch):
    monkeypatch.setattr(requests, "get", _fake_get_factory(catalog=["invalid", {"product_id": 1, "unit_cost": 22.0}]))
    state = agents.supplier_coordinator(agents.reorder_agent(agents.demand_forecaster(initial_state(1))))
    assert state["supplier_quote"]["quoted_unit_cost"] == 22.0


def test_inventory_auditor_sets_status_complete(monkeypatch):
    monkeypatch.setattr(requests, "get", _fake_get_factory())
    state = agents.demand_forecaster(initial_state(1))
    state = agents.reorder_agent(state)
    state = agents.supplier_coordinator(state)
    state = agents.inventory_auditor(state)
    assert state["analysis_status"] == "complete"
    assert state["audit_report"]
    assert "SKU-GRO-0001" in state["audit_report"]


def test_inventory_auditor_handles_missing_product_data():
    state = initial_state(1)
    state["errors"] = ["Product fetch error: offline"]
    state = agents.inventory_auditor(state)
    assert state["analysis_status"] == "complete"
    assert "incomplete" in state["audit_report"]


def test_api_token_context_roundtrip():
    token_state = agents.set_api_token("abc123")
    try:
        assert agents._api_token.get() == "abc123"
        assert agents._auth_headers() == {"Authorization": "Bearer abc123"}
    finally:
        agents.reset_api_token(token_state)
    assert agents._api_token.get() is None
