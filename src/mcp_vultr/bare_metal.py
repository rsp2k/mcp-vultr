"""
Vultr Bare Metal Servers FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr bare metal servers.
"""

from typing import List, Dict, Any, Optional
from fastmcp import FastMCP


def create_bare_metal_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr bare metal server management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with bare metal server management tools
    """
    mcp = FastMCP(name="vultr-bare-metal")
    
    # Helper function to check if string is UUID format
    def is_uuid_format(value: str) -> bool:
        """Check if a string looks like a UUID."""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))
    
    # Helper function to get bare metal server ID from label or ID
    async def get_bare_metal_id(identifier: str) -> str:
        """Get the bare metal server ID from label or existing ID."""
        if is_uuid_format(identifier):
            return identifier
        
        servers = await vultr_client.list_bare_metal_servers()
        for server in servers:
            if (server.get("label") == identifier or 
                server.get("hostname") == identifier):
                return server["id"]
        
        raise ValueError(f"Bare metal server '{identifier}' not found")
    
    @mcp.tool()
    async def list_bare_metal_servers() -> List[Dict[str, Any]]:
        """
        List all bare metal servers.
        
        Returns:
            List of bare metal servers with details
        """
        return await vultr_client.list_bare_metal_servers()
    
    @mcp.tool()
    async def get_bare_metal_server(server_identifier: str) -> Dict[str, Any]:
        """
        Get details of a specific bare metal server.
        Smart identifier resolution: use server label, hostname, or UUID.
        
        Args:
            server_identifier: The bare metal server label, hostname, or ID
            
        Returns:
            Bare metal server details
        """
        server_id = await get_bare_metal_id(server_identifier)
        return await vultr_client.get_bare_metal_server(server_id)
    
    @mcp.tool()
    async def create_bare_metal_server(
        region: str,
        plan: str,
        os_id: Optional[str] = None,
        iso_id: Optional[str] = None,
        script_id: Optional[str] = None,
        ssh_key_ids: Optional[List[str]] = None,
        label: Optional[str] = None,
        tag: Optional[str] = None,
        user_data: Optional[str] = None,
        enable_ipv6: Optional[bool] = None,
        enable_private_network: Optional[bool] = None,
        attach_private_network: Optional[List[str]] = None,
        attach_vpc: Optional[List[str]] = None,
        attach_vpc2: Optional[List[str]] = None,
        enable_ddos_protection: Optional[bool] = None,
        hostname: Optional[str] = None,
        persistent_pxe: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Create a new bare metal server.
        
        Args:
            region: Region to deploy in
            plan: Bare metal plan ID
            os_id: Operating system ID
            iso_id: ISO ID for custom installation
            script_id: Startup script ID
            ssh_key_ids: List of SSH key IDs
            label: Server label
            tag: Server tag
            user_data: Cloud-init user data
            enable_ipv6: Enable IPv6
            enable_private_network: Enable private network
            attach_private_network: Private network IDs to attach
            attach_vpc: VPC IDs to attach
            attach_vpc2: VPC 2.0 IDs to attach
            enable_ddos_protection: Enable DDoS protection
            hostname: Server hostname
            persistent_pxe: Enable persistent PXE
            
        Returns:
            Created bare metal server details
        """
        return await vultr_client.create_bare_metal_server(
            region=region,
            plan=plan,
            os_id=os_id,
            iso_id=iso_id,
            script_id=script_id,
            ssh_key_ids=ssh_key_ids,
            label=label,
            tag=tag,
            user_data=user_data,
            enable_ipv6=enable_ipv6,
            enable_private_network=enable_private_network,
            attach_private_network=attach_private_network,
            attach_vpc=attach_vpc,
            attach_vpc2=attach_vpc2,
            enable_ddos_protection=enable_ddos_protection,
            hostname=hostname,
            persistent_pxe=persistent_pxe
        )
    
    @mcp.tool()
    async def update_bare_metal_server(
        server_identifier: str,
        label: Optional[str] = None,
        tag: Optional[str] = None,
        user_data: Optional[str] = None,
        enable_ddos_protection: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update a bare metal server.
        Smart identifier resolution: use server label, hostname, or UUID.
        
        Args:
            server_identifier: The bare metal server label, hostname, or ID
            label: New label
            tag: New tag
            user_data: New user data
            enable_ddos_protection: Enable/disable DDoS protection
            
        Returns:
            Updated bare metal server details
        """
        server_id = await get_bare_metal_id(server_identifier)
        return await vultr_client.update_bare_metal_server(
            server_id, label, tag, user_data, enable_ddos_protection
        )
    
    @mcp.tool()
    async def delete_bare_metal_server(server_identifier: str) -> str:
        """
        Delete a bare metal server.
        Smart identifier resolution: use server label, hostname, or UUID.
        
        Args:
            server_identifier: The bare metal server label, hostname, or ID to delete
            
        Returns:
            Success message
        """
        server_id = await get_bare_metal_id(server_identifier)
        await vultr_client.delete_bare_metal_server(server_id)
        return f"Successfully deleted bare metal server {server_identifier}"
    
    @mcp.tool()
    async def start_bare_metal_server(server_identifier: str) -> str:
        """
        Start a bare metal server.
        Smart identifier resolution: use server label, hostname, or UUID.
        
        Args:
            server_identifier: The bare metal server label, hostname, or ID
            
        Returns:
            Success message
        """
        server_id = await get_bare_metal_id(server_identifier)
        await vultr_client.start_bare_metal_server(server_id)
        return f"Successfully started bare metal server {server_identifier}"
    
    @mcp.tool()
    async def stop_bare_metal_server(server_identifier: str) -> str:
        """
        Stop a bare metal server.
        Smart identifier resolution: use server label, hostname, or UUID.
        
        Args:
            server_identifier: The bare metal server label, hostname, or ID
            
        Returns:
            Success message
        """
        server_id = await get_bare_metal_id(server_identifier)
        await vultr_client.stop_bare_metal_server(server_id)
        return f"Successfully stopped bare metal server {server_identifier}"
    
    @mcp.tool()
    async def reboot_bare_metal_server(server_identifier: str) -> str:
        """
        Reboot a bare metal server.
        Smart identifier resolution: use server label, hostname, or UUID.
        
        Args:
            server_identifier: The bare metal server label, hostname, or ID
            
        Returns:
            Success message
        """
        server_id = await get_bare_metal_id(server_identifier)
        await vultr_client.reboot_bare_metal_server(server_id)
        return f"Successfully rebooted bare metal server {server_identifier}"
    
    @mcp.tool()
    async def reinstall_bare_metal_server(
        server_identifier: str,
        hostname: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reinstall a bare metal server.
        Smart identifier resolution: use server label, hostname, or UUID.
        
        Args:
            server_identifier: The bare metal server label, hostname, or ID
            hostname: New hostname for the server
            
        Returns:
            Reinstall operation details
        """
        server_id = await get_bare_metal_id(server_identifier)
        return await vultr_client.reinstall_bare_metal_server(server_id, hostname)
    
    @mcp.tool()
    async def get_bare_metal_bandwidth(server_identifier: str) -> Dict[str, Any]:
        """
        Get bandwidth usage for a bare metal server.
        Smart identifier resolution: use server label, hostname, or UUID.
        
        Args:
            server_identifier: The bare metal server label, hostname, or ID
            
        Returns:
            Bandwidth usage information
        """
        server_id = await get_bare_metal_id(server_identifier)
        return await vultr_client.get_bare_metal_bandwidth(server_id)
    
    @mcp.tool()
    async def get_bare_metal_neighbors(server_identifier: str) -> List[Dict[str, Any]]:
        """
        Get neighbors (other servers on same physical host) for a bare metal server.
        Smart identifier resolution: use server label, hostname, or UUID.
        
        Args:
            server_identifier: The bare metal server label, hostname, or ID
            
        Returns:
            List of neighboring servers
        """
        server_id = await get_bare_metal_id(server_identifier)
        return await vultr_client.get_bare_metal_neighbors(server_id)
    
    @mcp.tool()
    async def get_bare_metal_user_data(server_identifier: str) -> Dict[str, Any]:
        """
        Get user data for a bare metal server.
        Smart identifier resolution: use server label, hostname, or UUID.
        
        Args:
            server_identifier: The bare metal server label, hostname, or ID
            
        Returns:
            User data information
        """
        server_id = await get_bare_metal_id(server_identifier)
        return await vultr_client.get_bare_metal_user_data(server_id)
    
    @mcp.tool()
    async def list_bare_metal_plans(plan_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available bare metal plans.
        
        Args:
            plan_type: Optional plan type filter
            
        Returns:
            List of bare metal plans
        """
        return await vultr_client.list_bare_metal_plans(plan_type)
    
    @mcp.tool()
    async def get_bare_metal_plan(plan_id: str) -> Dict[str, Any]:
        """
        Get details of a specific bare metal plan.
        
        Args:
            plan_id: The plan ID
            
        Returns:
            Bare metal plan details
        """
        return await vultr_client.get_bare_metal_plan(plan_id)
    
    @mcp.tool()
    async def search_bare_metal_plans(
        min_vcpus: Optional[int] = None,
        min_ram: Optional[int] = None,
        min_disk: Optional[int] = None,
        max_monthly_cost: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search bare metal plans by specifications.
        
        Args:
            min_vcpus: Minimum number of vCPUs
            min_ram: Minimum RAM in GB
            min_disk: Minimum disk space in GB
            max_monthly_cost: Maximum monthly cost in USD
            
        Returns:
            List of plans matching the criteria
        """
        all_plans = await vultr_client.list_bare_metal_plans()
        matching_plans = []
        
        for plan in all_plans:
            # Check vCPUs
            if min_vcpus and plan.get("vcpu_count", 0) < min_vcpus:
                continue
            
            # Check RAM
            if min_ram and plan.get("ram", 0) < min_ram * 1024:  # Convert GB to MB
                continue
            
            # Check disk space
            if min_disk and plan.get("disk", 0) < min_disk:
                continue
            
            # Check monthly cost
            if max_monthly_cost and plan.get("monthly_cost", float('inf')) > max_monthly_cost:
                continue
            
            matching_plans.append(plan)
        
        return matching_plans
    
    @mcp.tool()
    async def list_bare_metal_servers_by_status(status: str) -> List[Dict[str, Any]]:
        """
        List bare metal servers by status.
        
        Args:
            status: Server status to filter by (e.g., 'active', 'stopped', 'installing')
            
        Returns:
            List of bare metal servers with the specified status
        """
        all_servers = await vultr_client.list_bare_metal_servers()
        filtered_servers = [server for server in all_servers 
                           if server.get("status", "").lower() == status.lower()]
        return filtered_servers
    
    @mcp.tool()
    async def list_bare_metal_servers_by_region(region: str) -> List[Dict[str, Any]]:
        """
        List bare metal servers in a specific region.
        
        Args:
            region: Region code (e.g., 'ewr', 'lax')
            
        Returns:
            List of bare metal servers in the specified region
        """
        all_servers = await vultr_client.list_bare_metal_servers()
        region_servers = [server for server in all_servers 
                         if server.get("region") == region]
        return region_servers
    
    @mcp.tool()
    async def get_bare_metal_server_summary(server_identifier: str) -> Dict[str, Any]:
        """
        Get a comprehensive summary of a bare metal server.
        Smart identifier resolution: use server label, hostname, or UUID.
        
        Args:
            server_identifier: The bare metal server label, hostname, or ID
            
        Returns:
            Comprehensive server summary including status, specs, and usage
        """
        server_id = await get_bare_metal_id(server_identifier)
        
        # Get multiple pieces of information
        server_info = await vultr_client.get_bare_metal_server(server_id)
        
        try:
            bandwidth = await vultr_client.get_bare_metal_bandwidth(server_id)
        except Exception:
            bandwidth = {"error": "Bandwidth data unavailable"}
        
        try:
            neighbors = await vultr_client.get_bare_metal_neighbors(server_id)
        except Exception:
            neighbors = []
        
        return {
            "server_info": server_info,
            "bandwidth_usage": bandwidth,
            "neighbors_count": len(neighbors),
            "neighbors": neighbors[:3] if neighbors else [],  # Show first 3 neighbors
            "summary": {
                "status": server_info.get("status"),
                "plan": server_info.get("plan"),
                "region": server_info.get("region"),
                "os": server_info.get("os"),
                "ram": server_info.get("ram"),
                "disk": server_info.get("disk"),
                "vcpu_count": server_info.get("vcpu_count"),
                "monthly_cost": server_info.get("cost_per_month")
            }
        }
    
    return mcp