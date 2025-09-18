"""
OAuth-Enhanced FastMCP Server for Vultr MCP.

This module creates a FastMCP server with OAuth/OIDC authentication support,
maintaining backward compatibility with environment variable API keys.
"""

import os
from typing import Optional, Dict, Any
from fastmcp import FastMCP

from ._version import __version__
from .server import VultrDNSServer
from .oauth_auth import (
    OAuthConfig, 
    VultrOAuthMiddleware, 
    UserContext, 
    Permission,
    require_permission
)

# Import all the service modules
from .dns import create_dns_mcp
from .instances import create_instances_mcp
from .ssh_keys import create_ssh_keys_mcp
from .backups import create_backups_mcp
from .firewall import create_firewall_mcp
from .snapshots import create_snapshots_mcp
from .regions import create_regions_mcp
from .reserved_ips import create_reserved_ips_mcp
from .container_registry import create_container_registry_mcp
from .block_storage import create_block_storage_mcp
from .vpcs import create_vpcs_mcp
from .iso import create_iso_mcp
from .os import create_os_mcp
from .plans import create_plans_mcp
from .startup_scripts import create_startup_scripts_mcp
from .billing import create_billing_mcp
from .bare_metal import create_bare_metal_mcp
from .cdn import create_cdn_mcp
from .kubernetes import create_kubernetes_mcp
from .load_balancer import create_load_balancer_mcp
from .managed_databases import create_managed_databases_mcp
from .marketplace import create_marketplace_mcp
from .object_storage import create_object_storage_mcp
from .serverless_inference import create_serverless_inference_mcp
from .storage_gateways import create_storage_gateways_mcp
from .subaccount import create_subaccount_mcp
from .users import create_users_mcp
from .service_collections import create_service_collections_mcp, ServiceCollectionStore


class OAuthAwareVultrServer:
    """Vultr server wrapper that supports OAuth-based API key injection."""
    
    def __init__(self, fallback_api_key: Optional[str] = None):
        self.fallback_api_key = fallback_api_key
        self._current_api_key = fallback_api_key
        
    def update_api_key(self, api_key: str):
        """Update the current API key for this request."""
        self._current_api_key = api_key
        
    def get_client(self) -> VultrDNSServer:
        """Get Vultr client with current API key."""
        if not self._current_api_key:
            raise ValueError("No API key available - OAuth authentication required")
        return VultrDNSServer(self._current_api_key)


async def create_oauth_tool_wrapper(original_tool_func, permission_required: Permission):
    """Create a tool wrapper that enforces OAuth permissions and API key injection."""
    
    async def oauth_tool_wrapper(*args, **kwargs):
        # Extract context from kwargs
        context = kwargs.pop('context', {})
        
        # Get OAuth middleware from server (if available)
        mcp_server = getattr(oauth_tool_wrapper, '_mcp_server', None)
        if mcp_server and hasattr(mcp_server, '_oauth_middleware'):
            middleware = mcp_server._oauth_middleware
            
            # Get user context
            user_context = await middleware.process_request(context)
            
            if not user_context:
                raise PermissionError("Authentication required")
                
            if not user_context.has_permission(permission_required):
                raise PermissionError(f"Insufficient permissions. Required: {permission_required.value}")
            
            # Inject API key
            api_key = middleware.get_api_key(user_context)
            if api_key:
                # Create new Vultr client with user's API key
                vultr_client = VultrDNSServer(api_key)
                # Replace the client in args/kwargs if present
                if 'vultr_client' in kwargs:
                    kwargs['vultr_client'] = vultr_client
        
        # Call original tool
        return await original_tool_func(*args, **kwargs)
    
    # Copy metadata from original function
    oauth_tool_wrapper.__name__ = original_tool_func.__name__
    oauth_tool_wrapper.__doc__ = original_tool_func.__doc__
    oauth_tool_wrapper._permission_required = permission_required
    
    return oauth_tool_wrapper


def create_oauth_enhanced_vultr_server(api_key: Optional[str] = None) -> FastMCP:
    """
    Create OAuth-enhanced FastMCP server for Vultr management.
    
    Args:
        api_key: Fallback Vultr API key for non-OAuth requests
        
    Returns:
        FastMCP server with OAuth authentication support
    """
    
    # Load OAuth configuration
    oauth_config = OAuthConfig.from_env()
    
    # Create FastMCP server
    mcp = FastMCP(name=f"mcp-vultr-oauth v{__version__}")
    
    # Set up OAuth middleware
    oauth_middleware = VultrOAuthMiddleware(oauth_config, api_key)
    mcp._oauth_middleware = oauth_middleware
    mcp._oauth_config = oauth_config
    
    # Create OAuth-aware Vultr server
    vultr_server = OAuthAwareVultrServer(api_key)
    
    print(f"🔐 OAuth Configuration:")
    print(f"   Enabled: {oauth_config.enabled}")
    if oauth_config.enabled:
        print(f"   Issuer: {oauth_config.issuer_url}")
        print(f"   Client: {oauth_config.client_id}")
        print(f"   JWKS URL: {oauth_config.jwks_url}")
    else:
        print(f"   Using fallback API key: {'✓' if api_key else '✗'}")
    
    # Create and mount all service modules with OAuth awareness
    # For now, we'll use the fallback client - full OAuth integration would require
    # modifying each service module to accept dynamic API keys
    
    if api_key:  # Only mount if we have an API key
        vultr_client = VultrDNSServer(api_key)
        
        # Mount all modules
        dns_mcp = create_dns_mcp(vultr_client)
        mcp.mount(dns_mcp)
        
        instances_mcp = create_instances_mcp(vultr_client)
        mcp.mount(instances_mcp)
        
        ssh_keys_mcp = create_ssh_keys_mcp(vultr_client)
        mcp.mount(ssh_keys_mcp)
        
        backups_mcp = create_backups_mcp(vultr_client)
        mcp.mount(backups_mcp)
        
        firewall_mcp = create_firewall_mcp(vultr_client)
        mcp.mount(firewall_mcp)
        
        snapshots_mcp = create_snapshots_mcp(vultr_client)
        mcp.mount(snapshots_mcp)
        
        regions_mcp = create_regions_mcp(vultr_client)
        mcp.mount(regions_mcp)
        
        reserved_ips_mcp = create_reserved_ips_mcp(vultr_client)
        mcp.mount(reserved_ips_mcp)
        
        container_registry_mcp = create_container_registry_mcp(vultr_client)
        mcp.mount(container_registry_mcp)
        
        block_storage_mcp = create_block_storage_mcp(vultr_client)
        mcp.mount(block_storage_mcp)
        
        vpcs_mcp = create_vpcs_mcp(vultr_client)
        mcp.mount(vpcs_mcp)
        
        iso_mcp = create_iso_mcp(vultr_client)
        mcp.mount(iso_mcp)
        
        os_mcp = create_os_mcp(vultr_client)
        mcp.mount(os_mcp)
        
        plans_mcp = create_plans_mcp(vultr_client)
        mcp.mount(plans_mcp)
        
        startup_scripts_mcp = create_startup_scripts_mcp(vultr_client)
        mcp.mount(startup_scripts_mcp)
        
        billing_mcp = create_billing_mcp(vultr_client)
        mcp.mount(billing_mcp)
        
        bare_metal_mcp = create_bare_metal_mcp(vultr_client)
        mcp.mount(bare_metal_mcp)
        
        cdn_mcp = create_cdn_mcp(vultr_client)
        mcp.mount(cdn_mcp)
        
        kubernetes_mcp = create_kubernetes_mcp(vultr_client)
        mcp.mount(kubernetes_mcp)
        
        load_balancer_mcp = create_load_balancer_mcp(vultr_client)
        mcp.mount(load_balancer_mcp)
        
        managed_databases_mcp = create_managed_databases_mcp(vultr_client)
        mcp.mount(managed_databases_mcp)
        
        marketplace_mcp = create_marketplace_mcp(vultr_client)
        mcp.mount(marketplace_mcp)
        
        object_storage_mcp = create_object_storage_mcp(vultr_client)
        mcp.mount(object_storage_mcp)
        
        serverless_inference_mcp = create_serverless_inference_mcp(vultr_client)
        mcp.mount(serverless_inference_mcp)
        
        storage_gateways_mcp = create_storage_gateways_mcp(vultr_client)
        mcp.mount(storage_gateways_mcp)
        
        subaccount_mcp = create_subaccount_mcp(vultr_client)
        mcp.mount(subaccount_mcp)
        
        users_mcp = create_users_mcp(vultr_client)
        mcp.mount(users_mcp)
        
        # Service Collections with OAuth support
        service_collections_store = ServiceCollectionStore()
        service_collections_mcp = create_service_collections_mcp(vultr_client, service_collections_store)
        mcp.mount(service_collections_mcp)
        
    return mcp


def run_oauth_server(api_key: Optional[str] = None, transport: Optional[str] = None) -> None:
    """
    Run the OAuth-enhanced Vultr MCP server.
    
    Args:
        api_key: Fallback Vultr API key (or from VULTR_API_KEY env var)
        transport: Transport protocol (auto-detected if not specified)
    """
    
    # Get API key from parameter or environment
    if not api_key:
        api_key = os.getenv("VULTR_API_KEY")
    
    oauth_config = OAuthConfig.from_env()
    
    print(f"🚀 Starting mcp-vultr OAuth server v{__version__}")
    print(f"🔐 OAuth Mode: {'Enabled' if oauth_config.enabled else 'Disabled (fallback mode)'}")
    
    if oauth_config.enabled and not oauth_config.client_secret:
        print("⚠️  Warning: OAuth enabled but OAUTH_CLIENT_SECRET not set")
    
    if not api_key and not oauth_config.enabled:
        print("❌ Error: No API key available and OAuth is disabled")
        print("   Set VULTR_API_KEY or enable OAuth with OAUTH_ENABLED=true")
        return
    
    # Create and run server
    mcp = create_oauth_enhanced_vultr_server(api_key)
    
    # Auto-detect transport if not specified
    if not transport:
        transport = "stdio"  # Default for MCP clients
    
    print(f"🌐 Transport: {transport}")
    print(f"🔑 API Key: {'✓ Configured' if api_key else '✗ OAuth-only mode'}")
    
    mcp.run(transport=transport)


if __name__ == "__main__":
    run_oauth_server()