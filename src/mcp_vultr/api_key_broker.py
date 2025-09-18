"""
API Key Broker for Vultr MCP Server.

This module implements a secure API key brokering system that addresses
Vultr's security limitations by providing:
- Ephemeral key management with expiration
- Resource-scoped permissions
- Comprehensive audit logging  
- Prevention of privilege escalation
"""

import asyncio
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from enum import Enum
import httpx

from .oauth_auth import (
    UserContext, 
    Permission, 
    ServiceCollectionMembership, 
    ServiceCollectionPermissions,
    APIKeyBrokerConfig
)


class VultrOperation(Enum):
    """Vultr API operations with risk levels."""
    
    # Low Risk - Read Operations
    LIST_DOMAINS = ("list_domains", "low")
    GET_DOMAIN = ("get_domain", "low") 
    LIST_INSTANCES = ("list_instances", "low")
    GET_INSTANCE = ("get_instance", "low")
    LIST_REGIONS = ("list_regions", "low")
    GET_ACCOUNT_INFO = ("get_account", "low")
    
    # Medium Risk - Management Operations
    CREATE_DOMAIN = ("create_domain", "medium")
    CREATE_RECORD = ("create_record", "medium")
    UPDATE_RECORD = ("update_record", "medium")
    DELETE_RECORD = ("delete_record", "medium")
    START_INSTANCE = ("start_instance", "medium")
    STOP_INSTANCE = ("stop_instance", "medium")
    REBOOT_INSTANCE = ("reboot_instance", "medium")
    
    # High Risk - Destructive Operations
    DELETE_DOMAIN = ("delete_domain", "high")
    DELETE_INSTANCE = ("delete_instance", "high")
    REINSTALL_INSTANCE = ("reinstall_instance", "high")
    
    # Critical Risk - Account/Security Operations
    CREATE_API_KEY = ("create_api_key", "critical")
    DELETE_API_KEY = ("delete_api_key", "critical")
    CREATE_USER = ("create_user", "critical")
    DELETE_USER = ("delete_user", "critical")
    
    def __init__(self, operation: str, risk_level: str):
        self.operation = operation
        self.risk_level = risk_level


@dataclass
class ResourceScope:
    """Defines resource-level access scope for an ephemeral key."""
    
    # DNS Resources
    allowed_domains: Optional[Set[str]] = None
    
    # Instance Resources  
    allowed_instances: Optional[Set[str]] = None
    
    # General restrictions
    forbidden_operations: Optional[Set[str]] = None
    
    # Service Collection constraints
    service_collection_id: Optional[str] = None
    collection_permissions: Optional[ServiceCollectionPermissions] = None
    
    def allows_domain(self, domain: str) -> bool:
        """Check if domain access is allowed."""
        # Check Service Collection permissions first
        if self.collection_permissions:
            return self.collection_permissions.can_access_domain(domain, "read")
        
        if self.allowed_domains is None:
            return True  # No restriction
        return domain in self.allowed_domains
    
    def allows_instance(self, instance_id: str) -> bool:
        """Check if instance access is allowed."""
        # Check Service Collection permissions first
        if self.collection_permissions:
            return self.collection_permissions.can_access_instance(instance_id, "read")
        
        if self.allowed_instances is None:
            return True  # No restriction
        return instance_id in self.allowed_instances
    
    def allows_operation(self, operation: str) -> bool:
        """Check if operation is allowed."""
        # Check Service Collection global restrictions
        if self.collection_permissions:
            if f"no_{operation}" in self.collection_permissions.global_restrictions:
                return False
        
        if self.forbidden_operations is None:
            return True  # No restriction
        return operation not in self.forbidden_operations
    
    def allows_domain_operation(self, domain: str, operation: str) -> bool:
        """Check if specific domain operation is allowed."""
        if self.collection_permissions:
            return self.collection_permissions.can_access_domain(domain, operation)
        return self.allows_domain(domain) and self.allows_operation(operation)
    
    def allows_instance_operation(self, instance_id: str, operation: str) -> bool:
        """Check if specific instance operation is allowed."""
        if self.collection_permissions:
            return self.collection_permissions.can_access_instance(instance_id, operation)
        return self.allows_instance(instance_id) and self.allows_operation(operation)


@dataclass 
class EphemeralKey:
    """Represents a temporary, scoped API key."""
    
    key_id: str
    vultr_api_key: str
    user_id: str
    permissions: Set[Permission]
    resource_scope: ResourceScope
    created_at: datetime
    expires_at: datetime
    max_operations: Optional[int] = None
    operation_count: int = 0
    revoked: bool = False
    
    # Service Collection context
    service_collection_id: Optional[str] = None
    collection_membership: Optional[ServiceCollectionMembership] = None
    trusted_by_broker: bool = False  # Whether this key is trusted by the broker system
    
    @property
    def is_expired(self) -> bool:
        """Check if key has expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if key is valid for use."""
        if self.revoked or self.is_expired:
            return False
        if self.max_operations and self.operation_count >= self.max_operations:
            return False
        return True
    
    def use_operation(self) -> None:
        """Increment operation counter."""
        self.operation_count += 1


@dataclass
class AuditLogEntry:
    """Audit log entry for API operations."""
    
    timestamp: datetime
    user_id: str
    ephemeral_key_id: str
    operation: str
    resource_type: str
    resource_id: Optional[str]
    success: bool
    error_message: Optional[str] = None
    request_data: Optional[Dict] = None
    response_data: Optional[Dict] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class APIKeyBroker:
    """
    Secure API key broker for Vultr operations.
    
    This class manages ephemeral API keys with:
    - Time-based expiration
    - Resource-level scoping
    - Operation tracking and limits
    - Comprehensive audit logging
    """
    
    def __init__(self, master_api_key: str, broker_config: Optional[APIKeyBrokerConfig] = None, audit_logger=None):
        self.master_api_key = master_api_key
        self.broker_config = broker_config
        self.ephemeral_keys: Dict[str, EphemeralKey] = {}
        self.audit_logs: List[AuditLogEntry] = []
        self.audit_logger = audit_logger or self._default_audit_logger
        
        # Trusted Service Collections (from broker config)
        self.trusted_collections = set(broker_config.trusted_collections if broker_config else [])
        
    async def create_ephemeral_key(
        self,
        user_context: UserContext,
        permissions: List[Permission],
        resource_scope: Optional[ResourceScope] = None,
        expiry_hours: int = 24,
        max_operations: Optional[int] = None,
        approval_token: Optional[str] = None,
        service_collection_id: Optional[str] = None
    ) -> EphemeralKey:
        """
        Create a new ephemeral API key with limited scope and lifetime.
        
        Args:
            user_context: User requesting the key
            permissions: List of permissions to grant
            resource_scope: Resource-level access restrictions
            expiry_hours: Hours until key expires (1-168, default 24)
            max_operations: Maximum operations before key expires
            approval_token: Required for high-risk operations
            
        Returns:
            EphemeralKey with limited scope and expiration
            
        Raises:
            PermissionError: If user lacks required permissions
            ValueError: If parameters are invalid
        """
        
        # Validate expiry range (1 hour to 7 days)
        if not 1 <= expiry_hours <= 168:
            raise ValueError("Expiry hours must be between 1 and 168 (7 days)")
        
        # Validate user permissions and Service Collection access
        collection_membership = None
        collection_permissions = None
        trusted_by_broker = False
        
        if service_collection_id:
            # Check if user is member of the Service Collection
            collection_membership = user_context.get_collection_membership(service_collection_id)
            if not collection_membership:
                raise PermissionError(f"User is not a member of Service Collection: {service_collection_id}")
            
            # Check if this collection is trusted by the broker
            if service_collection_id in self.trusted_collections:
                trusted_by_broker = True
                collection_permissions = user_context.get_collection_permissions(service_collection_id)
                
                # Update resource scope with Service Collection constraints
                if resource_scope is None:
                    resource_scope = ResourceScope()
                resource_scope.service_collection_id = service_collection_id
                resource_scope.collection_permissions = collection_permissions
            else:
                raise PermissionError(f"Service Collection '{service_collection_id}' is not trusted by this broker")
        
        # Validate user permissions (standard check)
        for permission in permissions:
            if not user_context.has_permission(permission):
                raise PermissionError(f"User lacks permission: {permission.value}")
        
        # Check for high-risk operations requiring approval
        if self._requires_approval(permissions) and not approval_token:
            raise PermissionError("High-risk operations require approval token")
        
        # Create ephemeral Vultr API key using master key
        vultr_api_key = await self._create_vultr_ephemeral_key(
            expiry_hours=expiry_hours
        )
        
        # Generate unique key ID
        key_id = self._generate_key_id(user_context.username)
        
        # Create ephemeral key object
        ephemeral_key = EphemeralKey(
            key_id=key_id,
            vultr_api_key=vultr_api_key,
            user_id=user_context.username,
            permissions=set(permissions),
            resource_scope=resource_scope or ResourceScope(),
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=expiry_hours),
            max_operations=max_operations,
            service_collection_id=service_collection_id,
            collection_membership=collection_membership,
            trusted_by_broker=trusted_by_broker
        )
        
        # Store key
        self.ephemeral_keys[key_id] = ephemeral_key
        
        # Audit log
        await self._audit_log(
            user_context.username,
            key_id,
            "create_ephemeral_key", 
            "api_key",
            key_id,
            success=True,
            request_data={
                "permissions": [p.value for p in permissions],
                "expiry_hours": expiry_hours,
                "max_operations": max_operations
            }
        )
        
        return ephemeral_key
    
    async def validate_service_collection_token(
        self,
        user_context: UserContext,
        operation: VultrOperation,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        service_collection_id: Optional[str] = None
    ) -> bool:
        """
        Validate if a Service Collection token allows a specific operation.
        
        This method provides a way for the broker to validate operations
        based on Service Collection permissions without creating ephemeral keys.
        
        Args:
            user_context: User context with Service Collection claims
            operation: Vultr operation to validate
            resource_id: Specific resource ID (domain, instance, etc.)
            resource_type: Type of resource being accessed
            service_collection_id: Service Collection to validate against
            
        Returns:
            True if operation is allowed by Service Collection permissions
        """
        
        # Check if broker trusts this Service Collection
        if service_collection_id and service_collection_id not in self.trusted_collections:
            return False
        
        # Check if user is member of the Service Collection
        if service_collection_id:
            membership = user_context.get_collection_membership(service_collection_id)
            if not membership:
                return False
            
            # Get collection permissions
            permissions = user_context.get_collection_permissions(service_collection_id)
            if not permissions:
                return True  # No specific restrictions
            
            # Check resource-specific access
            if resource_type == "domain" and resource_id:
                operation_type = self._vultr_operation_to_action(operation)
                return permissions.can_access_domain(resource_id, operation_type)
            
            elif resource_type == "instance" and resource_id:
                operation_type = self._vultr_operation_to_action(operation)
                return permissions.can_access_instance(resource_id, operation_type)
        
        # For operations without specific Service Collection, check general permissions
        required_permission = self._operation_to_permission(operation)
        if required_permission:
            return user_context.has_permission(required_permission)
        
        return True
    
    def _vultr_operation_to_action(self, operation: VultrOperation) -> str:
        """Map Vultr operations to action types for Service Collection validation."""
        create_operations = {VultrOperation.CREATE_DOMAIN, VultrOperation.CREATE_RECORD}
        delete_operations = {VultrOperation.DELETE_DOMAIN, VultrOperation.DELETE_RECORD, VultrOperation.DELETE_INSTANCE}
        write_operations = {VultrOperation.UPDATE_RECORD, VultrOperation.START_INSTANCE, VultrOperation.STOP_INSTANCE, VultrOperation.REBOOT_INSTANCE}
        
        if operation in create_operations:
            return "create"
        elif operation in delete_operations:
            return "delete"
        elif operation in write_operations:
            return "write"
        else:
            return "read"
    
    async def create_service_collection_ephemeral_key(
        self,
        user_context: UserContext,
        service_collection_id: str,
        expiry_hours: int = 1
    ) -> EphemeralKey:
        """
        Create an ephemeral key for a trusted Service Collection.
        
        This is a convenience method that automatically sets up permissions
        and resource scope based on the Service Collection.
        
        Args:
            user_context: User context with Service Collection membership
            service_collection_id: Service Collection to create key for
            expiry_hours: Hours until key expires (default: 1 hour for security)
            
        Returns:
            EphemeralKey configured for the Service Collection
        """
        
        # Get collection membership
        membership = user_context.get_collection_membership(service_collection_id)
        if not membership:
            raise PermissionError(f"User is not a member of Service Collection: {service_collection_id}")
        
        # Map collection role to permissions
        permissions = []
        if membership.role in ["owner", "editor"]:
            permissions = [Permission.MANAGER]
        else:  # viewer
            permissions = [Permission.VIEWER]
        
        # Create key with Service Collection context
        return await self.create_ephemeral_key(
            user_context=user_context,
            permissions=permissions,
            expiry_hours=expiry_hours,
            service_collection_id=service_collection_id
        )
    
    async def validate_operation(
        self,
        key_id: str,
        operation: VultrOperation,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> bool:
        """
        Validate if an operation is allowed with the given ephemeral key.
        
        Args:
            key_id: Ephemeral key ID
            operation: Vultr operation to validate
            resource_id: Specific resource ID (domain, instance, etc.)
            resource_type: Type of resource being accessed
            
        Returns:
            True if operation is allowed, False otherwise
        """
        
        # Get ephemeral key
        ephemeral_key = self.ephemeral_keys.get(key_id)
        if not ephemeral_key or not ephemeral_key.is_valid:
            return False
        
        # Check resource scope
        if resource_type == "domain" and resource_id:
            if not ephemeral_key.resource_scope.allows_domain(resource_id):
                return False
        
        if resource_type == "instance" and resource_id:
            if not ephemeral_key.resource_scope.allows_instance(resource_id):
                return False
        
        # Check operation restrictions
        if not ephemeral_key.resource_scope.allows_operation(operation.operation):
            return False
        
        # Check permission requirements
        required_permission = self._operation_to_permission(operation)
        if required_permission and required_permission not in ephemeral_key.permissions:
            return False
        
        return True
    
    async def execute_operation(
        self,
        key_id: str,
        operation: VultrOperation,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a Vultr API operation through the broker.
        
        Args:
            key_id: Ephemeral key ID
            operation: Operation being performed
            endpoint: Vultr API endpoint
            method: HTTP method
            data: Request data
            resource_id: Resource being accessed
            resource_type: Type of resource
            
        Returns:
            API response data
            
        Raises:
            PermissionError: If operation is not allowed
            ValueError: If key is invalid
        """
        
        # Validate operation
        if not await self.validate_operation(key_id, operation, resource_id, resource_type):
            await self._audit_log(
                self.ephemeral_keys[key_id].user_id if key_id in self.ephemeral_keys else "unknown",
                key_id,
                operation.operation,
                resource_type or "unknown",
                resource_id,
                success=False,
                error_message="Operation not allowed"
            )
            raise PermissionError(f"Operation {operation.operation} not allowed")
        
        ephemeral_key = self.ephemeral_keys[key_id]
        
        try:
            # Execute API call using ephemeral Vultr key
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {ephemeral_key.vultr_api_key}",
                    "Content-Type": "application/json"
                }
                
                response = await client.request(
                    method=method,
                    url=f"https://api.vultr.com/v2{endpoint}",
                    headers=headers,
                    json=data,
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()
            
            # Update operation count
            ephemeral_key.use_operation()
            
            # Audit successful operation
            await self._audit_log(
                ephemeral_key.user_id,
                key_id,
                operation.operation,
                resource_type or "unknown",
                resource_id,
                success=True,
                request_data=data,
                response_data=result
            )
            
            return result
            
        except Exception as e:
            # Audit failed operation
            await self._audit_log(
                ephemeral_key.user_id,
                key_id,
                operation.operation,
                resource_type or "unknown", 
                resource_id,
                success=False,
                error_message=str(e),
                request_data=data
            )
            raise
    
    async def revoke_key(self, key_id: str, reason: str = "Manual revocation") -> bool:
        """
        Immediately revoke an ephemeral key.
        
        Args:
            key_id: Key to revoke
            reason: Reason for revocation
            
        Returns:
            True if key was revoked, False if not found
        """
        
        if key_id not in self.ephemeral_keys:
            return False
        
        ephemeral_key = self.ephemeral_keys[key_id]
        ephemeral_key.revoked = True
        
        # Also revoke the actual Vultr key
        await self._revoke_vultr_key(ephemeral_key.vultr_api_key)
        
        # Audit log
        await self._audit_log(
            ephemeral_key.user_id,
            key_id,
            "revoke_ephemeral_key",
            "api_key", 
            key_id,
            success=True,
            request_data={"reason": reason}
        )
        
        return True
    
    async def cleanup_expired_keys(self) -> int:
        """
        Clean up expired ephemeral keys.
        
        Returns:
            Number of keys cleaned up
        """
        
        expired_keys = [
            key_id for key_id, key in self.ephemeral_keys.items()
            if key.is_expired
        ]
        
        for key_id in expired_keys:
            ephemeral_key = self.ephemeral_keys[key_id]
            await self._revoke_vultr_key(ephemeral_key.vultr_api_key)
            del self.ephemeral_keys[key_id]
        
        return len(expired_keys)
    
    def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        operation: Optional[str] = None
    ) -> List[AuditLogEntry]:
        """
        Get audit logs with optional filtering.
        
        Args:
            user_id: Filter by user ID
            start_time: Filter by start time
            end_time: Filter by end time  
            operation: Filter by operation
            
        Returns:
            Filtered audit log entries
        """
        
        logs = self.audit_logs
        
        if user_id:
            logs = [log for log in logs if log.user_id == user_id]
        
        if start_time:
            logs = [log for log in logs if log.timestamp >= start_time]
        
        if end_time:
            logs = [log for log in logs if log.timestamp <= end_time]
        
        if operation:
            logs = [log for log in logs if log.operation == operation]
        
        return logs
    
    def get_key_status(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for an ephemeral key."""
        
        if key_id not in self.ephemeral_keys:
            return None
        
        key = self.ephemeral_keys[key_id]
        
        return {
            "key_id": key.key_id,
            "user_id": key.user_id,
            "permissions": [p.value for p in key.permissions],
            "created_at": key.created_at.isoformat(),
            "expires_at": key.expires_at.isoformat(),
            "operation_count": key.operation_count,
            "max_operations": key.max_operations,
            "is_expired": key.is_expired,
            "is_valid": key.is_valid,
            "revoked": key.revoked,
            "resource_scope": asdict(key.resource_scope)
        }
    
    # Private methods
    
    def _generate_key_id(self, username: str) -> str:
        """Generate unique key ID."""
        timestamp = datetime.utcnow().isoformat()
        random_suffix = secrets.token_hex(8)
        content = f"{username}-{timestamp}-{random_suffix}"
        return f"eph_{hashlib.sha256(content.encode()).hexdigest()[:16]}"
    
    async def _create_vultr_ephemeral_key(self, expiry_hours: int) -> str:
        """Create ephemeral key in Vultr using master API key."""
        
        # Calculate expiration date
        expiry_date = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.master_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "name": f"ephemeral-{secrets.token_hex(4)}",
                "acls": ["*"],  # Vultr doesn't support granular permissions
                "date_expire": expiry_date.strftime("%Y-%m-%d")
            }
            
            response = await client.post(
                "https://api.vultr.com/v2/api-keys",
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result["api_key"]["api_key"]
    
    async def _revoke_vultr_key(self, vultr_api_key: str) -> None:
        """Revoke a Vultr API key."""
        
        # Note: Vultr doesn't provide an API to revoke keys by key value
        # This would need to be implemented by listing keys and finding the ID
        # For now, we rely on expiration
        pass
    
    def _requires_approval(self, permissions: List[Permission]) -> bool:
        """Check if permissions require approval."""
        
        high_risk_permissions = {
            Permission.ADMIN  # Admin operations require approval
        }
        
        return any(p in high_risk_permissions for p in permissions)
    
    def _operation_to_permission(self, operation: VultrOperation) -> Optional[Permission]:
        """Map operation to required permission."""
        
        operation_permissions = {
            VultrOperation.CREATE_DOMAIN: Permission.MANAGER,
            VultrOperation.DELETE_DOMAIN: Permission.ADMIN,
            VultrOperation.CREATE_USER: Permission.ADMIN,
            VultrOperation.DELETE_USER: Permission.ADMIN,
            # Add more mappings as needed
        }
        
        return operation_permissions.get(operation)
    
    async def _audit_log(
        self,
        user_id: str,
        key_id: str,
        operation: str,
        resource_type: str,
        resource_id: Optional[str],
        success: bool,
        error_message: Optional[str] = None,
        request_data: Optional[Dict] = None,
        response_data: Optional[Dict] = None
    ) -> None:
        """Add entry to audit log."""
        
        entry = AuditLogEntry(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            ephemeral_key_id=key_id,
            operation=operation,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            error_message=error_message,
            request_data=request_data,
            response_data=response_data
        )
        
        self.audit_logs.append(entry)
        
        # Send to external audit system if configured
        if self.audit_logger:
            await self.audit_logger(entry)
    
    async def _default_audit_logger(self, entry: AuditLogEntry) -> None:
        """Default audit logger - prints to stdout."""
        
        print(f"AUDIT: {entry.timestamp} | {entry.user_id} | {entry.operation} | "
              f"{entry.resource_type}:{entry.resource_id} | {'SUCCESS' if entry.success else 'FAILED'}")