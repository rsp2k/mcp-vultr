"""Pydantic schemas for resource management."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.models.resource import ResourceType, ResourceStatus


# Planned Resource Schemas
class PlannedResourceCreate(BaseModel):
    """Schema for creating a planned resource."""
    service_collection_id: UUID
    resource_type: ResourceType
    resource_name: str = Field(..., min_length=1, max_length=255)
    resource_config: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list, description="List of resource names this depends on")
    estimated_monthly_cost: Optional[str] = None
    estimated_setup_cost: Optional[str] = None
    approval_required: bool = True

    @field_validator('resource_name')
    @classmethod
    def validate_resource_name(cls, v: str) -> str:
        """Validate resource name format."""
        if not v or not v.strip():
            raise ValueError("Resource name cannot be empty")
        # Allow alphanumeric, hyphens, underscores
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "Resource name must contain only letters, numbers, hyphens, and underscores"
            )
        return v.strip()


class PlannedResourceUpdate(BaseModel):
    """Schema for updating a planned resource."""
    resource_name: Optional[str] = Field(None, min_length=1, max_length=255)
    resource_config: Optional[Dict[str, Any]] = None
    depends_on: Optional[List[str]] = None
    estimated_monthly_cost: Optional[str] = None
    estimated_setup_cost: Optional[str] = None
    approval_required: Optional[bool] = None


class PlannedResourceApprove(BaseModel):
    """Schema for approving a planned resource."""
    approver_notes: Optional[str] = None


class PlannedResourceResponse(BaseModel):
    """Schema for planned resource response."""
    id: UUID
    project_id: UUID
    service_collection_id: UUID
    resource_type: str
    resource_name: str
    resource_config: Dict[str, Any]
    depends_on: List[str]
    estimated_monthly_cost: Optional[str] = None
    estimated_setup_cost: Optional[str] = None
    planned_by: str
    approved_by: Optional[str] = None
    approval_required: bool
    created_at: datetime
    approved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# Managed Resource Schemas
class ManagedResourceCreate(BaseModel):
    """Schema for creating/importing a managed resource."""
    service_collection_id: UUID
    vultr_resource_id: str = Field(..., min_length=1)
    resource_type: ResourceType
    resource_name: str = Field(..., min_length=1, max_length=255)
    configuration: Dict[str, Any] = Field(default_factory=dict)
    resource_metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata")
    monthly_cost: Optional[str] = None
    import_source: str = "manual"  # manual, vultr_import, workflow_created

    @field_validator('import_source')
    @classmethod
    def validate_import_source(cls, v: str) -> str:
        """Validate import source."""
        valid_sources = {"manual", "vultr_import", "workflow_created", "terraform", "api"}
        if v not in valid_sources:
            raise ValueError(f"Import source must be one of: {', '.join(valid_sources)}")
        return v


class ManagedResourceUpdate(BaseModel):
    """Schema for updating a managed resource."""
    resource_name: Optional[str] = Field(None, min_length=1, max_length=255)
    configuration: Optional[Dict[str, Any]] = None
    resource_metadata: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    monthly_cost: Optional[str] = None
    status: Optional[ResourceStatus] = None


class ManagedResourceSync(BaseModel):
    """Schema for syncing a managed resource with Vultr."""
    force_sync: bool = False
    update_cost: bool = True


class ManagedResourceResponse(BaseModel):
    """Schema for managed resource response."""
    id: UUID
    project_id: UUID
    service_collection_id: UUID
    vultr_credential_id: Optional[UUID] = None  # Link to credential for refresh
    vultr_resource_id: str
    resource_type: str
    resource_name: str
    status: str
    configuration: Dict[str, Any]
    metadata: Dict[str, Any]
    cached_vultr_data: Optional[Dict[str, Any]] = None  # Full Vultr API response
    monthly_cost: Optional[str] = None
    last_cost_update: Optional[datetime] = None
    managed_by: str
    import_source: str
    created_at: datetime
    last_sync: Optional[datetime] = None
    can_refresh: bool = False  # True if credential is linked

    model_config = {"from_attributes": True}


# Resource List Response
class ResourceListResponse(BaseModel):
    """Schema for resource list response."""
    items: List[Any]  # Can be PlannedResourceResponse or ManagedResourceResponse
    total: int
    limit: int
    offset: int
    has_more: bool


# Resource Summary
class ResourceSummary(BaseModel):
    """Summary of resources in a collection."""
    total_planned: int
    total_managed: int
    total_estimated_cost: str
    total_actual_cost: str
    resources_by_type: Dict[str, int]
    resources_by_status: Dict[str, int]
