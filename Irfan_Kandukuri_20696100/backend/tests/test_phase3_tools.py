from agent import tools


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            error = requests.HTTPError("request failed")
            error.response = self
            raise error

    def json(self):
        return self.payload


def test_low_stock_tool_formats_existing_alert_contract(monkeypatch):
    monkeypatch.setattr(
        tools.requests,
        "get",
        lambda *args, **kwargs: FakeResponse([{"sku": "SKU-GRO-0001", "product_name": "Rice", "message": "only 2 units left"}]),
    )

    result = tools.get_low_stock_alerts.invoke({"query": "Which products need reorder?"})

    assert "SKU-GRO-0001" in result
    assert "1 products need reorder" in result


def test_api_get_handles_connection_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise tools.requests.exceptions.ConnectionError("offline")

    monkeypatch.setattr(tools.requests, "get", fail)

    assert tools._api_get("/dashboard") == {"error": "API unavailable"}


def test_api_get_handles_not_found(monkeypatch):
    monkeypatch.setattr(tools.requests, "get", lambda *args, **kwargs: FakeResponse({}, 404))

    assert tools._api_get("/products/999") == {"error": "not_found"}


def test_api_get_handles_timeout(monkeypatch):
    monkeypatch.setattr(tools.requests, "get", lambda *args, **kwargs: (_ for _ in ()).throw(tools.requests.exceptions.Timeout()))

    assert tools._api_get("/dashboard") == {"error": "API request timed out"}


def test_dashboard_tool_formats_response(monkeypatch):
    monkeypatch.setattr(tools.requests, "get", lambda *args, **kwargs: FakeResponse({"total_products": 4, "low_stock_count": 1, "out_of_stock_count": 0, "open_po_count": 2, "total_stock_value": 1250.5}))
    assert "Total stock value: 1,250.50" in tools.get_dashboard_stats.invoke({"query": "dashboard"})


def test_product_tool_formats_response(monkeypatch):
    monkeypatch.setattr(tools.requests, "get", lambda *args, **kwargs: FakeResponse({"sku": "SKU-GRO-0001", "name": "Rice", "unit_of_measure": "kg", "stock_level": {"quantity_on_hand": 5, "quantity_available": 4, "quantity_reserved": 1}, "reorder_point": 2, "reorder_quantity": 10}))
    assert "Available: 4" in tools.get_product_stock.invoke({"product_id": "1"})


def test_supplier_tool_formats_response(monkeypatch):
    monkeypatch.setattr(tools.requests, "get", lambda *args, **kwargs: FakeResponse([{"sku": "SKU-GRO-0001", "name": "Rice", "unit_cost": 20.0}]))
    assert "Supplier 1 catalog" in tools.get_supplier_catalog.invoke({"supplier_id": "1"})


def test_policy_tool_uses_phase2_rag(monkeypatch):
    monkeypatch.setattr("rag.rag_chain.ask_question", lambda question: {"answer": "Policy answer"})
    assert tools.search_inventory_policy.invoke({"question": "What is reorder point?"}) == "Policy answer"
