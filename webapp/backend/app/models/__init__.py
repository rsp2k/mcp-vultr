"""Database models for Service Collection webapp."""

from app.models.service_collection import ServiceCollection, CollectionEnvironment, CollectionStatus
from app.models.workflow import WorkflowOperation, ApprovalRequest, OperationStatus, OperationType, ApprovalStatus
from app.models.resource import PlannedResource, ManagedResource, ResourceType, ResourceStatus
from app.models.user import User, UserRole, UserStatus
from app.models.project import Project, ProjectInvitation, AuditLog, ProjectStatus, ProjectRole
from app.models.audit_log import AuditLogEntry, AuditAction, AuditSeverity
from app.models.connected_account import (
    ConnectedAccount, PassKey, AuthenticationSession,
    ProviderType, PassKeyAuthenticatorType
)
from app.models.refresh_token import RefreshToken, REFRESH_TOKEN_EXPIRE_DAYS

__all__ = [
    # Core models
    "ServiceCollection",
    "WorkflowOperation",
    "ApprovalRequest",
    "PlannedResource",
    "ManagedResource",
    "User",
    "AuditLogEntry",

    # Project models
    "Project",
    "ProjectInvitation",
    "AuditLog",

    # Authentication models
    "ConnectedAccount",
    "PassKey",
    "AuthenticationSession",
    "RefreshToken",
    "REFRESH_TOKEN_EXPIRE_DAYS",

    # Enums for Service Collections
    "CollectionEnvironment",
    "CollectionStatus",

    # Enums for Workflows
    "OperationStatus",
    "OperationType",
    "ApprovalStatus",

    # Enums for Resources
    "ResourceType",
    "ResourceStatus",

    # Enums for Users
    "UserRole",
    "UserStatus",

    # Enums for Projects
    "ProjectStatus",
    "ProjectRole",

    # Enums for Authentication
    "ProviderType",
    "PassKeyAuthenticatorType",

    # Enums for Audit Logging
    "AuditAction",
    "AuditSeverity"
]