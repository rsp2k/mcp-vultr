"""Project management and multi-tenancy models."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4
import enum

from sqlalchemy import (
    Column, String, DateTime, Text, Boolean, JSON, Integer,
    ForeignKey, UniqueConstraint, Index, Enum, Table
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.database import Base


class ProjectStatus(enum.Enum):
    """Project status types."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class ProjectRole(enum.Enum):
    """User roles within a project."""
    OWNER = "owner"          # Full control including deletion
    ADMIN = "admin"          # Manage everything except deletion
    MANAGER = "manager"      # Manage resources and workflows
    DEVELOPER = "developer"  # Create/edit resources and workflows
    VIEWER = "viewer"        # Read-only access


# Association table for project team members
project_members = Table(
    'project_members',
    Base.metadata,
    Column('id', UUID(as_uuid=True), primary_key=True, default=uuid4),
    Column('project_id', UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False),
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), nullable=False),
    Column('role', Enum(ProjectRole), nullable=False, default=ProjectRole.VIEWER),
    Column('added_by_user_id', UUID(as_uuid=True), ForeignKey('users.id'), nullable=True),
    Column('added_at', DateTime(timezone=True), nullable=False, default=datetime.utcnow),
    Column('updated_at', DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
    UniqueConstraint('project_id', 'user_id', name='uq_project_user'),
    Index('idx_project_members_project_id', 'project_id'),
    Index('idx_project_members_user_id', 'user_id'),
    Index('idx_project_members_role', 'role')
)


class Project(Base):
    """
    Project model for multi-tenant organization of resources.

    Projects serve as the top-level organizational unit containing:
    - Service Collections
    - Resources
    - Workflows
    - Team members with role-based permissions
    """
    __tablename__ = "projects"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)  # URL-friendly identifier
    description = Column(Text)

    # Status and metadata
    status = Column(Enum(ProjectStatus), nullable=False, default=ProjectStatus.ACTIVE)
    color = Column(String(7), nullable=True)  # Hex color for UI (#RRGGBB)
    avatar_url = Column(String(512), nullable=True)

    # Ownership and timestamps
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Project settings
    settings = Column(JSON, nullable=False, default=dict)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_projects")

    # Many-to-many relationship with users through project_members
    members = relationship(
        "User",
        secondary=project_members,
        back_populates="projects",
        lazy="selectin",
        primaryjoin="Project.id == project_members.c.project_id",
        secondaryjoin="User.id == project_members.c.user_id"
    )

    # One-to-many relationships
    service_collections = relationship("ServiceCollection", back_populates="project", cascade="all, delete-orphan")

    # Resource relationships (PlannedResource and ManagedResource)
    planned_resources = relationship("PlannedResource", back_populates="project", cascade="all, delete-orphan")
    managed_resources = relationship("ManagedResource", back_populates="project", cascade="all, delete-orphan")

    # Workflow relationships
    workflow_operations = relationship("WorkflowOperation", back_populates="project", cascade="all, delete-orphan")

    # Audit logging
    audit_logs = relationship("AuditLog", back_populates="project", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_projects_owner_id', 'owner_id'),
        Index('idx_projects_status', 'status'),
        Index('idx_projects_slug', 'slug'),
    )

    @hybrid_property
    def member_count(self) -> int:
        """Get count of project members."""
        # Avoid lazy loading in hybrid property - return 1 by default (owner)
        # This should be calculated in the API layer with proper session handling
        try:
            if hasattr(self, '_member_count'):
                return self._member_count
            return 1  # At minimum, the owner is a member
        except Exception:
            return 1

    @hybrid_property
    def collection_count(self) -> int:
        """Get count of service collections."""
        # Avoid lazy loading in hybrid property - return 0 by default
        # This should be calculated in the API layer with proper session handling
        try:
            if hasattr(self, '_service_collections_count'):
                return self._service_collections_count
            return 0
        except Exception:
            return 0

    def get_user_role(self, user_id: UUID) -> Optional[ProjectRole]:
        """Get user's role in this project."""
        # Owner always has OWNER role
        if self.owner_id == user_id:
            return ProjectRole.OWNER

        # Check project_members table for role
        # This would typically be done in a service/repository layer
        return None

    def can_user_access(self, user_id: UUID, required_role: ProjectRole = ProjectRole.VIEWER) -> bool:
        """Check if user has required access level to project."""
        user_role = self.get_user_role(user_id)
        if not user_role:
            return False

        # Define role hierarchy (higher number = more permissions)
        role_hierarchy = {
            ProjectRole.VIEWER: 1,
            ProjectRole.DEVELOPER: 2,
            ProjectRole.MANAGER: 3,
            ProjectRole.ADMIN: 4,
            ProjectRole.OWNER: 5
        }

        return role_hierarchy[user_role] >= role_hierarchy[required_role]

    def to_dict(self, include_members: bool = False) -> Dict[str, Any]:
        """Convert project to dictionary representation."""
        data = {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'status': self.status.value,
            'color': self.color,
            'avatar_url': self.avatar_url,
            'owner_id': str(self.owner_id),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'settings': self.settings,
            'member_count': self.member_count,
            'collection_count': self.collection_count
        }

        if include_members:
            data['members'] = [
                {
                    'user_id': str(member.id),
                    'email': member.email,
                    'full_name': member.full_name,
                    'avatar_url': member.avatar_url,
                    'role': self.get_user_role(member.id).value if self.get_user_role(member.id) else None
                }
                for member in (self.members or [])
            ]

        return data


class ProjectInvitation(Base):
    """
    Model for managing project invitations.

    Allows inviting users to projects before they join, with role specification.
    """
    __tablename__ = "project_invitations"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)

    # Invitation details
    email = Column(String(255), nullable=False)
    role = Column(Enum(ProjectRole), nullable=False, default=ProjectRole.VIEWER)
    token = Column(String(255), nullable=False, unique=True)  # Secure invitation token

    # Status and metadata
    accepted = Column(Boolean, nullable=False, default=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    accepted_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Who created the invitation
    invited_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    project = relationship("Project")
    invited_by = relationship("User", foreign_keys=[invited_by_user_id])
    accepted_by = relationship("User", foreign_keys=[accepted_by_user_id])

    # Indexes
    __table_args__ = (
        Index('idx_project_invitations_project_id', 'project_id'),
        Index('idx_project_invitations_email', 'email'),
        Index('idx_project_invitations_token', 'token'),
        Index('idx_project_invitations_expires_at', 'expires_at'),
        UniqueConstraint('project_id', 'email', name='uq_project_invitation_email')
    )

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_pending(self) -> bool:
        """Check if invitation is still pending."""
        return not self.accepted and not self.is_expired

    def to_dict(self) -> Dict[str, Any]:
        """Convert invitation to dictionary representation."""
        return {
            'id': str(self.id),
            'project_id': str(self.project_id),
            'project_name': self.project.name if self.project else None,
            'email': self.email,
            'role': self.role.value,
            'accepted': self.accepted,
            'accepted_at': self.accepted_at.isoformat() if self.accepted_at else None,
            'invited_by': {
                'id': str(self.invited_by.id),
                'email': self.invited_by.email,
                'full_name': self.invited_by.full_name
            } if self.invited_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired,
            'is_pending': self.is_pending
        }


class AuditLog(Base):
    """
    Audit logging for project activities.

    Tracks all significant actions within projects for compliance and security.
    """
    __tablename__ = "project_audit_logs"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)

    # Action details
    action = Column(String(100), nullable=False)  # e.g., "collection.create", "user.invite"
    resource_type = Column(String(50), nullable=False)  # e.g., "collection", "user", "workflow"
    resource_id = Column(String(255), nullable=True)  # ID of affected resource
    resource_name = Column(String(255), nullable=True)  # Name/title of affected resource

    # User and context
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6 address
    user_agent = Column(Text, nullable=True)

    # Change details
    old_values = Column(JSON, nullable=True)  # Previous state
    new_values = Column(JSON, nullable=True)  # New state
    context_data = Column(JSON, nullable=True)    # Additional context

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="audit_logs")
    user = relationship("User")

    # Indexes
    __table_args__ = (
        Index('idx_audit_logs_project_id', 'project_id'),
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_resource_type', 'resource_type'),
        Index('idx_audit_logs_created_at', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary representation."""
        return {
            'id': str(self.id),
            'project_id': str(self.project_id),
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'resource_name': self.resource_name,
            'user': {
                'id': str(self.user.id),
                'email': self.user.email,
                'full_name': self.user.full_name
            } if self.user else None,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'context_data': self.context_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }