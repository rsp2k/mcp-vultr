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