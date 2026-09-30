from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_current_user

from .agents import reset_api_token, set_api_token
from .graph import analyze_product
from .schemas import MultiAgentAnalyzeRequest, MultiAgentAnalyzeResponse

router = APIRouter()


@router.post("/analyze", response_model=MultiAgentAnalyzeResponse)
def analyze(
    payload: MultiAgentAnalyzeRequest,
    request: Request,
    _user=Depends(get_current_user),
):
    token_state = set_api_token(request.headers.get("authorization"))
    try:
        result = analyze_product(payload.product_id)
    finally:
        reset_api_token(token_state)

    return MultiAgentAnalyzeResponse(
        product_id=result["product_id"],
        demand_forecast=result["demand_forecast"],
        reorder_recommendation=result["reorder_recommendation"],
        supplier_quote=result["supplier_quote"],
        audit_report=result["audit_report"],
        analysis_status=result["analysis_status"],
        errors=result["errors"],
        messages=result["messages"],
    )
