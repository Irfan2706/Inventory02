from multi_agent.state import InventoryAnalysisState, initial_state


def test_initial_state_has_all_required_fields():
    state = initial_state(1)
    expected_fields = {
        "product_id",
        "product_data",
        "demand_forecast",
        "reorder_recommendation",
        "supplier_quote",
        "audit_report",
        "analysis_status",
        "errors",
        "messages",
    }
    assert set(state.keys()) == expected_fields


def test_initial_state_sets_product_id():
    state = initial_state(42)
    assert state["product_id"] == 42


def test_initial_state_default_values():
    state = initial_state(1)
    assert state["product_data"] == {}
    assert state["demand_forecast"] == {}
    assert state["reorder_recommendation"] == {}
    assert state["supplier_quote"] == {}
    assert state["audit_report"] == ""
    assert state["analysis_status"] == "analyzing"
    assert state["errors"] == []
    assert state["messages"] == []


def test_initial_state_is_typed_dict_annotation():
    annotations = InventoryAnalysisState.__annotations__
    assert set(annotations.keys()) == {
        "product_id",
        "product_data",
        "demand_forecast",
        "reorder_recommendation",
        "supplier_quote",
        "audit_report",
        "analysis_status",
        "errors",
        "messages",
    }


def test_initial_state_lists_are_independent_instances():
    state_a = initial_state(1)
    state_b = initial_state(2)
    state_a["errors"].append("boom")
    assert state_b["errors"] == []
