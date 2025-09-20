"""Audit logging utilities."""

import structlog
from typing import Dict, Any, Optional
from datetime import datetime

from app.models.audit_log import AuditLogEntry, AuditAction, AuditSeverity

logger = structlog.get_logger()


async def audit_log(
    action: AuditAction,
    user_id: str,
    description: str,
    severity: AuditSeverity = AuditSeverity.INFO,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    vultr_resource_id: Optional[str] = None,
    before_data: Optional[Dict[str, Any]] = None,
    after_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    session_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    is_sensitive: bool = False
) -> AuditLogEntry:
    """
    Create an audit log entry.
    
    Args:
        action: Type of action performed
        user_id: ID of user performing action
        description: Human-readable description of the action
        severity: Severity level of the action
        resource_type: Type of resource being acted upon
        resource_id: ID of the resource
        vultr_resource_id: Vultr resource ID if applicable
        before_data: State before the action
        after_data: State after the action
        metadata: Additional context data
        request_id: Request ID for tracing
        correlation_id: Correlation ID for related operations
        session_id: User session ID
        ip_address: Client IP address
        user_agent: Client user agent
        error_code: Error code if action failed
        error_message: Error message if action failed
        is_sensitive: Whether this log contains sensitive data
        
    Returns:
        Created audit log entry
    """
    # Create audit log entry
    entry = AuditLogEntry(
        action=action,
        user_id=user_id,
        description=description,
        severity=severity,
        resource_type=resource_type,
        resource_id=resource_id,
        vultr_resource_id=vultr_resource_id,
        before_data=before_data or {},
        after_data=after_data or {},
        audit_metadata=metadata or {},
        request_id=request_id,
        correlation_id=correlation_id,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        error_code=error_code,
        error_message=error_message,
        is_sensitive=is_sensitive,
        timestamp=datetime.utcnow()
    )
    
    # Log to structured logger as well
    logger.info(
        "Audit log entry",
        action=action.value,
        user_id=user_id,
        description=description,
        severity=severity.value,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        correlation_id=correlation_id
    )
    
    return entry


async def audit_service_collection_action(
    action: AuditAction,
    user_id: str,
    service_collection_id: str,
    description: str,
    severity: AuditSeverity = AuditSeverity.INFO,
    before_data: Optional[Dict[str, Any]] = None,
    after_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs
) -> AuditLogEntry:
    """
    Convenience function for auditing Service Collection actions.
    
    Args:
        action: Type of action performed
        user_id: ID of user performing action
        service_collection_id: ID of the service collection
        description: Human-readable description
        severity: Severity level
        before_data: State before action
        after_data: State after action
        metadata: Additional context
        **kwargs: Additional audit_log parameters
        
    Returns:
        Created audit log entry
    """
    return await audit_log(
        action=action,
        user_id=user_id,
        description=description,
        severity=severity,
        resource_type="service_collection",
        resource_id=service_collection_id,
        before_data=before_data,
        after_data=after_data,
        metadata=metadata,
        **kwargs
    )


async def audit_workflow_action(
    action: AuditAction,
    user_id: str,
    workflow_id: str,
    description: str,
    severity: AuditSeverity = AuditSeverity.INFO,
    before_data: Optional[Dict[str, Any]] = None,
    after_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs
) -> AuditLogEntry:
    """
    Convenience function for auditing workflow actions.
    
    Args:
        action: Type of action performed
        user_id: ID of user performing action
        workflow_id: ID of the workflow
        description: Human-readable description
        severity: Severity level
        before_data: State before action
        after_data: State after action
        metadata: Additional context
        **kwargs: Additional audit_log parameters
        
    Returns:
        Created audit log entry
    """
    return await audit_log(
        action=action,
        user_id=user_id,
        description=description,
        severity=severity,
        resource_type="workflow",
        resource_id=workflow_id,
        before_data=before_data,
        after_data=after_data,
        metadata=metadata,
        **kwargs
    )