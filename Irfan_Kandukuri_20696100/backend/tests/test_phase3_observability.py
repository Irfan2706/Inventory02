def test_phase3_tools_have_required_names_and_spans():
    from agent.tools import TOOLS

    names = {item.name for item in TOOLS}
    assert names == {
        "get_low_stock_alerts",
        "get_product_stock",
        "get_supplier_catalog",
        "get_dashboard_stats",
        "search_inventory_policy",
    }

    for item in TOOLS:
        assert f"tool.{item.name}" in item.func.__code__.co_consts


def test_phase3_prompt_references_all_tools():
    from agent.prompts import INVENTORY_AGENT_SYSTEM_PROMPT

    for name in ("get_low_stock_alerts", "get_product_stock", "get_supplier_catalog", "get_dashboard_stats", "search_inventory_policy"):
        assert name in INVENTORY_AGENT_SYSTEM_PROMPT


def test_phase3_prompt_contains_domain_formats():
    from agent.prompts import INVENTORY_AGENT_SYSTEM_PROMPT

    assert "SKU-{CATEGORY_PREFIX}-{NNNN}" in INVENTORY_AGENT_SYSTEM_PROMPT
    assert "PO-{YEAR}-{NNNN}" in INVENTORY_AGENT_SYSTEM_PROMPT


def test_phase3_prompt_contains_lifecycle_rules():
    from agent.prompts import INVENTORY_AGENT_SYSTEM_PROMPT

    assert "quantity_available <= reorder_point" in INVENTORY_AGENT_SYSTEM_PROMPT
    assert "draft -> submitted -> acknowledged -> received" in INVENTORY_AGENT_SYSTEM_PROMPT
