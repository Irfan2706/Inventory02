from __future__ import annotations

import contextvars
from typing import Any

import requests
import structlog
from opentelemetry import trace


logger = structlog.get_logger()
tracer = trace.get_tracer("poc-07-mcp")
BASE_URL = "http://localhost:8000/api/v1"
_api_token: contextvars.ContextVar[str | None] = contextvars.ContextVar("mcp_api_token", default=None)


def set_api_token(token: str | None):
    return _api_token.set(token)


def reset_api_token(token_state: contextvars.Token) -> None:
    _api_token.reset(token_state)


def _headers() -> dict[str, str]:
    token = _api_token.get()
    if not token:
        return {}
    return {"Authorization": token if token.lower().startswith("bearer ") else f"Bearer {token}"}


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    requester=None,
):
    try:
        url = f"{BASE_URL}{path}"
        if requester is None:
            response = requests.request(method, url, params=params or {}, json=payload, headers=_headers(), timeout=10)
        else:
            response = requester(url, params=params or {}, json=payload, headers=_headers(), timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "API unavailable"}
    except requests.exceptions.Timeout:
        return {"error": "API request timed out"}
    except requests.exceptions.HTTPError as exc:
        detail = None
        if exc.response is not None:
            try:
                detail = exc.response.json().get("detail")
            except (ValueError, AttributeError):
                detail = None
        return {"error": str(detail or exc)}
    except Exception as exc:
        return {"error": str(exc)}


def _get(path: str, params: dict[str, Any] | None = None):
    return _request("GET", path, params=params)


def _post(path: str, payload: dict[str, Any]):
    return _request("POST", path, payload=payload)


def _patch(path: str, payload: dict[str, Any]):
    return _request("PATCH", path, payload=payload)


def _delete(path: str):
    return _request("DELETE", path)


def _tool_span(name: str):
    return tracer.start_as_current_span(f"mcp.tool.{name}")


def _log_tool(name: str, **fields: Any) -> None:
    logger.info("mcp_tool_called", poc_id="POC-07", phase="P4", tool=name, **fields)


def update_stock(product_id: int, movement_type: str, quantity: int, reference_number: str | None = None, notes: str | None = None, *, _requester=None) -> dict:
    with _tool_span("update_stock") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        result = _request("PATCH", f"/stock/products/{product_id}", payload={"movement_type": movement_type, "quantity": quantity, "reference_number": reference_number, "notes": notes}, requester=_requester)
        _log_tool("update_stock", product_id=product_id)
        return result


def create_purchase_order(supplier_id: int, order_date: str, items: list, expected_delivery: str | None = None, *, _requester=None) -> dict:
    with _tool_span("create_purchase_order") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        result = _request("POST", "/orders", payload={"supplier_id": supplier_id, "order_date": order_date, "items": items, "expected_delivery": expected_delivery}, requester=_requester)
        _log_tool("create_purchase_order", supplier_id=supplier_id)
        return result


def get_low_stock_products(*, _requester=None) -> list | dict:
    with _tool_span("get_low_stock_products") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        result = _request("GET", "/stock/low-alerts", requester=_requester)
        _log_tool("get_low_stock_products")
        return result


def get_supplier_catalog(supplier_id: int, *, _requester=None) -> list | dict:
    with _tool_span("get_supplier_catalog") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        result = _request("GET", f"/suppliers/{supplier_id}/catalog", requester=_requester)
        _log_tool("get_supplier_catalog", supplier_id=supplier_id)
        return result


def get_purchase_orders(status: str | None = None, supplier_id: int | None = None, *, _requester=None) -> list | dict:
    with _tool_span("get_purchase_orders") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        params = {key: value for key, value in {"status": status, "supplier_id": supplier_id}.items() if value is not None}
        result = _request("GET", "/orders", params=params, requester=_requester)
        _log_tool("get_purchase_orders")
        return result


def list_products(category: str | None = None, *, _requester=None) -> list | dict:
    with _tool_span("list_products") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        params = {"category": category} if category else None
        result = _request("GET", "/products", params=params, requester=_requester)
        _log_tool("list_products")
        return result


def get_inventory_dashboard(*, _requester=None) -> dict:
    with _tool_span("get_inventory_dashboard") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        result = _request("GET", "/dashboard", requester=_requester)
        _log_tool("get_inventory_dashboard")
        return result


def create_product(payload: dict[str, Any]) -> dict:
    with _tool_span("create_product") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        result = _post("/products", payload)
        _log_tool("create_product", product_name=payload.get("name"))
        return result


def create_supplier(payload: dict[str, Any]) -> dict:
    with _tool_span("create_supplier") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        result = _post("/suppliers", payload)
        _log_tool("create_supplier", supplier_name=payload.get("name"))
        return result


def receive_purchase_order(order_id: int) -> dict:
    with _tool_span("receive_purchase_order") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        result = _request("PATCH", f"/orders/{order_id}/receive")
        _log_tool("receive_purchase_order", order_id=order_id)
        return result


def list_suppliers(*, _requester=None) -> list | dict:
    with _tool_span("list_suppliers") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        result = _request("GET", "/suppliers", requester=_requester)
        _log_tool("list_suppliers")
        return result


def update_product(product_id: int, payload: dict[str, Any]) -> dict:
    with _tool_span("update_product") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        result = _patch(f"/products/{product_id}", payload)
        _log_tool("update_product", product_id=product_id)
        return result


def delete_product(product_id: int) -> dict:
    with _tool_span("delete_product") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        result = _delete(f"/products/{product_id}")
        _log_tool("delete_product", product_id=product_id)
        return result


def update_supplier(supplier_id: int, payload: dict[str, Any]) -> dict:
    with _tool_span("update_supplier") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        result = _patch(f"/suppliers/{supplier_id}", payload)
        _log_tool("update_supplier", supplier_id=supplier_id)
        return result


def generate_inventory_report() -> dict:
    with _tool_span("generate_inventory_report") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P4")
        dashboard = _request("GET", "/dashboard")
        alerts = _request("GET", "/stock/low-alerts")
        _log_tool("generate_inventory_report")
        return {"dashboard": dashboard, "low_stock_alerts": alerts}


MCP_FUNCTIONS = [
    update_stock,
    create_purchase_order,
    get_low_stock_products,
    get_supplier_catalog,
    get_purchase_orders,
    get_inventory_dashboard,
    create_product,
    create_supplier,
    receive_purchase_order,
    list_suppliers,
    list_products,
    update_product,
    delete_product,
    update_supplier,
    generate_inventory_report,
]