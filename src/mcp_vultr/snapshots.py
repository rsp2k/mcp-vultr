"""
Vultr Snapshots FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr snapshots.
"""

from typing import Any

from fastmcp import Context, FastMCP

from .notification_manager import NotificationManager
from .server import VultrResourceNotFoundError


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
        return bool(len(s) == 36 and s.count("-") == 4)

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
            if (
                instance.get("label") == identifier
                or instance.get("hostname") == identifier
            ):
                return instance["id"]

        raise ValueError(
            f"Instance '{identifier}' not found (searched by label and hostname)"
        )

    # Snapshot resources
    @mcp.resource("snapshots://list")
    async def list_snapshots_resource() -> list[dict[str, Any]]:
        """List all snapshots in your Vultr account."""
        try:
            return await vultr_client.list_snapshots()
        except Exception:
            # If the API returns an error when no snapshots exist, return empty list
            return []

    @mcp.resource("snapshots://{snapshot_id}")
    async def get_snapshot_resource(snapshot_id: str) -> dict[str, Any]:
        """Get information about a specific snapshot.

        Args:
            snapshot_id: The snapshot ID or description
        """
        actual_id = await get_snapshot_id(snapshot_id)
        return await vultr_client.get_snapshot(actual_id)

    # Snapshot tools
    # Snapshot management tools

    @mcp.tool
    async def create(
        instance_id: str, ctx: Context | None = None, description: str | None = None
    ) -> dict[str, Any]:
        """Create a snapshot from an instance.

        Args:
            instance_id: The instance ID, label, or hostname (e.g., "web-server", "db.example.com", or UUID)
            description: Description for the snapshot (optional)

        Returns:
            Created snapshot information

        Note: Creating a snapshot may take several minutes depending on the instance size.
        The snapshot will appear with status 'pending' initially.
        """
        # Resolve label/hostname to actual instance ID
        actual_id = await get_instance_id(instance_id)
        result = await vultr_client.create_snapshot(actual_id, description)

        # Notify clients that snapshot list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="create_snapshot", snapshot_id=result.get("id")
            )

        return result

    @mcp.tool
    async def create_from_url(
        url: str, ctx: Context | None = None, description: str | None = None
    ) -> dict[str, Any]:
        """Create a snapshot from a URL.

        Args:
            url: The URL of the snapshot to create (must be a valid snapshot URL)
            description: Description for the snapshot (optional)

        Returns:
            Created snapshot information

        Note: The URL must point to a valid Vultr snapshot file.
        """
        result = await vultr_client.create_snapshot_from_url(url, description)

        # Notify clients that snapshot list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="create_snapshot", snapshot_id=result.get("id")
            )

        return result

    @mcp.tool
    async def update(
        snapshot_id: str, description: str, ctx: Context | None = None
    ) -> dict[str, str]:
        """Update a snapshot description.

        Args:
            snapshot_id: The snapshot ID or description (e.g., "backup-2024-01" or UUID)
            description: New description for the snapshot

        Returns:
            Status message confirming update
        """
        actual_id = await get_snapshot_id(snapshot_id)
        await vultr_client.update_snapshot(actual_id, description)

        # Notify clients that snapshot list and specific snapshot have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="update_snapshot", snapshot_id=actual_id
            )

        return {
            "status": "success",
            "message": f"Snapshot {snapshot_id} updated successfully",
        }

    @mcp.tool
    async def delete(snapshot_id: str, ctx: Context | None = None) -> dict[str, str]:
        """Delete a snapshot.

        Args:
            snapshot_id: The snapshot ID or description (e.g., "backup-2024-01" or UUID)

        Returns:
            Status message confirming deletion

        Warning: This action cannot be undone!
        """
        actual_id = await get_snapshot_id(snapshot_id)
        try:
            await vultr_client.delete_snapshot(actual_id)
        except VultrResourceNotFoundError:
            snapshots = await vultr_client.list_snapshots()
            if snapshots:
                snap_list = ", ".join(
                    f"{s.get('description', 'unnamed')} ({s.get('id')})" for s in snapshots
                )
                raise ValueError(
                    f"Snapshot '{snapshot_id}' not found. "
                    f"Available snapshots: {snap_list}."
                ) from None
            else:
                raise ValueError(
                    f"Snapshot '{snapshot_id}' not found. "
                    f"No snapshots exist in this account."
                ) from None

        # Notify clients that snapshot list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="delete_snapshot", snapshot_id=actual_id
            )

        return {
            "status": "success",
            "message": f"Snapshot {snapshot_id} deleted successfully",
        }

    return mcp
