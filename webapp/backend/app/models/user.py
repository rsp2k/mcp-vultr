"""User management and authentication models."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4
import enum

from sqlalchemy import (
    Column, String, DateTime, Boolean, JSON, 
    ForeignKey, UniqueConstraint, Index, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import bcrypt

from app.core.database import Base
from app.models.project import project_members


class UserRole(enum.Enum):
    """User roles in the system."""
    ADMIN = "admin"
    MANAGER = "manager"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    SERVICE_ACCOUNT = "service_account"


class UserStatus(enum.Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class User(Base):
    """
    User model for authentication and authorization.
    
    Supports both OAuth users and service accounts with role-based
    access control and Service Collection membership tracking.
    """
    __tablename__ = "users"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(100), nullable=True, unique=True)
    
    # Authentication
    password_hash = Column(String(255), nullable=True)  # Null for OAuth-only users
    oauth_provider = Column(String(50), nullable=True)  # keycloak, google, etc.
    oauth_subject = Column(String(255), nullable=True)  # OAuth subject ID
    
    # Profile information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    display_name = Column(String(200), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Account settings
    role = Column(Enum(UserRole), nullable=False, default=UserRole.VIEWER)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.PENDING_VERIFICATION)
    is_service_account = Column(Boolean, default=False)
    
    # API access
    api_key_hash = Column(String(255), nullable=True)
    api_key_created_at = Column(DateTime, nullable=True)
    api_key_last_used = Column(DateTime, nullable=True)
    
    # Preferences and settings
    preferences = Column(JSON, default=dict)
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    
    # Security and audit
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv6 max length
    failed_login_attempts = Column(JSON, default=list)
    
    # Permissions and access
    global_permissions = Column(JSON, default=list)  # System-wide permissions
    service_collection_memberships = Column(JSON, default=dict)  # Collection ID -> role mapping
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    suspended_at = Column(DateTime, nullable=True)
    
    # Relationships
    audit_logs = relationship(
        "AuditLogEntry",
        back_populates="user",
        foreign_keys="AuditLogEntry.user_id"
    )
    
    # Workflow relationships
    requested_operations = relationship(
        "WorkflowOperation",
        foreign_keys="WorkflowOperation.requested_by_id",
        back_populates="requested_by"
    )

    assigned_operations = relationship(
        "WorkflowOperation",
        foreign_keys="WorkflowOperation.assigned_to_id",
        back_populates="assigned_to"
    )
    
    # Authentication relationships
    connected_accounts = relationship(
        "ConnectedAccount",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    passkeys = relationship(
        "PassKey",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    authentication_sessions = relationship(
        "AuthenticationSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # Project relationships
    owned_projects = relationship(
        "Project",
        foreign_keys="Project.owner_id",
        back_populates="owner"
    )

    projects = relationship(
        "Project",
        secondary=project_members,
        back_populates="members",
        primaryjoin="User.id == project_members.c.user_id",
        secondaryjoin="Project.id == project_members.c.project_id"
    )

    # Note: WorkflowApproval and WorkflowTemplate relationships
    # commented out until these models are implemented
    # approvals_given = relationship(
    #     "WorkflowApproval",
    #     back_populates="approved_by"
    # )
    #
    # workflow_templates = relationship(
    #     "WorkflowTemplate",
    #     back_populates="created_by"
    # )
    
    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint('oauth_provider', 'oauth_subject', name='unique_oauth_identity'),
        Index('idx_users_email', 'email'),
        Index('idx_users_oauth', 'oauth_provider', 'oauth_subject'),
        Index('idx_users_role', 'role'),
        Index('idx_users_status', 'status'),
        Index('idx_users_last_login', 'last_login_at'),
    )
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN
    
    def set_password(self, password: str) -> None:
        """Hash and set user password."""
        if password:
            salt = bcrypt.gensalt()
            self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Verify user password."""
        if not self.password_hash or not password:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def generate_api_key(self) -> str:
        """Generate and set new API key."""
        import secrets
        api_key = f"vsc_{secrets.token_urlsafe(32)}"
        
        # Hash the API key for storage
        salt = bcrypt.gensalt()
        self.api_key_hash = bcrypt.hashpw(api_key.encode('utf-8'), salt).decode('utf-8')
        self.api_key_created_at = datetime.utcnow()
        
        return api_key
    
    def verify_api_key(self, api_key: str) -> bool:
        """Verify API key."""
        if not self.api_key_hash or not api_key:
            return False
        
        is_valid = bcrypt.checkpw(api_key.encode('utf-8'), self.api_key_hash.encode('utf-8'))
        if is_valid:
            self.api_key_last_used = datetime.utcnow()
        
        return is_valid
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific global permission."""
        return permission in self.global_permissions
    
    def get_collection_role(self, collection_id: str) -> Optional[str]:
        """Get user's role in a specific Service Collection."""
        return self.service_collection_memberships.get(str(collection_id))
    
    def add_collection_membership(self, collection_id: str, role: str) -> None:
        """Add user to a Service Collection with specified role."""
        if not self.service_collection_memberships:
            self.service_collection_memberships = {}
        self.service_collection_memberships[str(collection_id)] = role
    
    def remove_collection_membership(self, collection_id: str) -> None:
        """Remove user from a Service Collection."""
        if self.service_collection_memberships:
            self.service_collection_memberships.pop(str(collection_id), None)
    
    def can_access_collection(self, collection_id: str, operation: str = "read") -> bool:
        """Check if user can perform operation on a Service Collection."""
        # Admins can access everything
        if self.is_admin:
            return True
        
        # Check collection-specific role
        role = self.get_collection_role(collection_id)
        if not role:
            return False
        
        # Role-based permissions (same as ServiceCollection model)
        role_permissions = {
            "owner": ["read", "write", "create", "update", "delete", "approve", "manage"],
            "manager": ["read", "write", "create", "update", "approve"],
            "editor": ["read", "write", "create", "update"],
            "viewer": ["read"],
            "approver": ["read", "approve"]
        }
        
        allowed_operations = role_permissions.get(role, [])
        return operation in allowed_operations
    
    def record_login(self, ip_address: str) -> None:
        """Record successful login."""
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = ip_address
        self.failed_login_attempts = []  # Clear failed attempts on success
    
    def record_failed_login(self, ip_address: str) -> None:
        """Record failed login attempt."""
        if not self.failed_login_attempts:
            self.failed_login_attempts = []
        
        self.failed_login_attempts.append({
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": ip_address
        })
        
        # Keep only last 10 failed attempts
        if len(self.failed_login_attempts) > 10:
            self.failed_login_attempts = self.failed_login_attempts[-10:]
    
    @property
    def recent_failed_logins(self) -> int:
        """Count recent failed login attempts (last hour)."""
        if not self.failed_login_attempts:
            return 0
        
        one_hour_ago = datetime.utcnow().timestamp() - 3600
        recent_attempts = 0
        
        for attempt in self.failed_login_attempts:
            attempt_time = datetime.fromisoformat(attempt["timestamp"]).timestamp()
            if attempt_time > one_hour_ago:
                recent_attempts += 1
        
        return recent_attempts
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "role": self.role.value,
            "status": self.status.value,
            "is_service_account": self.is_service_account,
            "oauth_provider": self.oauth_provider,
            "preferences": self.preferences,
            "timezone": self.timezone,
            "language": self.language,
            "global_permissions": self.global_permissions,
            "service_collection_memberships": self.service_collection_memberships,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "is_active": self.is_active,
            "is_admin": self.is_admin
        }
        
        if include_sensitive:
            result.update({
                "last_login_ip": self.last_login_ip,
                "api_key_created_at": self.api_key_created_at.isoformat() if self.api_key_created_at else None,
                "api_key_last_used": self.api_key_last_used.isoformat() if self.api_key_last_used else None,
                "recent_failed_logins": self.recent_failed_logins,
                "suspended_at": self.suspended_at.isoformat() if self.suspended_at else None
            })
        
        return result