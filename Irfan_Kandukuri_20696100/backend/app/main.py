from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.logging_config import configure_logging, get_logger
from app.models import User, UserRole
from app.routers import agent, auth, dashboard, mcp, orders, products, rag, stock, suppliers
from app.security import hash_password
from app.telemetry import configure_telemetry
from multi_agent.api import router as multi_agent_router


configure_logging()
logger = get_logger("main")
HTTP_REQUEST_OPERATION = "http.request"


def seed_development_user() -> None:
    if not settings.seed_dev_user:
        return

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == settings.dev_user_email).first()
        if user is None:
            db.add(
                User(
                    email=settings.dev_user_email,
                    hashed_password=hash_password(settings.dev_user_password),
                    full_name="Inventory Manager",
                    role=UserRole.manager,
                    is_active=True,
                )
            )
            db.commit()
            logger.info("development_user_seeded", email=settings.dev_user_email, role="manager")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_development_user()
    logger.info("startup", operation="app.startup", status="success", duration_ms=0)
    yield


app = FastAPI(
    title="POC-07 Inventory Management API",
    description="Inventory Management and Procurement backend for retail operations.",
    version="1.0.0",
    lifespan=lifespan,
)

configure_telemetry(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cache-Control": "no-store",
}


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    for header, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    return response


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = perf_counter()
    request_id = f"req_{uuid4().hex[:12]}"
    structlog.contextvars.bind_contextvars(
        poc_id=settings.poc_id,
        phase=settings.phase,
        associate_id=settings.associate_id,
        request_id=request_id,
    )

    logger.info(
        "request_started",
        operation=HTTP_REQUEST_OPERATION,
        status="success",
        duration_ms=0,
        method=request.method,
        path=request.url.path,
        query_params=dict(request.query_params),
    )
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = int((perf_counter() - start) * 1000)
        logger.exception(
            "request_failed",
            operation=HTTP_REQUEST_OPERATION,
            status="failure",
            duration_ms=duration_ms,
            method=request.method,
            path=request.url.path,
        )
        raise

    duration_ms = int((perf_counter() - start) * 1000)
    status_value = "success" if response.status_code < 400 else "failure"
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed",
        operation=HTTP_REQUEST_OPERATION,
        status=status_value,
        duration_ms=duration_ms,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )
    structlog.contextvars.clear_contextvars()
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, exc: Exception):
    try:
        logger.exception(
            "unhandled_exception",
            operation="http.unhandled_exception",
            status="failure",
            error=str(exc),
        )
    finally:
        structlog.contextvars.clear_contextvars()
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["Suppliers"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Purchase Orders"])
app.include_router(stock.router, prefix="/api/v1/stock", tags=["Stock"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(rag.router, prefix="/api/v1/rag", tags=["RAG"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["Agent"])
app.include_router(mcp.router, prefix="/api/v1/mcp", tags=["MCP Chat"])
app.include_router(multi_agent_router, prefix="/api/v1/multi-agent", tags=["Multi-Agent"])


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "poc_id": settings.poc_id}


@app.get("/health")
def health_check():
    return {"status": "ok", "poc_id": settings.poc_id}
