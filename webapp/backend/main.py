"""
Service Collection Webapp - FastAPI Backend

This FastAPI application provides the backend for the Service Collection management
webapp, including workflow orchestration, approval systems, and Vultr API integration.

Hot reload test: Changes to this file should trigger container restart.
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import init_db
from app.core.procrastinate_app import procrastinate_app
from app.api.auth import router as auth_router
from app.api.collections import router as collections_router
from app.api.dashboard import router as dashboard_router
from app.api.workflows import router as workflows_router
from app.api.projects import router as projects_router
from app.api.resources import router as resources_router
from app.api.vultr_credentials import router as vultr_credentials_router
from app.core.exceptions import ServiceCollectionException

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with comprehensive error handling."""
    settings = get_settings()

    logger.info("🚀 Starting Service Collection Webapp Backend")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"OAuth Enabled: {settings.oauth_enabled}")
    # Hide password in database URL for logging
    db_url_str = str(settings.database_url)
    if '@' in db_url_str and ':' in db_url_str:
        # Replace password in postgresql://user:password@host format
        parts = db_url_str.split('@')
        if len(parts) == 2:
            user_pass = parts[0].split(':')
            if len(user_pass) >= 3:  # postgresql://user:password
                user_pass[2] = '***'
                parts[0] = ':'.join(user_pass)
                db_url_str = '@'.join(parts)
    logger.info(f"Database URL: {db_url_str}")

    startup_errors = []

    # Initialize database with error handling
    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        error_msg = f"❌ Database initialization failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        startup_errors.append(f"Database: {str(e)}")

        # Check for common database issues
        if "could not translate host name" in str(e):
            logger.error("🔍 Database connection issue detected:")
            logger.error("   - PostgreSQL hostname cannot be resolved")
            logger.error("   - If running in Docker, ensure database service is running")
            logger.error("   - If running locally, ensure DATABASE_URL points to accessible host")
            logger.error(f"   - Current DATABASE_URL: {settings.database_url.obscure_password()}")
        elif "Connection refused" in str(e):
            logger.error("🔍 Database connection refused:")
            logger.error("   - PostgreSQL service may not be running")
            logger.error("   - Check if PostgreSQL is accessible on the specified port")
        elif "authentication failed" in str(e):
            logger.error("🔍 Database authentication failed:")
            logger.error("   - Check database credentials in DATABASE_URL")
            logger.error("   - Verify user exists and has proper permissions")

    # Initialize Procrastinate with error handling
    try:
        await procrastinate_app.open_async()
        logger.info("✅ Procrastinate queue system initialized")
    except Exception as e:
        error_msg = f"❌ Procrastinate initialization failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        startup_errors.append(f"Queue system: {str(e)}")

    # If critical services failed, log comprehensive startup report
    if startup_errors:
        logger.error("❌ APPLICATION STARTUP ISSUES DETECTED:")
        for i, error in enumerate(startup_errors, 1):
            logger.error(f"   {i}. {error}")
        logger.error("🔧 The application may not function correctly until these issues are resolved")
        logger.error("💡 Check the error messages above for troubleshooting guidance")
    else:
        logger.info("🎉 All services initialized successfully!")

    yield

    # Cleanup with error handling
    try:
        await procrastinate_app.close_async()
        logger.info("✅ Procrastinate queue system closed")
    except Exception as e:
        logger.error(f"❌ Error closing Procrastinate: {str(e)}")

    logger.info("👋 Service Collection Webapp Backend shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Service Collection Management API",
        description="Backend API for Service Collection workflow management and Vultr integration",
        version="0.1.0",
        docs_url="/docs" if settings.environment == "development" else None,
        redoc_url="/redoc" if settings.environment == "development" else None,
        lifespan=lifespan
    )
    
    # Security middleware
    if settings.environment == "production":
        app.add_middleware(
            TrustedHostMiddleware, 
            allowed_hosts=[settings.domain, f"api.{settings.domain}"]
        )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            f"https://{settings.domain}",
            f"https://api.{settings.domain}",
            "http://localhost:4321",  # Astro dev server
            "http://localhost:3000"   # Alternative frontend dev
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Exception handlers
    @app.exception_handler(ServiceCollectionException)
    async def service_collection_exception_handler(
        request: Request, exc: ServiceCollectionException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception", exc_info=exc, request=request.url)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "An internal error occurred"
            }
        )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "service-collection-webapp",
            "version": "0.1.0",
            "environment": settings.environment
        }
    
    # API routers
    app.include_router(auth_router, prefix="/api")
    app.include_router(projects_router, prefix="/api")
    app.include_router(collections_router, prefix="/api")
    app.include_router(resources_router, prefix="/api")
    app.include_router(vultr_credentials_router, prefix="/api")
    app.include_router(dashboard_router, prefix="/api")
    app.include_router(workflows_router, prefix="/api")

    # Also include auth router without /api prefix for GitHub OAuth compatibility
    app.include_router(auth_router)
    
    return app


# Create application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_config=None  # Use structlog configuration
    )