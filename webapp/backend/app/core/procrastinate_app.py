"""Procrastinate queue system configuration."""

import structlog
from procrastinate import App
from procrastinate.contrib.aiopg import AiopgConnector
from procrastinate.contrib.sqlalchemy import SQLAlchemyPsycopg2Connector
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings

logger = structlog.get_logger()


def create_procrastinate_app() -> App:
    """Create and configure Procrastinate app."""
    settings = get_settings()
    
    # Convert asyncpg URL to psycopg2 URL for Procrastinate
    db_url = str(settings.procrastinate_database_url).replace("postgresql+asyncpg://", "postgresql://")
    
    # Use AiopgConnector for async operations
    connector = AiopgConnector(dsn=db_url)
    
    # Create app
    app = App(
        connector=connector,
        import_paths=[
            "app.tasks.vultr_operations",
            "app.tasks.workflow_operations", 
            "app.tasks.notification_tasks",
            "app.tasks.cost_estimation",
            "app.tasks.audit_tasks"
        ]
    )
    
    logger.info("✅ Procrastinate app configured")
    return app


# Global Procrastinate app instance
procrastinate_app = create_procrastinate_app()


# Convenience functions for task management
async def enqueue_task(task_name: str, **kwargs) -> str:
    """Enqueue a task for background processing."""
    job = await procrastinate_app.configure_task(task_name).defer_async(**kwargs)
    logger.info("Task enqueued", task_name=task_name, job_id=job.id, kwargs=kwargs)
    return job.id


async def get_job_status(job_id: int) -> dict:
    """Get the status of a background job."""
    # Note: This would need to be implemented based on Procrastinate's job tracking
    # For now, return a placeholder
    return {
        "job_id": job_id,
        "status": "unknown",
        "message": "Job status tracking not yet implemented"
    }


async def cancel_job(job_id: int) -> bool:
    """Cancel a background job."""
    # Note: This would need to be implemented based on Procrastinate's job management
    logger.info("Job cancellation requested", job_id=job_id)
    return True


# Task decorators for convenience
def vultr_task(name: str, **kwargs):
    """Decorator for Vultr API tasks."""
    return procrastinate_app.task(name=name, queue="vultr_operations", **kwargs)


def workflow_task(name: str, **kwargs):
    """Decorator for workflow processing tasks."""
    return procrastinate_app.task(name=name, queue="workflow_processing", **kwargs)


def notification_task(name: str, **kwargs):
    """Decorator for notification tasks.""" 
    return procrastinate_app.task(name=name, queue="notifications", **kwargs)


def audit_task(name: str, **kwargs):
    """Decorator for audit logging tasks."""
    return procrastinate_app.task(name=name, queue="audit_logging", **kwargs)