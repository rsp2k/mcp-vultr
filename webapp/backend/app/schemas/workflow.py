"""Pydantic schemas for workflow operations and approvals."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.workflow import OperationType, OperationStatus, ApprovalStatus


class WorkflowOperationBase(BaseModel):
    """Base schema for workflow operations."""
    operation_type: OperationType
    resource_type: str = Field(..., description="Type of resource (instance, domain, etc.)")
    resource_config: Dict[str, Any] = Field(..., description="Configuration for the resource")
    request_context: Optional[Dict[str, Any]] = Field(None, description="Additional request context")
    depends_on_operations: Optional[List[str]] = Field(None, description="List of operation IDs this depends on")
    estimated_cost_monthly: Optional[str] = Field(None, description="Estimated monthly cost")
    estimated_cost_setup: Optional[str] = Field(None, description="One-time setup cost")
    scheduled_at: Optional[datetime] = Field(None, description="When to execute (for scheduled operations)")


class WorkflowOperationCreate(WorkflowOperationBase):
    """Schema for creating a workflow operation."""
    service_collection_id: UUID = Field(..., description="ID of the service collection")


class WorkflowOperationUpdate(BaseModel):
    """Schema for updating a workflow operation."""
    resource_config: Optional[Dict[str, Any]] = None
    request_context: Optional[Dict[str, Any]] = None
    estimated_cost_monthly: Optional[str] = None
    estimated_cost_setup: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class WorkflowOperationResponse(WorkflowOperationBase):
    """Schema for workflow operation responses."""
    id: UUID
    status: OperationStatus
    service_collection_id: UUID
    requested_by: str
    vultr_resource_id: Optional[str] = None
    execution_job_id: Optional[str] = None
    execution_logs: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    requires_approval: bool
    can_execute: bool
    
    class Config:
        from_attributes = True


class ApprovalRequestBase(BaseModel):
    """Base schema for approval requests."""
    approval_reason: Optional[str] = Field(None, description="Why approval is needed")
    business_justification: Optional[str] = Field(None, description="Business case for the operation")
    risk_assessment: Optional[Dict[str, Any]] = Field(None, description="Risk analysis")


class ApprovalRequestCreate(ApprovalRequestBase):
    """Schema for creating an approval request."""
    workflow_operation_id: UUID
    approver_email: str
    expires_at: Optional[datetime] = None


class ApprovalRequestResponse(ApprovalRequestBase):
    """Schema for approval request responses."""
    id: UUID
    workflow_operation_id: UUID
    status: ApprovalStatus
    approver_email: str
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    is_expired: bool
    is_pending: bool
    
    class Config:
        from_attributes = True


class ApprovalDecision(BaseModel):
    """Schema for approval decisions."""
    approve: bool = Field(..., description="Whether to approve or reject")
    reason: Optional[str] = Field(None, description="Reason for the decision")


class WorkflowStats(BaseModel):
    """Schema for workflow statistics."""
    total_operations: int
    pending_approval: int
    approved: int
    rejected: int
    executing: int
    completed: int
    failed: int
    cancelled: int
    
    pending_approvals: int
    expired_approvals: int
    
    operations_by_type: Dict[str, int]
    operations_by_collection: Dict[str, int]
    
    avg_approval_time_hours: Optional[float] = None
    avg_execution_time_minutes: Optional[float] = None


class OperationTemplate(BaseModel):
    """Schema for operation templates."""
    id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    operation_type: OperationType
    resource_type: str
    default_config: Dict[str, Any]
    parameter_schema: Optional[Dict[str, Any]] = None
    requires_approval: bool = True
    auto_approve_environments: List[str] = []
    estimated_cost_monthly: Optional[str] = None
    estimated_cost_setup: Optional[str] = None
    
    class Config:
        from_attributes = True


class BulkOperationRequest(BaseModel):
    """Schema for bulk operation requests."""
    service_collection_id: UUID
    operations: List[WorkflowOperationCreate]
    description: Optional[str] = Field(None, description="Description for the bulk operation")
    execute_sequentially: bool = Field(False, description="Execute operations in sequence")


class OperationExecutionLog(BaseModel):
    """Schema for operation execution logs."""
    timestamp: datetime
    level: str = Field(..., description="Log level (info, warning, error)")
    message: str
    details: Optional[Dict[str, Any]] = None
    
    
class WorkflowMetrics(BaseModel):
    """Schema for workflow metrics and analytics."""
    date_range: str
    total_requests: int
    approval_rate: float
    avg_approval_time_hours: float
    avg_execution_time_minutes: float
    
    success_rate: float
    failure_rate: float
    
    most_common_operations: List[Dict[str, Any]]
    busiest_collections: List[Dict[str, Any]]
    busiest_requesters: List[Dict[str, Any]]
    
    cost_estimates: Dict[str, float]  # total_monthly, total_setup
    
    trends: Dict[str, List[Dict[str, Any]]]  # daily/weekly trends