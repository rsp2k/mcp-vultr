"""Audit logging models for tracking all system activities."""

from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4
import enum

from sqlalchemy import (
    Column, String, DateTime, Text, Boolean, JSON, 
    ForeignKey, Index, Enum, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditAction(enum.Enum):
    """Types of actions that can be audited."""
    # Authentication actions
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGED = "password_changed"
    API_KEY_CREATED = "api_key_created"
    API_KEY_USED = "api_key_used"

    # PassKey/WebAuthn actions
    PASSKEY_REGISTERED = "passkey_registered"
    PASSKEY_AUTHENTICATION = "passkey_authentication"
    PASSKEY_DELETED = "passkey_deleted"
    CONNECTED_ACCOUNT_ADDED = "connected_account_added"
    CONNECTED_ACCOUNT_REMOVED = "connected_account_removed"
    
    # Service Collection actions
    COLLECTION_CREATED = "collection_created"
    COLLECTION_UPDATED = "collection_updated"
    COLLECTION_DELETED = "collection_deleted"
    COLLECTION_ARCHIVED = "collection_archived"
    COLLECTION_MEMBER_ADDED = "collection_member_added"
    COLLECTION_MEMBER_REMOVED = "collection_member_removed"
    COLLECTION_MEMBER_ROLE_CHANGED = "collection_member_role_changed"
    
    # Resource actions
    RESOURCE_PLANNED = "resource_planned"
    RESOURCE_CREATED = "resource_created"
    RESOURCE_UPDATED = "resource_updated"
    RESOURCE_DELETED = "resource_deleted"
    RESOURCE_IMPORTED = "resource_imported"
    RESOURCE_COST_UPDATED = "resource_cost_updated"
    
    # Workflow actions
    WORKFLOW_OPERATION_CREATED = "workflow_operation_created"
    WORKFLOW_OPERATION_STARTED = "workflow_operation_started"
    WORKFLOW_OPERATION_COMPLETED = "workflow_operation_completed"
    WORKFLOW_OPERATION_FAILED = "workflow_operation_failed"
    WORKFLOW_OPERATION_CANCELLED = "workflow_operation_cancelled"
    
    # Approval actions
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_EXPIRED = "approval_expired"
    
    # User management actions
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_SUSPENDED = "user_suspended"
    USER_ACTIVATED = "user_activated"
    USER_ROLE_CHANGED = "user_role_changed"
    
    # Vultr API actions
    VULTR_API_CALL = "vultr_api_call"
    VULTR_API_ERROR = "vultr_api_error"
    VULTR_RESOURCE_SYNC = "vultr_resource_sync"
    
    # System actions
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    CONFIGURATION_CHANGED = "configuration_changed"
    BACKUP_CREATED = "backup_created"
    MIGRATION_EXECUTED = "migration_executed"


class AuditSeverity(enum.Enum):
    """Severity levels for audit events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogEntry(Base):
    """
    Audit log entry for tracking all system activities.
    
    Provides comprehensive audit trail for security, compliance,
    and debugging purposes with structured metadata.
    """
    __tablename__ = "audit_logs"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Action details
    action = Column(Enum(AuditAction), nullable=False)
    severity = Column(Enum(AuditSeverity), nullable=False, default=AuditSeverity.INFO)
    message = Column(Text, nullable=False)
    
    # Context relationships
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    service_collection_id = Column(UUID(as_uuid=True), ForeignKey("service_collections.id"), nullable=True)
    
    # Request context
    session_id = Column(String(255), nullable=True)
    request_id = Column(String(255), nullable=True)  # For request tracing
    correlation_id = Column(String(255), nullable=True)  # For operation correlation
    
    # Source information
    source_ip = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(Text, nullable=True)
    source_system = Column(String(100), nullable=True)  # web, api, cli, worker, etc.
    
    # Resource identification
    resource_type = Column(String(50), nullable=True)  # Type of resource affected
    resource_id = Column(String(255), nullable=True)  # ID of resource affected
    parent_resource_id = Column(String(255), nullable=True)  # Parent resource if applicable
    
    # Operation details
    operation_id = Column(String(255), nullable=True)  # Workflow operation ID
    vultr_resource_id = Column(String(255), nullable=True)  # Vultr resource ID
    
    # Data and metadata
    before_data = Column(JSON, nullable=True)  # State before change
    after_data = Column(JSON, nullable=True)  # State after change
    audit_metadata = Column(JSON, default=dict)  # Additional context data (renamed from 'metadata')
    
    # Tags and categorization
    tags = Column(JSON, default=list)  # Tags for categorization
    category = Column(String(50), nullable=True)  # Logical category
    
    # Error information
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    
    # Timing information
    duration_ms = Column(Integer, nullable=True)  # Operation duration in milliseconds
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Compliance and retention
    retention_policy = Column(String(50), default="standard")  # Retention policy
    is_sensitive = Column(Boolean, default=False)  # Contains sensitive data
    is_compliance_relevant = Column(Boolean, default=False)  # Compliance/audit relevant
    
    # Relationships
    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
    service_collection = relationship("ServiceCollection", back_populates="audit_logs")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_audit_logs_timestamp', 'timestamp'),
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_severity', 'severity'),
        Index('idx_audit_logs_collection_id', 'service_collection_id'),
        Index('idx_audit_logs_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_logs_source_ip', 'source_ip'),
        Index('idx_audit_logs_session', 'session_id'),
        Index('idx_audit_logs_request', 'request_id'),
        Index('idx_audit_logs_correlation', 'correlation_id'),
        Index('idx_audit_logs_operation', 'operation_id'),
        Index('idx_audit_logs_compliance', 'is_compliance_relevant', 'timestamp'),
        Index('idx_audit_logs_category_time', 'category', 'timestamp'),
    )
    
    @classmethod
    def create_entry(
        cls,
        action: AuditAction,
        message: str,
        user_id: Optional[str] = None,
        service_collection_id: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        **kwargs
    ) -> "AuditLogEntry":
        """Create a new audit log entry with common fields."""
        return cls(
            action=action,
            message=message,
            severity=severity,
            user_id=user_id,
            service_collection_id=service_collection_id,
            **kwargs
        )
    
    @classmethod
    def log_user_action(
        cls,
        user_id: str,
        action: AuditAction,
        message: str,
        source_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> "AuditLogEntry":
        """Log a user-initiated action."""
        return cls.create_entry(
            action=action,
            message=message,
            user_id=user_id,
            source_ip=source_ip,
            metadata=metadata or {},
            source_system="web",
            **kwargs
        )
    
    @classmethod
    def log_collection_action(
        cls,
        collection_id: str,
        action: AuditAction,
        message: str,
        user_id: Optional[str] = None,
        before_data: Optional[Dict[str, Any]] = None,
        after_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> "AuditLogEntry":
        """Log a Service Collection-related action."""
        return cls.create_entry(
            action=action,
            message=message,
            user_id=user_id,
            service_collection_id=collection_id,
            before_data=before_data,
            after_data=after_data,
            category="service_collection",
            **kwargs
        )
    
    @classmethod
    def log_workflow_action(
        cls,
        operation_id: str,
        action: AuditAction,
        message: str,
        user_id: Optional[str] = None,
        collection_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        **kwargs
    ) -> "AuditLogEntry":
        """Log a workflow operation action."""
        return cls.create_entry(
            action=action,
            message=message,
            user_id=user_id,
            service_collection_id=collection_id,
            operation_id=operation_id,
            duration_ms=duration_ms,
            category="workflow",
            **kwargs
        )
    
    @classmethod
    def log_vultr_api_call(
        cls,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: int,
        user_id: Optional[str] = None,
        collection_id: Optional[str] = None,
        **kwargs
    ) -> "AuditLogEntry":
        """Log a Vultr API call."""
        severity = AuditSeverity.ERROR if status_code >= 400 else AuditSeverity.INFO
        action = AuditAction.VULTR_API_ERROR if status_code >= 400 else AuditAction.VULTR_API_CALL
        
        return cls.create_entry(
            action=action,
            message=f"{method} {endpoint} -> {status_code}",
            severity=severity,
            user_id=user_id,
            service_collection_id=collection_id,
            duration_ms=duration_ms,
            metadata={
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code
            },
            category="vultr_api",
            **kwargs
        )
    
    @classmethod
    def log_system_event(
        cls,
        action: AuditAction,
        message: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> "AuditLogEntry":
        """Log a system-level event."""
        return cls.create_entry(
            action=action,
            message=message,
            severity=severity,
            metadata=metadata or {},
            source_system="system",
            category="system",
            **kwargs
        )
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to this audit entry."""
        if not self.tags:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from this audit entry."""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if audit entry has a specific tag."""
        return bool(self.tags and tag in self.tags)
    
    @property
    def is_error(self) -> bool:
        """Check if this is an error-level event."""
        return self.severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]
    
    @property
    def is_security_relevant(self) -> bool:
        """Check if this event is security-relevant."""
        security_actions = [
            AuditAction.LOGIN_FAILED,
            AuditAction.PASSWORD_CHANGED,
            AuditAction.USER_SUSPENDED,
            AuditAction.USER_ROLE_CHANGED,
            AuditAction.COLLECTION_MEMBER_ROLE_CHANGED,
        ]
        return self.action in security_actions
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            "id": str(self.id),
            "action": self.action.value,
            "severity": self.severity.value,
            "message": self.message,
            "user_id": str(self.user_id) if self.user_id else None,
            "service_collection_id": str(self.service_collection_id) if self.service_collection_id else None,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "parent_resource_id": self.parent_resource_id,
            "operation_id": self.operation_id,
            "vultr_resource_id": self.vultr_resource_id,
            "category": self.category,
            "tags": self.tags,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "is_error": self.is_error,
            "is_security_relevant": self.is_security_relevant,
            "is_compliance_relevant": self.is_compliance_relevant
        }
        
        if include_sensitive:
            result.update({
                "source_ip": self.source_ip,
                "user_agent": self.user_agent,
                "source_system": self.source_system,
                "session_id": self.session_id,
                "request_id": self.request_id,
                "correlation_id": self.correlation_id,
                "before_data": self.before_data,
                "after_data": self.after_data,
                "metadata": self.audit_metadata,
                "error_code": self.error_code,
                "error_message": self.error_message,
                "retention_policy": self.retention_policy,
                "is_sensitive": self.is_sensitive
            })
        
        return result