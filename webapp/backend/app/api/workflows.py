"""Workflow and approval API routes."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.service_collection import ServiceCollection
from app.models.workflow import (
    WorkflowOperation, ApprovalRequest, OperationType, 
    OperationStatus, ApprovalStatus
)
from app.schemas.workflow import (
    WorkflowOperationCreate, WorkflowOperationResponse,
    ApprovalRequestCreate, ApprovalRequestResponse,
    ApprovalDecision, WorkflowOperationUpdate
)
from app.core.audit import audit_log
from app.workers.workflow_processor import execute_workflow_operation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/operations")
async def list_workflow_operations(
    collection_id: Optional[UUID] = Query(None, description="Filter by service collection"),
    status: Optional[OperationStatus] = Query(None, description="Filter by status"),
    operation_type: Optional[OperationType] = Query(None, description="Filter by operation type"),
    requested_by: Optional[str] = Query(None, description="Filter by requester email"),
    limit: int = Query(50, ge=1, le=100, description="Number of operations to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List workflow operations with filtering and pagination."""
    
    query = select(WorkflowOperation).options(
        selectinload(WorkflowOperation.service_collection),
        selectinload(WorkflowOperation.approval_requests)
    )
    
    # Apply filters
    filters = []
    
    if collection_id:
        # Check if user has access to this collection
        collection_query = select(ServiceCollection).where(ServiceCollection.id == collection_id)
        result = await db.execute(collection_query)
        collection = result.scalar_one_or_none()
        
        if not collection or not collection.can_user_access(current_user.email, "viewer"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service collection not found or access denied"
            )
        
        filters.append(WorkflowOperation.service_collection_id == collection_id)
    else:
        # Filter to collections user has access to
        user_collections = select(ServiceCollection.id).where(
            or_(
                ServiceCollection.created_by == current_user.email,
                ServiceCollection.members.contains([{"email": current_user.email}])
            )
        )
        filters.append(WorkflowOperation.service_collection_id.in_(user_collections))
    
    if status:
        filters.append(WorkflowOperation.status == status)
        
    if operation_type:
        filters.append(WorkflowOperation.operation_type == operation_type)
        
    if requested_by:
        filters.append(WorkflowOperation.requested_by == requested_by)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Order by created_at descending
    query = query.order_by(WorkflowOperation.created_at.desc())
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    operations = result.scalars().all()
    
    await audit_log(
        db, current_user.email, "workflow.operations.list",
        {"collection_id": str(collection_id) if collection_id else None, "count": len(operations)}
    )
    
    return [op.to_dict() for op in operations]


@router.get("/operations/{operation_id}")
async def get_workflow_operation(
    operation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific workflow operation."""
    
    query = select(WorkflowOperation).options(
        selectinload(WorkflowOperation.service_collection),
        selectinload(WorkflowOperation.approval_requests)
    ).where(WorkflowOperation.id == operation_id)
    
    result = await db.execute(query)
    operation = result.scalar_one_or_none()
    
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow operation not found"
        )
    
    # Check access
    if not operation.service_collection.can_user_access(current_user.email, "viewer"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow operation not found or access denied"
        )
    
    await audit_log(
        db, current_user.email, "workflow.operation.view",
        {"operation_id": str(operation_id)}
    )
    
    return operation.to_dict()


@router.post("/operations")
async def create_workflow_operation(
    operation_data: WorkflowOperationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new workflow operation."""
    
    # Get and validate service collection
    collection_query = select(ServiceCollection).where(
        ServiceCollection.id == operation_data.service_collection_id
    )
    result = await db.execute(collection_query)
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service collection not found"
        )
    
    # Check if user can create operations in this collection
    user_role = collection.get_user_role(current_user.email)
    if user_role not in ["member", "manager", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create operations in this collection"
        )
    
    # Create workflow operation
    operation = WorkflowOperation(
        operation_type=operation_data.operation_type,
        service_collection_id=operation_data.service_collection_id,
        requested_by=current_user.email,
        request_context=operation_data.request_context or {},
        resource_type=operation_data.resource_type,
        resource_config=operation_data.resource_config,
        depends_on_operations=operation_data.depends_on_operations or [],
        estimated_cost_monthly=operation_data.estimated_cost_monthly,
        estimated_cost_setup=operation_data.estimated_cost_setup,
        scheduled_at=operation_data.scheduled_at
    )
    
    # Determine initial status
    if operation.requires_approval():
        operation.status = OperationStatus.PENDING_APPROVAL
    else:
        operation.status = OperationStatus.APPROVED
    
    db.add(operation)
    await db.flush()  # Get the ID
    
    # Create approval requests if needed
    if operation.requires_approval():
        await _create_approval_requests(db, operation, collection)
    
    await db.commit()
    
    # Reload with relationships
    await db.refresh(operation, ["service_collection", "approval_requests"])
    
    await audit_log(
        db, current_user.email, "workflow.operation.create",
        {
            "operation_id": str(operation.id),
            "operation_type": operation.operation_type.value,
            "collection_id": str(operation.service_collection_id),
            "requires_approval": operation.requires_approval()
        }
    )
    
    return operation.to_dict()


@router.patch("/operations/{operation_id}")
async def update_workflow_operation(
    operation_id: UUID,
    update_data: WorkflowOperationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a workflow operation."""
    
    query = select(WorkflowOperation).options(
        selectinload(WorkflowOperation.service_collection),
        selectinload(WorkflowOperation.approval_requests)
    ).where(WorkflowOperation.id == operation_id)
    
    result = await db.execute(query)
    operation = result.scalar_one_or_none()
    
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow operation not found"
        )
    
    # Check permissions
    user_role = operation.service_collection.get_user_role(current_user.email)
    
    # Only requester or managers/admins can update
    can_update = (
        operation.requested_by == current_user.email or
        user_role in ["manager", "admin"]
    )
    
    if not can_update:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update this operation"
        )
    
    # Can't update completed or failed operations
    if operation.status in [OperationStatus.COMPLETED, OperationStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update completed or failed operations"
        )
    
    # Apply updates
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(operation, field, value)
    
    operation.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(operation, ["service_collection", "approval_requests"])
    
    await audit_log(
        db, current_user.email, "workflow.operation.update",
        {"operation_id": str(operation_id), "updates": update_dict}
    )
    
    return operation.to_dict()


@router.delete("/operations/{operation_id}")
async def delete_workflow_operation(
    operation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a workflow operation."""
    
    query = select(WorkflowOperation).options(
        selectinload(WorkflowOperation.service_collection)
    ).where(WorkflowOperation.id == operation_id)
    
    result = await db.execute(query)
    operation = result.scalar_one_or_none()
    
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow operation not found"
        )
    
    # Check permissions
    user_role = operation.service_collection.get_user_role(current_user.email)
    
    # Only requester or managers/admins can delete
    can_delete = (
        operation.requested_by == current_user.email or
        user_role in ["manager", "admin"]
    )
    
    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete this operation"
        )
    
    # Can't delete executing operations
    if operation.status == OperationStatus.EXECUTING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete executing operations"
        )
    
    await db.delete(operation)
    await db.commit()
    
    await audit_log(
        db, current_user.email, "workflow.operation.delete",
        {"operation_id": str(operation_id)}
    )
    
    return {"message": "Operation deleted successfully"}


@router.get("/approvals")
async def list_approval_requests(
    status: Optional[ApprovalStatus] = Query(None, description="Filter by approval status"),
    approver_email: Optional[str] = Query(None, description="Filter by approver email"),
    collection_id: Optional[UUID] = Query(None, description="Filter by service collection"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List approval requests."""
    
    query = select(ApprovalRequest).options(
        selectinload(ApprovalRequest.workflow_operation).selectinload(
            WorkflowOperation.service_collection
        )
    )
    
    filters = []
    
    # Filter to approvals for collections user has access to
    user_collections = select(ServiceCollection.id).where(
        or_(
            ServiceCollection.created_by == current_user.email,
            ServiceCollection.members.contains([{"email": current_user.email}])
        )
    )
    
    operation_filter = select(WorkflowOperation.id).where(
        WorkflowOperation.service_collection_id.in_(user_collections)
    )
    
    filters.append(ApprovalRequest.workflow_operation_id.in_(operation_filter))
    
    if status:
        filters.append(ApprovalRequest.status == status)
        
    if approver_email:
        filters.append(ApprovalRequest.approver_email == approver_email)
        
    if collection_id:
        collection_operations = select(WorkflowOperation.id).where(
            WorkflowOperation.service_collection_id == collection_id
        )
        filters.append(ApprovalRequest.workflow_operation_id.in_(collection_operations))
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.order_by(ApprovalRequest.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    approvals = result.scalars().all()
    
    await audit_log(
        db, current_user.email, "workflow.approvals.list",
        {"count": len(approvals)}
    )
    
    return [approval.to_dict() for approval in approvals]


@router.post("/approvals/{approval_id}/decide")
async def decide_approval(
    approval_id: UUID,
    decision: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve or reject an approval request."""
    
    query = select(ApprovalRequest).options(
        selectinload(ApprovalRequest.workflow_operation).selectinload(
            WorkflowOperation.service_collection
        )
    ).where(ApprovalRequest.id == approval_id)
    
    result = await db.execute(query)
    approval = result.scalar_one_or_none()
    
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found"
        )
    
    # Check if current user is the designated approver
    if approval.approver_email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to approve this request"
        )
    
    # Check if approval is still pending
    if not approval.is_pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This approval request is no longer pending"
        )
    
    # Update approval
    approval.status = ApprovalStatus.APPROVED if decision.approve else ApprovalStatus.REJECTED
    approval.decision = "approved" if decision.approve else "rejected"
    approval.decision_reason = decision.reason
    approval.decided_by = current_user.email
    approval.decided_at = datetime.utcnow()
    
    # Update operation status if all approvals are resolved
    operation = approval.workflow_operation
    if decision.approve:
        # Check if all required approvals are now approved
        pending_approvals = [
            req for req in operation.approval_requests
            if req.status == ApprovalStatus.PENDING
        ]
        
        if not pending_approvals:
            operation.status = OperationStatus.APPROVED
            operation.approved_at = datetime.utcnow()
    else:
        # Rejection means operation is rejected
        operation.status = OperationStatus.REJECTED
    
    await db.commit()
    
    await audit_log(
        db, current_user.email, "workflow.approval.decide",
        {
            "approval_id": str(approval_id),
            "operation_id": str(operation.id),
            "decision": "approved" if decision.approve else "rejected",
            "reason": decision.reason
        }
    )
    
    return {"message": f"Approval request {approval.decision}"}


@router.post("/operations/{operation_id}/execute")
async def execute_operation(
    operation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually execute an approved operation."""
    
    query = select(WorkflowOperation).options(
        selectinload(WorkflowOperation.service_collection),
        selectinload(WorkflowOperation.approval_requests)
    ).where(WorkflowOperation.id == operation_id)
    
    result = await db.execute(query)
    operation = result.scalar_one_or_none()
    
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow operation not found"
        )
    
    # Check permissions
    user_role = operation.service_collection.get_user_role(current_user.email)
    if user_role not in ["manager", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to execute operations"
        )
    
    # Check if operation can be executed
    if not operation.can_execute():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Operation cannot be executed. Status: {operation.status.value}"
        )
    
    # Queue for execution
    await execute_workflow_operation.defer(str(operation_id))
    
    await audit_log(
        db, current_user.email, "workflow.operation.execute",
        {"operation_id": str(operation_id)}
    )
    
    return {"message": "Operation queued for execution"}


@router.get("/operations/{operation_id}/logs")
async def get_operation_logs(
    operation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get execution logs for an operation."""
    
    query = select(WorkflowOperation).options(
        selectinload(WorkflowOperation.service_collection)
    ).where(WorkflowOperation.id == operation_id)
    
    result = await db.execute(query)
    operation = result.scalar_one_or_none()
    
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow operation not found"
        )
    
    # Check access
    if not operation.service_collection.can_user_access(current_user.email, "viewer"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation not found or access denied"
        )
    
    return {
        "operation_id": str(operation_id),
        "logs": operation.execution_logs or "",
        "error_message": operation.error_message,
        "started_at": operation.started_at.isoformat() if operation.started_at else None,
        "completed_at": operation.completed_at.isoformat() if operation.completed_at else None,
        "status": operation.status.value
    }


async def _create_approval_requests(
    db: AsyncSession,
    operation: WorkflowOperation,
    collection: ServiceCollection
) -> None:
    """Create approval requests for a workflow operation."""
    
    # Get approvers based on collection configuration and operation type
    approvers = []
    
    # For production environments, require admin approval
    if collection.environment == "production":
        admin_members = [
            member for member in collection.members 
            if member.get("role") == "admin"
        ]
        approvers.extend([member["email"] for member in admin_members])
    else:
        # For non-production, managers and admins can approve
        manager_admin_members = [
            member for member in collection.members
            if member.get("role") in ["manager", "admin"]
        ]
        approvers.extend([member["email"] for member in manager_admin_members])
    
    # If no specific approvers found, use collection creator
    if not approvers:
        approvers = [collection.created_by]
    
    # Create approval requests
    for approver_email in approvers:
        approval = ApprovalRequest(
            workflow_operation_id=operation.id,
            approver_email=approver_email,
            approval_reason=f"Approval required for {operation.operation_type.value} in {collection.environment} environment",
            expires_at=datetime.utcnow() + timedelta(days=7)  # 7 day expiration
        )
        db.add(approval)