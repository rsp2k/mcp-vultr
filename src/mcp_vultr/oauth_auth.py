"""
OAuth/OIDC Authentication Module for MCP Vultr.

This module provides OAuth/OIDC integration with Keycloak for secure API key management
and permission-based access control to Vultr MCP tools.
"""

import os
import json
import jwt
import httpx
import fnmatch
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum
from fastmcp import FastMCP
from contextlib import asynccontextmanager


class Permission(Enum):
    """Vultr permission levels."""
    ADMIN = "vultr-admin"
    MANAGER = "vultr-manager" 
    VIEWER = "vultr-viewer"
    SERVICE_COLLECTION_OWNER = "service-collection-owner"
    SERVICE_COLLECTION_EDITOR = "service-collection-editor"
    WORKFLOW_APPROVER = "workflow-approver"


@dataclass
class OAuthConfig:
    """OAuth/OIDC configuration."""
    enabled: bool = False
    issuer_url: str = ""
    client_id: str = ""
    client_secret: str = ""
    jwks_url: str = ""
    audience: str = ""
    
    @classmethod
    def from_env(cls) -> "OAuthConfig":
        """Load OAuth configuration from environment variables."""
        return cls(
            enabled=os.getenv("OAUTH_ENABLED", "false").lower() == "true",
            issuer_url=os.getenv("OAUTH_ISSUER_URL", "https://auth.l.inspect.systems/realms/mcp-vultr"),
            client_id=os.getenv("OAUTH_CLIENT_ID", "mcp-vultr-server"),
            client_secret=os.getenv("OAUTH_CLIENT_SECRET", ""),
            jwks_url=os.getenv("OAUTH_JWKS_URL", "https://auth.l.inspect.systems/realms/mcp-vultr/protocol/openid-connect/certs"),
            audience=os.getenv("OAUTH_AUDIENCE", "mcp-vultr-server"),
        )


@dataclass
class ServiceCollectionMembership:
    """Service Collection membership details."""
    collection_id: str
    role: str  # owner, editor, viewer
    permissions: List[str] = field(default_factory=list)
    
    def can_perform_operation(self, operation: str) -> bool:
        """Check if membership allows specific operation."""
        if self.role == "owner":
            return True
        elif self.role == "editor":
            return operation in ["read", "write", "create", "update"]
        elif self.role == "viewer":
            return operation == "read"
        return operation in self.permissions


@dataclass
class ServiceCollectionPermissions:
    """Permissions within a Service Collection."""
    collection_id: str
    vultr_resources: Dict[str, Any] = field(default_factory=dict)
    global_restrictions: List[str] = field(default_factory=list)
    
    def can_access_domain(self, domain: str, operation: str) -> bool:
        """Check if can access specific domain with operation."""
        dns_config = self.vultr_resources.get("dns", {})
        
        # Check allowed domains
        allowed_domains = dns_config.get("allowed_domains", [])
        if allowed_domains:
            domain_allowed = any(fnmatch.fnmatch(domain, pattern) for pattern in allowed_domains)
            if not domain_allowed:
                return False
        
        # Check forbidden operations
        forbidden_ops = dns_config.get("forbidden_operations", [])
        if operation in forbidden_ops:
            return False
        
        # Check global restrictions
        if f"no_{operation}" in self.global_restrictions:
            return False
            
        return True
    
    def can_access_instance(self, instance_id: str, operation: str) -> bool:
        """Check if can access specific instance with operation."""
        compute_config = self.vultr_resources.get("compute", {})
        
        # Check patterns and explicit IDs
        allowed_instances = compute_config.get("allowed_instances", [])
        if allowed_instances:
            instance_allowed = any(fnmatch.fnmatch(instance_id, pattern) for pattern in allowed_instances)
            if not instance_allowed:
                return False
        
        # Check operation restrictions
        forbidden_ops = compute_config.get("forbidden_operations", [])
        if operation in forbidden_ops:
            return False
        
        # Check global restrictions
        if f"no_{operation}" in self.global_restrictions:
            return False
            
        return True


@dataclass
class APIKeyBrokerConfig:
    """API Key Broker configuration."""
    broker_id: str
    trusted_collections: List[str] = field(default_factory=list)
    key_expiry_hours: int = 24
    allowed_operations: List[str] = field(default_factory=list)
    audit_required: bool = True


@dataclass
class UserContext:
    """User authentication and authorization context."""
    username: str
    email: str
    vultr_api_key: Optional[str] = None
    permissions: Set[Permission] = None
    authenticated: bool = False
    
    # Service Collection support
    service_collections: List[ServiceCollectionMembership] = field(default_factory=list)
    collection_permissions: Dict[str, ServiceCollectionPermissions] = field(default_factory=dict)
    api_key_broker_config: Optional[APIKeyBrokerConfig] = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = set()
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions or Permission.ADMIN in self.permissions
    
    def get_collection_membership(self, collection_id: str) -> Optional[ServiceCollectionMembership]:
        """Get membership details for a specific Service Collection."""
        for membership in self.service_collections:
            if membership.collection_id == collection_id:
                return membership
        return None
    
    def get_collection_permissions(self, collection_id: str) -> Optional[ServiceCollectionPermissions]:
        """Get resource permissions for a specific Service Collection."""
        return self.collection_permissions.get(collection_id)
    
    def can_access_collection_resource(self, collection_id: str, resource_type: str, resource_id: str, operation: str) -> bool:
        """Check if user can access a resource within a Service Collection."""
        # Check if user is member of the collection
        membership = self.get_collection_membership(collection_id)
        if not membership:
            return False
        
        # Check if membership role allows the operation
        if not membership.can_perform_operation(operation):
            return False
        
        # Check resource-specific permissions
        permissions = self.get_collection_permissions(collection_id)
        if not permissions:
            return True  # No specific restrictions
        
        if resource_type == "domain":
            return permissions.can_access_domain(resource_id, operation)
        elif resource_type == "instance":
            return permissions.can_access_instance(resource_id, operation)
        
        # Default: allow if membership allows
        return True
    
    def can_access_tool(self, tool_name: str, resource_context: Optional[Dict[str, str]] = None) -> bool:
        """Check if user can access a specific tool based on permissions and Service Collections."""
        # Admin override
        if Permission.ADMIN in self.permissions:
            return True
        
        # If resource context provided, check Service Collection permissions
        if resource_context:
            collection_id = resource_context.get("collection_id")
            resource_type = resource_context.get("resource_type")
            resource_id = resource_context.get("resource_id")
            operation = resource_context.get("operation", "read")
            
            if collection_id and resource_type and resource_id:
                return self.can_access_collection_resource(collection_id, resource_type, resource_id, operation)
        
        # Read-only tools - all authenticated users can access
        readonly_tools = {
            "list_domains", "get_domain", "list_records", "get_record",
            "list_instances", "get_instance", "list_plans", "get_plan",
            "list_regions", "get_region", "list_operating_systems",
            "list_ssh_keys", "list_snapshots", "list_backups",
            "get_account_info", "get_current_balance", "list_billing_history"
        }
        
        if tool_name in readonly_tools and Permission.VIEWER in self.permissions:
            return True
        
        # Management tools - require manager or admin
        management_tools = {
            "create_domain", "delete_domain", "create_record", "update_record", "delete_record",
            "create_instance", "update_instance", "delete_instance", "start", "stop", "reboot",
            "create_ssh_key", "update_ssh_key", "delete_ssh_key",
            "create_snapshot", "delete_snapshot"
        }
        
        if tool_name in management_tools and (Permission.MANAGER in self.permissions or Permission.ADMIN in self.permissions):
            return True
        
        # Service collection tools
        service_collection_tools = {
            "list_collections", "get_collection", "create_service_collection",
            "add_resource_to_collection", "remove_resource_from_collection"
        }
        
        if tool_name in service_collection_tools:
            return (Permission.SERVICE_COLLECTION_OWNER in self.permissions or 
                   Permission.SERVICE_COLLECTION_EDITOR in self.permissions or
                   Permission.ADMIN in self.permissions)
        
        # Admin-only tools
        admin_tools = {
            "create_user", "update_user", "delete_user",
            "create_firewall_group", "delete_firewall_group",
            "setup_web_server_rules"
        }
        
        if tool_name in admin_tools and Permission.ADMIN in self.permissions:
            return True
        
        return False


class OAuthAuthenticator:
    """OAuth/OIDC authenticator for Keycloak integration."""
    
    def __init__(self, config: OAuthConfig):
        self.config = config
        self._jwks_cache: Optional[Dict[str, Any]] = None
        
    async def get_jwks(self) -> Dict[str, Any]:
        """Fetch and cache JWKS from Keycloak."""
        if self._jwks_cache is None:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.config.jwks_url)
                response.raise_for_status()
                self._jwks_cache = response.json()
        return self._jwks_cache
    
    async def validate_token(self, token: str) -> Optional[UserContext]:
        """Validate JWT token and extract user context."""
        try:
            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            
            # Get public key from JWKS
            jwks = await self.get_jwks()
            key = None
            for jwk in jwks["keys"]:
                if jwk["kid"] == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
                    break
            
            if not key:
                return None
            
            # Validate token
            # Note: Use account audience since that's what Keycloak includes by default
            # or disable audience verification for more flexible configuration
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience="account",  # Use default Keycloak audience
                issuer=self.config.issuer_url
            )
            
            # Extract user information
            username = payload.get("preferred_username")
            email = payload.get("email")
            vultr_api_key = payload.get("vultr_api_key")
            realm_roles = payload.get("realm_access", {}).get("roles", [])
            
            # Map roles to permissions
            permissions = set()
            for role in realm_roles:
                try:
                    permission = Permission(role)
                    permissions.add(permission)
                except ValueError:
                    # Skip unknown roles
                    continue
            
            # Parse Service Collection claims
            service_collections = []
            collection_permissions = {}
            api_key_broker_config = None
            
            # Parse service_collections claim
            service_collections_claim = payload.get("service_collections")
            if service_collections_claim:
                try:
                    collections_data = json.loads(service_collections_claim)
                    
                    # Parse owned collections
                    for owned in collections_data.get("owned", []):
                        membership = ServiceCollectionMembership(
                            collection_id=owned["collection_id"],
                            role=owned["role"],
                            permissions=owned.get("permissions", [])
                        )
                        service_collections.append(membership)
                    
                    # Parse member_of collections
                    for member in collections_data.get("member_of", []):
                        membership = ServiceCollectionMembership(
                            collection_id=member["collection_id"],
                            role=member["role"],
                            permissions=member.get("permissions", [])
                        )
                        service_collections.append(membership)
                        
                except (json.JSONDecodeError, KeyError):
                    # Skip malformed service collections data
                    pass
            
            # Parse collection_permissions claim
            collection_permissions_claim = payload.get("collection_permissions")
            if collection_permissions_claim:
                try:
                    permissions_data = json.loads(collection_permissions_claim)
                    
                    for collection_id, perms_data in permissions_data.items():
                        permissions_obj = ServiceCollectionPermissions(
                            collection_id=collection_id,
                            vultr_resources=perms_data.get("vultr_resources", {}),
                            global_restrictions=perms_data.get("global_restrictions", [])
                        )
                        collection_permissions[collection_id] = permissions_obj
                        
                except (json.JSONDecodeError, KeyError):
                    # Skip malformed permissions data
                    pass
            
            # Parse api_key_broker_config claim
            broker_config_claim = payload.get("api_key_broker_config")
            if broker_config_claim:
                try:
                    broker_data = json.loads(broker_config_claim)
                    api_key_broker_config = APIKeyBrokerConfig(
                        broker_id=broker_data["broker_id"],
                        trusted_collections=broker_data.get("trusted_collections", []),
                        key_expiry_hours=broker_data.get("key_expiry_hours", 24),
                        allowed_operations=broker_data.get("allowed_operations", []),
                        audit_required=broker_data.get("audit_required", True)
                    )
                except (json.JSONDecodeError, KeyError):
                    # Skip malformed broker config
                    pass
            
            return UserContext(
                username=username,
                email=email,
                vultr_api_key=vultr_api_key,
                permissions=permissions,
                authenticated=True,
                service_collections=service_collections,
                collection_permissions=collection_permissions,
                api_key_broker_config=api_key_broker_config
            )
            
        except jwt.InvalidTokenError:
            return None
        except Exception:
            return None


class VultrOAuthMiddleware:
    """FastMCP middleware for OAuth authentication and API key injection."""
    
    def __init__(self, oauth_config: OAuthConfig, fallback_api_key: Optional[str] = None):
        self.oauth_config = oauth_config
        self.fallback_api_key = fallback_api_key
        self.authenticator = OAuthAuthenticator(oauth_config) if oauth_config.enabled else None
        
    async def process_request(self, context: Dict[str, Any]) -> Optional[UserContext]:
        """Process incoming request and extract authentication context."""
        if not self.oauth_config.enabled:
            # OAuth disabled - use fallback API key
            return UserContext(
                username="anonymous",
                email="",
                vultr_api_key=self.fallback_api_key,
                permissions={Permission.ADMIN},  # Full access when OAuth disabled
                authenticated=bool(self.fallback_api_key)
            )
        
        # Extract Bearer token from Authorization header
        auth_header = context.get("headers", {}).get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        return await self.authenticator.validate_token(token)
    
    def get_api_key(self, user_context: Optional[UserContext]) -> Optional[str]:
        """Extract Vultr API key from user context or fallback."""
        if user_context and user_context.vultr_api_key:
            return user_context.vultr_api_key
        return self.fallback_api_key


def create_oauth_enhanced_server(fallback_api_key: Optional[str] = None) -> FastMCP:
    """Create FastMCP server with OAuth enhancement."""
    oauth_config = OAuthConfig.from_env()
    middleware = VultrOAuthMiddleware(oauth_config, fallback_api_key)
    
    # Create FastMCP server
    mcp = FastMCP(name=f"mcp-vultr-oauth")
    
    # Store middleware in server context for use by tools
    mcp._oauth_middleware = middleware
    mcp._oauth_config = oauth_config
    
    return mcp


async def get_user_context_from_mcp(mcp: FastMCP, context: Dict[str, Any]) -> Optional[UserContext]:
    """Extract user context from MCP server and request context."""
    if hasattr(mcp, '_oauth_middleware'):
        return await mcp._oauth_middleware.process_request(context)
    return None


def require_permission(permission: Permission, resource_context: Optional[Dict[str, str]] = None):
    """Decorator to enforce permission requirements on MCP tools with Service Collection support."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract MCP server and context from kwargs
            mcp = kwargs.get('mcp')
            context = kwargs.get('context', {})
            
            if mcp and hasattr(mcp, '_oauth_middleware'):
                user_context = await get_user_context_from_mcp(mcp, context)
                
                if not user_context:
                    raise PermissionError("Authentication required")
                
                # Check Service Collection permissions if resource context provided
                if resource_context:
                    if not user_context.can_access_tool(func.__name__, resource_context):
                        collection_id = resource_context.get('collection_id', 'unknown')
                        resource_type = resource_context.get('resource_type', 'unknown')
                        resource_id = resource_context.get('resource_id', 'unknown')
                        operation = resource_context.get('operation', 'unknown')
                        raise PermissionError(
                            f"Access denied: Cannot perform '{operation}' on {resource_type} '{resource_id}' "
                            f"in collection '{collection_id}'"
                        )
                
                # Check general permission requirements
                if not user_context.has_permission(permission):
                    raise PermissionError(f"Insufficient permissions. Required: {permission.value}")
                
                # Inject API key into server context
                api_key = mcp._oauth_middleware.get_api_key(user_context)
                if api_key:
                    # Update the Vultr client with user's API key
                    # This would need to be implemented in each tool
                    kwargs['api_key'] = api_key
                    kwargs['user_context'] = user_context  # Pass user context for further validation
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_collection_access(collection_id: str, resource_type: str, operation: str = "read"):
    """Decorator to enforce Service Collection access requirements."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract MCP server and context from kwargs
            mcp = kwargs.get('mcp')
            context = kwargs.get('context', {})
            
            if mcp and hasattr(mcp, '_oauth_middleware'):
                user_context = await get_user_context_from_mcp(mcp, context)
                
                if not user_context:
                    raise PermissionError("Authentication required")
                
                # Extract resource ID from function arguments or kwargs
                resource_id = kwargs.get('resource_id') or kwargs.get('domain') or kwargs.get('instance_id')
                if not resource_id and args:
                    resource_id = args[0] if args else "unknown"
                
                # Check Service Collection access
                if not user_context.can_access_collection_resource(collection_id, resource_type, resource_id, operation):
                    raise PermissionError(
                        f"Access denied: Cannot perform '{operation}' on {resource_type} '{resource_id}' "
                        f"in collection '{collection_id}'"
                    )
                
                # Inject API key and context
                api_key = mcp._oauth_middleware.get_api_key(user_context)
                if api_key:
                    kwargs['api_key'] = api_key
                    kwargs['user_context'] = user_context
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Example usage in tool definitions:
"""
# Basic permission check
@mcp.tool()
@require_permission(Permission.MANAGER)
async def create_domain(domain: str, ip: str, context: dict = None) -> dict:
    # Tool implementation with automatic permission checking
    # and API key injection
    pass

# Service Collection-based access control
@mcp.tool()
@require_collection_access("prod-infrastructure", "domain", "write")
async def create_dns_record(domain: str, record_type: str, name: str, data: str, context: dict = None) -> dict:
    # Tool implementation with Service Collection validation
    # Only users with write access to the prod-infrastructure collection
    # can create DNS records for domains in that collection
    pass
"""