from __future__ import annotations

import requests

try:
    from fastmcp import FastMCP
except ImportError:
    class FastMCP:
        """Local compatibility implementation when the optional MCP transport is absent."""
        def __init__(self, name: str):
            self.name = name
            self._tools = {}

        def tool(self):
            def decorator(function):
                self._tools[function.__name__] = function
                return function
            return decorator

        def run(self):
            raise RuntimeError("Install fastmcp to run the MCP transport; the HTTP chat API remains available.")

from . import mcp_tools as _tools

mcp = FastMCP("Inventory Management Server")


@mcp.tool()
def update_stock(product_id: int, movement_type: str, quantity: int, reference_number: str | None = None, notes: str | None = None) -> dict:
    return _tools.update_stock(product_id, movement_type, quantity, reference_number, notes, _requester=requests.post)


@mcp.tool()
def create_purchase_order(supplier_id: int, order_date: str, items: list, expected_delivery: str | None = None) -> dict:
    return _tools.create_purchase_order(supplier_id, order_date, items, expected_delivery, _requester=requests.post)


@mcp.tool()
def get_low_stock_products() -> list | dict:
    return _tools.get_low_stock_products(_requester=requests.get)


@mcp.tool()
def get_supplier_catalog(supplier_id: int) -> list | dict:
    return _tools.get_supplier_catalog(supplier_id, _requester=requests.get)


@mcp.tool()
def get_purchase_orders(status: str | None = None, supplier_id: int | None = None) -> list | dict:
    return _tools.get_purchase_orders(status, supplier_id, _requester=requests.get)


@mcp.tool()
def get_inventory_dashboard() -> dict:
    return _tools.get_inventory_dashboard(_requester=requests.get)


@mcp.tool()
def create_product(payload: dict) -> dict:
    return _tools.create_product(payload)


@mcp.tool()
def create_supplier(payload: dict) -> dict:
    return _tools.create_supplier(payload)


@mcp.tool()
def receive_purchase_order(order_id: int) -> dict:
    return _tools.receive_purchase_order(order_id)


@mcp.tool()
def list_suppliers() -> list | dict:
    return _tools.list_suppliers(_requester=requests.get)


@mcp.tool()
def list_products(category: str | None = None) -> list | dict:
    return _tools.list_products(category, _requester=requests.get)


@mcp.tool()
def update_product(product_id: int, payload: dict) -> dict:
    return _tools.update_product(product_id, payload)


@mcp.tool()
def delete_product(product_id: int) -> dict:
    return _tools.delete_product(product_id)


@mcp.tool()
def update_supplier(supplier_id: int, payload: dict) -> dict:
    return _tools.update_supplier(supplier_id, payload)


@mcp.tool()
def generate_inventory_report() -> dict:
    return _tools.generate_inventory_report()


if __name__ == "__main__":
    mcp.run()