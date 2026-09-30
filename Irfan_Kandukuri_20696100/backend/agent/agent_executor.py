from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .prompts import INVENTORY_AGENT_SYSTEM_PROMPT
from .tools import (
    TOOLS,
    get_dashboard_stats,
    get_low_stock_alerts,
    get_product_stock,
    get_supplier_catalog,
    search_inventory_policy,
)


@dataclass
class AgentResult:
    answer: str
    tools_used: list[str]
    reasoning: str


def _product_id(question: str) -> str | None:
    return _numeric_identifier(question, ("product", "item"))


def _supplier_id(question: str) -> str | None:
    return _numeric_identifier(question, ("supplier",))


def _numeric_identifier(question: str, labels: tuple[str, ...]) -> str | None:
    lowered = question.lower()
    for label in labels:
        position = lowered.find(label)
        if position < 0:
            continue
        candidate = question[position + len(label):].lstrip()
        if candidate.lower().startswith("id"):
            candidate = candidate[2:].lstrip()
        candidate = candidate.lstrip("#:- ")
        digits = []
        for character in candidate:
            if not character.isdigit():
                break
            digits.append(character)
        if digits:
            return "".join(digits)
    return None


class InventoryAgentExecutor:
    """A local ReAct loop: select an applicable LangChain tool, invoke it, summarize its observation."""

    system_prompt = INVENTORY_AGENT_SYSTEM_PROMPT
    tools = TOOLS

    @staticmethod
    def _question(payload: dict[str, Any] | str) -> str:
        if isinstance(payload, str):
            return payload.strip()
        return str(payload.get("input", payload.get("question", ""))).strip()

    @staticmethod
    def _select_tool(question: str) -> tuple[str, Any, dict[str, str]]:
        lowered = question.lower()
        product_id = _product_id(question)
        supplier_id = _supplier_id(question)
        if any(term in lowered for term in ("what does", "mean", "policy", "procedure", "rule")):
            return "search_inventory_policy", search_inventory_policy, {"question": question}
        if any(term in lowered for term in ("low stock", "out of stock", "reorder", "replenish", "alert")):
            return "get_low_stock_alerts", get_low_stock_alerts, {"query": question}
        if any(term in lowered for term in ("dashboard", "summary", "total inventory", "inventory value", "open po")):
            return "get_dashboard_stats", get_dashboard_stats, {"query": question}
        if supplier_id and any(term in lowered for term in ("catalog", "carries", "supplier", "price")):
            return "get_supplier_catalog", get_supplier_catalog, {"supplier_id": supplier_id}
        if product_id:
            return "get_product_stock", get_product_stock, {"product_id": product_id}
        return "search_inventory_policy", search_inventory_policy, {"question": question}

    def invoke(self, payload: dict[str, Any] | str) -> dict[str, Any]:
        question = self._question(payload)
        name, selected_tool, arguments = self._select_tool(question)
        observations = [(name, selected_tool.invoke(arguments))]

        answer = observations[-1][1] if observations else "I could not select an inventory tool."
        return {
            "output": answer,
            "tools_used": [name for name, _ in observations],
            "reasoning": "Classified the question, invoked " + ", ".join(name for name, _ in observations) + ", and summarized the tool observation.",
            "intermediate_steps": observations,
        }


def build_agent_executor() -> InventoryAgentExecutor:
    return InventoryAgentExecutor()
