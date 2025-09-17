"""
Vultr Firewall FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr firewall groups and rules.
"""

from typing import Any

from fastmcp import Context, FastMCP

from .notification_manager import NotificationManager


def create_firewall_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr firewall management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with firewall management tools
    """
    mcp = FastMCP(name="vultr-firewall")

    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        return bool(len(s) == 36 and s.count("-") == 4)

    # Helper function to get firewall group ID from description
    async def get_firewall_group_id(identifier: str) -> str:
        """
        Get the firewall group ID from a description or UUID.

        Args:
            identifier: Firewall group description or UUID

        Returns:
            The firewall group ID (UUID)

        Raises:
            ValueError: If the firewall group is not found
        """
        # If it looks like a UUID, return it as-is
        if is_uuid_format(identifier):
            return identifier

        # Otherwise, search for it by description
        groups = await vultr_client.list_firewall_groups()
        for group in groups:
            if group.get("description") == identifier:
                return group["id"]

        raise ValueError(f"Firewall group '{identifier}' not found")

    # Firewall Group resources
    @mcp.resource("firewall://groups")
    async def list_groups_resource() -> list[dict[str, Any]]:
        """List all firewall groups in your Vultr account."""
        return await vultr_client.list_firewall_groups()

    @mcp.resource("firewall://groups/{firewall_group_id}")
    async def get_group_resource(firewall_group_id: str) -> dict[str, Any]:
        """Get information about a specific firewall group.

        Args:
            firewall_group_id: The firewall group ID or description
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        return await vultr_client.get_firewall_group(actual_id)

    @mcp.resource("firewall://groups/{firewall_group_id}/rules")
    async def list_rules_resource(firewall_group_id: str) -> list[dict[str, Any]]:
        """List all rules in a firewall group.

        Args:
            firewall_group_id: The firewall group ID or description
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        return await vultr_client.list_firewall_rules(actual_id)

    @mcp.resource("firewall://groups/{firewall_group_id}/rules/{firewall_rule_id}")
    async def get_rule_resource(
        firewall_group_id: str, firewall_rule_id: str
    ) -> dict[str, Any]:
        """Get information about a specific firewall rule.

        Args:
            firewall_group_id: The firewall group ID or description
            firewall_rule_id: The firewall rule ID
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        return await vultr_client.get_firewall_rule(actual_id, firewall_rule_id)

    # Firewall Group tools
    @mcp.tool
    async def list_groups() -> list[dict[str, Any]]:
        """List all firewall groups in your Vultr account.

        Returns:
            List of firewall group objects with details including:
            - id: Firewall group ID
            - description: Group description
            - date_created: Creation date
            - date_modified: Last modification date
            - instance_count: Number of instances using this group
            - rule_count: Number of rules in this group
            - max_rule_count: Maximum allowed rules
        """
        return await vultr_client.list_firewall_groups()

    @mcp.tool
    async def get_group(firewall_group_id: str) -> dict[str, Any]:
        """Get information about a specific firewall group.

        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)

        Returns:
            Firewall group information
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        return await vultr_client.get_firewall_group(actual_id)

    @mcp.tool
    async def create_group(
        description: str, ctx: Context | None = None
    ) -> dict[str, Any]:
        """Create a new firewall group.

        Args:
            description: Description for the firewall group
            ctx: FastMCP context for resource change notifications

        Returns:
            Created firewall group information
        """
        result = await vultr_client.create_firewall_group(description)

        # Notify clients that firewall group list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx,
                operation="create_firewall_group",
                firewall_group_id=result.get("id"),
            )

        return result

    @mcp.tool
    async def update_group(
        firewall_group_id: str, description: str, ctx: Context
    ) -> dict[str, str]:
        """Update a firewall group description.

        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)
            description: New description for the firewall group
            ctx: FastMCP context for resource change notifications

        Returns:
            Status message confirming update
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        await vultr_client.update_firewall_group(actual_id, description)

        # Notify clients that firewall group list and specific group have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="update_firewall_group", firewall_group_id=actual_id
            )

        return {
            "status": "success",
            "message": f"Firewall group {firewall_group_id} updated successfully",
        }

    @mcp.tool
    async def delete_group(
        firewall_group_id: str, ctx: Context | None = None
    ) -> dict[str, str]:
        """Delete a firewall group.

        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)
            ctx: FastMCP context for resource change notifications

        Returns:
            Status message confirming deletion
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        await vultr_client.delete_firewall_group(actual_id)

        # Notify clients that firewall group list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="delete_firewall_group", firewall_group_id=actual_id
            )

        return {
            "status": "success",
            "message": f"Firewall group {firewall_group_id} deleted successfully",
        }

    # Firewall Rule tools
    @mcp.tool
    async def list_rules(firewall_group_id: str) -> list[dict[str, Any]]:
        """List all rules in a firewall group.

        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)

        Returns:
            List of firewall rules with details
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        return await vultr_client.list_firewall_rules(actual_id)

    @mcp.tool
    async def get_rule(firewall_group_id: str, firewall_rule_id: str) -> dict[str, Any]:
        """Get information about a specific firewall rule.

        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)
            firewall_rule_id: The firewall rule ID

        Returns:
            Firewall rule information
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        return await vultr_client.get_firewall_rule(actual_id, firewall_rule_id)

    @mcp.tool
    async def create_rule(
        firewall_group_id: str,
        ip_type: str,
        protocol: str,
        subnet: str,
        subnet_size: int,
        ctx: Context | None = None,
        port: str | None = None,
        source: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Create a new firewall rule.

        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)
            ip_type: IP type (v4 or v6)
            protocol: Protocol (tcp, udp, icmp, gre)
            subnet: IP subnet (use "0.0.0.0" for any IPv4, "::" for any IPv6)
            subnet_size: Subnet size (0-32 for IPv4, 0-128 for IPv6)
            ctx: FastMCP context for resource change notifications
            port: Port or port range (e.g., "80" or "8000:8999") - required for tcp/udp
            source: Source type (e.g., "cloudflare") - optional
            notes: Notes for the rule - optional

        Returns:
            Created firewall rule information

        Examples:
            # Allow HTTP from anywhere
            create_rule(group_id, "v4", "tcp", "0.0.0.0", 0, ctx, port="80")

            # Allow SSH from specific subnet
            create_rule(group_id, "v4", "tcp", "192.168.1.0", 24, ctx, port="22", notes="Office network")

            # Allow ping from anywhere
            create_rule(group_id, "v4", "icmp", "0.0.0.0", 0, ctx)
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        result = await vultr_client.create_firewall_rule(
            actual_id, ip_type, protocol, subnet, subnet_size, port, source, notes
        )

        # Notify clients that firewall rules for this group have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="create_firewall_rule", firewall_group_id=actual_id
            )

        return result

    @mcp.tool
    async def delete_rule(
        firewall_group_id: str, firewall_rule_id: str, ctx: Context
    ) -> dict[str, str]:
        """Delete a firewall rule.

        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)
            firewall_rule_id: The firewall rule ID to delete
            ctx: FastMCP context for resource change notifications

        Returns:
            Status message confirming deletion
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        await vultr_client.delete_firewall_rule(actual_id, firewall_rule_id)

        # Notify clients that firewall rules for this group have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="delete_firewall_rule", firewall_group_id=actual_id
            )

        return {
            "status": "success",
            "message": f"Firewall rule {firewall_rule_id} deleted successfully",
        }

    @mcp.tool
    async def setup_web_server_rules(
        firewall_group_id: str,
        ctx: Context | None = None,
        allow_ssh_from: str = "0.0.0.0/0",
    ) -> list[dict[str, Any]]:
        """Set up common firewall rules for a web server.

        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)
            ctx: FastMCP context for resource change notifications
            allow_ssh_from: IP subnet to allow SSH from (default: anywhere)

        Returns:
            List of created firewall rules

        Creates rules for:
        - HTTP (port 80) from anywhere
        - HTTPS (port 443) from anywhere
        - SSH (port 22) from specified subnet
        - ICMP (ping) from anywhere
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        rules = []

        # Parse SSH subnet
        ssh_parts = allow_ssh_from.split("/")
        ssh_subnet = ssh_parts[0]
        ssh_size = int(ssh_parts[1]) if len(ssh_parts) > 1 else 0

        # HTTP
        rules.append(
            await vultr_client.create_firewall_rule(
                actual_id, "v4", "tcp", "0.0.0.0", 0, port="80", notes="HTTP"
            )
        )

        # HTTPS
        rules.append(
            await vultr_client.create_firewall_rule(
                actual_id, "v4", "tcp", "0.0.0.0", 0, port="443", notes="HTTPS"
            )
        )

        # SSH
        rules.append(
            await vultr_client.create_firewall_rule(
                actual_id, "v4", "tcp", ssh_subnet, ssh_size, port="22", notes="SSH"
            )
        )

        # ICMP (ping)
        rules.append(
            await vultr_client.create_firewall_rule(
                actual_id, "v4", "icmp", "0.0.0.0", 0, notes="ICMP/Ping"
            )
        )

        # Notify clients that firewall rules for this group have changed (batch operation)
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="create_firewall_rule", firewall_group_id=actual_id
            )

        return rules

    return mcp
