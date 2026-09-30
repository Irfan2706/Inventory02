import inspect

from multi_agent import agents


def test_multi_agent_tracer_configured():
    assert agents.tracer is not None


def test_langsmith_project_constant():
    assert agents.LANGSMITH_PROJECT == "AI-Readiness-POC-07-P5"


def test_all_agents_use_expected_span_names():
    expected_spans = {
        "demand_forecaster": "multi_agent.demand_forecaster",
        "reorder_agent": "multi_agent.reorder_agent",
        "supplier_coordinator": "multi_agent.supplier_coordinator",
        "inventory_auditor": "multi_agent.inventory_auditor",
    }
    for func_name, span_name in expected_spans.items():
        source = inspect.getsource(inspect.unwrap(getattr(agents, func_name)))
        assert f'tracer.start_as_current_span("{span_name}")' in source


def test_all_agents_set_poc_and_phase_attributes():
    for func_name in ("demand_forecaster", "reorder_agent", "supplier_coordinator", "inventory_auditor"):
        source = inspect.getsource(inspect.unwrap(getattr(agents, func_name)))
        assert 'span.set_attribute("poc_id", POC_ID)' in source
        assert 'span.set_attribute("phase", PHASE)' in source


def test_poc_and_phase_constants():
    assert agents.POC_ID == "POC-07"
    assert agents.PHASE == "P5"


def test_traceable_decorator_degrades_gracefully_when_langsmith_missing(monkeypatch):
    monkeypatch.setattr(agents, "_langsmith_traceable", None)

    @agents.traceable(project_name="AI-Readiness-POC-07-P5")
    def sample(x):
        return x + 1

    assert sample(1) == 2


def test_traceable_decorator_recovers_from_tracing_failure(monkeypatch):
    def broken_traceable(*args, **kwargs):
        def decorator(func):
            def wrapper(*f_args, **f_kwargs):
                raise RuntimeError("LangSmith unavailable")

            return wrapper

        return decorator

    monkeypatch.setattr(agents, "_langsmith_traceable", broken_traceable)

    @agents.traceable(project_name="AI-Readiness-POC-07-P5")
    def sample(x):
        return x * 2

    assert sample(3) == 6


def test_agent_functions_log_completion(monkeypatch):
    from multi_agent.state import initial_state

    state = initial_state(1)
    state["errors"] = ["a", "b", "c"]
    result = agents.inventory_auditor(state)
    assert result["analysis_status"] == "complete"
