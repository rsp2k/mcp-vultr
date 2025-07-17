"""
Vultr Backups FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr backups.
"""

from typing import List, Dict, Any
from fastmcp import FastMCP


def create_backups_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr backups management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with backup management tools
    """
    mcp = FastMCP(name="vultr-backups")
    
    # Backup resources
    @mcp.resource("backups://list")
    async def list_backups_resource() -> List[Dict[str, Any]]:
        """List all backups in your Vultr account."""
        return await vultr_client.list_backups()
    
    @mcp.resource("backups://{backup_id}")
    async def get_backup_resource(backup_id: str) -> Dict[str, Any]:
        """Get information about a specific backup.
        
        Args:
            backup_id: The backup ID to get information for
        """
        return await vultr_client.get_backup(backup_id)
    
    # Backup tools
    @mcp.tool
    async def list() -> List[Dict[str, Any]]:
        """List all backups in your Vultr account.
        
        Returns:
            List of backup objects with details including:
            - id: Backup ID
            - date_created: Creation date
            - description: Backup description
            - size: Size in bytes
            - status: Backup status
        """
        return await vultr_client.list_backups()
    
    @mcp.tool
    async def get(backup_id: str) -> Dict[str, Any]:
        """Get information about a specific backup.
        
        Args:
            backup_id: The backup ID to get information for
            
        Returns:
            Backup information including:
            - id: Backup ID
            - date_created: Creation date
            - description: Backup description
            - size: Size in bytes
            - status: Backup status
        """
        return await vultr_client.get_backup(backup_id)
    
    return mcp