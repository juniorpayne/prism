#!/usr/bin/env python3
"""
FastAPI Application (SCRUM-17)
Main FastAPI application for REST API endpoints.
"""

import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from server.api.routes import hosts, health
from server.api.dependencies import set_app_config
from server.api.models import ErrorResponse

logger = logging.getLogger(__name__)


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
    
    # Get API configuration
    api_config = config.get('api', {})
    
    # Create FastAPI app
    app = FastAPI(
        title="Prism DNS Server API",
        description="REST API for managed DNS host data retrieval",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # Configure CORS
    if api_config.get('enable_cors', True):
        cors_origins = api_config.get('cors_origins', [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080"
        ])
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
        logger.info(f"CORS enabled for origins: {cors_origins}")
    
    # Include routers
    app.include_router(hosts.router)
    app.include_router(health.router)
    
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
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.warning(f"Validation error: {exc} - {request.url}")
        
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Request validation failed",
                "error_type": "validation_error",
                "validation_errors": exc.errors()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error: {exc} - {request.url}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_type": "internal_error"
            }
        )
    
    # Add root endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        """Root endpoint with API information."""
        return {
            "message": "Prism DNS Server API",
            "version": "1.0.0",
            "docs": "/api/docs",
            "health": "/api/health"
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
                "docs": "/api/docs"
            }
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
            "GET /api/stats - Server statistics"
        ]
    }