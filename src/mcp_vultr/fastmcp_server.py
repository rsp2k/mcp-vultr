"""
Vultr DNS FastMCP Server Implementation.

This module contains the FastMCP server implementation for managing DNS records 
through the Vultr API using the FastMCP framework.
"""

import os
from typing import Optional
from fastmcp import FastMCP
from .server import VultrDNSServer
from .instances import create_instances_mcp
from .dns import create_dns_mcp
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


def create_vultr_mcp_server(api_key: Optional[str] = None) -> FastMCP:
    """
    Create a FastMCP server for Vultr DNS management.
    
    Args:
        api_key: Vultr API key. If not provided, will read from VULTR_API_KEY env var.
        
    Returns:
        Configured FastMCP server instance
    """
    if not api_key:
        api_key = os.getenv("VULTR_API_KEY")
    
    if not api_key:
        raise ValueError(
            "VULTR_API_KEY must be provided either as parameter or environment variable"
        )
    
    # Create main FastMCP server
    mcp = FastMCP(name="mcp-vultr")
    
    # Initialize Vultr client
    vultr_client = VultrDNSServer(api_key)
    
    # Mount all modules with appropriate prefixes
    dns_mcp = create_dns_mcp(vultr_client)
    mcp.mount("dns", dns_mcp)
    
    instances_mcp = create_instances_mcp(vultr_client)
    mcp.mount("instances", instances_mcp)
    
    ssh_keys_mcp = create_ssh_keys_mcp(vultr_client)
    mcp.mount("ssh_keys", ssh_keys_mcp)
    
    backups_mcp = create_backups_mcp(vultr_client)
    mcp.mount("backups", backups_mcp)
    
    firewall_mcp = create_firewall_mcp(vultr_client)
    mcp.mount("firewall", firewall_mcp)
    
    snapshots_mcp = create_snapshots_mcp(vultr_client)
    mcp.mount("snapshots", snapshots_mcp)
    
    regions_mcp = create_regions_mcp(vultr_client)
    mcp.mount("regions", regions_mcp)
    
    reserved_ips_mcp = create_reserved_ips_mcp(vultr_client)
    mcp.mount("reserved_ips", reserved_ips_mcp)
    
    container_registry_mcp = create_container_registry_mcp(vultr_client)
    mcp.mount("container_registry", container_registry_mcp)
    
    block_storage_mcp = create_block_storage_mcp(vultr_client)
    mcp.mount("block_storage", block_storage_mcp)
    
    vpcs_mcp = create_vpcs_mcp(vultr_client)
    mcp.mount("vpcs", vpcs_mcp)
    
    iso_mcp = create_iso_mcp(vultr_client)
    mcp.mount("iso", iso_mcp)
    
    os_mcp = create_os_mcp(vultr_client)
    mcp.mount("os", os_mcp)
    
    plans_mcp = create_plans_mcp(vultr_client)
    mcp.mount("plans", plans_mcp)
    
    startup_scripts_mcp = create_startup_scripts_mcp(vultr_client)
    mcp.mount("startup_scripts", startup_scripts_mcp)
    
    billing_mcp = create_billing_mcp(vultr_client)
    mcp.mount("billing", billing_mcp)
    
    bare_metal_mcp = create_bare_metal_mcp(vultr_client)
    mcp.mount("bare_metal", bare_metal_mcp)
    
    cdn_mcp = create_cdn_mcp(vultr_client)
    mcp.mount("cdn", cdn_mcp)
    
    kubernetes_mcp = create_kubernetes_mcp(vultr_client)
    mcp.mount("kubernetes", kubernetes_mcp)
    
    load_balancer_mcp = create_load_balancer_mcp(vultr_client)
    mcp.mount("load_balancer", load_balancer_mcp)
    
    managed_databases_mcp = create_managed_databases_mcp(vultr_client)
    mcp.mount("managed_databases", managed_databases_mcp)
    
    marketplace_mcp = create_marketplace_mcp(vultr_client)
    mcp.mount("marketplace", marketplace_mcp)
    
    object_storage_mcp = create_object_storage_mcp(vultr_client)
    mcp.mount("object_storage", object_storage_mcp)
    
    serverless_inference_mcp = create_serverless_inference_mcp(vultr_client)
    mcp.mount("serverless_inference", serverless_inference_mcp)
    
    storage_gateways_mcp = create_storage_gateways_mcp(vultr_client)
    mcp.mount("storage_gateways", storage_gateways_mcp)
    
    subaccount_mcp = create_subaccount_mcp(vultr_client)
    mcp.mount("subaccount", subaccount_mcp)
    
    users_mcp = create_users_mcp(vultr_client)
    mcp.mount("users", users_mcp)
    
    return mcp


def run_server(api_key: Optional[str] = None) -> None:
    """
    Create and run a Vultr DNS FastMCP server.
    
    Args:
        api_key: Vultr API key. If not provided, will read from VULTR_API_KEY env var.
    """
    mcp = create_vultr_mcp_server(api_key)
    mcp.run()


if __name__ == "__main__":
    run_server()