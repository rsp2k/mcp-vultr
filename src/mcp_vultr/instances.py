"""
Vultr Instances FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr instances.
"""

from typing import Optional, List, Dict, Any
from fastmcp import FastMCP


def create_instances_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr instances management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with instance management tools
    """
    mcp = FastMCP(name="vultr-instances")
    
    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        if len(s) == 36 and s.count('-') == 4:
            return True
        return False
    
    # Helper function to get instance ID from label or hostname
    async def get_instance_id(identifier: str) -> str:
        """
        Get the instance ID from a label, hostname, or UUID.
        
        Args:
            identifier: Instance label, hostname, or UUID
            
        Returns:
            The instance ID (UUID)
            
        Raises:
            ValueError: If the instance is not found
        """
        # If it looks like a UUID, return it as-is
        if is_uuid_format(identifier):
            return identifier
            
        # Otherwise, search for it by label or hostname
        instances = await vultr_client.list_instances()
        for instance in instances:
            if instance.get("label") == identifier or instance.get("hostname") == identifier:
                return instance["id"]
        
        raise ValueError(f"Instance '{identifier}' not found (searched by label and hostname)")
    
    # Instance resources
    @mcp.resource("instances://list")
    async def list_instances_resource() -> List[Dict[str, Any]]:
        """List all instances in your Vultr account."""
        return await vultr_client.list_instances()
    
    @mcp.resource("instances://{instance_id}")
    async def get_instance_resource(instance_id: str) -> Dict[str, Any]:
        """Get information about a specific instance.
        
        Args:
            instance_id: The instance ID, label, or hostname
        """
        actual_id = await get_instance_id(instance_id)
        return await vultr_client.get_instance(actual_id)
    
    # Instance tools
    @mcp.tool
    async def list() -> List[Dict[str, Any]]:
        """List all instances in your Vultr account.
        
        Returns:
            List of instance objects with details including:
            - id: Instance ID
            - label: Instance label
            - hostname: Instance hostname
            - region: Region code
            - plan: Plan ID
            - os: Operating system
            - status: Instance status (active, pending, etc.)
            - main_ip: Primary IPv4 address
            - v6_main_ip: Primary IPv6 address
            - date_created: Creation date
        """
        return await vultr_client.list_instances()
    
    @mcp.tool
    async def get(instance_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific instance.
        
        Args:
            instance_id: The instance ID, label, or hostname (e.g., "web-server", "db.example.com", or UUID)
            
        Returns:
            Detailed instance information
        """
        actual_id = await get_instance_id(instance_id)
        return await vultr_client.get_instance(actual_id)
    
    @mcp.tool
    async def create(
        region: str,
        plan: str,
        label: Optional[str] = None,
        os_id: Optional[int] = None,
        iso_id: Optional[str] = None,
        script_id: Optional[str] = None,
        snapshot_id: Optional[str] = None,
        enable_ipv6: bool = False,
        enable_private_network: bool = False,
        attach_private_network: Optional[List[str]] = None,
        ssh_key_ids: Optional[List[str]] = None,
        backups: bool = False,
        app_id: Optional[int] = None,
        user_data: Optional[str] = None,
        ddos_protection: bool = False,
        activation_email: bool = False,
        hostname: Optional[str] = None,
        tag: Optional[str] = None,
        firewall_group_id: Optional[str] = None,
        reserved_ipv4: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new instance.
        
        Args:
            region: Region code (e.g., 'ewr', 'lax')
            plan: Plan ID (e.g., 'vc2-1c-1gb')
            label: Label for the instance
            os_id: Operating System ID (use list_os to get available options)
            iso_id: ISO ID for custom installation
            script_id: Startup script ID
            snapshot_id: Snapshot ID to restore from
            enable_ipv6: Enable IPv6
            enable_private_network: Enable private networking
            attach_private_network: List of private network IDs to attach
            ssh_key_ids: List of SSH key IDs to install
            backups: Enable automatic backups
            app_id: Application ID to install
            user_data: Cloud-init user data
            ddos_protection: Enable DDoS protection
            activation_email: Send activation email
            hostname: Hostname for the instance
            tag: Tag for the instance
            firewall_group_id: Firewall group ID
            reserved_ipv4: Reserved IPv4 address to use
            
        Returns:
            Created instance information
        """
        return await vultr_client.create_instance(
            region=region,
            plan=plan,
            label=label,
            os_id=os_id,
            iso_id=iso_id,
            script_id=script_id,
            snapshot_id=snapshot_id,
            enable_ipv6=enable_ipv6,
            enable_private_network=enable_private_network,
            attach_private_network=attach_private_network,
            ssh_key_ids=ssh_key_ids,
            backups=backups,
            app_id=app_id,
            user_data=user_data,
            ddos_protection=ddos_protection,
            activation_email=activation_email,
            hostname=hostname,
            tag=tag,
            firewall_group_id=firewall_group_id,
            reserved_ipv4=reserved_ipv4
        )
    
    @mcp.tool
    async def update(
        instance_id: str,
        label: Optional[str] = None,
        tag: Optional[str] = None,
        plan: Optional[str] = None,
        enable_ipv6: Optional[bool] = None,
        backups: Optional[bool] = None,
        ddos_protection: Optional[bool] = None,
        firewall_group_id: Optional[str] = None,
        user_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an existing instance.
        
        Args:
            instance_id: The instance ID to update
            label: New label for the instance
            tag: New tag for the instance
            plan: New plan ID (for resizing)
            enable_ipv6: Enable/disable IPv6
            backups: Enable/disable automatic backups
            ddos_protection: Enable/disable DDoS protection
            firewall_group_id: New firewall group ID
            user_data: New cloud-init user data
            
        Returns:
            Updated instance information
        """
        return await vultr_client.update_instance(
            instance_id=instance_id,
            label=label,
            tag=tag,
            plan=plan,
            enable_ipv6=enable_ipv6,
            backups=backups,
            ddos_protection=ddos_protection,
            firewall_group_id=firewall_group_id,
            user_data=user_data
        )
    
    @mcp.tool
    async def delete(instance_id: str) -> Dict[str, str]:
        """Delete an instance.
        
        Args:
            instance_id: The instance ID, label, or hostname (e.g., "web-server", "db.example.com", or UUID)
            
        Returns:
            Status message confirming deletion
        """
        actual_id = await get_instance_id(instance_id)
        await vultr_client.delete_instance(actual_id)
        return {"status": "success", "message": f"Instance {instance_id} deleted successfully"}
    
    @mcp.tool
    async def start(instance_id: str) -> Dict[str, str]:
        """Start a stopped instance.
        
        Args:
            instance_id: The instance ID, label, or hostname (e.g., "web-server", "db.example.com", or UUID)
            
        Returns:
            Status message confirming start
        """
        actual_id = await get_instance_id(instance_id)
        await vultr_client.start_instance(actual_id)
        return {"status": "success", "message": f"Instance {instance_id} started successfully"}
    
    @mcp.tool
    async def stop(instance_id: str) -> Dict[str, str]:
        """Stop a running instance.
        
        Args:
            instance_id: The instance ID, label, or hostname (e.g., "web-server", "db.example.com", or UUID)
            
        Returns:
            Status message confirming stop
        """
        actual_id = await get_instance_id(instance_id)
        await vultr_client.stop_instance(actual_id)
        return {"status": "success", "message": f"Instance {instance_id} stopped successfully"}
    
    @mcp.tool
    async def reboot(instance_id: str) -> Dict[str, str]:
        """Reboot an instance.
        
        Args:
            instance_id: The instance ID, label, or hostname (e.g., "web-server", "db.example.com", or UUID)
            
        Returns:
            Status message confirming reboot
        """
        actual_id = await get_instance_id(instance_id)
        await vultr_client.reboot_instance(actual_id)
        return {"status": "success", "message": f"Instance {instance_id} rebooted successfully"}
    
    @mcp.tool
    async def reinstall(instance_id: str, hostname: Optional[str] = None) -> Dict[str, Any]:
        """Reinstall an instance's operating system.
        
        Args:
            instance_id: The instance ID, label, or hostname (e.g., "web-server", "db.example.com", or UUID)
            hostname: New hostname for the instance (optional)
            
        Returns:
            Reinstall status information
        """
        actual_id = await get_instance_id(instance_id)
        return await vultr_client.reinstall_instance(actual_id, hostname)
    
    # Bandwidth information
    @mcp.resource("instances://{instance_id}/bandwidth")
    async def get_bandwidth_resource(instance_id: str) -> Dict[str, Any]:
        """Get bandwidth usage for an instance.
        
        Args:
            instance_id: The instance ID, label, or hostname
        """
        actual_id = await get_instance_id(instance_id)
        return await vultr_client.get_instance_bandwidth(actual_id)
    
    @mcp.tool
    async def get_bandwidth(instance_id: str) -> Dict[str, Any]:
        """Get bandwidth usage statistics for an instance.
        
        Args:
            instance_id: The instance ID, label, or hostname (e.g., "web-server", "db.example.com", or UUID)
            
        Returns:
            Bandwidth usage information
        """
        actual_id = await get_instance_id(instance_id)
        return await vultr_client.get_instance_bandwidth(actual_id)
    
    # IPv4 management
    @mcp.tool
    async def list_ipv4(instance_id: str) -> List[Dict[str, Any]]:
        """List IPv4 addresses for an instance.
        
        Args:
            instance_id: The instance ID, label, or hostname (e.g., "web-server", "db.example.com", or UUID)
            
        Returns:
            List of IPv4 addresses
        """
        actual_id = await get_instance_id(instance_id)
        return await vultr_client.list_instance_ipv4(actual_id)
    
    @mcp.tool
    async def create_ipv4(instance_id: str, reboot: bool = True) -> Dict[str, Any]:
        """Create a new IPv4 address for an instance.
        
        Args:
            instance_id: The instance ID, label, or hostname (e.g., "web-server", "db.example.com", or UUID)
            reboot: Whether to reboot the instance (default: True)
            
        Returns:
            Created IPv4 information
        """
        actual_id = await get_instance_id(instance_id)
        return await vultr_client.create_instance_ipv4(actual_id, reboot)
    
    @mcp.tool
    async def delete_ipv4(instance_id: str, ipv4: str) -> Dict[str, str]:
        """Delete an IPv4 address from an instance.
        
        Args:
            instance_id: The instance ID, label, or hostname (e.g., "web-server", "db.example.com", or UUID)
            ipv4: The IPv4 address to delete
            
        Returns:
            Status message confirming deletion
        """
        actual_id = await get_instance_id(instance_id)
        await vultr_client.delete_instance_ipv4(actual_id, ipv4)
        return {"status": "success", "message": f"IPv4 {ipv4} deleted successfully"}
    
    # IPv6 management
    @mcp.resource("instances://{instance_id}/ipv6")
    async def list_ipv6_resource(instance_id: str) -> List[Dict[str, Any]]:
        """List IPv6 addresses for an instance.
        
        Args:
            instance_id: The instance ID, label, or hostname
        """
        actual_id = await get_instance_id(instance_id)
        return await vultr_client.list_instance_ipv6(actual_id)
    
    @mcp.tool
    async def list_ipv6(instance_id: str) -> List[Dict[str, Any]]:
        """List IPv6 addresses for an instance.
        
        Args:
            instance_id: The instance ID, label, or hostname (e.g., "web-server", "db.example.com", or UUID)
            
        Returns:
            List of IPv6 addresses
        """
        actual_id = await get_instance_id(instance_id)
        return await vultr_client.list_instance_ipv6(actual_id)
    
    return mcp