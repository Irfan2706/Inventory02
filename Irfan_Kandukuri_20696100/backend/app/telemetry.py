from __future__ import annotations

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from app.config import settings


_telemetry_configured = False


def configure_telemetry(app) -> None:
    global _telemetry_configured
    if _telemetry_configured:
        return

    resource = Resource.create(
        {
            "service.name": f"{settings.poc_id}-inventory-api",
            "service.version": "1.0.0",
            "poc_id": settings.poc_id,
            "phase": settings.phase,
            "associate_id": settings.associate_id,
        }
    )

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    _telemetry_configured = True
