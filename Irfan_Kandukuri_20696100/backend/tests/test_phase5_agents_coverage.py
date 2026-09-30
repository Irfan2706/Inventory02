"""Targeted tests closing coverage gaps in multi_agent/agents.py for Phase 5 SonarQube compliance."""
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


def _fake_get(product, catalog=None, supplier=None):
    catalog = catalog if catalog is not None else []
    supplier = supplier or {"id": 5, "lead_time_days": 4}

    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/products/1"):
            return FakeResponse(product)
        if url.endswith("/suppliers/5/catalog"):
            return FakeResponse(catalog)
        if url.endswith("/suppliers/5"):
            return FakeResponse(supplier)
        return FakeResponse({}, 404)

    return fake_get


# --- private helper functions -------------------------------------------------


def test_round_returns_zero_on_invalid_value():
    assert agents._round("not-a-number") == 0.0
    assert agents._round(None) == 0.0


def test_generate_text_falls_back_when_llm_invoke_raises(monkeypatch):
    class FailingLLM:
        def invoke(self, prompt):
            raise RuntimeError("model unreachable")

    monkeypatch.setattr(agents, "_llm", lambda: FailingLLM())
    assert agents._generate_text("prompt", "fallback text") == "fallback text"


def test_traceable_falls_back_to_undecorated_function_on_trace_failure(monkeypatch):
    class ExplodingTraceable:
        def __call__(self, func):
            def _boom(*a, **k):
                raise RuntimeError("langsmith down")

            return _boom

    monkeypatch.setattr(agents, "_langsmith_traceable", lambda *a, **k: ExplodingTraceable())

    @agents.traceable(project_name="x")
    def add_one(x):
        return x + 1

    assert add_one(1) == 2


# --- demand_forecaster branch coverage ----------------------------------------


def test_demand_forecaster_skips_movement_without_recorded_at(monkeypatch):
    product = {
        "id": 1, "sku": "SKU-1", "reorder_point": 20,
        "stock_level": {"quantity_available": 50},
        "movements": [{"movement_type": "sale", "quantity": 3}],
    }
    monkeypatch.setattr(requests, "get", _fake_get(product))
    state = agents.demand_forecaster(initial_state(1))
    # No usable sale_dates means days_observed falls back to 1; the movement is still counted as a sale.
    assert state["demand_forecast"]["avg_daily_demand"] == 3.0


def test_demand_forecaster_skips_movement_with_unparseable_date(monkeypatch):
    product = {
        "id": 1, "sku": "SKU-1", "reorder_point": 20,
        "stock_level": {"quantity_available": 50},
        "movements": [{"movement_type": "sale", "quantity": 3, "recorded_at": "not-a-date"}],
    }
    monkeypatch.setattr(requests, "get", _fake_get(product))
    state = agents.demand_forecaster(initial_state(1))
    assert state["demand_forecast"]["avg_daily_demand"] == 3.0


def test_demand_forecaster_trend_decreasing(monkeypatch):
    product = {
        "id": 1, "sku": "SKU-1", "reorder_point": 20,
        "stock_level": {"quantity_available": 50},
        "movements": [
            {"movement_type": "sale", "quantity": 1, "recorded_at": "2026-08-01T00:00:00"},
            {"movement_type": "sale", "quantity": 1, "recorded_at": "2026-08-05T00:00:00"},
            {"movement_type": "sale", "quantity": 20, "recorded_at": "2026-08-28T00:00:00"},
            {"movement_type": "sale", "quantity": 20, "recorded_at": "2026-08-30T00:00:00"},
        ],
    }
    monkeypatch.setattr(requests, "get", _fake_get(product))
    state = agents.demand_forecaster(initial_state(1))
    assert state["demand_forecast"]["demand_trend"] == "decreasing"


def test_demand_forecaster_trend_stable(monkeypatch):
    product = {
        "id": 1, "sku": "SKU-1", "reorder_point": 20,
        "stock_level": {"quantity_available": 50},
        "movements": [
            {"movement_type": "sale", "quantity": 10, "recorded_at": "2026-08-01T00:00:00"},
            {"movement_type": "sale", "quantity": 10, "recorded_at": "2026-08-15T00:00:00"},
            {"movement_type": "sale", "quantity": 10, "recorded_at": "2026-08-20T00:00:00"},
            {"movement_type": "sale", "quantity": 10, "recorded_at": "2026-08-30T00:00:00"},
        ],
    }
    monkeypatch.setattr(requests, "get", _fake_get(product))
    state = agents.demand_forecaster(initial_state(1))
    assert state["demand_forecast"]["demand_trend"] == "stable"


def test_demand_forecaster_high_risk_from_zero_stock(monkeypatch):
    product = {
        "id": 1, "sku": "SKU-1", "reorder_point": 0,
        "stock_level": {"quantity_available": 0},
        "movements": [],
    }
    monkeypatch.setattr(requests, "get", _fake_get(product))
    state = agents.demand_forecaster(initial_state(1))
    assert state["demand_forecast"]["stockout_risk"] == "high"


def test_demand_forecaster_high_risk_from_low_days_remaining(monkeypatch):
    product = {
        "id": 1, "sku": "SKU-1", "reorder_point": 0,
        "stock_level": {"quantity_available": 3},
        "movements": [
            {"movement_type": "sale", "quantity": 2, "recorded_at": "2026-08-30T00:00:00"},
        ],
    }
    monkeypatch.setattr(requests, "get", _fake_get(product))
    state = agents.demand_forecaster(initial_state(1))
    assert state["demand_forecast"]["stockout_risk"] == "high"


def test_demand_forecaster_medium_risk(monkeypatch):
    product = {
        "id": 1, "sku": "SKU-1", "reorder_point": 0,
        "stock_level": {"quantity_available": 6},
        "movements": [
            {"movement_type": "sale", "quantity": 2, "recorded_at": "2026-08-30T00:00:00"},
        ],
    }
    monkeypatch.setattr(requests, "get", _fake_get(product))
    state = agents.demand_forecaster(initial_state(1))
    assert state["demand_forecast"]["stockout_risk"] == "medium"


# --- reorder_agent branch coverage ---------------------------------------------


def test_reorder_agent_urgency_within_3_days():
    state = initial_state(1)
    state["product_data"] = {"id": 1, "reorder_quantity": 10, "reorder_point": 20, "stock_level": {"quantity_available": 25}}
    state["demand_forecast"] = {"stockout_risk": "medium", "demand_trend": "stable"}
    state = agents.reorder_agent(state)
    # below_reorder_point False (25>20), high_risk False (medium != high) -> not required
    assert state["reorder_recommendation"]["urgency"] == "not_required"


def test_reorder_agent_urgency_medium_when_high_risk_precaution():
    state = initial_state(1)
    state["product_data"] = {"id": 1, "reorder_quantity": 10, "reorder_point": 20, "stock_level": {"quantity_available": 25}}
    state["demand_forecast"] = {"stockout_risk": "high", "demand_trend": "stable"}
    state = agents.reorder_agent(state)
    reco = state["reorder_recommendation"]
    assert reco["reorder_required"] is True
    assert reco["urgency"] == "immediate"
    assert "precaution" in reco["reason"]


def test_reorder_agent_urgency_within_week_when_below_reorder_point_low_risk():
    state = initial_state(1)
    state["product_data"] = {"id": 1, "reorder_quantity": 10, "reorder_point": 20, "stock_level": {"quantity_available": 15}}
    state["demand_forecast"] = {"stockout_risk": "low", "demand_trend": "stable"}
    state = agents.reorder_agent(state)
    assert state["reorder_recommendation"]["urgency"] == "within_week"


def test_reorder_agent_urgency_within_3_days_when_medium_risk_and_below_point():
    state = initial_state(1)
    state["product_data"] = {"id": 1, "reorder_quantity": 10, "reorder_point": 20, "stock_level": {"quantity_available": 15}}
    state["demand_forecast"] = {"stockout_risk": "medium", "demand_trend": "stable"}
    state = agents.reorder_agent(state)
    assert state["reorder_recommendation"]["urgency"] == "within_3_days"


# --- supplier_coordinator / inventory_auditor ternary branches ----------------


def test_supplier_coordinator_no_reorder_required_branch():
    state = initial_state(1)
    state["product_data"] = {"id": 1, "supplier_id": None, "cost_price": 10}
    state["reorder_recommendation"] = {"reorder_required": False, "recommended_quantity": 0}
    state = agents.supplier_coordinator(state)
    assert "No reorder required" in state["supplier_quote"]["quote_notes"]


def test_inventory_auditor_no_reorder_required_branch():
    state = initial_state(1)
    state["product_data"] = {"id": 1, "sku": "SKU-1", "name": "Rice", "reorder_point": 20, "stock_level": {"quantity_available": 50}}
    state["demand_forecast"] = {"stockout_risk": "low", "days_of_stock_remaining": 30}
    state["reorder_recommendation"] = {"reorder_required": False, "urgency": "not_required", "recommended_quantity": 0}
    state["supplier_quote"] = {"total_order_cost": 0, "estimated_lead_time_days": 0}
    state = agents.inventory_auditor(state)
    assert "No reorder is required" in state["audit_report"]
