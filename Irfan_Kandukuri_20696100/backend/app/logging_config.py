import logging
import sys

import structlog

from app.config import settings


_configured = False


def add_mandatory_fields(_, __, event_dict: dict) -> dict:
    event_dict.setdefault("poc_id", settings.poc_id)
    event_dict.setdefault("phase", settings.phase)
    event_dict.setdefault("associate_id", settings.associate_id)
    event_dict.setdefault("request_id", "system")
    event_dict.setdefault("operation", event_dict.get("event", "unknown_operation"))

    level = str(event_dict.get("level", "info")).lower()
    default_status = "failure" if level in {"error", "exception", "critical"} else "success"
    event_dict.setdefault("status", default_status)
    event_dict.setdefault("duration_ms", 0)
    event_dict.setdefault("error", None)
    return event_dict


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        timestamper,
        add_mandatory_fields,
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.add_logger_name,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
    _configured = True


def get_logger(name: str = "inventory"):
    configure_logging()
    return structlog.get_logger(name)
