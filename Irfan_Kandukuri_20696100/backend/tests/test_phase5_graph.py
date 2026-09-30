import requests

from multi_agent import agents, graph as graph_module
from multi_agent.graph import analyze_product, build_inventory_graph, should_skip_to_audit
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
    "movements": [{"movement_type": "sale", "quantity": 5, "recorded_at": "2026-08-25T00:00:00"}],
}
CATALOG = [{"product_id": 1, "sku": "SKU-GRO-0001", "name": "Rice", "unit_cost": 22.0}]
SUPPLIER = {"id": 5, "lead_time_days": 4}


def _healthy_pipeline_get(url, headers=None, timeout=None):
    if url.endswith("/products/1"):
        return FakeResponse(PRODUCT)
    if url.endswith("/suppliers/5/catalog"):
        return FakeResponse(CATALOG)
    if url.endswith("/suppliers/5"):
        return FakeResponse(SUPPLIER)
    return FakeResponse({}, 404)


def test_should_skip_to_audit_on_error_status():
    state = initial_state(1)
    state["analysis_status"] = "error"
    assert should_skip_to_audit(state) == "inventory_auditor"


def test_should_skip_to_audit_on_three_errors():
    state = initial_state(1)
    state["errors"] = ["a", "b", "c"]
    assert should_skip_to_audit(state) == "inventory_auditor"


def test_should_continue_to_reorder_agent_when_healthy():
    state = initial_state(1)
    assert should_skip_to_audit(state) == "reorder_agent"


def test_build_inventory_graph_returns_invokable_object():
    graph = build_inventory_graph()
    assert hasattr(graph, "invoke")


def test_analyze_product_runs_full_pipeline(monkeypatch):
    monkeypatch.setattr(requests, "get", _healthy_pipeline_get)
    result = analyze_product(1)
    assert result["analysis_status"] == "complete"
    assert result["demand_forecast"]
    assert result["reorder_recommendation"]
    assert result["supplier_quote"]
    assert result["audit_report"]
    assert len(result["messages"]) == 4


def test_analyze_product_skips_to_auditor_on_repeated_errors(monkeypatch):
    def fail(url, headers=None, timeout=None):
        raise requests.exceptions.ConnectionError("offline")

    monkeypatch.setattr(requests, "get", fail)
    result = analyze_product(1)
    assert result["analysis_status"] == "complete"
    assert result["reorder_recommendation"] == {}
    assert result["supplier_quote"] == {}
    assert "incomplete" in result["audit_report"]


def test_analyze_product_returns_correct_product_id(monkeypatch):
    monkeypatch.setattr(requests, "get", _healthy_pipeline_get)
    result = analyze_product(1)
    assert result["product_id"] == 1


def test_build_inventory_graph_falls_back_when_langgraph_unavailable(monkeypatch):
    monkeypatch.setattr(graph_module, "StateGraph", None)
    fallback = build_inventory_graph()
    assert isinstance(fallback, graph_module._SequentialInventoryGraph)


def test_sequential_fallback_graph_runs_healthy_pipeline(monkeypatch):
    monkeypatch.setattr(requests, "get", _healthy_pipeline_get)
    fallback = graph_module._SequentialInventoryGraph()
    result = fallback.invoke(initial_state(1))
    assert result["analysis_status"] == "complete"
    assert result["reorder_recommendation"]
    assert result["supplier_quote"]
    assert result["audit_report"]


def test_sequential_fallback_graph_skips_to_auditor_on_errors(monkeypatch):
    def fail(url, headers=None, timeout=None):
        raise requests.exceptions.ConnectionError("offline")

    monkeypatch.setattr(requests, "get", fail)
    fallback = graph_module._SequentialInventoryGraph()
    result = fallback.invoke(initial_state(1))
    assert result["reorder_recommendation"] == {}
    assert result["supplier_quote"] == {}
    assert "incomplete" in result["audit_report"]
