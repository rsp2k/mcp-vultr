"""Dashboard API routes for overview and analytics."""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.auth import require_auth
from app.models import (
    ServiceCollection, CollectionEnvironment, CollectionStatus,
    WorkflowOperation, OperationStatus, AuditLogEntry, AuditAction, AuditSeverity,
    User
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=Dict[str, Any])
async def get_dashboard_overview(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard overview data for current user."""
    # Get collections accessible to user
    collection_conditions = []
    if not current_user.is_admin:
        collection_ids = list(current_user.service_collection_memberships.keys())
        if collection_ids:
            collection_conditions.append(
                ServiceCollection.id.in_([collection_ids])
            )
        collection_conditions.append(ServiceCollection.owner_email == current_user.email)
    
    # Count collections by environment
    collections_query = select(ServiceCollection)
    if collection_conditions:
        collections_query = collections_query.where(or_(*collection_conditions))
    
    collections_result = await db.execute(collections_query)
    all_collections = collections_result.scalars().all()
    
    # Group collections by environment and status
    collections_by_env = {}
    collections_by_status = {}
    total_collections = len(all_collections)
    
    for collection in all_collections:
        env = collection.environment.value
        status = collection.status.value
        
        collections_by_env[env] = collections_by_env.get(env, 0) + 1
        collections_by_status[status] = collections_by_status.get(status, 0) + 1
    
    # Get recent workflow operations
    operations_query = select(WorkflowOperation).order_by(
        WorkflowOperation.created_at.desc()
    ).limit(10)
    
    if not current_user.is_admin:
        # Filter operations for user's collections
        if collection_ids:
            operations_query = operations_query.where(
                WorkflowOperation.service_collection_id.in_(collection_ids)
            )
        else:
            # No operations if user has no collections
            operations_query = operations_query.where(False)
    
    operations_result = await db.execute(operations_query)
    recent_operations = operations_result.scalars().all()
    
    # Count operations by status
    operations_by_status = {}
    for operation in recent_operations:
        status = operation.status.value
        operations_by_status[status] = operations_by_status.get(status, 0) + 1
    
    # Get recent audit logs for user's activities
    audit_query = select(AuditLogEntry).where(
        AuditLogEntry.user_id == current_user.id
    ).order_by(AuditLogEntry.timestamp.desc()).limit(10)
    
    audit_result = await db.execute(audit_query)
    recent_activities = audit_result.scalars().all()
    
    # Calculate cost estimates (placeholder for now)
    estimated_monthly_cost = sum(
        float(collection.cost_budget_monthly or "0")
        for collection in all_collections
        if collection.cost_budget_monthly
    )
    
    return {
        "summary": {
            "total_collections": total_collections,
            "collections_by_environment": collections_by_env,
            "collections_by_status": collections_by_status,
            "operations_by_status": operations_by_status,
            "estimated_monthly_cost": estimated_monthly_cost
        },
        "recent_operations": [
            {
                "id": str(op.id),
                "operation_type": op.operation_type.value,
                "status": op.status.value,
                "resource_type": op.resource_type,
                "created_at": op.created_at.isoformat(),
                "collection_id": str(op.service_collection_id)
            }
            for op in recent_operations
        ],
        "recent_activities": [
            {
                "id": str(activity.id),
                "action": activity.action.value,
                "message": activity.message,
                "timestamp": activity.timestamp.isoformat(),
                "severity": activity.severity.value
            }
            for activity in recent_activities
        ]
    }


@router.get("/collections-summary")
async def get_collections_summary(
    environment: Optional[CollectionEnvironment] = Query(None),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get summary of Service Collections."""
    # Build query conditions
    conditions = []
    
    if not current_user.is_admin:
        collection_ids = list(current_user.service_collection_memberships.keys())
        if collection_ids:
            conditions.append(
                or_(
                    ServiceCollection.owner_email == current_user.email,
                    ServiceCollection.id.in_(collection_ids)
                )
            )
        else:
            conditions.append(ServiceCollection.owner_email == current_user.email)
    
    if environment:
        conditions.append(ServiceCollection.environment == environment)
    
    # Get collections
    query = select(ServiceCollection)
    if conditions:
        query = query.where(and_(*conditions))
    
    result = await db.execute(query)
    collections = result.scalars().all()
    
    # Calculate summary statistics
    summary = {
        "total": len(collections),
        "by_environment": {},
        "by_status": {},
        "total_estimated_cost": 0.0,
        "collections": []
    }
    
    for collection in collections:
        # Count by environment
        env = collection.environment.value
        summary["by_environment"][env] = summary["by_environment"].get(env, 0) + 1
        
        # Count by status
        status = collection.status.value
        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
        
        # Add to cost estimate
        if collection.cost_budget_monthly:
            try:
                summary["total_estimated_cost"] += float(collection.cost_budget_monthly)
            except ValueError:
                pass
        
        # Add collection summary
        user_role = current_user.get_collection_role(str(collection.id))
        summary["collections"].append({
            "id": str(collection.id),
            "name": collection.name,
            "environment": collection.environment.value,
            "status": collection.status.value,
            "is_owner": collection.owner_email == current_user.email,
            "user_role": user_role,
            "created_at": collection.created_at.isoformat(),
            "estimated_cost": collection.cost_budget_monthly
        })
    
    return summary


@router.get("/activity-feed")
async def get_activity_feed(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get activity feed for user's collections."""
    since_date = datetime.utcnow() - timedelta(days=days)
    
    # Get user's collection IDs
    collection_ids = list(current_user.service_collection_memberships.keys())
    
    # Build audit log query
    conditions = [AuditLogEntry.timestamp >= since_date]
    
    if not current_user.is_admin:
        # Show activities for user's collections or user's own activities
        user_conditions = [AuditLogEntry.user_id == current_user.id]
        
        if collection_ids:
            user_conditions.append(
                AuditLogEntry.service_collection_id.in_(collection_ids)
            )
        
        conditions.append(or_(*user_conditions))
    
    query = select(AuditLogEntry).where(and_(*conditions)).order_by(
        AuditLogEntry.timestamp.desc()
    ).limit(limit)
    
    result = await db.execute(query)
    activities = result.scalars().all()
    
    return {
        "activities": [
            {
                "id": str(activity.id),
                "action": activity.action.value,
                "message": activity.message,
                "severity": activity.severity.value,
                "timestamp": activity.timestamp.isoformat(),
                "user_id": str(activity.user_id) if activity.user_id else None,
                "collection_id": str(activity.service_collection_id) if activity.service_collection_id else None,
                "resource_type": activity.resource_type,
                "category": activity.category
            }
            for activity in activities
        ],
        "total": len(activities),
        "days": days
    }


@router.get("/system-health")
async def get_system_health(
    admin_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get system health metrics (admin only)."""
    if not admin_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Count total entities
    users_result = await db.execute(select(func.count(User.id)))
    total_users = users_result.scalar()
    
    collections_result = await db.execute(select(func.count(ServiceCollection.id)))
    total_collections = collections_result.scalar()
    
    operations_result = await db.execute(select(func.count(WorkflowOperation.id)))
    total_operations = operations_result.scalar()
    
    # Count recent errors (last 24 hours)
    since_yesterday = datetime.utcnow() - timedelta(hours=24)
    errors_result = await db.execute(
        select(func.count(AuditLogEntry.id)).where(
            and_(
                AuditLogEntry.timestamp >= since_yesterday,
                AuditLogEntry.severity.in_([AuditSeverity.ERROR, AuditSeverity.CRITICAL])
            )
        )
    )
    recent_errors = errors_result.scalar()
    
    # Get pending operations
    pending_ops_result = await db.execute(
        select(func.count(WorkflowOperation.id)).where(
            WorkflowOperation.status.in_([
                OperationStatus.QUEUED,
                OperationStatus.PENDING_APPROVAL,
                OperationStatus.EXECUTING
            ])
        )
    )
    pending_operations = pending_ops_result.scalar()
    
    return {
        "system_metrics": {
            "total_users": total_users,
            "total_collections": total_collections,
            "total_operations": total_operations,
            "recent_errors_24h": recent_errors,
            "pending_operations": pending_operations
        },
        "health_status": "healthy" if recent_errors < 10 else "warning",
        "timestamp": datetime.utcnow().isoformat()
    }