"""
Vultr Reserved IPs FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr reserved IPs.
"""

from typing import Any

from fastmcp import Context, FastMCP

from .notification_manager import NotificationManager


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

    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        return bool(len(s) == 36 and s.count("-") == 4)

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

    # Reserved IP resources
    @mcp.resource("reserved-ips://list")
    async def list_reserved_ips_resource() -> list[dict[str, Any]]:
        """List all reserved IPs."""
        try:
            return await vultr_client.list_reserved_ips()
        except Exception:
            # If the API returns an error when no reserved IPs exist, return empty list
            return []

    @mcp.resource("reserved-ips://{reserved_ip}")
    async def get_reserved_ip_resource(reserved_ip: str) -> dict[str, Any]:
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
    # Reserved IP management tools

    @mcp.tool
    async def create(
        region: str,
        ctx: Context | None = None,
        ip_type: str = "v4",
        label: str | None = None,
    ) -> dict[str, Any]:
        """Create a new reserved IP in a specific region.

        Args:
            region: The region ID where to reserve the IP (e.g., "ewr", "lax")
            ctx: FastMCP context for resource change notifications
            ip_type: Type of IP to reserve - "v4" for IPv4 or "v6" for IPv6 (default: "v4")
            label: Optional label for the reserved IP

        Returns:
            Created reserved IP information

        Example:
            Create a reserved IPv4 in New Jersey:
            create(region="ewr", ip_type="v4", label="web-server-ip")
        """
        result = await vultr_client.create_reserved_ip(region, ip_type, label)

        # Notify clients that reserved IP list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="create_reserved_ip", reserved_ip_id=result.get("id")
            )

        return result

    @mcp.tool
    async def update(reserved_ip: str, label: str, ctx: Context | None = None) -> str:
        """Update a reserved IP's label.

        Args:
            reserved_ip: The reserved IP address (e.g., "192.168.1.1" or "2001:db8::1")
            label: New label for the reserved IP
            ctx: FastMCP context for resource change notifications

        Returns:
            Success message
        """
        # Try to look up UUID if it looks like an IP address
        if "." in reserved_ip or ":" in reserved_ip:
            reserved_ip_uuid = await get_reserved_ip_uuid(reserved_ip)
        else:
            reserved_ip_uuid = reserved_ip
        await vultr_client.update_reserved_ip(reserved_ip_uuid, label)

        # Notify clients that reserved IP list and specific IP have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="update_reserved_ip", reserved_ip_id=reserved_ip_uuid
            )

        return f"Reserved IP {reserved_ip} label updated to: {label}"

    @mcp.tool
    async def delete(reserved_ip: str, ctx: Context | None = None) -> str:
        """Delete a reserved IP.

        Args:
            reserved_ip: The reserved IP address to delete (e.g., "192.168.1.1" or "2001:db8::1")
            ctx: FastMCP context for resource change notifications

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

        # Notify clients that reserved IP list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="delete_reserved_ip", reserved_ip_id=reserved_ip_uuid
            )

        return f"Reserved IP {reserved_ip} deleted successfully"

    @mcp.tool
    async def attach(
        reserved_ip: str, instance_id: str, ctx: Context | None = None
    ) -> str:
        """Attach a reserved IP to an instance.

        Args:
            reserved_ip: The reserved IP address (e.g., "192.168.1.1" or "2001:db8::1")
            instance_id: The instance ID, label, or hostname (e.g., "web-server", "db.example.com", or UUID)
            ctx: FastMCP context for resource change notifications

        Returns:
            Success message

        Note: The instance must be in the same region as the reserved IP.
        """
        # Try to look up UUID if it looks like an IP address
        if "." in reserved_ip or ":" in reserved_ip:
            reserved_ip_uuid = await get_reserved_ip_uuid(reserved_ip)
        else:
            reserved_ip_uuid = reserved_ip
        # Resolve instance label/hostname to actual instance ID
        actual_instance_id = await get_instance_id(instance_id)
        await vultr_client.attach_reserved_ip(reserved_ip_uuid, actual_instance_id)

        # Notify clients that reserved IP list and specific IP have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="attach_reserved_ip", reserved_ip_id=reserved_ip_uuid
            )

        return f"Reserved IP {reserved_ip} attached to instance {instance_id}"

    @mcp.tool
    async def detach(reserved_ip: str, ctx: Context | None = None) -> str:
        """Detach a reserved IP from its instance.

        Args:
            reserved_ip: The reserved IP address to detach (e.g., "192.168.1.1" or "2001:db8::1")
            ctx: FastMCP context for resource change notifications

        Returns:
            Success message
        """
        # Try to look up UUID if it looks like an IP address
        if "." in reserved_ip or ":" in reserved_ip:
            reserved_ip_uuid = await get_reserved_ip_uuid(reserved_ip)
        else:
            reserved_ip_uuid = reserved_ip
        await vultr_client.detach_reserved_ip(reserved_ip_uuid)

        # Notify clients that reserved IP list and specific IP have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="detach_reserved_ip", reserved_ip_id=reserved_ip_uuid
            )

        return f"Reserved IP {reserved_ip} detached from instance"

    @mcp.tool
    async def convert_instance_ip(
        ip_address: str,
        instance_id: str,
        ctx: Context | None = None,
        label: str | None = None,
    ) -> dict[str, Any]:
        """Convert an existing instance IP to a reserved IP.

        Args:
            ip_address: The IP address to convert
            instance_id: The instance ID, label, or hostname that owns the IP (e.g., "web-server" or UUID)
            ctx: FastMCP context for resource change notifications
            label: Optional label for the reserved IP

        Returns:
            Created reserved IP information

        This is useful when you want to keep an IP address even after
        destroying the instance. The IP will be converted to a reserved IP
        and remain attached to the instance.
        """
        # Resolve instance label/hostname to actual instance ID
        actual_instance_id = await get_instance_id(instance_id)
        result = await vultr_client.convert_instance_ip_to_reserved(
            ip_address, actual_instance_id, label
        )

        # Notify clients that reserved IP list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="create_reserved_ip", reserved_ip_id=result.get("id")
            )

        return result

    @mcp.tool
    async def list_by_region(region: str) -> list[dict[str, Any]]:
        """List all reserved IPs in a specific region.

        Args:
            region: The region ID to filter by (e.g., "ewr", "lax")

        Returns:
            List of reserved IPs in the specified region
        """
        all_ips = await vultr_client.list_reserved_ips()
        return [ip for ip in all_ips if ip.get("region") == region]

    @mcp.tool
    async def list_unattached() -> list[dict[str, Any]]:
        """List all unattached reserved IPs.

        Returns:
            List of reserved IPs that are not attached to any instance
        """
        all_ips = await vultr_client.list_reserved_ips()
        return [ip for ip in all_ips if not ip.get("instance_id")]

    @mcp.tool
    async def list_attached() -> list[dict[str, Any]]:
        """List all attached reserved IPs.

        Returns:
            List of reserved IPs that are attached to instances,
            including the instance ID they're attached to
        """
        all_ips = await vultr_client.list_reserved_ips()
        return [ip for ip in all_ips if ip.get("instance_id")]

    return mcp
