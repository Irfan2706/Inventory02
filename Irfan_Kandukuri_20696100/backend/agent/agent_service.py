from __future__ import annotations

from opentelemetry import trace

from .agent_executor import build_agent_executor
from .tools import reset_api_token, set_api_token

try:
    from langsmith import traceable
except ImportError:  # pragma: no cover - optional observability dependency
    def traceable(project_name: str):
        del project_name

        def decorator(function):
            return function

        return decorator


tracer = trace.get_tracer("poc-07-agent")


@traceable(project_name="AI-Readiness-POC-07-P3")
def answer_question(question: str, authorization: str | None = None) -> dict:
    token_state = set_api_token(authorization)
    try:
        with tracer.start_as_current_span("agent.query") as span:
            span.set_attribute("poc_id", "POC-07")
            span.set_attribute("phase", "P3")
            result = build_agent_executor().invoke({"input": question})
            span.set_attribute("agent.tools_used", ",".join(result.get("tools_used", [])))
            return {
                "answer": result.get("output", ""),
                "tools_used": result.get("tools_used", []),
                "reasoning": result.get("reasoning", ""),
            }
    finally:
        reset_api_token(token_state)
