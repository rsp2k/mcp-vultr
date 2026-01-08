"""
Vultr DNS FastMCP Server Implementation.

This module contains the FastMCP server implementation for managing DNS records
through the Vultr API using the FastMCP framework.
"""

import os
import sys

from fastmcp import FastMCP

from ._version import __version__
from .backups import create_backups_mcp
from .bare_metal import create_bare_metal_mcp
from .billing import create_billing_mcp
from .block_storage import create_block_storage_mcp
from .cdn import create_cdn_mcp
from .container_registry import create_container_registry_mcp
from .dns import create_dns_mcp
from .firewall import create_firewall_mcp
from .instances import create_instances_mcp
from .iso import create_iso_mcp
from .kubernetes import create_kubernetes_mcp
from .load_balancer import create_load_balancer_mcp
from .managed_databases import create_managed_databases_mcp
from .marketplace import create_marketplace_mcp
from .object_storage import create_object_storage_mcp
from .os import create_os_mcp
from .plans import create_plans_mcp
from .regions import create_regions_mcp
from .reserved_ips import create_reserved_ips_mcp
from .server import VultrDNSServer
from .serverless_inference import create_serverless_inference_mcp
from .snapshots import create_snapshots_mcp
from .ssh_keys import create_ssh_keys_mcp
from .startup_scripts import create_startup_scripts_mcp
from .storage_gateways import create_storage_gateways_mcp
from .subaccount import create_subaccount_mcp
from .service_collections import create_service_collections_mcp, ServiceCollectionStore
from .users import create_users_mcp
from .vpcs import create_vpcs_mcp
from .oauth_auth import create_oauth_enhanced_server, OAuthConfig, VultrOAuthMiddleware


def create_vultr_mcp_server(api_key: str | None = None) -> FastMCP:
    """
    Create a standard Vultr MCP server without OAuth authentication.
    
    Args:
        api_key: Vultr API key. If not provided, will read from VULTR_API_KEY env var.
        
    Returns:
        Configured FastMCP server instance
    """
    return _create_vultr_server_internal(api_key, enable_oauth=False)


def create_oauth_vultr_mcp_server(api_key: str | None = None) -> FastMCP:
    """
    Create an OAuth-enhanced Vultr MCP server with Service Collection support.
    
    Args:
        api_key: Vultr API key. If not provided, will read from VULTR_API_KEY env var.
        
    Returns:
        OAuth-enhanced FastMCP server instance
    """
    return _create_vultr_server_internal(api_key, enable_oauth=True)


def _create_vultr_server_internal(api_key: str | None = None, enable_oauth: bool = False) -> FastMCP:
    """
    Internal server creation function that supports both OAuth and standard modes.
    
    Args:
        api_key: Vultr API key. If not provided, will read from VULTR_API_KEY env var.
        enable_oauth: Whether to enable OAuth authentication and Service Collection validation
        
    Returns:
        Configured FastMCP server instance
    """
    if not api_key:
        api_key = os.getenv("VULTR_API_KEY")

    if not api_key:
        raise ValueError(
            "VULTR_API_KEY must be provided either as parameter or environment variable"
        )

    # Create main FastMCP server with OAuth support if enabled
    if enable_oauth:
        mcp = create_oauth_enhanced_server(api_key)
        mcp.name = f"mcp-vultr-oauth v{__version__}"
    else:
        mcp = FastMCP(name=f"mcp-vultr v{__version__}")

    # Initialize Vultr client
    vultr_client = VultrDNSServer(api_key)

    # Mount all modules with prefixes to avoid tool name collisions
    # Tools become: prefix_toolname (e.g., instance_create, dns_create_record)
    dns_mcp = create_dns_mcp(vultr_client)
    mcp.mount(dns_mcp, prefix="dns")

    instances_mcp = create_instances_mcp(vultr_client)
    mcp.mount(instances_mcp, prefix="instance")

    ssh_keys_mcp = create_ssh_keys_mcp(vultr_client)
    mcp.mount(ssh_keys_mcp, prefix="ssh_key")

    backups_mcp = create_backups_mcp(vultr_client)
    mcp.mount(backups_mcp, prefix="backup")

    firewall_mcp = create_firewall_mcp(vultr_client)
    mcp.mount(firewall_mcp, prefix="firewall")

    snapshots_mcp = create_snapshots_mcp(vultr_client)
    mcp.mount(snapshots_mcp, prefix="snapshot")

    regions_mcp = create_regions_mcp(vultr_client)
    mcp.mount(regions_mcp, prefix="region")

    reserved_ips_mcp = create_reserved_ips_mcp(vultr_client)
    mcp.mount(reserved_ips_mcp, prefix="reserved_ip")

    container_registry_mcp = create_container_registry_mcp(vultr_client)
    mcp.mount(container_registry_mcp, prefix="registry")

    block_storage_mcp = create_block_storage_mcp(vultr_client)
    mcp.mount(block_storage_mcp, prefix="block_storage")

    vpcs_mcp = create_vpcs_mcp(vultr_client)
    mcp.mount(vpcs_mcp, prefix="vpc")

    iso_mcp = create_iso_mcp(vultr_client)
    mcp.mount(iso_mcp, prefix="iso")

    os_mcp = create_os_mcp(vultr_client)
    mcp.mount(os_mcp, prefix="os")

    plans_mcp = create_plans_mcp(vultr_client)
    mcp.mount(plans_mcp, prefix="plan")

    startup_scripts_mcp = create_startup_scripts_mcp(vultr_client)
    mcp.mount(startup_scripts_mcp, prefix="startup_script")

    billing_mcp = create_billing_mcp(vultr_client)
    mcp.mount(billing_mcp, prefix="billing")

    bare_metal_mcp = create_bare_metal_mcp(vultr_client)
    mcp.mount(bare_metal_mcp, prefix="bare_metal")

    cdn_mcp = create_cdn_mcp(vultr_client)
    mcp.mount(cdn_mcp, prefix="cdn")

    kubernetes_mcp = create_kubernetes_mcp(vultr_client)
    mcp.mount(kubernetes_mcp, prefix="k8s")

    load_balancer_mcp = create_load_balancer_mcp(vultr_client)
    mcp.mount(load_balancer_mcp, prefix="lb")

    managed_databases_mcp = create_managed_databases_mcp(vultr_client)
    mcp.mount(managed_databases_mcp, prefix="db")

    marketplace_mcp = create_marketplace_mcp(vultr_client)
    mcp.mount(marketplace_mcp, prefix="marketplace")

    object_storage_mcp = create_object_storage_mcp(vultr_client)
    mcp.mount(object_storage_mcp, prefix="object_storage")

    serverless_inference_mcp = create_serverless_inference_mcp(vultr_client)
    mcp.mount(serverless_inference_mcp, prefix="inference")

    storage_gateways_mcp = create_storage_gateways_mcp(vultr_client)
    mcp.mount(storage_gateways_mcp, prefix="storage_gateway")

    subaccount_mcp = create_subaccount_mcp(vultr_client)
    mcp.mount(subaccount_mcp, prefix="subaccount")

    users_mcp = create_users_mcp(vultr_client)
    mcp.mount(users_mcp, prefix="user")

    # Service Collections - Enterprise infrastructure organization
    service_collections_store = ServiceCollectionStore()
    service_collections_mcp = create_service_collections_mcp(vultr_client, service_collections_store)
    mcp.mount(service_collections_mcp, prefix="collection")

    return mcp


def _detect_transport() -> str:
    """
    Intelligently detect the appropriate transport based on environment.

    Returns:
        Transport type: "stdio" for MCP clients, "sse" for HTTP deployment
    """
    # Check if running in MCP context (typical indicators)
    if (
        # Claude Desktop or other MCP clients typically don't set these
        "HTTP_HOST" not in os.environ
        and "PORT" not in os.environ
        and "SERVER_NAME" not in os.environ
        # Command line usage typically indicates MCP client
        and len(sys.argv) == 1
    ):
        return "stdio"

    # Default to stdio for MCP compatibility
    return "stdio"


def run_server(api_key: str | None = None, transport: str | None = None, enable_oauth: bool = None) -> None:
    """
    Create and run a Vultr DNS FastMCP server with intelligent transport selection.

    Args:
        api_key: Vultr API key. If not provided, will read from VULTR_API_KEY env var.
        transport: Transport protocol ("stdio", "sse", "streamable-http").
                  If not provided, will auto-detect based on environment.
        enable_oauth: Whether to enable OAuth authentication. If None, auto-detect from env.
    """
    # Auto-detect OAuth mode if not specified
    if enable_oauth is None:
        oauth_config = OAuthConfig.from_env()
        enable_oauth = oauth_config.enabled
    
    # Print version info for debugging/verification
    server_type = "OAuth-enabled" if enable_oauth else "standard"
    print(f"🚀 Starting mcp-vultr v{__version__} ({server_type})")

    if enable_oauth:
        mcp = create_oauth_vultr_mcp_server(api_key)
    else:
        mcp = create_vultr_mcp_server(api_key)

    # Use provided transport or auto-detect
    selected_transport = transport or _detect_transport()

    # Explicitly specify transport for reliable operation
    mcp.run(transport=selected_transport)


if __name__ == "__main__":
    run_server()
