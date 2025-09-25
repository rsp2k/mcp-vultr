"""Database configuration and session management."""

import asyncio
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


# Global database engine and session factory
engine: AsyncEngine = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] = None


def create_database_engine() -> AsyncEngine:
    """Create database engine with optimized configuration."""
    settings = get_settings()
    
    # Connection arguments
    connect_args = {
        "command_timeout": 60,
        "server_settings": {
            "jit": "off",  # Disable JIT for faster startup
        },
    }
    
    # Create engine with conditional pool settings
    engine_kwargs = {
        "url": str(settings.database_url),
        "echo": settings.debug,
        "pool_pre_ping": True,
        "pool_recycle": 3600,  # Recycle connections every hour
        "connect_args": connect_args,
    }
    
    # Use NullPool for development to avoid connection issues
    if settings.environment == "development":
        engine_kwargs["poolclass"] = NullPool
    else:
        # Only add pool settings when not using NullPool
        engine_kwargs.update({
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_max_overflow,
        })
    
    engine = create_async_engine(**engine_kwargs)
    
    # Log SQL queries in development
    if settings.debug:
        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            logger.debug("SQL Query", statement=statement, parameters=parameters)
    
    return engine


async def init_db() -> None:
    """Initialize database connection and create tables."""
    global engine, AsyncSessionLocal
    
    settings = get_settings()
    
    # Create engine
    engine = create_database_engine()
    
    # Create session factory
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False,
    )
    
    # Import all models to ensure they're registered
    from app.models import (
        service_collection,
        workflow,
        resource,
        user,
        audit_log,
        project
    )


    # Check if alembic_version table exists to determine if migrations are set up
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            current_migration = result.scalar()
            if current_migration:
                logger.info(f"✅ Database schema managed by Alembic (current: {current_migration})")
            else:
                logger.warning("⚠️ Alembic version table exists but no migration recorded")
    except Exception as e:
        # Alembic version table doesn't exist
        if "relation \"alembic_version\" does not exist" in str(e):
            logger.error("❌ Database migrations not initialized!")
            logger.error("🔧 Please run: docker compose exec vultr-backend uv run alembic upgrade head")
            logger.error("📚 Or for initial setup: docker compose exec vultr-backend uv run alembic stamp head")
            # Don't raise - let the app start but warn about missing migrations
        else:
            logger.error(f"❌ Database connection error: {str(e)}")
            raise
    
    logger.info("✅ Database connection initialized")



async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Alias for compatibility
get_db = get_db_session


async def close_db() -> None:
    """Close database connections."""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("✅ Database connections closed")


# Health check function
async def check_database_health() -> bool:
    """Check if database is healthy."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False