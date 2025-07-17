"""
Vultr Reserved IPs FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr reserved IPs.
"""

from typing import List, Dict, Any, Optional
from fastmcp import FastMCP


def create_reserved_ips_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr reserved IPs management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with reserved IP management tools
    """
    mcp = FastMCP(name="vultr-reserved-ips")
    
    # Helper function to get UUID from IP address
    async def get_reserved_ip_uuid(ip_address: str) -> str:
        """
        Get the UUID for a reserved IP address.
        
        Args:
            ip_address: The IP address to look up
            
        Returns:
            The UUID of the reserved IP
            
        Raises:
            ValueError: If the IP address is not found
        """
        reserved_ips = await vultr_client.list_reserved_ips()
        for rip in reserved_ips:
            if rip.get("subnet") == ip_address:
                return rip["id"]
        raise ValueError(f"Reserved IP {ip_address} not found")
    
    # Reserved IP resources
    @mcp.resource("reserved-ips://list")
    async def list_reserved_ips_resource() -> List[Dict[str, Any]]:
        """List all reserved IPs."""
        return await vultr_client.list_reserved_ips()
    
    @mcp.resource("reserved-ips://{reserved_ip}")
    async def get_reserved_ip_resource(reserved_ip: str) -> Dict[str, Any]:
        """Get details of a specific reserved IP.
        
        Args:
            reserved_ip: The reserved IP address
        """
        # Try to look up UUID if it looks like an IP address
        if "." in reserved_ip or ":" in reserved_ip:
            reserved_ip_uuid = await get_reserved_ip_uuid(reserved_ip)
        else:
            reserved_ip_uuid = reserved_ip
        return await vultr_client.get_reserved_ip(reserved_ip_uuid)
    
    # Reserved IP tools
    @mcp.tool
    async def list() -> List[Dict[str, Any]]:
        """List all reserved IPs in your account.
        
        Returns:
            List of reserved IP objects with details including:
            - id: Reserved IP ID
            - region: Region ID where IP is reserved
            - ip_type: IP type ("v4" or "v6")
            - subnet: IP address
            - subnet_size: Subnet size
            - label: User-defined label
            - instance_id: Attached instance ID (if any)
        """
        return await vultr_client.list_reserved_ips()
    
    @mcp.tool
    async def get(reserved_ip: str) -> Dict[str, Any]:
        """Get details of a specific reserved IP.
        
        Args:
            reserved_ip: The reserved IP address (e.g., "192.168.1.1" or "2001:db8::1")
            
        Returns:
            Reserved IP details including attachment status
        """
        # Try to look up UUID if it looks like an IP address
        if "." in reserved_ip or ":" in reserved_ip:
            reserved_ip_uuid = await get_reserved_ip_uuid(reserved_ip)
        else:
            reserved_ip_uuid = reserved_ip
        return await vultr_client.get_reserved_ip(reserved_ip_uuid)
    
    @mcp.tool
    async def create(
        region: str,
        ip_type: str = "v4",
        label: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new reserved IP in a specific region.
        
        Args:
            region: The region ID where to reserve the IP (e.g., "ewr", "lax")
            ip_type: Type of IP to reserve - "v4" for IPv4 or "v6" for IPv6 (default: "v4")
            label: Optional label for the reserved IP
            
        Returns:
            Created reserved IP information
            
        Example:
            Create a reserved IPv4 in New Jersey:
            create(region="ewr", ip_type="v4", label="web-server-ip")
        """
        return await vultr_client.create_reserved_ip(region, ip_type, label)
    
    @mcp.tool
    async def update(reserved_ip: str, label: str) -> str:
        """Update a reserved IP's label.
        
        Args:
            reserved_ip: The reserved IP address (e.g., "192.168.1.1" or "2001:db8::1")
            label: New label for the reserved IP
            
        Returns:
            Success message
        """
        # Try to look up UUID if it looks like an IP address
        if "." in reserved_ip or ":" in reserved_ip:
            reserved_ip_uuid = await get_reserved_ip_uuid(reserved_ip)
        else:
            reserved_ip_uuid = reserved_ip
        await vultr_client.update_reserved_ip(reserved_ip_uuid, label)
        return f"Reserved IP {reserved_ip} label updated to: {label}"
    
    @mcp.tool
    async def delete(reserved_ip: str) -> str:
        """Delete a reserved IP.
        
        Args:
            reserved_ip: The reserved IP address to delete (e.g., "192.168.1.1" or "2001:db8::1")
            
        Returns:
            Success message
            
        Note: The IP must be detached from any instance before deletion.
        """
        # Try to look up UUID if it looks like an IP address
        if "." in reserved_ip or ":" in reserved_ip:
            reserved_ip_uuid = await get_reserved_ip_uuid(reserved_ip)
        else:
            reserved_ip_uuid = reserved_ip
        await vultr_client.delete_reserved_ip(reserved_ip_uuid)
        return f"Reserved IP {reserved_ip} deleted successfully"
    
    @mcp.tool
    async def attach(reserved_ip: str, instance_id: str) -> str:
        """Attach a reserved IP to an instance.
        
        Args:
            reserved_ip: The reserved IP address (e.g., "192.168.1.1" or "2001:db8::1")
            instance_id: The instance ID to attach to
            
        Returns:
            Success message
            
        Note: The instance must be in the same region as the reserved IP.
        """
        # Try to look up UUID if it looks like an IP address
        if "." in reserved_ip or ":" in reserved_ip:
            reserved_ip_uuid = await get_reserved_ip_uuid(reserved_ip)
        else:
            reserved_ip_uuid = reserved_ip
        await vultr_client.attach_reserved_ip(reserved_ip_uuid, instance_id)
        return f"Reserved IP {reserved_ip} attached to instance {instance_id}"
    
    @mcp.tool
    async def detach(reserved_ip: str) -> str:
        """Detach a reserved IP from its instance.
        
        Args:
            reserved_ip: The reserved IP address to detach (e.g., "192.168.1.1" or "2001:db8::1")
            
        Returns:
            Success message
        """
        # Try to look up UUID if it looks like an IP address
        if "." in reserved_ip or ":" in reserved_ip:
            reserved_ip_uuid = await get_reserved_ip_uuid(reserved_ip)
        else:
            reserved_ip_uuid = reserved_ip
        await vultr_client.detach_reserved_ip(reserved_ip_uuid)
        return f"Reserved IP {reserved_ip} detached from instance"
    
    @mcp.tool
    async def convert_instance_ip(
        ip_address: str,
        instance_id: str,
        label: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert an existing instance IP to a reserved IP.
        
        Args:
            ip_address: The IP address to convert
            instance_id: The instance ID that owns the IP
            label: Optional label for the reserved IP
            
        Returns:
            Created reserved IP information
            
        This is useful when you want to keep an IP address even after
        destroying the instance. The IP will be converted to a reserved IP
        and remain attached to the instance.
        """
        return await vultr_client.convert_instance_ip_to_reserved(ip_address, instance_id, label)
    
    @mcp.tool
    async def list_by_region(region: str) -> List[Dict[str, Any]]:
        """List all reserved IPs in a specific region.
        
        Args:
            region: The region ID to filter by (e.g., "ewr", "lax")
            
        Returns:
            List of reserved IPs in the specified region
        """
        all_ips = await vultr_client.list_reserved_ips()
        return [ip for ip in all_ips if ip.get("region") == region]
    
    @mcp.tool
    async def list_unattached() -> List[Dict[str, Any]]:
        """List all unattached reserved IPs.
        
        Returns:
            List of reserved IPs that are not attached to any instance
        """
        all_ips = await vultr_client.list_reserved_ips()
        return [ip for ip in all_ips if not ip.get("instance_id")]
    
    @mcp.tool
    async def list_attached() -> List[Dict[str, Any]]:
        """List all attached reserved IPs.
        
        Returns:
            List of reserved IPs that are attached to instances,
            including the instance ID they're attached to
        """
        all_ips = await vultr_client.list_reserved_ips()
        return [ip for ip in all_ips if ip.get("instance_id")]
    
    return mcp