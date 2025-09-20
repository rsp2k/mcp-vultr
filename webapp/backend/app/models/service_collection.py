"""Service Collection database model."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

from sqlalchemy import (
    Column, String, DateTime, Text, Boolean, JSON, 
    ForeignKey, UniqueConstraint, Index, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
import enum

from app.core.database import Base


class CollectionEnvironment(enum.Enum):
    """Environment types for Service Collections."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class CollectionStatus(enum.Enum):
    """Status types for Service Collections."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class ServiceCollection(Base):
    """
    Service Collection model representing a logical grouping of infrastructure resources.
    
    Service Collections can exist before their underlying resources, serving as
    deployment blueprints with approval workflows and access controls.
    """
    __tablename__ = "service_collections"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Environment and status
    environment = Column(Enum(CollectionEnvironment), nullable=False, default=CollectionEnvironment.DEVELOPMENT)
    status = Column(Enum(CollectionStatus), nullable=False, default=CollectionStatus.DRAFT)
    
    # Ownership and permissions
    created_by = Column(String(255), nullable=False)  # User email/username
    owner_email = Column(String(255), nullable=False)
    
    # Resource configuration
    vultr_service_user = Column(String(255))  # Service user for managed deployments
    allowed_regions = Column(JSON, default=list)  # List of allowed Vultr regions
    cost_budget_monthly = Column(String(20))  # Monthly budget limit (as string for precision)
    
    # Access control
    members = Column(JSON, default=list)  # List of member configurations
    permissions = Column(JSON, default=dict)  # Permission configurations
    
    # Resource definitions
    planned_resources = Column(JSON, default=list)  # Resources queued for creation
    managed_resources = Column(JSON, default=list)  # Existing Vultr resources
    
    # Workflow configuration
    approval_required = Column(Boolean, default=True)
    auto_approve_operations = Column(JSON, default=list)  # Operations that auto-approve
    restricted_operations = Column(JSON, default=list)  # Operations requiring special approval
    
    # Metadata
    tags = Column(JSON, default=dict)
    configuration = Column(JSON, default=dict)  # Custom configuration
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    archived_at = Column(DateTime, nullable=True)
    
    # Relationships
    workflow_operations = relationship(
        "WorkflowOperation", 
        back_populates="service_collection",
        cascade="all, delete-orphan"
    )
    
    audit_logs = relationship(
        "AuditLogEntry",
        back_populates="service_collection", 
        cascade="all, delete-orphan"
    )
    
    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint('name', 'environment', 'owner_email', name='unique_collection_per_env_owner'),
        Index('idx_service_collections_owner', 'owner_email'),
        Index('idx_service_collections_environment', 'environment'),
        Index('idx_service_collections_status', 'status'),
        Index('idx_service_collections_created_by', 'created_by'),
    )
    
    @hybrid_property
    def full_name(self) -> str:
        """Full collection name including environment."""
        return f"{self.name}-{self.environment.value}"
    
    @hybrid_property
    def is_active(self) -> bool:
        """Check if collection is in active status."""
        return self.status == CollectionStatus.ACTIVE
    
    @hybrid_property
    def is_production(self) -> bool:
        """Check if collection is production environment."""
        return self.environment == CollectionEnvironment.PRODUCTION
    
    def get_member_role(self, user_email: str) -> Optional[str]:
        """Get the role of a specific member."""
        for member in self.members:
            if member.get("email") == user_email:
                return member.get("role")
        
        # Check if user is the owner
        if user_email == self.owner_email:
            return "owner"
        
        return None
    
    def can_user_access(self, user_email: str, operation: str = "read") -> bool:
        """Check if user can perform operation on this collection."""
        role = self.get_member_role(user_email)
        
        if not role:
            return False
        
        # Owner can do everything
        if role == "owner":
            return True
        
        # Role-based access control
        role_permissions = {
            "editor": ["read", "write", "create", "update"],
            "viewer": ["read"],
            "approver": ["read", "approve"],
            "manager": ["read", "write", "create", "update", "approve"]
        }
        
        allowed_operations = role_permissions.get(role, [])
        return operation in allowed_operations
    
    def requires_approval(self, operation: str) -> bool:
        """Check if operation requires approval for this collection."""
        if not self.approval_required:
            return False
        
        # Auto-approve operations don't need approval
        if operation in self.auto_approve_operations:
            return False
        
        # Production environments require approval by default
        if self.is_production:
            return True
        
        # Restricted operations always require approval
        if operation in self.restricted_operations:
            return True
        
        return False
    
    def estimate_monthly_cost(self) -> float:
        """Estimate monthly cost for all resources in collection."""
        total_cost = 0.0
        
        # Calculate cost for planned resources
        for resource in self.planned_resources:
            # This would integrate with Vultr pricing API
            # For now, return placeholder
            total_cost += 10.0  # Placeholder
        
        # Calculate cost for managed resources
        for resource in self.managed_resources:
            # This would query actual Vultr billing data
            total_cost += 15.0  # Placeholder
        
        return total_cost
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "environment": self.environment.value,
            "status": self.status.value,
            "created_by": self.created_by,
            "owner_email": self.owner_email,
            "vultr_service_user": self.vultr_service_user,
            "allowed_regions": self.allowed_regions,
            "cost_budget_monthly": self.cost_budget_monthly,
            "members": self.members,
            "permissions": self.permissions,
            "planned_resources": self.planned_resources,
            "managed_resources": self.managed_resources,
            "approval_required": self.approval_required,
            "auto_approve_operations": self.auto_approve_operations,
            "restricted_operations": self.restricted_operations,
            "tags": self.tags,
            "configuration": self.configuration,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_production": self.is_production,
            "estimated_monthly_cost": self.estimate_monthly_cost()
        }