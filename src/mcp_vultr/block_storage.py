"""
Vultr Block Storage FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr block storage volumes.
"""

from typing import List, Dict, Any, Optional
from fastmcp import FastMCP


def create_block_storage_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr block storage management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with block storage management tools
    """
    mcp = FastMCP(name="vultr-block-storage")
    
    # Helper function to check if string is UUID format
    def is_uuid_format(value: str) -> bool:
        """Check if a string looks like a UUID."""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))
    
    # Helper function to get block storage ID from label or ID
    async def get_block_storage_id(identifier: str) -> str:
        """
        Get the block storage ID from label or existing ID.
        
        Args:
            identifier: Block storage label or ID
            
        Returns:
            The block storage ID
            
        Raises:
            ValueError: If the block storage volume is not found
        """
        # If it looks like a UUID, return as-is
        if is_uuid_format(identifier):
            return identifier
        
        # Search by label
        volumes = await vultr_client.list_block_storage()
        for volume in volumes:
            if volume.get("label") == identifier:
                return volume["id"]
        
        raise ValueError(f"Block storage volume '{identifier}' not found")
    
    # Block Storage resources
    @mcp.resource("block-storage://list")
    async def list_volumes_resource() -> List[Dict[str, Any]]:
        """List all block storage volumes."""
        return await vultr_client.list_block_storage()
    
    @mcp.resource("block-storage://{volume_identifier}")
    async def get_volume_resource(volume_identifier: str) -> Dict[str, Any]:
        """Get details of a specific block storage volume.
        
        Args:
            volume_identifier: The volume label or ID
        """
        volume_id = await get_block_storage_id(volume_identifier)
        return await vultr_client.get_block_storage(volume_id)
    
    # Block Storage tools
    @mcp.tool
    async def list() -> List[Dict[str, Any]]:
        """List all block storage volumes in your account.
        
        Returns:
            List of block storage volume objects with details including:
            - id: Volume ID
            - label: User-defined label
            - region: Region where volume is located
            - size_gb: Storage size in GB
            - status: Current status (active, pending, etc.)
            - attached_to_instance: Instance ID if attached (null if detached)
            - cost_per_month: Monthly cost
            - date_created: Creation date
        """
        return await vultr_client.list_block_storage()
    
    @mcp.tool
    async def get(volume_identifier: str) -> Dict[str, Any]:
        """Get detailed information about a specific block storage volume.
        
        Smart identifier resolution: Use volume label or ID.
        
        Args:
            volume_identifier: Volume label or ID to retrieve
            
        Returns:
            Detailed volume information including status, attachment, and cost
        """
        volume_id = await get_block_storage_id(volume_identifier)
        return await vultr_client.get_block_storage(volume_id)
    
    @mcp.tool
    async def create(
        region: str,
        size_gb: int,
        label: Optional[str] = None,
        block_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new block storage volume.
        
        Args:
            region: Region code where the volume will be created (e.g., "ewr", "lax", "fra")
            size_gb: Size in GB (10-40000 depending on block_type)
            label: Optional label for the volume (recommended for easy identification)
            block_type: Optional block storage type (affects size limits and performance)
            
        Returns:
            Created volume information including ID, cost, and configuration
        """
        return await vultr_client.create_block_storage(region, size_gb, label, block_type)
    
    @mcp.tool
    async def update(
        volume_identifier: str, 
        size_gb: Optional[int] = None, 
        label: Optional[str] = None
    ) -> Dict[str, str]:
        """Update block storage volume configuration.
        
        Smart identifier resolution: Use volume label or ID.
        
        Args:
            volume_identifier: Volume label or ID to update
            size_gb: New size in GB (can only increase, not decrease)
            label: New label for the volume
            
        Returns:
            Success confirmation
        """
        volume_id = await get_block_storage_id(volume_identifier)
        await vultr_client.update_block_storage(volume_id, size_gb, label)
        
        changes = []
        if size_gb is not None:
            changes.append(f"size to {size_gb}GB")
        if label is not None:
            changes.append(f"label to '{label}'")
        
        return {
            "success": True,
            "message": f"Volume updated: {', '.join(changes) if changes else 'no changes'}",
            "volume_id": volume_id
        }
    
    @mcp.tool
    async def delete(volume_identifier: str) -> Dict[str, str]:
        """Delete a block storage volume.
        
        Smart identifier resolution: Use volume label or ID.
        
        Args:
            volume_identifier: Volume label or ID to delete
            
        Returns:
            Success confirmation
        """
        volume_id = await get_block_storage_id(volume_identifier)
        await vultr_client.delete_block_storage(volume_id)
        return {
            "success": True,
            "message": f"Block storage volume deleted successfully",
            "volume_id": volume_id
        }
    
    @mcp.tool
    async def attach(
        volume_identifier: str,
        instance_identifier: str,
        live: bool = True
    ) -> Dict[str, str]:
        """Attach block storage volume to an instance.
        
        Smart identifier resolution: Use volume label/ID and instance label/hostname/ID.
        
        Args:
            volume_identifier: Volume label or ID to attach
            instance_identifier: Instance label, hostname, or ID to attach to
            live: Whether to attach without rebooting the instance (default: True)
            
        Returns:
            Success confirmation
        """
        volume_id = await get_block_storage_id(volume_identifier)
        
        # Get instance ID using the instances module pattern
        if is_uuid_format(instance_identifier):
            instance_id = instance_identifier
        else:
            instances = await vultr_client.list_instances()
            instance_id = None
            for instance in instances:
                if (instance.get("label") == instance_identifier or 
                    instance.get("hostname") == instance_identifier):
                    instance_id = instance["id"]
                    break
            if not instance_id:
                raise ValueError(f"Instance '{instance_identifier}' not found")
        
        await vultr_client.attach_block_storage(volume_id, instance_id, live)
        return {
            "success": True,
            "message": f"Volume attached to instance {'without reboot' if live else 'with reboot'}",
            "volume_id": volume_id,
            "instance_id": instance_id
        }
    
    @mcp.tool
    async def detach(volume_identifier: str, live: bool = True) -> Dict[str, str]:
        """Detach block storage volume from its instance.
        
        Smart identifier resolution: Use volume label or ID.
        
        Args:
            volume_identifier: Volume label or ID to detach
            live: Whether to detach without rebooting the instance (default: True)
            
        Returns:
            Success confirmation
        """
        volume_id = await get_block_storage_id(volume_identifier)
        await vultr_client.detach_block_storage(volume_id, live)
        return {
            "success": True,
            "message": f"Volume detached {'without reboot' if live else 'with reboot'}",
            "volume_id": volume_id
        }
    
    @mcp.tool
    async def list_by_region(region: str) -> List[Dict[str, Any]]:
        """List block storage volumes in a specific region.
        
        Args:
            region: Region code to filter by (e.g., "ewr", "lax", "fra")
            
        Returns:
            List of volumes in the specified region
        """
        volumes = await vultr_client.list_block_storage()
        return [volume for volume in volumes if volume.get("region") == region]
    
    @mcp.tool
    async def list_unattached() -> List[Dict[str, Any]]:
        """List all unattached block storage volumes.
        
        Returns:
            List of volumes that are not currently attached to any instance
        """
        volumes = await vultr_client.list_block_storage()
        return [volume for volume in volumes if volume.get("attached_to_instance") is None]
    
    @mcp.tool
    async def list_attached() -> List[Dict[str, Any]]:
        """List all attached block storage volumes with instance information.
        
        Returns:
            List of volumes that are currently attached to instances
        """
        volumes = await vultr_client.list_block_storage()
        return [volume for volume in volumes if volume.get("attached_to_instance") is not None]
    
    @mcp.tool
    async def get_volume_status(volume_identifier: str) -> Dict[str, Any]:
        """Get comprehensive status information for a block storage volume.
        
        Smart identifier resolution: Use volume label or ID.
        
        Args:
            volume_identifier: Volume label or ID
            
        Returns:
            Detailed status including attachment, usage, and cost information
        """
        volume_id = await get_block_storage_id(volume_identifier)
        volume = await vultr_client.get_block_storage(volume_id)
        
        # Enhanced status information
        status_info = {
            **volume,
            "is_attached": volume.get("attached_to_instance") is not None,
            "attachment_status": "attached" if volume.get("attached_to_instance") else "detached",
            "size_info": {
                "current_gb": volume.get("size_gb", 0),
                "can_expand": True,  # Block storage can always be expanded
                "max_size_gb": 40000  # Current Vultr limit
            },
            "cost_info": {
                "monthly_cost": volume.get("cost_per_month", 0),
                "yearly_cost": (volume.get("cost_per_month", 0) * 12)
            }
        }
        
        return status_info
    
    @mcp.tool
    async def get_mounting_instructions(volume_identifier: str) -> Dict[str, Any]:
        """Get instructions for mounting a block storage volume on Linux.
        
        Smart identifier resolution: Use volume label or ID.
        
        Args:
            volume_identifier: Volume label or ID
            
        Returns:
            Step-by-step mounting instructions and commands
        """
        volume_id = await get_block_storage_id(volume_identifier)
        volume = await vultr_client.get_block_storage(volume_id)
        
        # Generate mounting instructions
        device_name = "/dev/vdb"  # Common device name for second block device
        mount_point = f"/mnt/{volume.get('label', 'block-storage')}"
        
        instructions = {
            "volume_info": {
                "id": volume_id,
                "label": volume.get("label", "unlabeled"),
                "size_gb": volume.get("size_gb", 0),
                "attached": volume.get("attached_to_instance") is not None
            },
            "prerequisites": [
                "Volume must be attached to an instance",
                "Run commands as root or with sudo",
                "Backup any existing data before formatting"
            ],
            "commands": {
                "check_device": f"lsblk | grep {device_name[5:]}",
                "format_ext4": f"mkfs.ext4 {device_name}",
                "create_mount_point": f"mkdir -p {mount_point}",
                "mount_volume": f"mount {device_name} {mount_point}",
                "verify_mount": f"df -h {mount_point}",
                "auto_mount": f"echo '{device_name} {mount_point} ext4 defaults 0 0' >> /etc/fstab"
            },
            "full_script": f"""# Complete mounting script for {volume.get('label', 'block-storage')}
sudo lsblk | grep {device_name[5:]}
sudo mkfs.ext4 {device_name}
sudo mkdir -p {mount_point}
sudo mount {device_name} {mount_point}
sudo df -h {mount_point}
echo '{device_name} {mount_point} ext4 defaults 0 0' | sudo tee -a /etc/fstab"""
        }
        
        if not volume.get("attached_to_instance"):
            instructions["warning"] = "Volume is not attached to any instance. Attach it first before mounting."
        
        return instructions

    return mcp