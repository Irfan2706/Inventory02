from __future__ import annotations

from app.logging_config import get_logger

from .agents import LANGSMITH_PROJECT, demand_forecaster, inventory_auditor, reorder_agent, supplier_coordinator, traceable
from .state import InventoryAnalysisState, initial_state

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - dependency is optional at import time
    StateGraph = None
    END = "END"

logger = get_logger("multi_agent")

MAX_ERROR_COUNT = 3


def should_skip_to_audit(state: InventoryAnalysisState) -> str:
    if len(state.get("errors", [])) >= MAX_ERROR_COUNT or state.get("analysis_status") == "error":
        return "inventory_auditor"
    return "reorder_agent"


class _SequentialInventoryGraph:
    """Deterministic fallback pipeline used when the LangGraph dependency is unavailable."""

    def invoke(self, state: InventoryAnalysisState) -> InventoryAnalysisState:
        state = demand_forecaster(state)
        if should_skip_to_audit(state) == "inventory_auditor":
            return inventory_auditor(state)
        state = reorder_agent(state)
        state = supplier_coordinator(state)
        return inventory_auditor(state)


def build_inventory_graph():
    if StateGraph is None:
        logger.warning("multi_agent_langgraph_unavailable", reason="langgraph not installed; using sequential fallback pipeline")
        return _SequentialInventoryGraph()

    graph = StateGraph(InventoryAnalysisState)
    graph.add_node("demand_forecaster", demand_forecaster)
    graph.add_node("reorder_agent", reorder_agent)
    graph.add_node("supplier_coordinator", supplier_coordinator)
    graph.add_node("inventory_auditor", inventory_auditor)
    graph.set_entry_point("demand_forecaster")
    graph.add_conditional_edges(
        "demand_forecaster",
        should_skip_to_audit,
        {"reorder_agent": "reorder_agent", "inventory_auditor": "inventory_auditor"},
    )
    graph.add_edge("reorder_agent", "supplier_coordinator")
    graph.add_edge("supplier_coordinator", "inventory_auditor")
    graph.add_edge("inventory_auditor", END)
    return graph.compile()


@traceable(project_name=LANGSMITH_PROJECT)
def analyze_product(product_id: int) -> InventoryAnalysisState:
    return build_inventory_graph().invoke(initial_state(product_id))
