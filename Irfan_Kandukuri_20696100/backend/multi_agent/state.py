from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class InventoryAnalysisState(TypedDict):
    product_id: int
    product_data: Dict[str, Any]  # Product + stock details
    demand_forecast: Dict[str, Any]  # Demand Forecaster output
    reorder_recommendation: Dict[str, Any]  # Reorder Agent output
    supplier_quote: Dict[str, Any]  # Supplier Coordinator output
    audit_report: str  # Inventory Auditor final report
    analysis_status: str  # "analyzing" | "reorder_required" | "healthy" | "complete" | "error"
    errors: List[str]
    messages: List[str]


def initial_state(product_id: int) -> InventoryAnalysisState:
    return InventoryAnalysisState(
        product_id=product_id,
        product_data={},
        demand_forecast={},
        reorder_recommendation={},
        supplier_quote={},
        audit_report="",
        analysis_status="analyzing",
        errors=[],
        messages=[],
    )
