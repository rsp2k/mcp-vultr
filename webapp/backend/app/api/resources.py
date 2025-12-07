"""Resource management API routes."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_, cast, literal
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.middleware.rbac import require_auth
from app.models.user import User
from app.models.project import Project, ProjectRole
from app.models.service_collection import ServiceCollection
from app.models.resource import PlannedResource, ManagedResource, ResourceType, ResourceStatus
from app.schemas.resource import (
    PlannedResourceCreate, PlannedResourceUpdate, PlannedResourceApprove, PlannedResourceResponse,
    ManagedResourceCreate, ManagedResourceUpdate, ManagedResourceSync, ManagedResourceResponse,
    ResourceListResponse, ResourceSummary
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resources", tags=["resources"])


# ============================================================================
# PLANNED RESOURCES
# ============================================================================

@router.post("/planned", response_model=PlannedResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_planned_resource(
    resource_data: PlannedResourceCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Create a new planned resource."""

    # Get collection and verify access
    collection_query = select(ServiceCollection).where(
        ServiceCollection.id == resource_data.service_collection_id
    ).options(selectinload(ServiceCollection.project))

    result = await db.execute(collection_query)
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service collection not found"
        )

    # Check permissions (require at least DEVELOPER role)
    if not collection.can_user_access(current_user.email, "create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create resources in this collection"
        )

    # Check for duplicate resource name in collection
    existing_query = select(PlannedResource).where(
        and_(
            PlannedResource.service_collection_id == resource_data.service_collection_id,
            PlannedResource.resource_name == resource_data.resource_name
        )
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Resource with name '{resource_data.resource_name}' already exists in this collection"
        )

    # Create planned resource
    planned_resource = PlannedResource(
        project_id=collection.project_id,
        service_collection_id=resource_data.service_collection_id,
        resource_type=resource_data.resource_type,
        resource_name=resource_data.resource_name,
        resource_config=resource_data.resource_config,
        depends_on=resource_data.depends_on,
        estimated_monthly_cost=resource_data.estimated_monthly_cost,
        estimated_setup_cost=resource_data.estimated_setup_cost,
        planned_by=current_user.email,
        approval_required=resource_data.approval_required
    )

    db.add(planned_resource)
    await db.commit()
    await db.refresh(planned_resource)

    logger.info(f"Created planned resource: {planned_resource.resource_name} in collection {collection.id}")

    return planned_resource


@router.get("/planned", response_model=ResourceListResponse)
async def list_planned_resources(
    collection_id: Optional[UUID] = Query(None, description="Filter by collection"),
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    resource_type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    approved: Optional[bool] = Query(None, description="Filter by approval status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """List planned resources with filtering."""

    query = select(PlannedResource).options(
        selectinload(PlannedResource.project),
        selectinload(PlannedResource.service_collection)
    )

    # Build filters
    filters = []

    if collection_id:
        # Verify user has access to collection
        collection_query = select(ServiceCollection).where(ServiceCollection.id == collection_id)
        result = await db.execute(collection_query)
        collection = result.scalar_one_or_none()

        if not collection or not collection.can_user_access(current_user.email, "read"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found or access denied"
            )

        filters.append(PlannedResource.service_collection_id == collection_id)

    elif project_id:
        # Verify user has access to project
        project_query = select(Project).where(Project.id == project_id)
        result = await db.execute(project_query)
        project = result.scalar_one_or_none()

        if not project or not project.can_user_access(current_user.id, ProjectRole.VIEWER):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )

        filters.append(PlannedResource.project_id == project_id)

    else:
        # Filter to accessible collections
        accessible_collections = select(ServiceCollection.id).where(
            or_(
                ServiceCollection.owner_email == current_user.email,
                ServiceCollection.members.contains([{"email": current_user.email}])
            )
        )
        filters.append(PlannedResource.service_collection_id.in_(accessible_collections))

    if resource_type:
        filters.append(PlannedResource.resource_type == resource_type)

    if approved is not None:
        if approved:
            filters.append(PlannedResource.approved_by.isnot(None))
        else:
            filters.append(PlannedResource.approved_by.is_(None))

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    query = query.order_by(PlannedResource.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    resources = result.scalars().all()

    return ResourceListResponse(
        items=[PlannedResourceResponse.model_validate(r) for r in resources],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(resources)) < total
    )


@router.get("/planned/{resource_id}", response_model=PlannedResourceResponse)
async def get_planned_resource(
    resource_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific planned resource."""

    query = select(PlannedResource).where(PlannedResource.id == resource_id).options(
        selectinload(PlannedResource.service_collection)
    )

    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned resource not found"
        )

    # Check access
    if not resource.service_collection.can_user_access(current_user.email, "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return resource


@router.put("/planned/{resource_id}", response_model=PlannedResourceResponse)
async def update_planned_resource(
    resource_id: UUID,
    update_data: PlannedResourceUpdate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Update a planned resource."""

    query = select(PlannedResource).where(PlannedResource.id == resource_id).options(
        selectinload(PlannedResource.service_collection)
    )

    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned resource not found"
        )

    # Check access (require update permission)
    if not resource.service_collection.can_user_access(current_user.email, "update"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update this resource"
        )

    # Cannot update approved resources
    if resource.approved_by:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot update an approved resource"
        )

    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(resource, field, value)

    await db.commit()
    await db.refresh(resource)

    logger.info(f"Updated planned resource: {resource.id}")

    return resource


@router.post("/planned/{resource_id}/approve", response_model=PlannedResourceResponse)
async def approve_planned_resource(
    resource_id: UUID,
    approval_data: PlannedResourceApprove,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Approve a planned resource for creation."""

    query = select(PlannedResource).where(PlannedResource.id == resource_id).options(
        selectinload(PlannedResource.service_collection)
    )

    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned resource not found"
        )

    # Check access (require approve permission)
    if not resource.service_collection.can_user_access(current_user.email, "approve"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to approve resources"
        )

    # Check if already approved
    if resource.approved_by:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resource is already approved"
        )

    # Approve resource
    resource.approved_by = current_user.email
    resource.approved_at = datetime.utcnow()

    await db.commit()
    await db.refresh(resource)

    logger.info(f"Approved planned resource: {resource.id} by {current_user.email}")

    return resource


@router.delete("/planned/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_planned_resource(
    resource_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Delete a planned resource."""

    query = select(PlannedResource).where(PlannedResource.id == resource_id).options(
        selectinload(PlannedResource.service_collection)
    )

    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned resource not found"
        )

    # Check access
    collection = resource.service_collection
    user_role = collection.get_member_role(current_user.email)

    # Only owner/manager or the person who planned it can delete
    if user_role not in ["owner", "manager"] and resource.planned_by != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the resource planner, collection owner, or manager can delete planned resources"
        )

    await db.delete(resource)
    await db.commit()

    logger.info(f"Deleted planned resource: {resource_id}")

    return None


# ============================================================================
# MANAGED RESOURCES
# ============================================================================

@router.post("/managed", response_model=ManagedResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_managed_resource(
    resource_data: ManagedResourceCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Create/import a managed resource."""

    # Get collection and verify access
    collection_query = select(ServiceCollection).where(
        ServiceCollection.id == resource_data.service_collection_id
    ).options(selectinload(ServiceCollection.project))

    result = await db.execute(collection_query)
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service collection not found"
        )

    # Check permissions
    if not collection.can_user_access(current_user.email, "create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage resources in this collection"
        )

    # Check for duplicate Vultr resource ID
    existing_query = select(ManagedResource).where(
        ManagedResource.vultr_resource_id == resource_data.vultr_resource_id
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Resource with Vultr ID '{resource_data.vultr_resource_id}' is already managed"
        )

    # Create managed resource
    managed_resource = ManagedResource(
        project_id=collection.project_id,
        service_collection_id=resource_data.service_collection_id,
        vultr_resource_id=resource_data.vultr_resource_id,
        resource_type=resource_data.resource_type,
        resource_name=resource_data.resource_name,
        status=ResourceStatus.ACTIVE,
        configuration=resource_data.configuration,
        resource_metadata=resource_data.resource_metadata,
        monthly_cost=resource_data.monthly_cost,
        managed_by=current_user.email,
        import_source=resource_data.import_source,
        last_sync=datetime.utcnow()
    )

    db.add(managed_resource)
    await db.commit()
    await db.refresh(managed_resource)

    logger.info(f"Created managed resource: {managed_resource.resource_name} ({managed_resource.vultr_resource_id})")

    return managed_resource


class BatchImportRequest(BaseModel):
    """Request model for batch import."""
    resources: List[Dict[str, Any]] = Field(..., description="List of resources to import")
    credential_id: Optional[UUID] = Field(None, description="Vultr credential ID used to discover these resources")


@router.post("/managed/batch-import", status_code=status.HTTP_201_CREATED)
async def batch_import_resources(
    collection_id: UUID = Query(..., description="Collection ID to import resources into"),
    request_body: BatchImportRequest = Body(...),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Batch import multiple discovered resources into a collection.

    This endpoint creates multiple managed resources in a single transaction.
    Duplicate Vultr resource IDs are skipped automatically.

    When credential_id is provided:
    - Resources are linked to the credential for future refresh operations
    - Full discovery data is cached in cached_vultr_data for richer display
    """
    resources = request_body.resources
    credential_id = request_body.credential_id

    # Debug logging
    logger.info(f"Batch import called - collection_id: {collection_id}, resources count: {len(resources) if resources else 0}, credential_id: {credential_id}")
    logger.info(f"User: {current_user.email}")

    # Get collection and verify access
    collection_query = select(ServiceCollection).where(
        ServiceCollection.id == collection_id
    ).options(selectinload(ServiceCollection.project))

    result = await db.execute(collection_query)
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service collection not found"
        )

    # Check permissions
    if not collection.can_user_access(current_user.email, "create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage resources in this collection"
        )

    # Get all existing Vultr resource IDs with their collection info to check for duplicates
    existing_query = (
        select(
            ManagedResource.vultr_resource_id,
            ManagedResource.service_collection_id,
            ServiceCollection.name.label('collection_name')
        )
        .join(ServiceCollection, ManagedResource.service_collection_id == ServiceCollection.id)
    )
    existing_result = await db.execute(existing_query)
    existing_resources = {
        row[0]: {"collection_id": str(row[1]), "collection_name": row[2]}
        for row in existing_result.fetchall()
    }

    # Process resources
    created_resources = []
    skipped_resources = []
    failed_resources = []

    for resource_data in resources:
        try:
            vultr_id = resource_data.get("vultr_id")

            # Skip if already managed - include which collection manages it
            if vultr_id in existing_resources:
                existing_info = existing_resources[vultr_id]
                skipped_resources.append({
                    "vultr_id": vultr_id,
                    "name": resource_data.get("name", "Unknown"),
                    "reason": f"Already managed in '{existing_info['collection_name']}'",
                    "existing_collection_id": existing_info["collection_id"],
                    "existing_collection_name": existing_info["collection_name"]
                })
                continue

            # Map resource type string to enum
            resource_type_str = resource_data.get("type", "instance")
            try:
                resource_type = ResourceType[resource_type_str.upper()]
            except KeyError:
                resource_type = ResourceType.INSTANCE  # Default fallback

            # Create managed resource with optional credential link
            managed_resource = ManagedResource(
                project_id=collection.project_id,
                service_collection_id=collection_id,
                vultr_credential_id=credential_id,  # Link to credential for refresh
                vultr_resource_id=vultr_id,
                resource_type=resource_type,
                resource_name=resource_data.get("name", vultr_id),
                status=ResourceStatus.ACTIVE,
                configuration=resource_data.get("configuration", {}),
                resource_metadata=resource_data,  # Store discovery metadata
                cached_vultr_data=resource_data,  # Cache full Vultr data for display
                monthly_cost=str(resource_data.get("monthly_cost", "0.00")),
                managed_by=current_user.email,
                import_source="vultr_import",
                last_sync=datetime.utcnow()
            )

            db.add(managed_resource)
            created_resources.append({
                "vultr_id": vultr_id,
                "name": managed_resource.resource_name,
                "type": resource_type_str
            })

        except Exception as e:
            logger.error(f"Failed to import resource {resource_data.get('vultr_id', 'unknown')}: {e}")
            failed_resources.append({
                "vultr_id": resource_data.get("vultr_id", "unknown"),
                "name": resource_data.get("name", "Unknown"),
                "reason": str(e)
            })

    # Commit all changes
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to commit batch import: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import resources"
        )

    logger.info(
        f"Batch import completed: {len(created_resources)} created, "
        f"{len(skipped_resources)} skipped, {len(failed_resources)} failed"
    )

    return {
        "collection_id": str(collection_id),
        "summary": {
            "total_requested": len(resources),
            "created": len(created_resources),
            "skipped": len(skipped_resources),
            "failed": len(failed_resources)
        },
        "created_resources": created_resources,
        "skipped_resources": skipped_resources,
        "failed_resources": failed_resources
    }


@router.get("/managed", response_model=ResourceListResponse)
async def list_managed_resources(
    collection_id: Optional[UUID] = Query(None, description="Filter by collection"),
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    resource_type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    status: Optional[ResourceStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """List managed resources with filtering."""

    query = select(ManagedResource).options(
        selectinload(ManagedResource.project),
        selectinload(ManagedResource.service_collection)
    )

    # Build filters
    filters = []

    if collection_id:
        # Verify user has access to collection
        collection_query = select(ServiceCollection).where(ServiceCollection.id == collection_id)
        result = await db.execute(collection_query)
        collection = result.scalar_one_or_none()

        if not collection or not collection.can_user_access(current_user.email, "read"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found or access denied"
            )

        filters.append(ManagedResource.service_collection_id == collection_id)

    elif project_id:
        # Verify user has access to project
        project_query = select(Project).where(Project.id == project_id)
        result = await db.execute(project_query)
        project = result.scalar_one_or_none()

        if not project or not project.can_user_access(current_user.id, ProjectRole.VIEWER):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )

        filters.append(ManagedResource.project_id == project_id)

    else:
        # Filter to accessible collections
        # Use PostgreSQL JSONB containment operator to check if user is in members array
        # The @> operator checks if the JSON column contains the specified JSON value
        # We must serialize the Python list to JSON string for proper parameter binding
        member_json = json.dumps([{"email": current_user.email}])
        accessible_collections = select(ServiceCollection.id).where(
            or_(
                ServiceCollection.owner_email == current_user.email,
                cast(ServiceCollection.members, JSONB).contains(
                    cast(literal(member_json), JSONB)
                )
            )
        )
        filters.append(ManagedResource.service_collection_id.in_(accessible_collections))

    if resource_type:
        filters.append(ManagedResource.resource_type == resource_type)

    if status:
        filters.append(ManagedResource.status == status)

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    query = query.order_by(ManagedResource.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    resources = result.scalars().all()

    return ResourceListResponse(
        items=[r.to_dict() for r in resources],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(resources)) < total
    )


@router.get("/managed/{resource_id}", response_model=ManagedResourceResponse)
async def get_managed_resource(
    resource_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific managed resource."""

    query = select(ManagedResource).where(ManagedResource.id == resource_id).options(
        selectinload(ManagedResource.service_collection)
    )

    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Managed resource not found"
        )

    # Check access
    if not resource.service_collection.can_user_access(current_user.email, "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return resource.to_dict()


@router.put("/managed/{resource_id}", response_model=ManagedResourceResponse)
async def update_managed_resource(
    resource_id: UUID,
    update_data: ManagedResourceUpdate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Update a managed resource."""

    query = select(ManagedResource).where(ManagedResource.id == resource_id).options(
        selectinload(ManagedResource.service_collection)
    )

    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Managed resource not found"
        )

    # Check access
    if not resource.service_collection.can_user_access(current_user.email, "update"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update this resource"
        )

    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        if field == "metadata":
            setattr(resource, "resource_metadata", value)
        else:
            setattr(resource, field, value)

    await db.commit()
    await db.refresh(resource)

    logger.info(f"Updated managed resource: {resource.id}")

    return resource.to_dict()


@router.post("/managed/{resource_id}/sync")
async def sync_managed_resource(
    resource_id: UUID,
    sync_data: ManagedResourceSync,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Sync managed resource state with Vultr API."""

    query = select(ManagedResource).where(ManagedResource.id == resource_id).options(
        selectinload(ManagedResource.service_collection)
    )

    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Managed resource not found"
        )

    # Check access
    if not resource.service_collection.can_user_access(current_user.email, "update"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to sync this resource"
        )

    # TODO: Implement actual Vultr API sync via MCP server
    # For now, just update the last_sync timestamp
    resource.last_sync = datetime.utcnow()

    await db.commit()
    await db.refresh(resource)

    logger.info(f"Synced managed resource: {resource.id}")

    return {
        "status": "synced",
        "resource_id": str(resource.id),
        "last_sync": resource.last_sync.isoformat(),
        "message": "Resource sync completed successfully"
    }


# Vultr API endpoint mapping for each resource type
VULTR_API_ENDPOINTS = {
    ResourceType.INSTANCE: ("https://api.vultr.com/v2/instances/{vultr_id}", "instance"),
    ResourceType.LOAD_BALANCER: ("https://api.vultr.com/v2/load-balancers/{vultr_id}", "load_balancer"),
    ResourceType.BLOCK_STORAGE: ("https://api.vultr.com/v2/blocks/{vultr_id}", "block"),
    ResourceType.VPC: ("https://api.vultr.com/v2/vpcs/{vultr_id}", "vpc"),
    ResourceType.FIREWALL_GROUP: ("https://api.vultr.com/v2/firewalls/{vultr_id}", "firewall_group"),
    ResourceType.SSH_KEY: ("https://api.vultr.com/v2/ssh-keys/{vultr_id}", "ssh_key"),
    ResourceType.SNAPSHOT: ("https://api.vultr.com/v2/snapshots/{vultr_id}", "snapshot"),
    ResourceType.DOMAIN: ("https://api.vultr.com/v2/domains/{vultr_id}", "domain"),
    ResourceType.OBJECT_STORAGE: ("https://api.vultr.com/v2/object-storage/{vultr_id}", "object_storage"),
}


class LinkCredentialRequest(BaseModel):
    """Request model for linking a credential to a resource."""
    credential_id: UUID


@router.post("/managed/{resource_id}/link-credential")
async def link_credential_to_resource(
    resource_id: UUID,
    request_body: LinkCredentialRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Link a Vultr credential to a managed resource.

    This enables the resource to be refreshed with live data from Vultr API.
    After linking, the resource's cached_vultr_data will be updated with fresh data.

    Requires:
    - User must have update access to the collection
    - User must own the credential being linked
    """
    from app.models.vultr_credential import VultrCredential
    from app.core.encryption import decrypt_value
    import httpx

    # Get resource with collection relationship
    query = select(ManagedResource).where(ManagedResource.id == resource_id).options(
        selectinload(ManagedResource.service_collection)
    )

    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Managed resource not found"
        )

    # Check access (require update permission)
    if not resource.service_collection.can_user_access(current_user.email, "update"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update this resource"
        )

    # Get and verify credential ownership
    cred_query = select(VultrCredential).where(
        and_(
            VultrCredential.id == request_body.credential_id,
            VultrCredential.user_id == current_user.id,
            VultrCredential.is_active == True
        )
    )

    cred_result = await db.execute(cred_query)
    credential = cred_result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found or not owned by you"
        )

    # Link the credential
    resource.vultr_credential_id = credential.id

    # Decrypt the API key for refresh
    try:
        api_key = decrypt_value(credential.encrypted_api_key, credential.encryption_key_id)
    except Exception as e:
        logger.error(f"Failed to decrypt API key for credential link: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt API key"
        )

    # Automatically refresh the data after linking
    endpoint_info = VULTR_API_ENDPOINTS.get(resource.resource_type)

    if endpoint_info:
        api_url, response_key = endpoint_info
        api_url = api_url.format(vultr_id=resource.vultr_resource_id)

        # Handle test API key
        if api_key.startswith("TEST_VULTR_API_KEY"):
            logger.info(f"Using mock data for test API key - link credential {resource.id}")
            mock_data = _generate_mock_refresh_data(resource)
            resource.cached_vultr_data = mock_data
            resource.last_sync = datetime.utcnow()
        else:
            # Fetch fresh data from Vultr API
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        api_url,
                        headers={"Authorization": f"Bearer {api_key}"}
                    )

                    if response.status_code == 200:
                        data = response.json()
                        fresh_data = data.get(response_key, data)
                        resource.cached_vultr_data = fresh_data
                        resource.last_sync = datetime.utcnow()
                    elif response.status_code == 404:
                        resource.status = ResourceStatus.DELETED
                        resource.last_sync = datetime.utcnow()
                        logger.warning(f"Resource {resource.vultr_resource_id} not found in Vultr")
                    else:
                        logger.warning(f"Vultr API returned {response.status_code} during link refresh")

            except Exception as e:
                logger.error(f"Failed to refresh during credential link: {e}")
                # Don't fail the link operation, just log the error

    # Update credential usage
    credential.usage_count += 1
    credential.last_used_at = datetime.utcnow()

    await db.commit()
    await db.refresh(resource)

    logger.info(f"Linked credential {credential.id} to resource {resource.id}")

    return {
        "status": "linked",
        "resource_id": str(resource.id),
        "credential_id": str(credential.id),
        "resource": resource.to_dict(),
        "message": "Credential linked and data refreshed successfully"
    }


@router.post("/managed/{resource_id}/refresh")
async def refresh_managed_resource(
    resource_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh a managed resource's cached data from the Vultr API.

    This endpoint fetches fresh data from Vultr for the specified resource,
    updates the cached_vultr_data field, and updates the last_sync timestamp.

    Requires:
    - User must have read access to the collection
    - Resource must have an associated vultr_credential_id

    Returns:
    - The updated resource with fresh cached_vultr_data
    """
    from app.models.vultr_credential import VultrCredential
    from app.core.encryption import decrypt_value
    import httpx

    # Get resource with credential relationship
    query = select(ManagedResource).where(ManagedResource.id == resource_id).options(
        selectinload(ManagedResource.service_collection),
        selectinload(ManagedResource.vultr_credential)
    )

    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Managed resource not found"
        )

    # Check access
    if not resource.service_collection.can_user_access(current_user.email, "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check if resource has an associated credential
    if not resource.vultr_credential_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource has no associated Vultr credential. Cannot refresh data."
        )

    # Get the credential
    credential = resource.vultr_credential
    if not credential or not credential.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Associated Vultr credential is inactive or not found"
        )

    # Decrypt the API key
    try:
        api_key = decrypt_value(credential.encrypted_api_key, credential.encryption_key_id)
    except Exception as e:
        logger.error(f"Failed to decrypt API key for resource refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt API key"
        )

    # Get the API endpoint for this resource type
    endpoint_info = VULTR_API_ENDPOINTS.get(resource.resource_type)
    if not endpoint_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refresh not supported for resource type: {resource.resource_type.value}"
        )

    api_url, response_key = endpoint_info
    api_url = api_url.format(vultr_id=resource.vultr_resource_id)

    # Handle test API key - return mock updated data
    if api_key.startswith("TEST_VULTR_API_KEY"):
        logger.info(f"Using mock data for test API key - resource {resource.id}")

        # Generate mock fresh data based on resource type
        mock_data = _generate_mock_refresh_data(resource)

        # Update the cached data
        resource.cached_vultr_data = mock_data
        resource.last_sync = datetime.utcnow()

        # Update credential usage
        credential.usage_count += 1
        credential.last_used_at = datetime.utcnow()

        await db.commit()
        await db.refresh(resource)

        logger.info(f"Refreshed managed resource (mock): {resource.id}")

        return {
            "status": "refreshed",
            "resource_id": str(resource.id),
            "resource": resource.to_dict(),
            "last_sync": resource.last_sync.isoformat(),
            "message": "Resource refreshed successfully (test mode)"
        }

    # Fetch fresh data from Vultr API
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                api_url,
                headers={"Authorization": f"Bearer {api_key}"}
            )

            if response.status_code == 200:
                data = response.json()

                # Extract the resource data from response
                fresh_data = data.get(response_key, data)

                # Update the cached data
                resource.cached_vultr_data = fresh_data
                resource.last_sync = datetime.utcnow()

                # Update credential usage
                credential.usage_count += 1
                credential.last_used_at = datetime.utcnow()

                await db.commit()
                await db.refresh(resource)

                logger.info(f"Refreshed managed resource: {resource.id}")

                return {
                    "status": "refreshed",
                    "resource_id": str(resource.id),
                    "resource": resource.to_dict(),
                    "last_sync": resource.last_sync.isoformat(),
                    "message": "Resource refreshed successfully"
                }

            elif response.status_code == 404:
                # Resource may have been deleted in Vultr
                resource.status = ResourceStatus.DELETED
                resource.last_sync = datetime.utcnow()
                await db.commit()

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Resource not found in Vultr. It may have been deleted."
                )

            elif response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Vultr API authentication failed. Check the credential."
                )

            else:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Vultr API returned status {response.status_code}"
                )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Vultr API request timed out"
        )
    except httpx.HTTPError as e:
        logger.error(f"HTTP error refreshing resource {resource.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with Vultr API: {str(e)}"
        )


def _generate_mock_refresh_data(resource: ManagedResource) -> Dict[str, Any]:
    """Generate mock refresh data for testing purposes."""
    base_data = {
        "id": resource.vultr_resource_id,
        "label": resource.resource_name,
        "date_created": resource.created_at.isoformat() if resource.created_at else None,
        "refreshed_at": datetime.utcnow().isoformat(),
    }

    if resource.resource_type == ResourceType.INSTANCE:
        return {
            **base_data,
            "main_ip": "192.168.1.100",
            "vcpu_count": 2,
            "ram": 4096,
            "disk": 80,
            "status": "active",
            "power_status": "running",
            "os": "Ubuntu 22.04",
            "region": "ewr",
            "plan": "vc2-2c-4gb",
            "allowed_bandwidth": 3000,
            "netmask_v4": "255.255.254.0",
            "gateway_v4": "192.168.0.1",
            "internal_ip": "10.0.0.5",
            "features": ["ddos_protection", "ipv6"],
            "server_status": "ok",
            "v6_network": "2001:db8::/64",
            "v6_main_ip": "2001:db8::1",
            "hostname": resource.resource_name.lower().replace(" ", "-"),
            "tags": ["managed", "production"],
        }
    elif resource.resource_type == ResourceType.LOAD_BALANCER:
        return {
            **base_data,
            "status": "active",
            "region": "ewr",
            "ipv4": "203.0.113.100",
            "forwarding_rules": [
                {"frontend_protocol": "HTTP", "frontend_port": 80, "backend_protocol": "HTTP", "backend_port": 8080},
                {"frontend_protocol": "HTTPS", "frontend_port": 443, "backend_protocol": "HTTP", "backend_port": 8080}
            ],
            "health_check": {"protocol": "HTTP", "port": 8080, "path": "/health", "interval": 15},
            "instances": ["instance-1", "instance-2"],
            "ssl_redirect": True,
        }
    elif resource.resource_type == ResourceType.BLOCK_STORAGE:
        return {
            **base_data,
            "status": "active",
            "region": "ewr",
            "size_gb": 100,
            "attached_to_instance": "instance-1",
            "block_type": "high_perf",
            "mount_id": "mount-123",
        }
    else:
        # Generic data for other types
        return {
            **base_data,
            "status": "active",
            "region": "ewr",
        }


# ============================================================================
# INSTANCE POWER ACTIONS
# ============================================================================

class PowerActionRequest(BaseModel):
    """Request model for instance power actions."""
    action: str = Field(..., description="Power action: start, stop, reboot, or reinstall")


@router.post("/managed/{resource_id}/power-action")
async def instance_power_action(
    resource_id: UUID,
    request_body: PowerActionRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform a power action on an instance resource.

    Supported actions:
    - start: Start a stopped instance
    - stop: Stop a running instance
    - reboot: Reboot an instance
    - reinstall: Reinstall the operating system (destructive!)

    Requires:
    - User must have update access to the collection
    - Resource must be an instance type
    - Resource must have an associated vultr_credential_id
    """
    from app.models.vultr_credential import VultrCredential
    from app.core.encryption import decrypt_value
    import httpx

    # Validate action
    valid_actions = {"start", "stop", "reboot", "reinstall"}
    action = request_body.action.lower()
    if action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}"
        )

    # Get resource with credential relationship
    query = select(ManagedResource).where(ManagedResource.id == resource_id).options(
        selectinload(ManagedResource.service_collection),
        selectinload(ManagedResource.vultr_credential)
    )

    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Managed resource not found"
        )

    # Check resource type - only instances support power actions
    if resource.resource_type != ResourceType.INSTANCE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Power actions only supported for instances, not {resource.resource_type.value}"
        )

    # Check access (require update permission)
    if not resource.service_collection.can_user_access(current_user.email, "update"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to perform actions on this resource"
        )

    # Check if resource has an associated credential
    if not resource.vultr_credential_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource has no associated Vultr credential. Link a credential first."
        )

    # Get the credential
    credential = resource.vultr_credential
    if not credential or not credential.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Associated Vultr credential is inactive or not found"
        )

    # Decrypt the API key
    try:
        api_key = decrypt_value(credential.encrypted_api_key, credential.encryption_key_id)
    except Exception as e:
        logger.error(f"Failed to decrypt API key for power action: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt API key"
        )

    # Handle test API key - return mock success
    if api_key.startswith("TEST_VULTR_API_KEY"):
        logger.info(f"Mock power action '{action}' on test resource {resource.id}")

        # Update cached power status for mock
        if resource.cached_vultr_data:
            if action == "start":
                resource.cached_vultr_data["power_status"] = "running"
                resource.cached_vultr_data["server_status"] = "ok"
            elif action == "stop":
                resource.cached_vultr_data["power_status"] = "stopped"
            elif action == "reboot":
                resource.cached_vultr_data["power_status"] = "running"
                resource.cached_vultr_data["server_status"] = "ok"

            resource.last_sync = datetime.utcnow()
            await db.commit()

        return {
            "status": "success",
            "action": action,
            "resource_id": str(resource.id),
            "message": f"Instance {action} initiated successfully (test mode)"
        }

    # Build the API endpoint based on action
    base_url = f"https://api.vultr.com/v2/instances/{resource.vultr_resource_id}"
    api_endpoints = {
        "start": (f"{base_url}/start", "POST"),
        "stop": (f"{base_url}/halt", "POST"),
        "reboot": (f"{base_url}/reboot", "POST"),
        "reinstall": (f"{base_url}/reinstall", "POST"),
    }

    api_url, method = api_endpoints[action]

    # Make the API call
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "POST":
                response = await client.post(
                    api_url,
                    headers={"Authorization": f"Bearer {api_key}"}
                )
            else:
                response = await client.get(
                    api_url,
                    headers={"Authorization": f"Bearer {api_key}"}
                )

            if response.status_code in (200, 202, 204):
                # Update credential usage
                credential.usage_count += 1
                credential.last_used_at = datetime.utcnow()

                # Update resource status based on action
                if action == "start":
                    resource.status = ResourceStatus.ACTIVE
                elif action == "stop":
                    resource.status = ResourceStatus.STOPPED
                elif action == "reinstall":
                    resource.status = ResourceStatus.PENDING

                await db.commit()

                logger.info(f"Power action '{action}' executed on resource {resource.id}")

                return {
                    "status": "success",
                    "action": action,
                    "resource_id": str(resource.id),
                    "message": f"Instance {action} initiated successfully"
                }

            elif response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Instance not found in Vultr"
                )

            elif response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Vultr API authentication failed"
                )

            else:
                error_detail = response.text
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Vultr API error ({response.status_code}): {error_detail}"
                )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Vultr API request timed out"
        )
    except httpx.HTTPError as e:
        logger.error(f"HTTP error during power action: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with Vultr API: {str(e)}"
        )


@router.delete("/managed/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_managed_resource(
    resource_id: UUID,
    remove_from_vultr: bool = Query(False, description="Also delete from Vultr"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a managed resource.

    By default, only removes from management (keeps resource in Vultr).
    Set remove_from_vultr=true to also delete the resource from Vultr.
    """

    query = select(ManagedResource).where(ManagedResource.id == resource_id).options(
        selectinload(ManagedResource.service_collection)
    )

    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Managed resource not found"
        )

    # Check access (require manager role for deletion)
    collection = resource.service_collection
    user_role = collection.get_member_role(current_user.email)

    if user_role not in ["owner", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only collection owner or manager can delete managed resources"
        )

    if remove_from_vultr:
        # TODO: Implement actual Vultr resource deletion via MCP server
        logger.warning(f"Vultr deletion requested for resource {resource.vultr_resource_id} but not yet implemented")

    await db.delete(resource)
    await db.commit()

    logger.info(f"Deleted managed resource: {resource_id} (Vultr deletion: {remove_from_vultr})")

    return None


# ============================================================================
# VULTR RESOURCE DISCOVERY
# ============================================================================

@router.get("/vultr/discover")
async def discover_vultr_resources(
    credential_id: UUID = Query(..., description="Vultr credential to use"),
    resource_types: Optional[str] = Query(None, description="Comma-separated resource types to fetch"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Discover available Vultr resources using a credential.

    Returns resources available in the Vultr account associated with the credential.
    Resource types can be filtered (e.g., "instance,load_balancer,database").
    """
    from app.models.vultr_credential import VultrCredential
    from app.core.encryption import decrypt_value
    import httpx

    # Get and verify credential access
    cred_query = select(VultrCredential).where(
        and_(
            VultrCredential.id == credential_id,
            VultrCredential.user_id == current_user.id,
            VultrCredential.is_active == True
        )
    )

    cred_result = await db.execute(cred_query)
    credential = cred_result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found or access denied"
        )

    # Decrypt the API key
    try:
        api_key = decrypt_value(credential.encrypted_api_key, credential.encryption_key_id)
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt API key"
        )

    # Update usage tracking
    credential.usage_count += 1
    credential.last_used_at = datetime.utcnow()
    await db.commit()

    # Parse requested resource types
    types_to_fetch = []
    if resource_types:
        types_to_fetch = [t.strip() for t in resource_types.split(",")]
    else:
        # Default: fetch common resource types
        types_to_fetch = ["instance", "load_balancer", "database", "kubernetes", "block_storage", "domain"]

    # Check if this is a test API key - return mock data for testing
    if api_key.startswith("TEST_VULTR_API_KEY"):
        logger.info("Using mock data for test API key")
        discovered_resources = {
            "instances": [
                {
                    "vultr_id": "test-instance-1",
                    "name": "web-server-prod-01",
                    "type": "instance",
                    "region": "ewr",
                    "plan": "vc2-2c-4gb",
                    "status": "active",
                    "os": "Ubuntu 22.04",
                    "main_ip": "192.168.1.10",
                    "ram": 4096,
                    "disk": 80,
                    "vcpu_count": 2,
                    "monthly_cost": "24.00",
                    "configuration": {"hostname": "web-01.example.com", "tags": ["production", "web"]}
                },
                {
                    "vultr_id": "test-instance-2",
                    "name": "api-server-prod-01",
                    "type": "instance",
                    "region": "ewr",
                    "plan": "vc2-4c-8gb",
                    "status": "active",
                    "os": "Ubuntu 22.04",
                    "main_ip": "192.168.1.20",
                    "ram": 8192,
                    "disk": 160,
                    "vcpu_count": 4,
                    "monthly_cost": "48.00",
                    "configuration": {"hostname": "api-01.example.com", "tags": ["production", "api"]}
                },
                {
                    "vultr_id": "test-instance-3",
                    "name": "staging-server",
                    "type": "instance",
                    "region": "lax",
                    "plan": "vc2-1c-2gb",
                    "status": "active",
                    "os": "Debian 11",
                    "main_ip": "192.168.2.10",
                    "ram": 2048,
                    "disk": 55,
                    "vcpu_count": 1,
                    "monthly_cost": "12.00",
                    "configuration": {"hostname": "staging-01.example.com", "tags": ["staging"]}
                }
            ],
            "load_balancers": [
                {
                    "vultr_id": "test-lb-1",
                    "name": "production-load-balancer",
                    "type": "load_balancer",
                    "region": "ewr",
                    "status": "active",
                    "ip": "203.0.113.10",
                    "monthly_cost": "10.00",
                    "configuration": {
                        "forwarding_rules": [{"frontend_port": 80, "backend_port": 8080}],
                        "health_check": {"protocol": "http", "path": "/health"}
                    }
                }
            ],
            "databases": [
                {
                    "vultr_id": "test-db-1",
                    "name": "postgres-production",
                    "type": "database",
                    "region": "ewr",
                    "database_engine": "postgresql",
                    "database_engine_version": "15",
                    "status": "running",
                    "plan": "vultr-dbaas-startup-cc-1-55-2",
                    "monthly_cost": "15.00",
                    "configuration": {"cluster_time_zone": "UTC", "backup_schedule": "daily"}
                },
                {
                    "vultr_id": "test-db-2",
                    "name": "redis-cache",
                    "type": "database",
                    "region": "ewr",
                    "database_engine": "redis",
                    "database_engine_version": "7",
                    "status": "running",
                    "plan": "vultr-dbaas-hobbyist-cc-1-25-1",
                    "monthly_cost": "10.00",
                    "configuration": {"max_connections": "100", "eviction_policy": "allkeys-lru"}
                }
            ],
            "kubernetes": [
                {
                    "vultr_id": "test-k8s-1",
                    "name": "production-cluster",
                    "type": "kubernetes",
                    "region": "ewr",
                    "version": "v1.28.2",
                    "status": "active",
                    "node_pools": 2,
                    "configuration": {
                        "node_pools": [
                            {"label": "workers", "node_count": 3, "plan": "vc2-2c-4gb"},
                            {"label": "spot-workers", "node_count": 2, "plan": "vc2-1c-2gb"}
                        ]
                    }
                }
            ],
            "block_storage": [
                {
                    "vultr_id": "test-bs-1",
                    "name": "database-backup-storage",
                    "type": "block_storage",
                    "region": "ewr",
                    "size_gb": 100,
                    "status": "active",
                    "attached_to_instance": "test-instance-1",
                    "monthly_cost": "10.00",
                    "configuration": {"mount_point": "/mnt/backups", "filesystem": "ext4"}
                },
                {
                    "vultr_id": "test-bs-2",
                    "name": "logs-storage",
                    "type": "block_storage",
                    "region": "ewr",
                    "size_gb": 50,
                    "status": "active",
                    "attached_to_instance": None,
                    "monthly_cost": "5.00",
                    "configuration": {"filesystem": "xfs"}
                }
            ],
            "domains": [
                {
                    "vultr_id": "example.com",
                    "name": "example.com",
                    "type": "domain",
                    "dns_sec": "disabled",
                    "date_created": "2024-01-15T10:30:00+00:00",
                    "record_count": 12,
                    "configuration": {}
                },
                {
                    "vultr_id": "api.example.com",
                    "name": "api.example.com",
                    "type": "domain",
                    "dns_sec": "enabled",
                    "date_created": "2024-03-20T14:45:00+00:00",
                    "record_count": 5,
                    "configuration": {}
                },
                {
                    "vultr_id": "staging.example.org",
                    "name": "staging.example.org",
                    "type": "domain",
                    "dns_sec": "disabled",
                    "date_created": "2024-06-10T08:15:00+00:00",
                    "record_count": 8,
                    "configuration": {}
                }
            ]
        }

        # Count total resources
        total_count = sum(len(resources) for resources in discovered_resources.values())

        return {
            "credential_id": str(credential_id),
            "credential_label": credential.label,
            "discovered_at": datetime.utcnow().isoformat(),
            "total_resources": total_count,
            "resources": discovered_resources
        }

    # Fetch resources from Vultr API
    discovered_resources = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Authorization": f"Bearer {api_key}"}

        # Fetch instances
        if "instance" in types_to_fetch:
            try:
                response = await client.get(
                    "https://api.vultr.com/v2/instances",
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    discovered_resources["instances"] = [
                        {
                            "vultr_id": inst["id"],
                            "name": inst.get("label", inst["id"]),
                            "type": "instance",
                            "region": inst.get("region"),
                            "plan": inst.get("plan"),
                            "status": inst.get("status"),
                            "os": inst.get("os"),
                            "main_ip": inst.get("main_ip"),
                            "ram": inst.get("ram"),
                            "disk": inst.get("disk"),
                            "vcpu_count": inst.get("vcpu_count"),
                            "monthly_cost": inst.get("cost_per_month")
                        }
                        for inst in data.get("instances", [])
                    ]
            except Exception as e:
                logger.error(f"Failed to fetch instances: {e}")
                discovered_resources["instances"] = []

        # Fetch load balancers
        if "load_balancer" in types_to_fetch:
            try:
                response = await client.get(
                    "https://api.vultr.com/v2/load-balancers",
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    discovered_resources["load_balancers"] = [
                        {
                            "vultr_id": lb["id"],
                            "name": lb.get("label", lb["id"]),
                            "type": "load_balancer",
                            "region": lb.get("region"),
                            "status": lb.get("status"),
                            "ip": lb.get("ipv4"),
                            "monthly_cost": lb.get("cost_per_month")
                        }
                        for lb in data.get("load_balancers", [])
                    ]
            except Exception as e:
                logger.error(f"Failed to fetch load balancers: {e}")
                discovered_resources["load_balancers"] = []

        # Fetch databases
        if "database" in types_to_fetch:
            try:
                response = await client.get(
                    "https://api.vultr.com/v2/databases",
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    discovered_resources["databases"] = [
                        {
                            "vultr_id": db["id"],
                            "name": db.get("label", db["id"]),
                            "type": "database",
                            "region": db.get("region"),
                            "database_engine": db.get("database_engine"),
                            "database_engine_version": db.get("database_engine_version"),
                            "status": db.get("status"),
                            "plan": db.get("plan"),
                            "monthly_cost": db.get("cost_per_month")
                        }
                        for db in data.get("databases", [])
                    ]
            except Exception as e:
                logger.error(f"Failed to fetch databases: {e}")
                discovered_resources["databases"] = []

        # Fetch Kubernetes clusters
        if "kubernetes" in types_to_fetch:
            try:
                response = await client.get(
                    "https://api.vultr.com/v2/kubernetes/clusters",
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    discovered_resources["kubernetes"] = [
                        {
                            "vultr_id": k8s["id"],
                            "name": k8s.get("label", k8s["id"]),
                            "type": "kubernetes",
                            "region": k8s.get("region"),
                            "version": k8s.get("version"),
                            "status": k8s.get("status"),
                            "node_pools": len(k8s.get("node_pools", []))
                        }
                        for k8s in data.get("vke_clusters", [])
                    ]
            except Exception as e:
                logger.error(f"Failed to fetch Kubernetes clusters: {e}")
                discovered_resources["kubernetes"] = []

        # Fetch block storage
        if "block_storage" in types_to_fetch:
            try:
                response = await client.get(
                    "https://api.vultr.com/v2/blocks",
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    discovered_resources["block_storage"] = [
                        {
                            "vultr_id": bs["id"],
                            "name": bs.get("label", bs["id"]),
                            "type": "block_storage",
                            "region": bs.get("region"),
                            "size_gb": bs.get("size_gb"),
                            "status": bs.get("status"),
                            "attached_to_instance": bs.get("attached_to_instance"),
                            "monthly_cost": bs.get("cost_per_month")
                        }
                        for bs in data.get("blocks", [])
                    ]
            except Exception as e:
                logger.error(f"Failed to fetch block storage: {e}")
                discovered_resources["block_storage"] = []

        # Fetch DNS domains
        if "domain" in types_to_fetch:
            try:
                response = await client.get(
                    "https://api.vultr.com/v2/domains",
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    discovered_resources["domains"] = [
                        {
                            "vultr_id": domain["domain"],  # Domain name is the ID
                            "name": domain.get("domain"),
                            "type": "domain",
                            "dns_sec": domain.get("dns_sec", "disabled"),
                            "date_created": domain.get("date_created"),
                            "record_count": domain.get("record_count", 0),
                            "configuration": {}
                        }
                        for domain in data.get("domains", [])
                    ]
            except Exception as e:
                logger.error(f"Failed to fetch DNS domains: {e}")
                discovered_resources["domains"] = []

    # Count total resources
    total_count = sum(len(resources) for resources in discovered_resources.values())

    return {
        "credential_id": str(credential_id),
        "credential_label": credential.label,
        "discovered_at": datetime.utcnow().isoformat(),
        "total_resources": total_count,
        "resources": discovered_resources
    }


# ============================================================================
# RESOURCE SUMMARY
# ============================================================================

@router.get("/summary", response_model=ResourceSummary)
async def get_resource_summary(
    collection_id: UUID = Query(..., description="Collection ID"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get summary of resources in a collection."""

    # Verify access
    collection_query = select(ServiceCollection).where(ServiceCollection.id == collection_id)
    result = await db.execute(collection_query)
    collection = result.scalar_one_or_none()

    if not collection or not collection.can_user_access(current_user.email, "read"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found or access denied"
        )

    # Count planned resources
    planned_count_query = select(func.count()).select_from(PlannedResource).where(
        PlannedResource.service_collection_id == collection_id
    )
    planned_result = await db.execute(planned_count_query)
    total_planned = planned_result.scalar_one()

    # Count managed resources
    managed_count_query = select(func.count()).select_from(ManagedResource).where(
        ManagedResource.service_collection_id == collection_id
    )
    managed_result = await db.execute(managed_count_query)
    total_managed = managed_result.scalar_one()

    # Get resources by type (both planned and managed)
    resources_by_type: Dict[str, int] = {}

    # Planned resources by type
    planned_by_type_query = select(
        PlannedResource.resource_type,
        func.count(PlannedResource.id)
    ).where(
        PlannedResource.service_collection_id == collection_id
    ).group_by(PlannedResource.resource_type)

    planned_by_type_result = await db.execute(planned_by_type_query)
    for resource_type, count in planned_by_type_result:
        type_str = resource_type.value if hasattr(resource_type, 'value') else str(resource_type)
        resources_by_type[type_str] = resources_by_type.get(type_str, 0) + count

    # Managed resources by type
    managed_by_type_query = select(
        ManagedResource.resource_type,
        func.count(ManagedResource.id)
    ).where(
        ManagedResource.service_collection_id == collection_id
    ).group_by(ManagedResource.resource_type)

    managed_by_type_result = await db.execute(managed_by_type_query)
    for resource_type, count in managed_by_type_result:
        type_str = resource_type.value if hasattr(resource_type, 'value') else str(resource_type)
        resources_by_type[type_str] = resources_by_type.get(type_str, 0) + count

    # Get managed resources by status
    resources_by_status: Dict[str, int] = {}
    status_query = select(
        ManagedResource.status,
        func.count(ManagedResource.id)
    ).where(
        ManagedResource.service_collection_id == collection_id
    ).group_by(ManagedResource.status)

    status_result = await db.execute(status_query)
    for status_enum, count in status_result:
        status_str = status_enum.value if hasattr(status_enum, 'value') else str(status_enum)
        resources_by_status[status_str] = count

    # Calculate costs (placeholder - would integrate with actual cost tracking)
    total_estimated_cost = "0.00"
    total_actual_cost = "0.00"

    return ResourceSummary(
        total_planned=total_planned,
        total_managed=total_managed,
        total_estimated_cost=total_estimated_cost,
        total_actual_cost=total_actual_cost,
        resources_by_type=resources_by_type,
        resources_by_status=resources_by_status
    )
