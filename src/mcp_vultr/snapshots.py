"""
Vultr Snapshots FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr snapshots.
"""

from typing import Optional, List, Dict, Any
from fastmcp import FastMCP


def create_snapshots_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr snapshots management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with snapshot management tools
    """
    mcp = FastMCP(name="vultr-snapshots")
    
    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        if len(s) == 36 and s.count('-') == 4:
            return True
        return False
    
    # Helper function to get snapshot ID from description
    async def get_snapshot_id(identifier: str) -> str:
        """
        Get the snapshot ID from a description or UUID.
        
        Args:
            identifier: Snapshot description or UUID
            
        Returns:
            The snapshot ID (UUID)
            
        Raises:
            ValueError: If the snapshot is not found
        """
        # If it looks like a UUID, return it as-is
        if is_uuid_format(identifier):
            return identifier
            
        # Otherwise, search for it by description
        snapshots = await vultr_client.list_snapshots()
        for snapshot in snapshots:
            if snapshot.get("description") == identifier:
                return snapshot["id"]
        
        raise ValueError(f"Snapshot '{identifier}' not found")
    
    # Snapshot resources
    @mcp.resource("snapshots://list")
    async def list_snapshots_resource() -> List[Dict[str, Any]]:
        """List all snapshots in your Vultr account."""
        return await vultr_client.list_snapshots()
    
    @mcp.resource("snapshots://{snapshot_id}")
    async def get_snapshot_resource(snapshot_id: str) -> Dict[str, Any]:
        """Get information about a specific snapshot.
        
        Args:
            snapshot_id: The snapshot ID or description
        """
        actual_id = await get_snapshot_id(snapshot_id)
        return await vultr_client.get_snapshot(actual_id)
    
    # Snapshot tools
    @mcp.tool
    async def list() -> List[Dict[str, Any]]:
        """List all snapshots in your Vultr account.
        
        Returns:
            List of snapshot objects with details including:
            - id: Snapshot ID
            - date_created: Creation date
            - description: Snapshot description
            - size: Size in bytes
            - compressed_size: Compressed size in bytes
            - status: Snapshot status
            - os_id: Operating system ID
            - app_id: Application ID
        """
        return await vultr_client.list_snapshots()
    
    @mcp.tool
    async def get(snapshot_id: str) -> Dict[str, Any]:
        """Get information about a specific snapshot.
        
        Args:
            snapshot_id: The snapshot ID or description (e.g., "backup-2024-01" or UUID)
            
        Returns:
            Snapshot information including:
            - id: Snapshot ID
            - date_created: Creation date
            - description: Snapshot description
            - size: Size in bytes
            - compressed_size: Compressed size in bytes
            - status: Snapshot status
            - os_id: Operating system ID
            - app_id: Application ID
        """
        actual_id = await get_snapshot_id(snapshot_id)
        return await vultr_client.get_snapshot(actual_id)
    
    @mcp.tool
    async def create(instance_id: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a snapshot from an instance.
        
        Args:
            instance_id: The instance ID to snapshot
            description: Description for the snapshot (optional)
            
        Returns:
            Created snapshot information
            
        Note: Creating a snapshot may take several minutes depending on the instance size.
        The snapshot will appear with status 'pending' initially.
        """
        return await vultr_client.create_snapshot(instance_id, description)
    
    @mcp.tool
    async def create_from_url(url: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a snapshot from a URL.
        
        Args:
            url: The URL of the snapshot to create (must be a valid snapshot URL)
            description: Description for the snapshot (optional)
            
        Returns:
            Created snapshot information
            
        Note: The URL must point to a valid Vultr snapshot file.
        """
        return await vultr_client.create_snapshot_from_url(url, description)
    
    @mcp.tool
    async def update(snapshot_id: str, description: str) -> Dict[str, str]:
        """Update a snapshot description.
        
        Args:
            snapshot_id: The snapshot ID or description (e.g., "backup-2024-01" or UUID)
            description: New description for the snapshot
            
        Returns:
            Status message confirming update
        """
        actual_id = await get_snapshot_id(snapshot_id)
        await vultr_client.update_snapshot(actual_id, description)
        return {"status": "success", "message": f"Snapshot {snapshot_id} updated successfully"}
    
    @mcp.tool
    async def delete(snapshot_id: str) -> Dict[str, str]:
        """Delete a snapshot.
        
        Args:
            snapshot_id: The snapshot ID or description (e.g., "backup-2024-01" or UUID)
            
        Returns:
            Status message confirming deletion
            
        Warning: This action cannot be undone!
        """
        actual_id = await get_snapshot_id(snapshot_id)
        await vultr_client.delete_snapshot(actual_id)
        return {"status": "success", "message": f"Snapshot {snapshot_id} deleted successfully"}
    
    return mcp