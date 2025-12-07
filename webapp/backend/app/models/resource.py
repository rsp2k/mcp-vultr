"""Resource management models."""

from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4
import enum

from sqlalchemy import Column, String, DateTime, Text, Boolean, JSON, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ResourceType(enum.Enum):
    """Types of Vultr resources."""
    INSTANCE = "instance"
    DOMAIN = "domain"
    DNS_RECORD = "dns_record"
    FIREWALL_GROUP = "firewall_group"
    FIREWALL_RULE = "firewall_rule"
    SSH_KEY = "ssh_key"
    SNAPSHOT = "snapshot"
    BLOCK_STORAGE = "block_storage"
    LOAD_BALANCER = "load_balancer"
    VPC = "vpc"
    OBJECT_STORAGE = "object_storage"


class ResourceStatus(enum.Enum):
    """Status of managed resources."""
    PLANNED = "planned"
    CREATING = "creating"
    ACTIVE = "active"
    ERROR = "error"
    DELETING = "deleting"
    DELETED = "deleted"


class PlannedResource(Base):
    """Resources that are planned but not yet created."""
    __tablename__ = "planned_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    service_collection_id = Column(UUID(as_uuid=True), ForeignKey("service_collections.id"), nullable=False)
    
    # Resource definition
    resource_type = Column(Enum(ResourceType), nullable=False)
    resource_name = Column(String(255), nullable=False)
    resource_config = Column(JSON, nullable=False)
    
    # Dependencies
    depends_on = Column(JSON, default=list)  # List of resource names this depends on
    
    # Cost estimation
    estimated_monthly_cost = Column(String(20))
    estimated_setup_cost = Column(String(20))
    
    # Planning metadata
    planned_by = Column(String(255), nullable=False)
    approved_by = Column(String(255))
    approval_required = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_at = Column(DateTime)

    # Relationships
    project = relationship("Project", back_populates="planned_resources")
    service_collection = relationship("ServiceCollection", back_populates="planned_resources_rel")

    # Indexes
    __table_args__ = (
        Index('idx_planned_resources_project_id', 'project_id'),
        Index('idx_planned_resources_collection_id', 'service_collection_id'),
        Index('idx_planned_resources_type', 'resource_type'),
        Index('idx_planned_resources_name', 'resource_name'),
    )


class ManagedResource(Base):
    """Resources that are actively managed by Service Collections."""
    __tablename__ = "managed_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    service_collection_id = Column(UUID(as_uuid=True), ForeignKey("service_collections.id"), nullable=False)

    # Vultr credential used for API access (nullable for backward compatibility)
    vultr_credential_id = Column(UUID(as_uuid=True), ForeignKey("vultr_credentials.id", ondelete="SET NULL"), nullable=True)

    # Resource identification
    vultr_resource_id = Column(String(255), nullable=False, unique=True)
    resource_type = Column(Enum(ResourceType), nullable=False)
    resource_name = Column(String(255), nullable=False)

    # Resource state
    status = Column(Enum(ResourceStatus), nullable=False, default=ResourceStatus.ACTIVE)
    configuration = Column(JSON, default=dict)
    resource_metadata = Column(JSON, default=dict)  # Renamed from 'metadata' to avoid SQLAlchemy conflict

    # Cached Vultr API data (full response from Vultr)
    cached_vultr_data = Column(JSON, default=dict)  # Full API response for richer display

    # Cost tracking
    monthly_cost = Column(String(20))
    last_cost_update = Column(DateTime)

    # Management metadata
    managed_by = Column(String(255), nullable=False)  # Service user or individual
    import_source = Column(String(50))  # How resource was added (created, imported, etc.)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_sync = Column(DateTime)  # Last sync with Vultr API

    # Relationships
    project = relationship("Project", back_populates="managed_resources")
    service_collection = relationship("ServiceCollection", back_populates="managed_resources_rel")
    vultr_credential = relationship("VultrCredential", backref="managed_resources")

    # Indexes
    __table_args__ = (
        Index('idx_managed_resources_project_id', 'project_id'),
        Index('idx_managed_resources_collection_id', 'service_collection_id'),
        Index('idx_managed_resources_credential_id', 'vultr_credential_id'),
        Index('idx_managed_resources_type', 'resource_type'),
        Index('idx_managed_resources_vultr_id', 'vultr_resource_id'),
        Index('idx_managed_resources_status', 'status'),
        Index('idx_managed_resources_name', 'resource_name'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "service_collection_id": str(self.service_collection_id),
            "vultr_credential_id": str(self.vultr_credential_id) if self.vultr_credential_id else None,
            "vultr_resource_id": self.vultr_resource_id,
            "resource_type": self.resource_type.value,
            "resource_name": self.resource_name,
            "status": self.status.value,
            "configuration": self.configuration,
            "metadata": self.resource_metadata,
            "cached_vultr_data": self.cached_vultr_data,
            "monthly_cost": self.monthly_cost,
            "last_cost_update": self.last_cost_update.isoformat() if self.last_cost_update else None,
            "managed_by": self.managed_by,
            "import_source": self.import_source,
            "created_at": self.created_at.isoformat(),
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "can_refresh": self.vultr_credential_id is not None  # Indicates if fresh data can be fetched
        }