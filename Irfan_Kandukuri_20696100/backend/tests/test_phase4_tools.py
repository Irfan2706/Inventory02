from mcp_server import mcp_tools


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_get_low_stock_products(monkeypatch):
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *args, **kwargs: Response([{"sku": "A"}]))
    assert mcp_tools.get_low_stock_products() == [{"sku": "A"}]


def test_get_supplier_catalog_uses_supplier_path(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *args, **kwargs: calls.append((args, kwargs)) or Response([]))
    mcp_tools.get_supplier_catalog(4)
    assert calls[0][0][:2] == ("GET", "http://localhost:8000/api/v1/suppliers/4/catalog")


def test_get_purchase_orders_passes_filters(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *args, **kwargs: calls.append(kwargs) or Response([]))
    mcp_tools.get_purchase_orders("draft", 2)
    assert calls[0]["params"] == {"status": "draft", "supplier_id": 2}


def test_update_stock_uses_existing_stock_route(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *args, **kwargs: calls.append((args, kwargs)) or Response({"message": "ok"}))
    assert mcp_tools.update_stock(3, "receipt", 5)["message"] == "ok"
    assert calls[0][0][0:2] == ("PATCH", "http://localhost:8000/api/v1/stock/products/3")


def test_create_purchase_order_posts_payload(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *args, **kwargs: calls.append(kwargs) or Response({"id": 1}))
    mcp_tools.create_purchase_order(2, "2026-08-24", [{"product_id": 1, "quantity_ordered": 2, "unit_cost": 4}])
    assert calls[0]["json"]["supplier_id"] == 2


def test_dashboard_returns_api_unavailable(monkeypatch):
    def fail(*args, **kwargs):
        raise mcp_tools.requests.exceptions.ConnectionError()
    monkeypatch.setattr(mcp_tools.requests, "request", fail)
    assert mcp_tools.get_inventory_dashboard() == {"error": "API unavailable"}


def test_timeout_is_consistent(monkeypatch):
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *args, **kwargs: (_ for _ in ()).throw(mcp_tools.requests.exceptions.Timeout()))
    assert mcp_tools.get_inventory_dashboard() == {"error": "API request timed out"}


def test_token_is_forwarded(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *args, **kwargs: calls.append(kwargs) or Response({}))
    state = mcp_tools.set_api_token("token")
    try:
        mcp_tools.get_inventory_dashboard()
    finally:
        mcp_tools.reset_api_token(state)
    assert calls[0]["headers"] == {"Authorization": "Bearer token"}


def test_request_timeout_and_unexpected_error(monkeypatch):
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *args, **kwargs: (_ for _ in ()).throw(mcp_tools.requests.exceptions.Timeout()))
    assert mcp_tools._request("GET", "/dashboard") == {"error": "API request timed out"}
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("bad response")))
    assert mcp_tools._request("GET", "/dashboard") == {"error": "bad response"}


def test_request_http_error_detail_and_invalid_detail(monkeypatch):
    class Response:
        def json(self):
            return {"detail": "not found"}

    error = mcp_tools.requests.exceptions.HTTPError("failed", response=Response())
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *args, **kwargs: (_ for _ in ()).throw(error))
    assert mcp_tools._request("GET", "/missing") == {"error": "not found"}

    class InvalidResponse:
        def json(self):
            raise ValueError("invalid")

    error = mcp_tools.requests.exceptions.HTTPError("failed", response=InvalidResponse())
    monkeypatch.setattr(mcp_tools.requests, "request", lambda *args, **kwargs: (_ for _ in ()).throw(error))
    assert mcp_tools._request("GET", "/missing") == {"error": "failed"}


def test_extended_tools_use_existing_api(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_tools, "_post", lambda path, payload: calls.append((path, payload)) or {"id": 1})
    monkeypatch.setattr(mcp_tools, "_request", lambda method, path, **kwargs: calls.append((method, path)) or {"status": "received"})
    assert mcp_tools.create_product({"name": "Rice"})["id"] == 1
    assert mcp_tools.create_supplier({"name": "ABC"})["id"] == 1
    assert mcp_tools.receive_purchase_order(3)["status"] == "received"
    assert calls[0][0] == "/products"
    assert calls[1][0] == "/suppliers"
    assert calls[2] == ("PATCH", "/orders/3/receive")