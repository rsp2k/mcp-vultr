"""Service Collections API routes."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.api.auth import require_auth
from app.models import (
    ServiceCollection, CollectionEnvironment, CollectionStatus,
    User, AuditLogEntry, AuditAction
)

router = APIRouter(prefix="/collections", tags=["service-collections"])


class ServiceCollectionCreate(BaseModel):
    """Service Collection creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    environment: CollectionEnvironment = CollectionEnvironment.DEVELOPMENT
    vultr_service_user: Optional[str] = Field(None, max_length=255)
    allowed_regions: List[str] = Field(default_factory=list)
    cost_budget_monthly: Optional[str] = Field(None, max_length=20)
    approval_required: bool = True
    auto_approve_operations: List[str] = Field(default_factory=list)
    restricted_operations: List[str] = Field(default_factory=list)
    tags: Dict[str, str] = Field(default_factory=dict)


class ServiceCollectionUpdate(BaseModel):
    """Service Collection update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    vultr_service_user: Optional[str] = Field(None, max_length=255)
    allowed_regions: Optional[List[str]] = None
    cost_budget_monthly: Optional[str] = Field(None, max_length=20)
    approval_required: Optional[bool] = None
    auto_approve_operations: Optional[List[str]] = None
    restricted_operations: Optional[List[str]] = None
    tags: Optional[Dict[str, str]] = None


class MembershipRequest(BaseModel):
    """Service Collection membership request."""
    user_email: str = Field(..., max_length=255)
    role: str = Field(..., pattern="^(owner|manager|editor|viewer|approver)$")


@router.post("", response_model=Dict[str, Any])
async def create_service_collection(
    collection_data: ServiceCollectionCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Create a new Service Collection."""
    # Check for duplicate name for this user in this environment
    result = await db.execute(
        select(ServiceCollection).where(
            and_(
                ServiceCollection.name == collection_data.name,
                ServiceCollection.environment == collection_data.environment,
                ServiceCollection.owner_email == current_user.email
            )
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Collection '{collection_data.name}' already exists in {collection_data.environment.value} environment"
        )
    
    # Create new Service Collection
    new_collection = ServiceCollection(
        name=collection_data.name,
        description=collection_data.description,
        environment=collection_data.environment,
        created_by=current_user.email,
        owner_email=current_user.email,
        vultr_service_user=collection_data.vultr_service_user,
        allowed_regions=collection_data.allowed_regions,
        cost_budget_monthly=collection_data.cost_budget_monthly,
        approval_required=collection_data.approval_required,
        auto_approve_operations=collection_data.auto_approve_operations,
        restricted_operations=collection_data.restricted_operations,
        tags=collection_data.tags,
        status=CollectionStatus.DRAFT
    )
    
    db.add(new_collection)
    await db.flush()  # Get the collection ID
    
    # Add creator as owner in membership
    current_user.add_collection_membership(str(new_collection.id), "owner")
    
    # Create audit log
    audit_entry = AuditLogEntry.log_collection_action(
        collection_id=str(new_collection.id),
        action=AuditAction.COLLECTION_CREATED,
        message=f"Service Collection '{new_collection.name}' created in {new_collection.environment.value}",
        user_id=str(current_user.id),
        after_data=new_collection.to_dict()
    )
    db.add(audit_entry)
    await db.commit()
    
    return new_collection.to_dict()


@router.get("", response_model=Dict[str, Any])
async def list_service_collections(
    environment: Optional[CollectionEnvironment] = Query(None),
    status: Optional[CollectionStatus] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """List Service Collections accessible to current user."""
    # Build query conditions
    conditions = []
    
    # Users can see collections where they are members or owner
    if not current_user.is_admin:
        # Get collection IDs where user is a member
        collection_ids = list(current_user.service_collection_memberships.keys())
        if collection_ids:
            conditions.append(
                or_(
                    ServiceCollection.owner_email == current_user.email,
                    ServiceCollection.id.in_([UUID(cid) for cid in collection_ids])
                )
            )
        else:
            conditions.append(ServiceCollection.owner_email == current_user.email)
    
    # Add filters
    if environment:
        conditions.append(ServiceCollection.environment == environment)
    if status:
        conditions.append(ServiceCollection.status == status)
    
    # Build and execute query
    query = select(ServiceCollection)
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(ServiceCollection.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    collections = result.scalars().all()
    
    # Get total count
    count_query = select(ServiceCollection)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())
    
    return {
        "collections": [collection.to_dict() for collection in collections],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{collection_id}", response_model=Dict[str, Any])
async def get_service_collection(
    collection_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get Service Collection by ID."""
    result = await db.execute(
        select(ServiceCollection).where(ServiceCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service Collection not found"
        )
    
    # Check access permissions
    if not collection.can_user_access(current_user.email, "read") and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this collection"
        )
    
    return collection.to_dict()


@router.put("/{collection_id}", response_model=Dict[str, Any])
async def update_service_collection(
    collection_id: UUID,
    update_data: ServiceCollectionUpdate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Update Service Collection."""
    result = await db.execute(
        select(ServiceCollection).where(ServiceCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service Collection not found"
        )
    
    # Check access permissions
    if not collection.can_user_access(current_user.email, "update") and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this collection"
        )
    
    before_data = collection.to_dict()
    
    # Update collection fields
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        if hasattr(collection, field):
            setattr(collection, field, value)
    
    collection.updated_at = datetime.utcnow()
    
    # Create audit log
    audit_entry = AuditLogEntry.log_collection_action(
        collection_id=str(collection.id),
        action=AuditAction.COLLECTION_UPDATED,
        message=f"Service Collection '{collection.name}' updated",
        user_id=str(current_user.id),
        before_data=before_data,
        after_data=collection.to_dict()
    )
    db.add(audit_entry)
    await db.commit()
    
    return collection.to_dict()


@router.delete("/{collection_id}")
async def delete_service_collection(
    collection_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Delete Service Collection."""
    result = await db.execute(
        select(ServiceCollection).where(ServiceCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service Collection not found"
        )
    
    # Check if user is owner or admin
    if collection.owner_email != current_user.email and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the collection owner or admin can delete this collection"
        )
    
    before_data = collection.to_dict()
    
    # Create audit log before deletion
    audit_entry = AuditLogEntry.log_collection_action(
        collection_id=str(collection.id),
        action=AuditAction.COLLECTION_DELETED,
        message=f"Service Collection '{collection.name}' deleted",
        user_id=str(current_user.id),
        before_data=before_data
    )
    db.add(audit_entry)
    
    # Delete collection (cascade will handle related records)
    await db.delete(collection)
    await db.commit()
    
    return {"message": "Service Collection deleted successfully"}


@router.post("/{collection_id}/members")
async def add_collection_member(
    collection_id: UUID,
    membership_data: MembershipRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Add member to Service Collection."""
    result = await db.execute(
        select(ServiceCollection).where(ServiceCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service Collection not found"
        )
    
    # Check if user can manage members
    if not collection.can_user_access(current_user.email, "manage") and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage members of this collection"
        )
    
    # Find the user to add
    user_result = await db.execute(
        select(User).where(User.email == membership_data.user_email)
    )
    target_user = user_result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Add membership
    target_user.add_collection_membership(str(collection.id), membership_data.role)
    
    # Create audit log
    audit_entry = AuditLogEntry.log_collection_action(
        collection_id=str(collection.id),
        action=AuditAction.COLLECTION_MEMBER_ADDED,
        message=f"User {membership_data.user_email} added to collection '{collection.name}' with role {membership_data.role}",
        user_id=str(current_user.id),
        metadata={
            "added_user_id": str(target_user.id),
            "added_user_email": membership_data.user_email,
            "role": membership_data.role
        }
    )
    db.add(audit_entry)
    await db.commit()
    
    return {"message": f"User {membership_data.user_email} added successfully"}


@router.delete("/{collection_id}/members/{user_email}")
async def remove_collection_member(
    collection_id: UUID,
    user_email: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Remove member from Service Collection."""
    result = await db.execute(
        select(ServiceCollection).where(ServiceCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service Collection not found"
        )
    
    # Check if user can manage members
    if not collection.can_user_access(current_user.email, "manage") and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage members of this collection"
        )
    
    # Prevent removing the owner
    if user_email == collection.owner_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the collection owner"
        )
    
    # Find the user to remove
    user_result = await db.execute(
        select(User).where(User.email == user_email)
    )
    target_user = user_result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Remove membership
    old_role = target_user.get_collection_role(str(collection.id))
    target_user.remove_collection_membership(str(collection.id))
    
    # Create audit log
    audit_entry = AuditLogEntry.log_collection_action(
        collection_id=str(collection.id),
        action=AuditAction.COLLECTION_MEMBER_REMOVED,
        message=f"User {user_email} removed from collection '{collection.name}'",
        user_id=str(current_user.id),
        metadata={
            "removed_user_id": str(target_user.id),
            "removed_user_email": user_email,
            "previous_role": old_role
        }
    )
    db.add(audit_entry)
    await db.commit()
    
    return {"message": f"User {user_email} removed successfully"}


class RoleUpdateRequest(BaseModel):
    """Role update request."""
    new_role: str = Field(..., pattern="^(manager|editor|viewer|approver)$")


@router.put("/{collection_id}/members/{user_email}/role")
async def update_member_role(
    collection_id: UUID,
    user_email: str,
    role_data: RoleUpdateRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Update member role in Service Collection."""
    result = await db.execute(
        select(ServiceCollection).where(ServiceCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service Collection not found"
        )
    
    # Check if user can manage members
    if not collection.can_user_access(current_user.email, "manage") and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage members of this collection"
        )
    
    # Prevent changing the owner role
    if user_email == collection.owner_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change the role of the collection owner"
        )
    
    # Find the user
    user_result = await db.execute(
        select(User).where(User.email == user_email)
    )
    target_user = user_result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    old_role = target_user.get_collection_role(str(collection.id))
    if not old_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of this collection"
        )
    
    # Update role
    target_user.add_collection_membership(str(collection.id), role_data.new_role)
    
    # Create audit log
    audit_entry = AuditLogEntry.log_collection_action(
        collection_id=str(collection.id),
        action=AuditAction.COLLECTION_MEMBER_ROLE_CHANGED,
        message=f"User {user_email} role changed from {old_role} to {role_data.new_role} in collection '{collection.name}'",
        user_id=str(current_user.id),
        metadata={
            "target_user_id": str(target_user.id),
            "target_user_email": user_email,
            "old_role": old_role,
            "new_role": role_data.new_role
        }
    )
    db.add(audit_entry)
    await db.commit()
    
    return {"message": f"Role updated to {role_data.new_role} successfully"}


@router.get("/{collection_id}/members")
async def list_collection_members(
    collection_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """List members of Service Collection."""
    result = await db.execute(
        select(ServiceCollection).where(ServiceCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service Collection not found"
        )
    
    # Check access permissions
    if not collection.can_user_access(current_user.email, "read") and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this collection's members"
        )
    
    # Get all users who are members
    all_users_result = await db.execute(select(User))
    all_users = all_users_result.scalars().all()
    
    members = []
    for user in all_users:
        role = user.get_collection_role(str(collection.id))
        if role:
            members.append({
                "user_id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": role,
                "is_owner": user.email == collection.owner_email
            })
    
    return {
        "members": members,
        "total": len(members)
    }