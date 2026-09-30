from __future__ import annotations

import contextvars
import functools
from datetime import datetime
from typing import Any

import requests
from opentelemetry import trace

from app.logging_config import get_logger

from .model_provider import get_local_llm
from .state import InventoryAnalysisState

try:
    from langsmith import traceable as _langsmith_traceable
except ImportError:  # pragma: no cover - optional observability dependency
    _langsmith_traceable = None

LANGSMITH_PROJECT = "AI-Readiness-POC-07-P5"
POC_ID = "POC-07"
PHASE = "P5"
BASE_URL = "http://localhost:8000/api/v1"
REQUEST_TIMEOUT_SECONDS = 10

logger = get_logger("multi_agent")
tracer = trace.get_tracer("poc07.multi_agent")
_api_token: contextvars.ContextVar[str | None] = contextvars.ContextVar("multi_agent_api_token", default=None)


def traceable(*args, **kwargs):
    """Wrap langsmith.traceable so tracing failures never break agent execution."""
    if _langsmith_traceable is None:
        def decorator(func):
            return func

        return decorator

    def decorator(func):
        traced = _langsmith_traceable(*args, **kwargs)(func)

        @functools.wraps(func)
        def safe_wrapper(*f_args, **f_kwargs):
            try:
                return traced(*f_args, **f_kwargs)
            except Exception:
                logger.warning("multi_agent_langsmith_trace_failed", reason="tracing unavailable; executing agent without tracing")
                return func(*f_args, **f_kwargs)

        return safe_wrapper

    return decorator


def set_api_token(token: str | None):
    return _api_token.set(token)


def reset_api_token(token_state: contextvars.Token):
    _api_token.reset(token_state)


def _auth_headers() -> dict[str, str]:
    token = _api_token.get()
    if not token:
        return {}
    return {"Authorization": token if token.lower().startswith("bearer ") else f"Bearer {token}"}


def _api_get(path: str) -> Any:
    try:
        response = requests.get(
            f"{BASE_URL}{path}",
            headers=_auth_headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.warning(
            "multi_agent_api_request_failed",
            path=path,
            error_type=type(exc).__name__,
        )
        return {"error": "The inventory service request could not be completed."}


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_mapping_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _round(value: float, digits: int = 2) -> float:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return 0.0


def _llm():
    """Factory for the local chat model; private test seam matching the Phase 5 spec (`multi_agent.agents._llm`)."""
    return get_local_llm()


def _generate_text(prompt: str, fallback: str) -> str:
    """Ask the local model for a short narrative, degrading gracefully to a deterministic fallback."""
    try:
        llm = _llm()
        if llm is None:
            return fallback
        response = llm.invoke(prompt)
        text = (getattr(response, "content", "") or "").strip()
        return text or fallback
    except Exception:
        logger.warning("multi_agent_llm_call_failed", reason="local model invocation failed; using deterministic narrative")
        return fallback


@traceable(project_name=LANGSMITH_PROJECT)
def demand_forecaster(state: InventoryAnalysisState) -> InventoryAnalysisState:
    """Agent 1: Fetch product data and forecast demand from stock movement history."""
    product_id = state["product_id"]
    errors = list(state["errors"])
    messages = list(state["messages"])

    with tracer.start_as_current_span("multi_agent.demand_forecaster") as span:
        span.set_attribute("poc_id", POC_ID)
        span.set_attribute("phase", PHASE)
        span.set_attribute("product_id", product_id)

        product_response = _api_get(f"/products/{product_id}")
        if isinstance(product_response, dict) and "error" in product_response:
            errors.append(f"Product fetch error: {product_response['error']}")
        elif not isinstance(product_response, dict):
            errors.append("Product fetch error: invalid response payload.")
        product_data = _as_mapping(product_response)
        if "error" in product_data:
            product_data = {}

        stock = product_data.get("stock_level") or {}
        quantity_available = stock.get("quantity_available", 0) or 0
        reorder_point = product_data.get("reorder_point", 0) or 0
        movements = product_data.get("movements") or []

        sales = [m for m in movements if m.get("movement_type") == "sale"]
        total_sold = sum(abs(m.get("quantity", 0)) for m in sales)
        sale_dates: list[datetime] = []
        for movement in sales:
            recorded_at = movement.get("recorded_at")
            if not recorded_at:
                continue
            try:
                sale_dates.append(datetime.fromisoformat(str(recorded_at).replace("Z", "+00:00")))
            except ValueError:
                continue

        if sale_dates:
            # Demand rate reflects the actual time elapsed since the earliest recorded sale,
            # not just the count of distinct sale dates, so a single old spike doesn't
            # permanently inflate the average once time has passed.
            elapsed_days = (datetime.now(sale_dates[0].tzinfo) - min(sale_dates)).days
            days_observed = max(elapsed_days, 1)
        else:
            days_observed = 1
        avg_daily_demand = _round(total_sold / days_observed) if sales else 0.0

        half = len(sales) // 2
        recent_half = sales[:half] if half else sales
        older_half = sales[half:] if half else []
        recent_avg = sum(abs(m.get("quantity", 0)) for m in recent_half) / max(len(recent_half), 1) if recent_half else 0
        older_avg = sum(abs(m.get("quantity", 0)) for m in older_half) / max(len(older_half), 1) if older_half else 0
        if len(sales) < 2:
            # A single data point cannot establish a trend direction.
            demand_trend = "unknown"
        elif recent_avg > older_avg * 1.1:
            demand_trend = "increasing"
        elif recent_avg < older_avg * 0.9:
            demand_trend = "decreasing"
        else:
            demand_trend = "stable"

        days_of_stock_remaining = _round(quantity_available / avg_daily_demand) if avg_daily_demand > 0 else 0.0

        if not product_data:
            stockout_risk = "unknown"
        elif quantity_available <= 0:
            stockout_risk = "high"
        elif reorder_point > 0 and quantity_available <= reorder_point:
            # The reorder point is always available real business data, even when no sales
            # history exists yet, so it takes priority over a demand-based day count.
            stockout_risk = "high"
        elif avg_daily_demand > 0 and days_of_stock_remaining <= 3:
            stockout_risk = "high"
        elif avg_daily_demand > 0 and days_of_stock_remaining <= 7:
            stockout_risk = "medium"
        else:
            stockout_risk = "low"

        if avg_daily_demand > 0:
            fallback_notes = (
                f"Average demand is {avg_daily_demand} units/day ({demand_trend}); "
                f"~{days_of_stock_remaining} days of stock remain, stockout risk is {stockout_risk}."
            )
        elif product_data:
            fallback_notes = (
                f"No recent sales history is available for this product; stockout risk is assessed as "
                f"{stockout_risk} based on {quantity_available} units available against a reorder point of {reorder_point}."
            )
        else:
            fallback_notes = "Demand could not be forecast because product data is unavailable."
        forecast_notes = fallback_notes
        if product_data:
            prompt = (
                "Summarize this product's demand outlook in exactly one sentence. "
                "Use only the numbers given below; do not invent statistics, dates, or market trends.\n"
                f"SKU: {product_data.get('sku', 'unknown')}, avg_daily_demand={avg_daily_demand}, "
                f"trend={demand_trend}, days_remaining={days_of_stock_remaining}, risk={stockout_risk}."
            )
            forecast_notes = _generate_text(prompt, fallback_notes)

        demand_forecast = {
            "avg_daily_demand": avg_daily_demand,
            "demand_trend": demand_trend,
            "days_of_stock_remaining": days_of_stock_remaining,
            "stockout_risk": stockout_risk,
            "forecast_notes": forecast_notes,
        }

        messages.append(f"Demand Forecaster: risk={stockout_risk}, trend={demand_trend}")
        logger.info("agent_complete", poc_id=POC_ID, phase=PHASE, agent="demand_forecaster")

    new_status = "error" if not product_data and errors else state["analysis_status"]
    return {
        **state,
        "product_data": product_data,
        "demand_forecast": demand_forecast,
        "analysis_status": new_status,
        "errors": errors,
        "messages": messages,
    }


@traceable(project_name=LANGSMITH_PROJECT)
def reorder_agent(state: InventoryAnalysisState) -> InventoryAnalysisState:
    """Agent 2: Determine if reorder is needed and recommend a quantity."""
    errors = list(state["errors"])
    messages = list(state["messages"])

    with tracer.start_as_current_span("multi_agent.reorder_agent") as span:
        span.set_attribute("poc_id", POC_ID)
        span.set_attribute("phase", PHASE)

        product_data = state["product_data"]
        forecast = state["demand_forecast"] or {}
        stock = product_data.get("stock_level")
        has_stock_data = isinstance(stock, dict) and "quantity_available" in stock
        quantity_available = stock.get("quantity_available", 0) if has_stock_data else 0
        reorder_point = product_data.get("reorder_point")
        has_reorder_point = isinstance(reorder_point, (int, float))
        base_quantity = product_data.get("reorder_quantity", 0) or 0

        # A product is only "below its reorder point" when both real stock and reorder-point
        # data exist; missing fields must never be treated as 0 <= 0 (a false trigger).
        below_reorder_point = has_stock_data and has_reorder_point and quantity_available <= reorder_point
        stockout_risk = forecast.get("stockout_risk", "unknown")
        high_risk = stockout_risk == "high"

        reorder_required = bool(product_data) and (below_reorder_point or high_risk)

        recommended_quantity = 0.0
        if reorder_required:
            trend_multiplier = {"increasing": 1.25, "decreasing": 0.85}.get(forecast.get("demand_trend"), 1.0)
            recommended_quantity = _round(max(base_quantity, 1) * trend_multiplier, 0)

        if not reorder_required:
            urgency = "not_required"
        elif stockout_risk == "high":
            urgency = "immediate"
        elif stockout_risk == "medium":
            urgency = "within_3_days"
        else:
            urgency = "within_week"

        if not product_data:
            reason = "Product data unavailable; unable to evaluate reorder need."
        elif below_reorder_point:
            reason = (
                f"Available quantity {quantity_available} is at or below the reorder point {reorder_point}; "
                f"recommending {recommended_quantity} units given a {forecast.get('demand_trend', 'unknown')} demand trend."
            )
        elif high_risk:
            reason = (
                f"Stockout risk is high based on the demand forecast even though available stock is not yet "
                f"below the reorder point; recommending {recommended_quantity} units as a precaution."
            )
        elif has_stock_data and has_reorder_point:
            reason = f"Available quantity {quantity_available} exceeds the reorder point {reorder_point}; no reorder needed."
        else:
            reason = "Demand outlook does not indicate a reorder is needed."

        reorder_recommendation = {
            "reorder_required": reorder_required,
            "recommended_quantity": recommended_quantity,
            "urgency": urgency,
            "reason": reason,
        }

        new_status = "reorder_required" if reorder_required else state["analysis_status"]
        messages.append(f"Reorder Agent: required={reorder_required}, urgency={urgency}")
        logger.info("agent_complete", poc_id=POC_ID, phase=PHASE, agent="reorder_agent")

    return {
        **state,
        "reorder_recommendation": reorder_recommendation,
        "analysis_status": new_status,
        "errors": errors,
        "messages": messages,
    }


@traceable(project_name=LANGSMITH_PROJECT)
def supplier_coordinator(state: InventoryAnalysisState) -> InventoryAnalysisState:
    """Agent 3: Find the supplier catalog entry and generate a quote for the recommended quantity."""
    errors = list(state["errors"])
    messages = list(state["messages"])

    with tracer.start_as_current_span("multi_agent.supplier_coordinator") as span:
        span.set_attribute("poc_id", POC_ID)
        span.set_attribute("phase", PHASE)

        product_data = state["product_data"]
        reorder = state["reorder_recommendation"]
        supplier_id = product_data.get("supplier_id")
        recommended_quantity = reorder.get("recommended_quantity", 0) or 0

        catalog: list[dict[str, Any]] = []
        lead_time_days = 7
        if supplier_id:
            catalog_data = _api_get(f"/suppliers/{supplier_id}/catalog")
            if isinstance(catalog_data, dict) and "error" in catalog_data:
                errors.append(f"Supplier fetch error: {catalog_data['error']}")
            else:
                catalog = _as_mapping_list(catalog_data)

            supplier_data = _as_mapping(_api_get(f"/suppliers/{supplier_id}"))
            if isinstance(supplier_data, dict) and "error" not in supplier_data:
                lead_time_days = supplier_data.get("lead_time_days", 7) or 7

        catalog_item = next((item for item in catalog if item.get("product_id") == product_data.get("id")), None)
        quoted_unit_cost = _round(
            catalog_item.get("unit_cost") if catalog_item else product_data.get("cost_price", 0)
        )
        total_order_cost = _round(quoted_unit_cost * recommended_quantity)

        fallback_notes = (
            f"Quote of {total_order_cost:.2f} for {recommended_quantity} units at {quoted_unit_cost:.2f}/unit, "
            f"lead time {lead_time_days} days."
            if reorder.get("reorder_required")
            else "No reorder required; no supplier quote needed."
        )
        quote_notes = fallback_notes
        if reorder.get("reorder_required") and product_data:
            prompt = (
                "Summarize this supplier quote recommendation in exactly one sentence. "
                "Use only the numbers given below; do not invent supplier names, dates, or terms.\n"
                f"supplier_id={supplier_id}, quantity={recommended_quantity}, unit_cost={quoted_unit_cost}, "
                f"total_cost={total_order_cost}, lead_time_days={lead_time_days}."
            )
            quote_notes = _generate_text(prompt, fallback_notes)

        supplier_quote = {
            "supplier_id": supplier_id,
            "quoted_unit_cost": quoted_unit_cost,
            "total_order_cost": total_order_cost,
            "estimated_lead_time_days": lead_time_days,
            "quote_notes": quote_notes,
        }

        messages.append(f"Supplier Coordinator: supplier={supplier_id}, cost={total_order_cost:.2f}")
        logger.info("agent_complete", poc_id=POC_ID, phase=PHASE, agent="supplier_coordinator")

    return {
        **state,
        "supplier_quote": supplier_quote,
        "errors": errors,
        "messages": messages,
    }


@traceable(project_name=LANGSMITH_PROJECT)
def inventory_auditor(state: InventoryAnalysisState) -> InventoryAnalysisState:
    """Agent 4: Generate the final inventory audit report and close out the analysis."""
    messages = list(state["messages"])

    with tracer.start_as_current_span("multi_agent.inventory_auditor") as span:
        span.set_attribute("poc_id", POC_ID)
        span.set_attribute("phase", PHASE)

        product = state["product_data"]
        forecast = state["demand_forecast"]
        reorder = state["reorder_recommendation"]
        quote = state["supplier_quote"]
        stock = product.get("stock_level") or {}

        if not product:
            audit_report = (
                "Inventory audit incomplete: product data could not be retrieved. "
                f"Errors encountered: {'; '.join(state['errors']) or 'unknown error'}."
            )
        else:
            fallback_report = (
                f"Product {product.get('sku', 'unknown')} ({product.get('name', '')}) has "
                f"{stock.get('quantity_available', 0)} units available against a reorder point of "
                f"{product.get('reorder_point', 0)}. Stockout risk is {forecast.get('stockout_risk', 'unknown')} "
                f"with {forecast.get('days_of_stock_remaining', 0)} days of stock remaining. "
                + (
                    f"Reorder is required ({reorder.get('urgency', 'n/a')}); recommended quantity is "
                    f"{reorder.get('recommended_quantity', 0)} units at an estimated cost of "
                    f"{quote.get('total_order_cost', 0):.2f} with a {quote.get('estimated_lead_time_days', 0)}-day lead time."
                    if reorder.get("reorder_required")
                    else "No reorder is required at this time; inventory health is stable."
                )
            )
            prompt = (
                "Write a concise 3-4 sentence inventory audit report covering stock health, stockout risk, "
                "and supplier impact. Use only the facts given below; do not invent numbers, dates, growth "
                "rates, or market commentary that are not listed here.\n"
                f"SKU: {product.get('sku', 'unknown')} — {product.get('name', '')}\n"
                f"Stock: {stock.get('quantity_available', 0)} available, reorder point {product.get('reorder_point', 0)}\n"
                f"Forecast: {forecast.get('days_of_stock_remaining', 0)} days remaining, risk {forecast.get('stockout_risk', 'unknown')}\n"
                f"Reorder: {'REQUIRED' if reorder.get('reorder_required') else 'Not required'} — urgency {reorder.get('urgency', 'n/a')}\n"
                f"Supplier quote: {quote.get('total_order_cost', 0):.2f} for {reorder.get('recommended_quantity', 0)} units"
            )
            audit_report = _generate_text(prompt, fallback_report)

        messages.append(f"Inventory Auditor: report generated ({len(audit_report)} chars)")
        logger.info("agent_complete", poc_id=POC_ID, phase=PHASE, agent="inventory_auditor")

    return {**state, "audit_report": audit_report, "analysis_status": "complete", "messages": messages}
