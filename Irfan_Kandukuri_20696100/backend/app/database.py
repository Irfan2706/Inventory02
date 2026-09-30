from sqlalchemy import create_engine
import time

from opentelemetry import trace
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings
from app.logging_config import get_logger

DB_QUERY_OPERATION = "db.query"


def _table_after(tokens: list[str], keyword: str) -> str:
    if keyword not in tokens:
        return "unknown"
    index = tokens.index(keyword) + 1
    return tokens[index].strip('"`[]') if index < len(tokens) else "unknown"


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_logger = get_logger("db")
tracer = trace.get_tracer("app.db")


def _extract_operation_and_table(statement: str) -> tuple[str, str]:
    sql = " ".join(statement.strip().split())
    lowered = sql.lower()
    operation = lowered.split(" ", 1)[0] if lowered else "unknown"

    table = "unknown"
    tokens = lowered.split()
    if operation == "insert":
        table = _table_after(tokens, "into")
    elif operation == "update" and len(tokens) > 1:
        table = tokens[1].strip('"`[]')
    elif operation == "select" and "from" in tokens:
        table = _table_after(tokens, "from")
    elif operation == "delete" and "from" in tokens:
        table = _table_after(tokens, "from")

    return operation, table


@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    del cursor, parameters, executemany
    context._query_start = time.perf_counter()
    operation, table = _extract_operation_and_table(statement)
    context._db_operation = operation
    context._db_table = table
    span = tracer.start_span(DB_QUERY_OPERATION)
    span.set_attribute("db.operation", operation)
    span.set_attribute("db.table", table)
    span.set_attribute("db.statement", statement[:500])
    context._db_span = span
    conn.info["last_db_query_start"] = context._query_start


@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    del conn, cursor, statement, parameters, executemany
    start = getattr(context, "_query_start", time.perf_counter())
    duration_ms = int((time.perf_counter() - start) * 1000)
    operation = getattr(context, "_db_operation", "unknown")
    table = getattr(context, "_db_table", "unknown")

    span = getattr(context, "_db_span", None)
    if span is not None:
        span.set_attribute("db.duration_ms", duration_ms)
        span.end()

    db_logger.info(
        "db_query",
        operation=DB_QUERY_OPERATION,
        status="success",
        duration_ms=duration_ms,
        db_operation=operation,
        db_table=table,
    )


@event.listens_for(engine, "handle_error")
def handle_error(exception_context):
    context = exception_context.execution_context
    if context is None:
        return

    start = getattr(context, "_query_start", time.perf_counter())
    duration_ms = int((time.perf_counter() - start) * 1000)
    operation = getattr(context, "_db_operation", "unknown")
    table = getattr(context, "_db_table", "unknown")

    span = getattr(context, "_db_span", None)
    if span is not None:
        span.record_exception(exception_context.original_exception)
        span.set_attribute("db.duration_ms", duration_ms)
        span.set_attribute("db.status", "failure")
        span.end()

    db_logger.error(
        "db_query_failed",
        operation=DB_QUERY_OPERATION,
        status="failure",
        duration_ms=duration_ms,
        error=str(exception_context.original_exception),
        db_operation=operation,
        db_table=table,
    )


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
