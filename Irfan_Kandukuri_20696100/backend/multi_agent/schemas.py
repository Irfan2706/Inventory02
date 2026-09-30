from __future__ import annotations

from pydantic import BaseModel, Field


class MultiAgentAnalyzeRequest(BaseModel):
    product_id: int = Field(gt=0)


class DemandForecastSchema(BaseModel):
    avg_daily_demand: float = 0
    demand_trend: str = "unknown"
    days_of_stock_remaining: float = 0
    stockout_risk: str = "unknown"
    forecast_notes: str = ""


class ReorderRecommendationSchema(BaseModel):
    reorder_required: bool = False
    recommended_quantity: float = 0
    urgency: str = "not_required"
    reason: str = ""


class SupplierQuoteSchema(BaseModel):
    supplier_id: int | None = None
    quoted_unit_cost: float = 0
    total_order_cost: float = 0
    estimated_lead_time_days: int = 7
    quote_notes: str = ""


class MultiAgentAnalyzeResponse(BaseModel):
    product_id: int
    demand_forecast: DemandForecastSchema
    reorder_recommendation: ReorderRecommendationSchema
    supplier_quote: SupplierQuoteSchema
    audit_report: str
    analysis_status: str
    errors: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)
