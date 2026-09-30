from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

import requests
from langchain_core.tools import StructuredTool
from opentelemetry import trace

from agent.tools import search_inventory_policy
from . import mcp_tools
from .session_manager import ChatSession, SessionManager

try:
    from langsmith import traceable
except ImportError:  # pragma: no cover
    def traceable(project_name: str):
        del project_name
        return lambda function: function


tracer = trace.get_tracer("poc-07-mcp-chat")
sessions = SessionManager()


def discover_local_model() -> str | None:
    """Return an already installed Ollama model, without pulling anything."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=1)
        response.raise_for_status()
        models = response.json().get("models", [])
        return models[0].get("name") if models else None
    except (requests.RequestException, ValueError, AttributeError, IndexError):
        return None


def _structured_tools() -> list[StructuredTool]:
    return [
        StructuredTool.from_function(mcp_tools.update_stock, description="Record a stock movement for a product."),
        StructuredTool.from_function(mcp_tools.create_purchase_order, description="Create a purchase order for a supplier."),
        StructuredTool.from_function(mcp_tools.get_low_stock_products, description="Get low stock and out-of-stock products."),
        StructuredTool.from_function(mcp_tools.get_supplier_catalog, description="Get a supplier catalog with prices."),
        StructuredTool.from_function(mcp_tools.get_purchase_orders, description="List purchase orders with optional filters."),
        StructuredTool.from_function(mcp_tools.get_inventory_dashboard, description="Get inventory dashboard metrics."),
    ]


CREATE_VERBS = ("create", "add", "new")
DEFAULT_UNIT_OF_MEASURE = {
    "grocery": "kg",
    "electronics": "pieces",
    "clothing": "pieces",
    "household": "pieces",
    "personal_care": "kg",
}
CATEGORY_DEFAULT_PRICING = {
    "grocery": {"cost_price": 50.0, "unit_price": 70.0},
    "electronics": {"cost_price": 2000.0, "unit_price": 2800.0},
    "clothing": {"cost_price": 300.0, "unit_price": 500.0},
    "household": {"cost_price": 150.0, "unit_price": 220.0},
    "personal_care": {"cost_price": 80.0, "unit_price": 120.0},
}
PRODUCT_UPDATE_FIELDS = ("name", "category", "unit_price", "cost_price", "unit_of_measure", "reorder_point", "reorder_quantity", "supplier_id")
PRODUCT_NUMERIC_FIELDS = {"unit_price", "cost_price", "reorder_point", "reorder_quantity", "supplier_id"}
SUPPLIER_UPDATE_FIELDS = ("name", "contact_email", "payment_terms_days", "lead_time_days", "is_active")
SUPPLIER_NUMERIC_FIELDS = {"payment_terms_days", "lead_time_days"}
NUMBER_PATTERN = r"\b(\d+)\b"


def _starts_with_verb(lowered: str, verbs: tuple[str, ...]) -> bool:
    return bool(re.match(rf"^\s*(?:{'|'.join(verbs)})\b", lowered))


def _extract_field_updates(text: str, fields: tuple[str, ...]) -> dict[str, str]:
    updates: dict[str, str] = {}
    for field in fields:
        alias = field.replace("_", " ")
        pattern = rf"(?:{re.escape(field)}|{re.escape(alias)})\s*(?:to|=|:)\s*([A-Za-z0-9_.\-@]+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            updates[field] = match.group(1).strip()
    return updates


def _coerce_numeric_updates(updates: dict[str, str], numeric_fields: set[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in updates.items():
        if key in numeric_fields:
            payload[key] = float(value) if "." in value else int(value)
        elif key == "is_active":
            payload[key] = value.strip().lower() in {"true", "1", "yes", "active"}
        else:
            payload[key] = value
    return payload


def _resolve_supplier_choice(question: str, options: dict[str, str]) -> int | None:
    stripped = question.strip()
    if stripped in options:
        return int(stripped)
    lowered_question = question.lower()
    for supplier_id, name in options.items():
        if name.lower() in lowered_question:
            return int(supplier_id)
    return None


def _reference_products(category: str | None) -> list[dict[str, Any]]:
    if not category:
        return []
    products = mcp_tools.list_products(category=category)
    return products if isinstance(products, list) else []


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _autofill_product_defaults(payload: dict[str, Any]) -> set[str]:
    """Fill cost/price/reorder/UOM from same-category products, falling back to category defaults."""
    auto_filled: set[str] = set()
    category = payload.get("category")
    references = _reference_products(category)

    if "unit_of_measure" not in payload:
        payload["unit_of_measure"] = DEFAULT_UNIT_OF_MEASURE.get(category, "pieces")
        auto_filled.add("unit_of_measure")

    fallback_pricing = CATEGORY_DEFAULT_PRICING.get(category, {"cost_price": 100.0, "unit_price": 150.0})
    if "cost_price" not in payload:
        reference_costs = [p["cost_price"] for p in references if isinstance(p.get("cost_price"), (int, float))]
        payload["cost_price"] = _average(reference_costs) or fallback_pricing["cost_price"]
        auto_filled.add("cost_price")
    if "unit_price" not in payload:
        reference_prices = [p["unit_price"] for p in references if isinstance(p.get("unit_price"), (int, float))]
        payload["unit_price"] = _average(reference_prices) or fallback_pricing["unit_price"]
        auto_filled.add("unit_price")

    if "reorder_point" not in payload:
        reference_points = [p["reorder_point"] for p in references if isinstance(p.get("reorder_point"), (int, float))]
        payload["reorder_point"] = round(_average(reference_points) or 10)
        auto_filled.add("reorder_point")
    if "reorder_quantity" not in payload:
        reference_quantities = [p["reorder_quantity"] for p in references if isinstance(p.get("reorder_quantity"), (int, float))]
        payload["reorder_quantity"] = round(_average(reference_quantities) or 50)
        auto_filled.add("reorder_quantity")

    return auto_filled


def _product_confirmation_summary(payload: dict[str, Any], auto_filled: set[str], supplier_auto_selected: bool) -> str:
    def label(field: str) -> str:
        suffix = " (auto-estimated)" if field in auto_filled else ""
        return f"{payload.get(field)}{suffix}"

    lines = [
        "Creating product with the following details:",
        f"- Name: {payload.get('name')}",
        f"- Category: {payload.get('category')}",
        f"- Unit of measure: {label('unit_of_measure')}",
        f"- Cost price: {label('cost_price')}",
        f"- Unit price: {label('unit_price')}",
        f"- Reorder point: {label('reorder_point')}",
        f"- Reorder quantity: {label('reorder_quantity')}",
    ]
    if payload.get("supplier_id") is not None:
        suffix = " (auto-selected)" if supplier_auto_selected else ""
        lines.append(f"- Supplier id: {payload['supplier_id']}{suffix}")
    else:
        lines.append("- Supplier: none assigned")
    return "\n".join(lines)


def _resolve_product_supplier(question: str, payload: dict[str, Any], session) -> tuple[dict[str, Any] | None, bool]:
    """Resolve supplier_id for a new product. Returns (early_response, supplier_auto_selected)."""
    if session and session.state.get("supplier_options"):
        chosen = _resolve_supplier_choice(question, session.state["supplier_options"])
        if chosen is None:
            return {"output": "Please choose one of the listed supplier ids.", "tools_used": []}, False
        payload["supplier_id"] = chosen
        session.state.pop("supplier_options", None)
        return None, False

    if "supplier_id" in payload:
        return None, False

    suppliers = mcp_tools.list_suppliers()
    active = [s for s in suppliers if s.get("is_active", True)] if isinstance(suppliers, list) else []
    if len(active) == 1:
        payload["supplier_id"] = active[0]["id"]
        return None, True
    if len(active) > 1:
        if session:
            session.state.update({
                "pending_intent": "create_product",
                "draft": payload,
                "supplier_options": {str(s["id"]): s["name"] for s in active},
            })
        names = ", ".join(f"{s['id']}: {s['name']}" for s in active)
        return {"output": f"Multiple active suppliers exist. Which supplier should I use? Options: {names}", "tools_used": []}, False
    # Zero active suppliers or a lookup error: proceed without blocking product creation.
    return None, False


def _finalize_product_creation(question: str, payload: dict[str, Any], session) -> dict[str, Any]:
    """Ask only for truly missing fields, auto-fill reasonable defaults, then resolve a supplier."""
    missing = _missing_product_fields(payload)
    if missing:
        if session:
            session.state.update({"pending_intent": "create_product", "draft": payload})
        return _ask_for_fields(missing)

    auto_filled = _autofill_product_defaults(payload)
    early_response, supplier_auto_selected = _resolve_product_supplier(question, payload, session)
    if early_response is not None:
        return early_response

    if session:
        session.state.clear()
    summary = _product_confirmation_summary(payload, auto_filled, supplier_auto_selected)
    outcome = _tool_result("create_product", mcp_tools.create_product(payload))
    outcome["output"] = f"{summary}\n\n{outcome['output']}"
    return outcome


def _enrich_low_stock_item(item: dict[str, Any]) -> dict[str, Any] | None:
    if all(key in item for key in ("supplier_id", "cost_price", "reorder_quantity")):
        return item
    product_id = item.get("id") or item.get("product_id")
    if not product_id:
        return None
    detail = mcp_tools._get(f"/products/{product_id}")
    if not isinstance(detail, dict) or "error" in detail:
        return None
    return {
        **item,
        "id": detail.get("id", product_id),
        "supplier_id": detail.get("supplier_id"),
        "cost_price": detail.get("cost_price", 0.01),
        "reorder_quantity": detail.get("reorder_quantity", 1),
    }


def _group_low_stock_by_supplier(items: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for raw_item in items:
        item = _enrich_low_stock_item(raw_item)
        if item is None or item.get("supplier_id") is None:
            continue
        grouped.setdefault(item["supplier_id"], []).append(item)
    return grouped


def _po_items_payload(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"product_id": item["id"], "quantity_ordered": item.get("reorder_quantity", 1), "unit_cost": item.get("cost_price", 0.01)}
        for item in items
        if item.get("id")
    ]


def _create_po_for_low_stock_immediately() -> dict[str, Any]:
    low_stock = mcp_tools.get_low_stock_products()
    if isinstance(low_stock, dict) and "error" in low_stock:
        return {"output": f"Could not read low stock items: {low_stock['error']}", "tools_used": ["get_low_stock_products"]}
    if not low_stock:
        return {"output": "No low stock products need a purchase order right now.", "tools_used": ["get_low_stock_products"]}

    grouped = _group_low_stock_by_supplier(low_stock)
    if not grouped:
        return {
            "output": "Low stock items exist but none have an assigned supplier, so I cannot create a purchase order automatically.",
            "tools_used": ["get_low_stock_products"],
        }

    created: list[Any] = []
    for supplier_id, items in grouped.items():
        po_items = _po_items_payload(items)
        if not po_items:
            continue
        result = mcp_tools.create_purchase_order(supplier_id, date.today().isoformat(), po_items)
        if isinstance(result, dict) and "error" not in result:
            created.append(result)

    if not created:
        return {"output": "Could not create a purchase order for the low stock items.", "tools_used": ["get_low_stock_products"]}

    lines = "\n".join(f"- {po.get('po_number', po.get('id'))} for supplier {po.get('supplier_id')}" for po in created)
    return {
        "output": f"Created {len(created)} purchase order(s) for low stock items:\n{lines}",
        "tools_used": ["create_purchase_order"],
        "tool_traces": [{"tool": "create_purchase_order", "result": po} for po in created],
    }


class LocalReActExecutor:
    """AgentExecutor-compatible local ReAct executor for corporate offline use."""

    def __init__(self, tools: list[StructuredTool]):
        self.tools = tools
        self.max_iterations = 5
        self.handle_parsing_errors = True
        self.model = discover_local_model()

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        question = str(payload.get("input", "")).strip()
        lowered = question.lower()
        session = payload.get("session")

        pending_result = _handle_pending_intent(question, lowered, session)
        if pending_result is not None:
            return pending_result

        mentions_product = "product" in lowered
        mentions_supplier = "supplier" in lowered
        mentions_po = bool(re.search(r"\bpo\b", lowered)) or "purchase order" in lowered

        for handler in (
            lambda: _handle_receive_and_po_commands(lowered, session, mentions_po),
            lambda: _handle_stock_command(question, lowered, session),
            lambda: _handle_product_command(question, lowered, session, mentions_product, mentions_po),
            lambda: _handle_supplier_command(question, lowered, session, mentions_supplier),
        ):
            result = handler()
            if result is not None:
                return result

        return _handle_report_and_fallback(question, lowered, self.tools)


def _handle_pending_intent(question: str, lowered: str, session) -> dict[str, Any] | None:
    """Resolve a follow-up message against whichever multi-turn intent is awaiting an answer."""
    if not session:
        return None
    intent = session.state.get("pending_intent")

    if intent == "create_product":
        product_payload = _product_followup(question, session.state.get("draft", {}))
        return _finalize_product_creation(question, product_payload, session)

    if intent == "create_supplier":
        supplier_payload = _supplier_followup(question, session.state.get("draft", {}))
        missing = _missing_supplier_fields(supplier_payload)
        if missing:
            session.state["draft"] = supplier_payload
            return _ask_for_fields(missing)
        session.state.clear()
        return _tool_result("create_supplier", mcp_tools.create_supplier(supplier_payload))

    if intent == "update_stock":
        quantity_match = re.search(r"\d+", question)
        if not quantity_match:
            return {"output": "Please provide a numeric quantity.", "tools_used": []}
        quantity = int(quantity_match.group(0))
        product_id = session.state.get("product_id")
        movement = session.state.get("movement_type", "receipt")
        session.state.clear()
        return _tool_result("update_stock", mcp_tools.update_stock(product_id, movement, quantity))

    if intent == "confirm_low_stock_po":
        return _resolve_low_stock_po_confirmation(lowered, session)

    return None


def _resolve_low_stock_po_confirmation(lowered: str, session) -> dict[str, Any]:
    if lowered not in {"yes", "y", "confirm", "approved", "do it", "create it"}:
        session.state.clear()
        return {"output": "Understood. I did not create a purchase order.", "tools_used": []}

    items = session.state.get("low_stock_items", [])
    grouped = _group_low_stock_by_supplier(items)
    session.state.clear()
    if len(grouped) == 1:
        supplier_id, supplier_items = next(iter(grouped.items()))
        po_items = _po_items_payload(supplier_items)
        if po_items:
            return _tool_result(
                "create_purchase_order",
                mcp_tools.create_purchase_order(supplier_id, date.today().isoformat(), po_items),
            )
    return {"output": "Please provide the supplier ID and quantities before I create the purchase order.", "tools_used": []}


def _handle_receive_and_po_commands(lowered: str, session, mentions_po: bool) -> dict[str, Any] | None:
    if ("receive" in lowered or "received" in lowered) and mentions_po:
        order_id = _first_number(lowered)
        if order_id is None:
            return {"output": "Which purchase order ID should I receive?", "tools_used": []}
        return _tool_result("receive_purchase_order", mcp_tools.receive_purchase_order(order_id))

    if "create po" in lowered or "create purchase order" in lowered:
        if "low stock" in lowered:
            return _create_po_for_low_stock_immediately()
        if "those items" in lowered or "them" in lowered:
            low_stock = mcp_tools.get_low_stock_products()
            if session:
                session.state["pending_intent"] = "confirm_low_stock_po"
                session.state["low_stock_items"] = low_stock
            return {
                "output": f"I found these low-stock items:\n{json.dumps(low_stock, default=str, indent=2)}\nShould I prepare a purchase order recommendation?",
                "tools_used": ["get_low_stock_products"],
                "tool_traces": [{"tool": "get_low_stock_products", "result": low_stock}],
            }
        return {"output": "Which supplier ID and product quantities should I use for the purchase order?", "tools_used": []}

    return None


def _handle_stock_command(question: str, lowered: str, session) -> dict[str, Any] | None:
    if not any(term in lowered for term in ("update stock", "add stock", "receive stock", "sell stock")):
        return None

    numbers = re.findall(NUMBER_PATTERN, question)
    product_id = int(numbers[0]) if numbers else None
    if product_id is None:
        return {"output": "Which product id should I update stock for?", "tools_used": []}

    quantity = int(numbers[-1]) if len(numbers) >= 2 else None
    movement = "sale" if "sell" in lowered else "receipt"
    if quantity is None:
        if session:
            session.state.update({"pending_intent": "update_stock", "product_id": product_id, "movement_type": movement})
        return {"output": f"How many units should I use for product {product_id}?", "tools_used": []}
    return _tool_result("update_stock", mcp_tools.update_stock(product_id, movement, quantity))


def _handle_product_command(question: str, lowered: str, session, mentions_product: bool, mentions_po: bool) -> dict[str, Any] | None:
    if any(verb in lowered for verb in ("delete", "remove")) and mentions_product:
        product_id = _first_number(question)
        if product_id is None:
            return {"output": "Which product id should I delete?", "tools_used": []}
        return _tool_result("delete_product", mcp_tools.delete_product(product_id))

    if "update" in lowered and mentions_product:
        product_id = _first_number(question)
        if product_id is None:
            return {"output": "Which product id should I update?", "tools_used": []}
        updates = _extract_field_updates(question, PRODUCT_UPDATE_FIELDS)
        if not updates:
            return {"output": "What field and value would you like to update? Example: unit_price to 150.", "tools_used": []}
        update_payload = _coerce_numeric_updates(updates, PRODUCT_NUMERIC_FIELDS)
        return _tool_result("update_product", mcp_tools.update_product(product_id, update_payload))

    if _starts_with_verb(lowered, CREATE_VERBS) and mentions_product and not mentions_po:
        product_payload = _product_payload(question, {})
        return _finalize_product_creation(question, product_payload, session)

    return None


def _handle_supplier_command(question: str, lowered: str, session, mentions_supplier: bool) -> dict[str, Any] | None:
    if "update" in lowered and mentions_supplier:
        supplier_id = _first_number(question)
        if supplier_id is None:
            return {"output": "Which supplier id should I update?", "tools_used": []}
        updates = _extract_field_updates(question, SUPPLIER_UPDATE_FIELDS)
        if not updates:
            return {"output": "What field and value would you like to update? Example: lead_time_days to 10.", "tools_used": []}
        update_payload = _coerce_numeric_updates(updates, SUPPLIER_NUMERIC_FIELDS)
        return _tool_result("update_supplier", mcp_tools.update_supplier(supplier_id, update_payload))

    if _starts_with_verb(lowered, CREATE_VERBS) and mentions_supplier:
        supplier_payload = _supplier_payload(question, {})
        missing = _missing_supplier_fields(supplier_payload)
        if missing:
            if session:
                session.state.update({"pending_intent": "create_supplier", "draft": supplier_payload})
            return _ask_for_fields(missing)
        return _tool_result("create_supplier", mcp_tools.create_supplier(supplier_payload))

    return None


def _classify_fallback_tool(lowered: str) -> str:
    if any(term in lowered for term in ("low stock", "out of stock", "reorder", "replenish", "alert")):
        return "get_low_stock_products"
    if "supplier" in lowered and any(term in lowered for term in ("catalog", "price", "product")):
        return "get_supplier_catalog"
    if any(term in lowered for term in ("purchase order", "purchase orders", "pos", "orders")):
        return "get_purchase_orders"
    if any(term in lowered for term in ("policy", "procedure", "rule", "what does", "mean")):
        return "search_inventory_policy"
    return "get_inventory_dashboard"


def _handle_report_and_fallback(question: str, lowered: str, tools: list[StructuredTool]) -> dict[str, Any]:
    if "report" in lowered:
        return _tool_result("generate_inventory_report", mcp_tools.generate_inventory_report())

    tool_name = _classify_fallback_tool(lowered)
    if tool_name == "search_inventory_policy":
        policy_result = search_inventory_policy.invoke({"question": question})
        return {"output": policy_result, "tools_used": ["search_inventory_policy"], "tool_traces": [{"tool": "search_inventory_policy", "result": policy_result}]}

    arguments: dict[str, Any] = {"supplier_id": _number_after(lowered, "supplier") or 0} if tool_name == "get_supplier_catalog" else {}
    next(tool for tool in tools if tool.name == tool_name)
    result = getattr(mcp_tools, tool_name)(**arguments)
    return _tool_result(tool_name, result)


def _tool_result(tool_name: str, result: Any) -> dict[str, Any]:
    output = result if isinstance(result, str) else json.dumps(result, default=str, indent=2)
    return {"output": output, "tools_used": [tool_name], "tool_traces": [{"tool": tool_name, "result": result}]}


def _ask_for_fields(fields: list[str]) -> dict[str, Any]:
    return {"output": "Please provide: " + ", ".join(fields) + ".", "tools_used": []}


def _first_number(value: str) -> int | None:
    match = re.search(NUMBER_PATTERN, value)
    return int(match.group(1)) if match else None


def _last_number(value: str) -> int | None:
    matches = re.findall(NUMBER_PATTERN, value)
    return int(matches[-1]) if matches else None


def _product_payload(question: str, draft: dict[str, Any]) -> dict[str, Any]:
    payload = dict(draft)
    lowered = question.lower()
    category = next((item for item in ("grocery", "electronics", "clothing", "household", "personal_care") if item.replace("_", " ") in lowered), None)
    if category:
        payload["category"] = category
    name_match = re.search(r"(?:product|item)\s+(?:named|called)\s+([\w -]+?)(?=\s+(?:category|cost|selling|price|supplier)\b|$)", question, re.I)  # NOSONAR
    if name_match:
        payload["name"] = name_match.group(1).strip()
    elif not payload.get("name"):
        generic_name = re.search(r"(?:create|add|new)\s+(?:a\s+)?([\w -]+?)\s+product\b", question, re.I)
        if generic_name and generic_name.group(1).strip().lower() not in {"a", "the", "grocery", "electronics", "clothing", "household", "personal care"}:
            payload["name"] = generic_name.group(1).strip().title()
    costs = re.findall(r"(?:cost|buying)\s*(?:price)?\s*(?:is|:)?\s*(\d+(?:\.\d+)?)", question, re.I)
    selling = re.findall(r"(?:selling|sale)\s*(?:price)?\s*(?:is|:)?\s*(\d+(?:\.\d+)?)", question, re.I)
    if costs: payload["cost_price"] = float(costs[-1])
    if selling: payload["unit_price"] = float(selling[-1])
    return payload


def _missing_product_fields(payload: dict[str, Any]) -> list[str]:
    return [field for field in ("name", "category") if field not in payload]


def _product_followup(question: str, draft: dict[str, Any]) -> dict[str, Any]:
    payload = _product_payload(question, draft)
    missing = _missing_product_fields(payload)
    if missing and "name" in missing and not re.search(r"(?:cost|selling|price|category|supplier)", question, re.I):
        payload["name"] = question.strip().title()
    elif missing and "category" in missing:
        category = question.strip().lower().replace(" ", "_")
        if category in {"grocery", "electronics", "clothing", "household", "personal_care"}:
            payload["category"] = category
    elif missing and "cost_price" in missing and re.fullmatch(r"\s*\d+(?:\.\d+)?\s*", question):
        payload["cost_price"] = float(question)
    elif missing and "unit_price" in missing and re.fullmatch(r"\s*\d+(?:\.\d+)?\s*", question):
        payload["unit_price"] = float(question)
    return payload


def _supplier_payload(question: str, draft: dict[str, Any]) -> dict[str, Any]:
    payload = dict(draft)
    match = re.search(r"supplier\s+(?:named|called)?\s*([\w &.-]+?)(?=\s+(?:email|lead|payment)\b|$)", question, re.I)  # NOSONAR
    if match: payload["name"] = match.group(1).strip()
    email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", question)
    if email: payload["contact_email"] = email.group(0)
    lead = re.search(r"lead(?: time)?\s*(?:is|:)?\s*(\d+)", question, re.I)
    payment = re.search(r"payment(?: terms)?\s*(?:is|:)?\s*(\d+)", question, re.I)
    if lead: payload["lead_time_days"] = int(lead.group(1))
    if payment: payload["payment_terms_days"] = int(payment.group(1))
    payload.setdefault("lead_time_days", 7)
    payload.setdefault("payment_terms_days", 30)
    if payload.get("name"):
        payload.setdefault("supplier_code", re.sub(r"[^A-Z0-9]", "", payload["name"].upper())[:16] or "SUPPLIER")
    return payload


def _missing_supplier_fields(payload: dict[str, Any]) -> list[str]:
    return [field for field in ("name",) if field not in payload]


def _supplier_followup(question: str, draft: dict[str, Any]) -> dict[str, Any]:
    payload = _supplier_payload(question, draft)
    labeled_lead = re.search(r"lead[_ ]?time[_ ]?days?\s*:\s*(\d+)", question, re.I)
    labeled_payment = re.search(r"payment[_ ]?terms[_ ]?days?\s*:\s*(\d+)", question, re.I)
    if labeled_lead:
        payload["lead_time_days"] = int(labeled_lead.group(1))
    if labeled_payment:
        payload["payment_terms_days"] = int(labeled_payment.group(1))
    missing = _missing_supplier_fields(payload)
    if missing and "name" in missing and "@" not in question and not question.strip().isdigit() and not labeled_lead and not labeled_payment:
        payload["name"] = question.strip()
        payload.setdefault("supplier_code", re.sub(r"[^A-Z0-9]", "", payload["name"].upper())[:16] or "SUPPLIER")
    elif missing and "contact_email" in missing and "@" in question:
        payload["contact_email"] = question.strip()
    elif missing and "lead_time_days" in missing and question.strip().isdigit():
        payload["lead_time_days"] = int(question)
    elif missing and "payment_terms_days" in missing and question.strip().isdigit():
        payload["payment_terms_days"] = int(question)
    return payload


def _number_after(question: str, label: str) -> int | None:
    fragment = question.split(label, 1)[1].lstrip(" :#-id")
    digits = "".join(character for character in fragment if character.isdigit())
    return int(digits) if digits else None


def build_chat_executor() -> LocalReActExecutor:
    return LocalReActExecutor(_structured_tools())


@traceable(project_name="AI-Readiness-POC-07-P4")
def process_message(message: str, session_id: str = "default", authorization: str | None = None) -> dict[str, Any]:
    session = sessions.get(session_id)
    session.add_message("user", message)
    token_state = mcp_tools.set_api_token(authorization)
    try:
        with tracer.start_as_current_span("mcp.chat.process") as span:
            span.set_attribute("poc_id", "POC-07")
            span.set_attribute("phase", "P4")
            result = build_chat_executor().invoke({"input": message, "chat_history": session.get_history_for_llm(), "session": session})
            session.add_message("assistant", result.get("output", ""))
            return {"output": result.get("output", ""), "session_id": session_id, "tools_used": result.get("tools_used", []), "tool_traces": result.get("tool_traces", []), "history": session.get_history_for_llm()}
    except Exception as exc:
        session.add_message("assistant", f"Error: {exc}")
        return {"output": f"Error: {exc}", "session_id": session_id, "tools_used": [], "tool_traces": [], "history": session.get_history_for_llm()}
    finally:
        mcp_tools.reset_api_token(token_state)
