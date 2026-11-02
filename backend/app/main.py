"""
NexusFlow Enterprise FastAPI Application
Production-ready configuration with structured JSON error handlers,
standard CORS for Angular client (http://localhost:4200), health diagnostics,
and LangGraph multi-agent workflow routers.
"""

import logging
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import init_db, check_db_health
from app.routers.workflow import router as workflow_router

# Configure centralized enterprise logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("nexusflow.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management for initialization and graceful teardown."""
    settings = get_settings()
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")

    # Initialize SQL database schema
    db_initialized = init_db()
    if db_initialized:
        logger.info("MS SQL Server connected and schema validated.")
    else:
        logger.warning("Operating with local or in-memory telemetry.")

    yield

    logger.info(f"Shutting down {settings.PROJECT_NAME} gracefully...")


# Instantiate FastAPI Application
settings = get_settings()
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Multi-Agent Code Generation and Review Platform powered by LangGraph and FastAPI.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Production CORS Configuration for Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Cache-Control", "X-Accel-Buffering"],
)


# Standardized JSON Error Handlers
@app.exception_handler(StarletteHTTPException)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Standardized error response for HTTP exceptions."""
    status_code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
    detail = getattr(exc, "detail", str(exc))
    return JSONResponse(
        status_code=status_code,
        content={
            "error": True,
            "status_code": status_code,
            "message": detail,
            "path": str(request.url.path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Standardized error response for schema validation failures."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "Input validation error in request payload.",
            "details": exc.errors(),
            "path": str(request.url.path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all structured JSON error handler for unhandled internal server errors."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "An unexpected internal server error occurred.",
            "details": str(exc) if settings.DEBUG else "Please contact system administrator.",
            "path": str(request.url.path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# Health Check Endpoint
@app.get(
    "/health",
    summary="System Health Diagnostics",
    description="Returns backend operational status, runtime version, database connectivity, and configured AI models.",
)
async def health_check() -> Dict[str, Any]:
    """Production health-check endpoint."""
    current_settings = get_settings()
    db_status = check_db_health()
    return {
        "status": "healthy",
        "project": current_settings.PROJECT_NAME,
        "version": current_settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "models": {
            "coder": current_settings.CODER_MODEL,
            "reviewer": current_settings.REVIEWER_MODEL,
        },
    }


# Mount Workflow Routers
app.include_router(workflow_router)
