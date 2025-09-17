"""
Vultr Backups FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr backups.
"""

from typing import Any

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
    async def list_backups_resource() -> list[dict[str, Any]]:
        """List all backups in your Vultr account."""
        try:
            return await vultr_client.list_backups()
        except Exception:
            # If the API returns an error when no backups exist, return empty list
            return []

    @mcp.resource("backups://{backup_id}")
    async def get_backup_resource(backup_id: str) -> dict[str, Any]:
        """Get information about a specific backup.

        Args:
            backup_id: The backup ID to get information for
        """
        return await vultr_client.get_backup(backup_id)

    # Backup tools
    # No backup management tools currently available in the API

    return mcp
