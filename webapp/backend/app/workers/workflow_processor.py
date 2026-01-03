"""Workflow operation processor using Procrastinate."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import UUID

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.core.procrastinate_app import procrastinate_app
from app.models.workflow import WorkflowOperation, OperationStatus, OperationType
from app.models.service_collection import ServiceCollection
from app.core.audit import audit_log

logger = structlog.get_logger(__name__)


@procrastinate_app.task(queue="workflow")
async def execute_workflow_operation(operation_id: str) -> Dict[str, Any]:
    """Execute a workflow operation."""
    
    logger.info("Starting workflow operation execution", operation_id=operation_id)
    
    async with get_db_session() as db:
        # Get operation with relationships
        query = select(WorkflowOperation).options(
            selectinload(WorkflowOperation.service_collection),
            selectinload(WorkflowOperation.approval_requests)
        ).where(WorkflowOperation.id == UUID(operation_id))
        
        result = await db.execute(query)
        operation = result.scalar_one_or_none()
        
        if not operation:
            logger.error("Operation not found", operation_id=operation_id)
            return {"status": "error", "message": "Operation not found"}
        
        # Check if operation can be executed
        if not operation.can_execute():
            logger.warning("Operation cannot be executed", 
                         operation_id=operation_id, 
                         status=operation.status.value)
            return {"status": "error", "message": "Operation cannot be executed"}
        
        # Update status to executing
        operation.status = OperationStatus.EXECUTING
        operation.started_at = datetime.utcnow()
        operation.execution_logs = f"Started execution at {datetime.utcnow().isoformat()}\n"
        
        await db.commit()
        
        try:
            # Execute the operation based on its type
            result = await _execute_operation_by_type(operation, db)
            
            # Update operation with results
            if result.get("success"):
                operation.status = OperationStatus.COMPLETED
                operation.completed_at = datetime.utcnow()
                operation.vultr_resource_id = result.get("resource_id")
                operation.execution_logs += f"Completed successfully at {datetime.utcnow().isoformat()}\n"
            else:
                operation.status = OperationStatus.FAILED
                operation.error_message = result.get("error", "Unknown error")
                operation.execution_logs += f"Failed at {datetime.utcnow().isoformat()}: {result.get('error')}\n"
            
            await db.commit()
            
            # Log audit entry
            await audit_log(
                db, operation.requested_by_email or "system", "workflow.operation.executed",
                {
                    "operation_id": operation_id,
                    "operation_type": operation.operation_type.value,
                    "status": operation.status.value,
                    "success": result.get("success", False)
                }
            )
            
            logger.info("Workflow operation execution completed",
                       operation_id=operation_id,
                       status=operation.status.value,
                       success=result.get("success", False))
            
            return {
                "status": "success" if result.get("success") else "failed",
                "operation_id": operation_id,
                "vultr_resource_id": result.get("resource_id"),
                "message": result.get("message", "Operation completed")
            }
            
        except Exception as e:
            logger.error("Error executing workflow operation",
                        operation_id=operation_id,
                        error=str(e),
                        exc_info=True)
            
            # Update operation with error
            operation.status = OperationStatus.FAILED
            operation.error_message = str(e)
            operation.execution_logs += f"Error at {datetime.utcnow().isoformat()}: {str(e)}\n"
            
            await db.commit()
            
            # Increment retry count and retry if possible
            operation.retry_count += 1
            if operation.retry_count < operation.max_retries:
                logger.info("Retrying workflow operation",
                           operation_id=operation_id,
                           retry_count=operation.retry_count)
                
                # Reset status for retry
                operation.status = OperationStatus.APPROVED
                await db.commit()
                
                # Schedule retry with delay
                await execute_workflow_operation.defer(operation_id, schedule_in={"minutes": 5})
            
            return {
                "status": "error",
                "operation_id": operation_id,
                "error": str(e),
                "retry_count": operation.retry_count
            }


async def _execute_operation_by_type(
    operation: WorkflowOperation, 
    db: AsyncSession
) -> Dict[str, Any]:
    """Execute operation based on its type."""
    
    operation_type = operation.operation_type
    resource_config = operation.resource_config
    
    logger.info("Executing operation", 
               operation_type=operation_type.value,
               resource_type=operation.resource_type)
    
    try:
        if operation_type == OperationType.CREATE_INSTANCE:
            return await _create_vultr_instance(operation, resource_config)
        elif operation_type == OperationType.DELETE_INSTANCE:
            return await _delete_vultr_instance(operation, resource_config)
        elif operation_type == OperationType.CREATE_DOMAIN:
            return await _create_vultr_domain(operation, resource_config)
        elif operation_type == OperationType.DELETE_DOMAIN:
            return await _delete_vultr_domain(operation, resource_config)
        elif operation_type == OperationType.CREATE_DNS_RECORD:
            return await _create_dns_record(operation, resource_config)
        elif operation_type == OperationType.UPDATE_DNS_RECORD:
            return await _update_dns_record(operation, resource_config)
        elif operation_type == OperationType.DELETE_DNS_RECORD:
            return await _delete_dns_record(operation, resource_config)
        else:
            return {
                "success": False,
                "error": f"Unsupported operation type: {operation_type.value}"
            }
    
    except Exception as e:
        logger.error("Error in operation execution",
                    operation_type=operation_type.value,
                    error=str(e))
        return {
            "success": False,
            "error": str(e)
        }


async def _create_vultr_instance(
    operation: WorkflowOperation, 
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a Vultr instance."""
    
    # This is a mock implementation - in real use, you'd integrate with Vultr API
    logger.info("Creating Vultr instance", config=config)
    
    # Simulate API call
    await _simulate_api_call()
    
    # Mock resource ID
    resource_id = f"instance_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    return {
        "success": True,
        "resource_id": resource_id,
        "message": f"Instance created successfully: {resource_id}"
    }


async def _delete_vultr_instance(
    operation: WorkflowOperation, 
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Delete a Vultr instance."""
    
    logger.info("Deleting Vultr instance", config=config)
    
    # Simulate API call
    await _simulate_api_call()
    
    return {
        "success": True,
        "message": f"Instance {config.get('instance_id')} deleted successfully"
    }


async def _create_vultr_domain(
    operation: WorkflowOperation, 
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a Vultr domain."""
    
    logger.info("Creating Vultr domain", config=config)
    
    # Simulate API call
    await _simulate_api_call()
    
    domain_name = config.get("domain_name")
    return {
        "success": True,
        "resource_id": domain_name,
        "message": f"Domain {domain_name} created successfully"
    }


async def _delete_vultr_domain(
    operation: WorkflowOperation, 
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Delete a Vultr domain."""
    
    logger.info("Deleting Vultr domain", config=config)
    
    # Simulate API call
    await _simulate_api_call()
    
    domain_name = config.get("domain_name")
    return {
        "success": True,
        "message": f"Domain {domain_name} deleted successfully"
    }


async def _create_dns_record(
    operation: WorkflowOperation, 
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a DNS record."""
    
    logger.info("Creating DNS record", config=config)
    
    # Simulate API call
    await _simulate_api_call()
    
    record_type = config.get("record_type")
    name = config.get("name")
    value = config.get("value")
    
    record_id = f"record_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    return {
        "success": True,
        "resource_id": record_id,
        "message": f"DNS record created: {name} ({record_type}) -> {value}"
    }


async def _update_dns_record(
    operation: WorkflowOperation, 
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Update a DNS record."""
    
    logger.info("Updating DNS record", config=config)
    
    # Simulate API call
    await _simulate_api_call()
    
    record_id = config.get("record_id")
    return {
        "success": True,
        "message": f"DNS record {record_id} updated successfully"
    }


async def _delete_dns_record(
    operation: WorkflowOperation, 
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Delete a DNS record."""
    
    logger.info("Deleting DNS record", config=config)
    
    # Simulate API call
    await _simulate_api_call()
    
    record_id = config.get("record_id")
    return {
        "success": True,
        "message": f"DNS record {record_id} deleted successfully"
    }


async def _simulate_api_call() -> None:
    """Simulate an API call delay."""
    import asyncio
    await asyncio.sleep(1)  # Simulate network delay


@procrastinate_app.task(queue="workflow")
async def auto_execute_approved_operations() -> Dict[str, Any]:
    """Automatically execute approved operations that are ready."""
    
    logger.info("Checking for approved operations to execute")
    
    async with get_db_session() as db:
        # Find approved operations that can be executed
        query = select(WorkflowOperation).options(
            selectinload(WorkflowOperation.service_collection),
            selectinload(WorkflowOperation.approval_requests)
        ).where(
            WorkflowOperation.status == OperationStatus.APPROVED
        )
        
        result = await db.execute(query)
        operations = result.scalars().all()
        
        executed_count = 0
        
        for operation in operations:
            if operation.can_execute():
                logger.info("Auto-executing approved operation", 
                           operation_id=str(operation.id))
                
                # Queue for execution
                await execute_workflow_operation.defer(str(operation.id))
                executed_count += 1
        
        logger.info("Auto-execution check completed", 
                   total_operations=len(operations),
                   executed_count=executed_count)
        
        return {
            "status": "success",
            "total_operations": len(operations),
            "executed_count": executed_count
        }


@procrastinate_app.task(queue="cleanup")  # Scheduled separately via Procrastinate CLI or scheduler
async def cleanup_old_operations() -> Dict[str, Any]:
    """Clean up old completed/failed operations."""
    
    logger.info("Starting cleanup of old workflow operations")
    
    async with get_db_session() as db:
        # Keep operations for 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Delete old completed/failed operations
        delete_query = select(WorkflowOperation).where(
            and_(
                WorkflowOperation.status.in_([
                    OperationStatus.COMPLETED, 
                    OperationStatus.FAILED,
                    OperationStatus.CANCELLED
                ]),
                WorkflowOperation.updated_at < cutoff_date
            )
        )
        
        result = await db.execute(delete_query)
        old_operations = result.scalars().all()
        
        deleted_count = 0
        for operation in old_operations:
            await db.delete(operation)
            deleted_count += 1
        
        await db.commit()
        
        logger.info("Cleanup completed", deleted_count=deleted_count)
        
        return {
            "status": "success",
            "deleted_count": deleted_count
        }