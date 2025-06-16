#!/usr/bin/env python3
"""
FastAPI Application (SCRUM-17)
Main FastAPI application for REST API endpoints.
"""

import logging
import os
import time
import uuid
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from server.api.dependencies import set_app_config
from server.api.models import ErrorResponse
from server.api.routes import health, hosts, metrics, users
from server.auth.dependencies import get_current_verified_user
from server.auth.routes import router as auth_router
from server.database.connection import init_async_db
from server.monitoring import get_metrics_collector

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to each request."""

    async def dispatch(self, request: Request, call_next):
        """Add request ID to request state."""
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# Create limiter
limiter = Limiter(key_func=get_remote_address)


def create_app(config: Dict[str, Any]) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        config: Application configuration

    Returns:
        Configured FastAPI application
    """
    # Set configuration for dependency injection
    set_app_config(config)

    # Initialize async database with auth database path
    auth_db_config = {
        "database": {
            "path": config.get("database", {}).get(
                "path", os.environ.get("PRISM_DATABASE_PATH", "/app/data/prism.db")
            ),
            "connection_pool_size": config.get("database", {}).get("connection_pool_size", 20),
        }
    }
    init_async_db(auth_db_config)

    # Get API configuration
    api_config = config.get("api", {})

    # Create FastAPI app
    app = FastAPI(
        title="Prism DNS Server API",
        description="REST API for managed DNS host data retrieval",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Configure CORS
    if api_config.get("enable_cors", True):
        cors_origins = api_config.get(
            "cors_origins",
            [
                "http://localhost:3000",
                "http://localhost:8080",
                "http://localhost:8090",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8080",
                "http://127.0.0.1:8090",
                "https://prism.thepaynes.ca",
            ],
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID"],
        )
        logger.info(f"CORS enabled for origins: {cors_origins}")

    # Add rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add request ID middleware
    app.add_middleware(RequestIDMiddleware)

    # Add request tracking middleware
    @app.middleware("http")
    async def track_requests(request: Request, call_next):
        """Track HTTP request metrics."""
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Track metrics (skip metrics endpoint to avoid recursion)
        if request.url.path != "/metrics":
            try:
                collector = get_metrics_collector()
                collector.record_http_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status=response.status_code,
                    duration=duration,
                )
            except Exception as e:
                logger.warning(f"Failed to record metrics: {e}")

        return response

    # Include routers
    app.include_router(hosts.router)
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(auth_router, prefix="/api")
    app.include_router(users.router)

    # Add custom exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with consistent error format."""
        logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_type": "http_error",
                "status_code": exc.status_code,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.warning(f"Validation error: {exc} - {request.url}")

        # Format validation errors to be JSON serializable
        errors = []
        for error in exc.errors():
            err_copy = error.copy()
            # Convert any non-serializable values to strings
            if "ctx" in err_copy and "error" in err_copy["ctx"]:
                if hasattr(err_copy["ctx"]["error"], "__str__"):
                    err_copy["ctx"]["error"] = str(err_copy["ctx"]["error"])
            errors.append(err_copy)

        return JSONResponse(
            status_code=422,
            content={
                "detail": "Request validation failed",
                "error_type": "validation_error",
                "validation_errors": errors,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error: {exc} - {request.url}", exc_info=True)

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error_type": "internal_error"},
        )

    # Add root endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        """Root endpoint with API information."""
        return {
            "message": "Prism DNS Server API",
            "version": "1.0.0",
            "docs": "/api/docs",
            "health": "/api/health",
        }

    # Add API root endpoint
    @app.get("/api", include_in_schema=False)
    async def api_root():
        """API root endpoint."""
        return {
            "message": "Prism DNS Server REST API",
            "version": "1.0.0",
            "endpoints": {
                "hosts": "/api/hosts",
                "health": "/api/health",
                "stats": "/api/stats",
                "docs": "/api/docs",
            },
        }

    logger.info("FastAPI application created and configured")

    return app


def get_application_info() -> Dict[str, Any]:
    """
    Get application information.

    Returns:
        Dictionary with application details
    """
    return {
        "name": "Prism DNS Server API",
        "version": "1.0.0",
        "description": "REST API for managed DNS host data retrieval",
        "endpoints": [
            "GET /api/hosts - List all hosts with pagination",
            "GET /api/hosts/{hostname} - Get specific host details",
            "GET /api/hosts/status/{status} - Filter hosts by status",
            "GET /api/health - Server health check",
            "GET /api/stats - Server statistics",
        ],
    }
