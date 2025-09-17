"""
Vultr SSH Keys FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr SSH keys.
"""

from typing import Any

from fastmcp import Context, FastMCP

from .notification_manager import NotificationManager


def create_ssh_keys_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr SSH keys management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with SSH key management tools
    """
    mcp = FastMCP(name="vultr-ssh-keys")

    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        return bool(len(s) == 36 and s.count("-") == 4)

    # Helper function to get SSH key ID from name
    async def get_ssh_key_id(identifier: str) -> str:
        """
        Get the SSH key ID from a name or UUID.

        Args:
            identifier: SSH key name or UUID

        Returns:
            The SSH key ID (UUID)

        Raises:
            ValueError: If the SSH key is not found
        """
        # If it looks like a UUID, return it as-is
        if is_uuid_format(identifier):
            return identifier

        # Otherwise, search for it by name
        ssh_keys = await vultr_client.list_ssh_keys()
        for key in ssh_keys:
            if key.get("name") == identifier:
                return key["id"]

        raise ValueError(f"SSH key '{identifier}' not found")

    # SSH Key resources
    @mcp.resource("ssh-keys://list")
    async def list_ssh_keys_resource() -> list[dict[str, Any]]:
        """List all SSH keys in your Vultr account."""
        try:
            return await vultr_client.list_ssh_keys()
        except Exception:
            # If the API returns an error when no SSH keys exist, return empty list
            return []

    @mcp.resource("ssh-keys://{ssh_key_id}")
    async def get_ssh_key_resource(ssh_key_id: str) -> dict[str, Any]:
        """Get information about a specific SSH key.

        Args:
            ssh_key_id: The SSH key ID or name
        """
        actual_id = await get_ssh_key_id(ssh_key_id)
        return await vultr_client.get_ssh_key(actual_id)

    # SSH Key tools
    # SSH Key management tools

    @mcp.tool
    async def create(
        name: str, ssh_key: str, ctx: Context | None = None
    ) -> dict[str, Any]:
        """Create a new SSH key.

        Args:
            name: Name for the SSH key
            ssh_key: The SSH public key (e.g., "ssh-rsa AAAAB3NzaC1yc2...")
            ctx: FastMCP context for resource change notifications

        Returns:
            Created SSH key information including:
            - id: SSH key ID
            - name: SSH key name
            - ssh_key: The public SSH key
            - date_created: Creation date
        """
        result = await vultr_client.create_ssh_key(name, ssh_key)

        # Notify clients that SSH key list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="create_ssh_key", ssh_key_id=result.get("id")
            )

        return result

    @mcp.tool
    async def update(
        ssh_key_id: str,
        ctx: Context | None = None,
        name: str | None = None,
        ssh_key: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing SSH key.

        Args:
            ssh_key_id: The SSH key ID or name (e.g., "my-laptop-key" or UUID)
            ctx: FastMCP context for resource change notifications
            name: New name for the SSH key (optional)
            ssh_key: New SSH public key (optional)

        Returns:
            Updated SSH key information
        """
        actual_id = await get_ssh_key_id(ssh_key_id)
        result = await vultr_client.update_ssh_key(actual_id, name, ssh_key)

        # Notify clients that SSH key list and specific key have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="update_ssh_key", ssh_key_id=actual_id
            )

        return result

    @mcp.tool
    async def delete(ssh_key_id: str, ctx: Context | None = None) -> dict[str, str]:
        """Delete an SSH key.

        Args:
            ssh_key_id: The SSH key ID or name (e.g., "my-laptop-key" or UUID)
            ctx: FastMCP context for resource change notifications

        Returns:
            Status message confirming deletion
        """
        actual_id = await get_ssh_key_id(ssh_key_id)
        await vultr_client.delete_ssh_key(actual_id)

        # Notify clients that SSH key list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="delete_ssh_key", ssh_key_id=actual_id
            )

        return {
            "status": "success",
            "message": f"SSH key {ssh_key_id} deleted successfully",
        }

    return mcp
