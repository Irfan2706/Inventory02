from __future__ import annotations

import contextvars
from typing import Any

import requests
import structlog
from langchain.tools import tool
from opentelemetry import trace


logger = structlog.get_logger()
tracer = trace.get_tracer("poc-07-agent")
BASE_URL = "http://localhost:8000/api/v1"
_api_token: contextvars.ContextVar[str | None] = contextvars.ContextVar("agent_api_token", default=None)


def set_api_token(token: str | None):
    """Set the current request token used when tools call the existing API."""
    return _api_token.set(token)


def reset_api_token(token_state: contextvars.Token):
    _api_token.reset(token_state)


def _api_get(path: str, params: dict | None = None) -> dict | list:
    headers = {}
    if token := _api_token.get():
        headers["Authorization"] = token if token.lower().startswith("bearer ") else f"Bearer {token}"
    try:
        response = requests.get(
            f"{BASE_URL}{path}",
            params=params or {},
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "API unavailable"}
    except requests.exceptions.Timeout:
        return {"error": "API request timed out"}
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return {"error": "not_found"}
        return {"error": str(exc)}
    except Exception as exc:
        return {"error": str(exc)}


def _span(name: str):
    span = tracer.start_as_current_span(name)
    return span


@tool("get_low_stock_alerts")
def get_low_stock_alerts(query: str = "") -> str:
    """Use for low stock, out-of-stock, reorder, or inventory alert questions; returns products needing procurement attention."""
    del query
    with _span("tool.get_low_stock_alerts") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P3")
        data = _api_get("/stock/low-alerts")
        if isinstance(data, dict) and "error" in data:
            return f"Error: {data['error']}"
        if not data:
            return "No low stock alerts. All products are above reorder points."
        lines = [
            f"- {item.get('sku')}: {item.get('product_name')} - {item.get('message')}"
            for item in data[:20]
        ]
        logger.info("tool_called", poc_id="POC-07", phase="P3", tool="get_low_stock_alerts")
        return f"{len(data)} products need reorder:\n" + "\n".join(lines)


@tool("get_product_stock")
def get_product_stock(product_id: str) -> str:
    """Use for a specific product's current stock level, availability, reserved quantity, reorder settings, or recent movements."""
    with _span("tool.get_product_stock") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P3")
        data = _api_get(f"/products/{product_id}")
        if isinstance(data, dict) and "error" in data:
            return f"Product {product_id} not found." if data["error"] == "not_found" else f"Error: {data['error']}"
        stock = data.get("stock_level", {})
        logger.info("tool_called", poc_id="POC-07", phase="P3", tool="get_product_stock")
        return (
            f"Product: {data.get('sku')} - {data.get('name')}\n"
            f"  On hand: {stock.get('quantity_on_hand', 0)} {data.get('unit_of_measure', 'units')}, "
            f"Available: {stock.get('quantity_available', 0)}, Reserved: {stock.get('quantity_reserved', 0)}\n"
            f"  Reorder point: {data.get('reorder_point')}, Reorder qty: {data.get('reorder_quantity')}"
        )


@tool("get_supplier_catalog")
def get_supplier_catalog(supplier_id: str) -> str:
    """Use for supplier products, supplier pricing, catalog contents, or purchase-order product selection for a supplier."""
    with _span("tool.get_supplier_catalog") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P3")
        data = _api_get(f"/suppliers/{supplier_id}/catalog")
        if isinstance(data, dict) and "error" in data:
            return f"Supplier {supplier_id} catalog unavailable."
        if not data:
            return f"Supplier {supplier_id} has no products in catalog."
        lines = [f"- {item.get('sku')}: {item.get('name')} - cost {item.get('unit_cost')}" for item in data[:20]]
        logger.info("tool_called", poc_id="POC-07", phase="P3", tool="get_supplier_catalog")
        return f"Supplier {supplier_id} catalog ({len(data)} products):\n" + "\n".join(lines)


@tool("get_dashboard_stats")
def get_dashboard_stats(query: str = "") -> str:
    """Use for overall inventory counts, low and out-of-stock alerts, open purchase orders, or total inventory value."""
    del query
    with _span("tool.get_dashboard_stats") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P3")
        data = _api_get("/dashboard")
        if isinstance(data, dict) and "error" in data:
            return f"Dashboard unavailable: {data['error']}"
        logger.info("tool_called", poc_id="POC-07", phase="P3", tool="get_dashboard_stats")
        return (
            "Inventory Dashboard:\n"
            f"  Total products: {data.get('total_products', 0)}\n"
            f"  Low stock: {data.get('low_stock_count', 0)}\n"
            f"  Out of stock: {data.get('out_of_stock_count', 0)}\n"
            f"  Open POs: {data.get('open_po_count', 0)}\n"
            f"  Total stock value: {data.get('total_stock_value', 0):,.2f}"
        )


@tool("search_inventory_policy")
def search_inventory_policy(question: str) -> str:
    """Use for inventory rules, reorder points, purchase-order process, stock movements, supplier procedures, and best practices."""
    with _span("tool.search_inventory_policy") as span:
        span.set_attribute("poc_id", "POC-07")
        span.set_attribute("phase", "P3")
        try:
            from rag.rag_chain import ask_question

            result = ask_question(question)
            logger.info("tool_called", poc_id="POC-07", phase="P3", tool="search_inventory_policy")
            return result.get("answer", "No answer found.")
        except Exception as exc:
            return f"Policy search error: {exc}"


TOOLS = [
    get_low_stock_alerts,
    get_product_stock,
    get_supplier_catalog,
    get_dashboard_stats,
    search_inventory_policy,
]
