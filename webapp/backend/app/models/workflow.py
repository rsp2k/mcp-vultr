"""Workflow and approval system models."""

from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4
import enum

from sqlalchemy import (
    Column, String, DateTime, Text, Boolean, JSON, 
    ForeignKey, Integer, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class OperationStatus(enum.Enum):
    """Status of workflow operations."""
    QUEUED = "queued"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OperationType(enum.Enum):
    """Types of operations that can be performed."""
    CREATE_INSTANCE = "create_instance"
    DELETE_INSTANCE = "delete_instance"
    UPDATE_INSTANCE = "update_instance"
    CREATE_DOMAIN = "create_domain"
    DELETE_DOMAIN = "delete_domain"
    CREATE_DNS_RECORD = "create_dns_record"
    UPDATE_DNS_RECORD = "update_dns_record"
    DELETE_DNS_RECORD = "delete_dns_record"
    CREATE_FIREWALL_RULE = "create_firewall_rule"
    DELETE_FIREWALL_RULE = "delete_firewall_rule"
    START_INSTANCE = "start_instance"
    STOP_INSTANCE = "stop_instance"
    REBOOT_INSTANCE = "reboot_instance"
    SNAPSHOT_INSTANCE = "snapshot_instance"


class ApprovalStatus(enum.Enum):
    """Status of approval requests."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class WorkflowOperation(Base):
    """
    Represents a queued operation in the workflow system.
    
    Operations are queued before execution and go through approval
    workflows based on Service Collection configuration.
    """
    __tablename__ = "workflow_operations"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Operation details
    operation_type = Column(Enum(OperationType), nullable=False)
    status = Column(Enum(OperationStatus), nullable=False, default=OperationStatus.QUEUED)
    
    # Relationships
    service_collection_id = Column(UUID(as_uuid=True), ForeignKey("service_collections.id"), nullable=False)
    
    # Request details
    requested_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    request_context = Column(JSON, default=dict)  # Additional context
    
    # Operation configuration
    resource_type = Column(String(50), nullable=False)  # domain, instance, etc.
    resource_config = Column(JSON, nullable=False)  # Configuration for the resource
    
    # Dependencies
    depends_on_operations = Column(JSON, default=list)  # List of operation IDs this depends on
    blocks_operations = Column(JSON, default=list)  # List of operations this blocks
    
    # Execution details
    vultr_resource_id = Column(String(255))  # Vultr resource ID after creation
    execution_job_id = Column(String(255))  # Procrastinate job ID
    execution_logs = Column(Text)
    error_message = Column(Text)
    
    # Cost estimation
    estimated_cost_monthly = Column(String(20))  # Estimated monthly cost
    estimated_cost_setup = Column(String(20))  # One-time setup cost
    
    # Timing
    scheduled_at = Column(DateTime)  # When to execute (for scheduled operations)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    service_collection = relationship("ServiceCollection", back_populates="workflow_operations")
    approval_requests = relationship(
        "ApprovalRequest",
        back_populates="workflow_operation",
        cascade="all, delete-orphan"
    )

    # User relationships
    requested_by = relationship("User", foreign_keys=[requested_by_id], back_populates="requested_operations")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], back_populates="assigned_operations")
    
    def requires_approval(self) -> bool:
        """Check if this operation requires approval."""
        return self.service_collection.requires_approval(self.operation_type.value)
    
    def can_execute(self) -> bool:
        """Check if operation is ready for execution."""
        if self.status != OperationStatus.APPROVED:
            return False
        
        # Check dependencies
        # This would need to query other operations
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "operation_type": self.operation_type.value,
            "status": self.status.value,
            "service_collection_id": str(self.service_collection_id),
            "requested_by_id": str(self.requested_by_id),
            "assigned_to_id": str(self.assigned_to_id) if self.assigned_to_id else None,
            "request_context": self.request_context,
            "resource_type": self.resource_type,
            "resource_config": self.resource_config,
            "depends_on_operations": self.depends_on_operations,
            "blocks_operations": self.blocks_operations,
            "vultr_resource_id": self.vultr_resource_id,
            "execution_job_id": self.execution_job_id,
            "execution_logs": self.execution_logs,
            "error_message": self.error_message,
            "estimated_cost_monthly": self.estimated_cost_monthly,
            "estimated_cost_setup": self.estimated_cost_setup,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "requires_approval": self.requires_approval(),
            "can_execute": self.can_execute()
        }


class ApprovalRequest(Base):
    """
    Represents an approval request for a workflow operation.
    
    Operations that require approval create approval requests
    that are routed to appropriate approvers.
    """
    __tablename__ = "approval_requests"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Relationships
    workflow_operation_id = Column(UUID(as_uuid=True), ForeignKey("workflow_operations.id"), nullable=False)
    
    # Approval details
    status = Column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    approver_email = Column(String(255), nullable=False)
    
    # Request metadata
    approval_reason = Column(Text)  # Why approval is needed
    business_justification = Column(Text)  # Business case
    risk_assessment = Column(JSON, default=dict)  # Risk analysis
    
    # Decision details
    decision = Column(String(20))  # approved, rejected, etc.
    decision_reason = Column(Text)
    decided_by = Column(String(255))  # Who made the decision
    decided_at = Column(DateTime)
    
    # Expiration
    expires_at = Column(DateTime)  # When approval request expires
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    workflow_operation = relationship("WorkflowOperation", back_populates="approval_requests")
    
    @property
    def is_expired(self) -> bool:
        """Check if approval request has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_pending(self) -> bool:
        """Check if approval is still pending."""
        return self.status == ApprovalStatus.PENDING and not self.is_expired
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "workflow_operation_id": str(self.workflow_operation_id),
            "status": self.status.value,
            "approver_email": self.approver_email,
            "approval_reason": self.approval_reason,
            "business_justification": self.business_justification,
            "risk_assessment": self.risk_assessment,
            "decision": self.decision,
            "decision_reason": self.decision_reason,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_expired": self.is_expired,
            "is_pending": self.is_pending
        }