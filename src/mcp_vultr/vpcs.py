"""
Vultr VPCs FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr VPCs and VPC 2.0 networks.
"""

from typing import Any

from fastmcp import Context, FastMCP

from .notification_manager import NotificationManager
from .server import VultrResourceNotFoundError


def create_vpcs_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr VPC management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with VPC management tools
    """
    mcp = FastMCP(name="vultr-vpcs")

    # Helper function to check if string is UUID format
    def is_uuid_format(value: str) -> bool:
        """Check if a string looks like a UUID."""
        import re

        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))

    # Helper function to get VPC ID from description or ID
    async def get_vpc_id(identifier: str) -> str:
        """
        Get the VPC ID from description or existing ID.

        Args:
            identifier: VPC description or ID

        Returns:
            The VPC ID

        Raises:
            ValueError: If the VPC is not found
        """
        # If it looks like a UUID, return as-is
        if is_uuid_format(identifier):
            return identifier

        # Search by description
        vpcs = await vultr_client.list_vpcs()
        for vpc in vpcs:
            if vpc.get("description") == identifier:
                return vpc["id"]

        raise ValueError(f"VPC '{identifier}' not found")

    # Helper function to get VPC 2.0 ID from description or ID
    async def get_vpc2_id(identifier: str) -> str:
        """
        Get the VPC 2.0 ID from description or existing ID.

        Args:
            identifier: VPC 2.0 description or ID

        Returns:
            The VPC 2.0 ID

        Raises:
            ValueError: If the VPC 2.0 is not found
        """
        # If it looks like a UUID, return as-is
        if is_uuid_format(identifier):
            return identifier

        # Search by description
        vpc2s = await vultr_client.list_vpc2s()
        for vpc2 in vpc2s:
            if vpc2.get("description") == identifier:
                return vpc2["id"]

        raise ValueError(f"VPC 2.0 '{identifier}' not found")

    # VPC resources
    @mcp.resource("vpcs://list")
    async def list_vpcs_resource() -> list[dict[str, Any]]:
        """List all VPCs."""
        try:
            return await vultr_client.list_vpcs()
        except Exception:
            # If the API returns an error when no VPCs exist, return empty list
            return []

    @mcp.resource("vpcs://{vpc_identifier}")
    async def get_vpc_resource(vpc_identifier: str) -> dict[str, Any]:
        """Get details of a specific VPC.

        Args:
            vpc_identifier: The VPC description or ID
        """
        vpc_id = await get_vpc_id(vpc_identifier)
        return await vultr_client.get_vpc(vpc_id)

    @mcp.resource("vpc2s://list")
    async def list_vpc2s_resource() -> list[dict[str, Any]]:
        """List all VPC 2.0 networks."""
        return await vultr_client.list_vpc2s()

    @mcp.resource("vpc2s://{vpc2_identifier}")
    async def get_vpc2_resource(vpc2_identifier: str) -> dict[str, Any]:
        """Get details of a specific VPC 2.0.

        Args:
            vpc2_identifier: The VPC 2.0 description or ID
        """
        vpc2_id = await get_vpc2_id(vpc2_identifier)
        return await vultr_client.get_vpc2(vpc2_id)

    # VPC management tools

    @mcp.tool
    async def create(
        region: str,
        description: str,
        ctx: Context | None = None,
        v4_subnet: str | None = None,
        v4_subnet_mask: int | None = None,
    ) -> dict[str, Any]:
        """Create a new VPC.

        Args:
            region: Region code where the VPC will be created (e.g., "ewr", "lax", "fra")
            description: Description/label for the VPC
            ctx: FastMCP context for resource change notifications
            v4_subnet: IPv4 subnet for the VPC (e.g., "10.0.0.0", defaults to auto-assigned)
            v4_subnet_mask: IPv4 subnet mask (e.g., 24, defaults to 24)

        Returns:
            Created VPC information including ID and subnet details
        """
        result = await vultr_client.create_vpc(
            region, description, v4_subnet, v4_subnet_mask
        )

        # Notify clients that VPC list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="create_vpc", vpc_id=result.get("id")
            )

        return result

    @mcp.tool
    async def update(
        vpc_identifier: str, description: str, ctx: Context
    ) -> dict[str, str]:
        """Update VPC description.

        Smart identifier resolution: Use VPC description or ID.

        Args:
            vpc_identifier: VPC description or ID to update
            description: New description for the VPC
            ctx: FastMCP context for resource change notifications

        Returns:
            Success confirmation
        """
        vpc_id = await get_vpc_id(vpc_identifier)
        await vultr_client.update_vpc(vpc_id, description)

        # Notify clients that VPC list and specific VPC have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="update_vpc", vpc_id=vpc_id
            )

        return {
            "success": True,
            "message": f"VPC description updated to '{description}'",
            "vpc_id": vpc_id,
        }

    @mcp.tool
    async def delete(vpc_identifier: str, ctx: Context | None = None) -> dict[str, str]:
        """Delete a VPC.

        Smart identifier resolution: Use VPC description or ID.

        Args:
            vpc_identifier: VPC description or ID to delete
            ctx: FastMCP context for resource change notifications

        Returns:
            Success confirmation
        """
        vpc_id = await get_vpc_id(vpc_identifier)
        try:
            await vultr_client.delete_vpc(vpc_id)
        except VultrResourceNotFoundError:
            vpcs = await vultr_client.list_vpcs()
            if vpcs:
                vpc_list = ", ".join(
                    f"{v.get('description', 'unnamed')} ({v.get('id')})" for v in vpcs
                )
                raise ValueError(
                    f"VPC '{vpc_identifier}' not found. "
                    f"Available VPCs: {vpc_list}."
                ) from None
            else:
                raise ValueError(
                    f"VPC '{vpc_identifier}' not found. "
                    f"No VPCs exist in this account."
                ) from None

        # Notify clients that VPC list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="delete_vpc", vpc_id=vpc_id
            )

        return {
            "success": True,
            "message": "VPC deleted successfully",
            "vpc_id": vpc_id,
        }

    # VPC 2.0 management tools

    @mcp.tool
    async def create_vpc2(
        region: str,
        description: str,
        ip_type: str = "v4",
        ip_block: str | None = None,
        prefix_length: int | None = None,
    ) -> dict[str, Any]:
        """Create a new VPC 2.0 network.

        Args:
            region: Region code where the VPC 2.0 will be created (e.g., "ewr", "lax", "fra")
            description: Description/label for the VPC 2.0
            ip_type: IP type ("v4" or "v6", defaults to "v4")
            ip_block: IP block for the VPC 2.0 (e.g., "10.0.0.0", defaults to auto-assigned)
            prefix_length: Prefix length (e.g., 24 for /24, defaults to 24)

        Returns:
            Created VPC 2.0 information including ID and IP block details
        """
        return await vultr_client.create_vpc2(
            region, description, ip_type, ip_block, prefix_length
        )

    @mcp.tool
    async def update_vpc2(vpc2_identifier: str, description: str) -> dict[str, str]:
        """Update VPC 2.0 description.

        Smart identifier resolution: Use VPC 2.0 description or ID.

        Args:
            vpc2_identifier: VPC 2.0 description or ID to update
            description: New description for the VPC 2.0

        Returns:
            Success confirmation
        """
        vpc2_id = await get_vpc2_id(vpc2_identifier)
        await vultr_client.update_vpc2(vpc2_id, description)
        return {
            "success": True,
            "message": f"VPC 2.0 description updated to '{description}'",
            "vpc2_id": vpc2_id,
        }

    @mcp.tool
    async def delete_vpc2(vpc2_identifier: str) -> dict[str, str]:
        """Delete a VPC 2.0 network.

        Smart identifier resolution: Use VPC 2.0 description or ID.

        Args:
            vpc2_identifier: VPC 2.0 description or ID to delete

        Returns:
            Success confirmation
        """
        vpc2_id = await get_vpc2_id(vpc2_identifier)
        try:
            await vultr_client.delete_vpc2(vpc2_id)
        except VultrResourceNotFoundError:
            vpc2s = await vultr_client.list_vpc2s()
            if vpc2s:
                vpc2_list = ", ".join(
                    f"{v.get('description', 'unnamed')} ({v.get('id')})" for v in vpc2s
                )
                raise ValueError(
                    f"VPC 2.0 '{vpc2_identifier}' not found. "
                    f"Available VPC 2.0s: {vpc2_list}."
                ) from None
            else:
                raise ValueError(
                    f"VPC 2.0 '{vpc2_identifier}' not found. "
                    f"No VPC 2.0 networks exist in this account."
                ) from None
        return {
            "success": True,
            "message": "VPC 2.0 deleted successfully",
            "vpc2_id": vpc2_id,
        }

    # Instance attachment tools
    @mcp.tool
    async def attach_to_instance(
        vpc_identifier: str, instance_identifier: str, vpc_type: str = "vpc"
    ) -> dict[str, str]:
        """Attach VPC or VPC 2.0 to an instance.

        Smart identifier resolution: Use VPC/instance description/label/hostname or ID.

        Args:
            vpc_identifier: VPC/VPC 2.0 description or ID to attach
            instance_identifier: Instance label, hostname, or ID to attach to
            vpc_type: Type of VPC ("vpc" or "vpc2", defaults to "vpc")

        Returns:
            Success confirmation
        """
        # Get instance ID using the instances module pattern
        if is_uuid_format(instance_identifier):
            instance_id = instance_identifier
        else:
            instances = await vultr_client.list_instances()
            instance_id = None
            for instance in instances:
                if (
                    instance.get("label") == instance_identifier
                    or instance.get("hostname") == instance_identifier
                ):
                    instance_id = instance["id"]
                    break
            if not instance_id:
                raise ValueError(f"Instance '{instance_identifier}' not found")

        if vpc_type == "vpc2":
            vpc2_id = await get_vpc2_id(vpc_identifier)
            await vultr_client.attach_vpc2_to_instance(instance_id, vpc2_id)
            return {
                "success": True,
                "message": "VPC 2.0 attached to instance successfully",
                "vpc2_id": vpc2_id,
                "instance_id": instance_id,
            }
        else:
            vpc_id = await get_vpc_id(vpc_identifier)
            await vultr_client.attach_vpc_to_instance(instance_id, vpc_id)
            return {
                "success": True,
                "message": "VPC attached to instance successfully",
                "vpc_id": vpc_id,
                "instance_id": instance_id,
            }

    @mcp.tool
    async def detach_from_instance(
        vpc_identifier: str, instance_identifier: str, vpc_type: str = "vpc"
    ) -> dict[str, str]:
        """Detach VPC or VPC 2.0 from an instance.

        Smart identifier resolution: Use VPC/instance description/label/hostname or ID.

        Args:
            vpc_identifier: VPC/VPC 2.0 description or ID to detach
            instance_identifier: Instance label, hostname, or ID to detach from
            vpc_type: Type of VPC ("vpc" or "vpc2", defaults to "vpc")

        Returns:
            Success confirmation
        """
        # Get instance ID using the instances module pattern
        if is_uuid_format(instance_identifier):
            instance_id = instance_identifier
        else:
            instances = await vultr_client.list_instances()
            instance_id = None
            for instance in instances:
                if (
                    instance.get("label") == instance_identifier
                    or instance.get("hostname") == instance_identifier
                ):
                    instance_id = instance["id"]
                    break
            if not instance_id:
                raise ValueError(f"Instance '{instance_identifier}' not found")

        if vpc_type == "vpc2":
            vpc2_id = await get_vpc2_id(vpc_identifier)
            await vultr_client.detach_vpc2_from_instance(instance_id, vpc2_id)
            return {
                "success": True,
                "message": "VPC 2.0 detached from instance successfully",
                "vpc2_id": vpc2_id,
                "instance_id": instance_id,
            }
        else:
            vpc_id = await get_vpc_id(vpc_identifier)
            await vultr_client.detach_vpc_from_instance(instance_id, vpc_id)
            return {
                "success": True,
                "message": "VPC detached from instance successfully",
                "vpc_id": vpc_id,
                "instance_id": instance_id,
            }

    @mcp.tool
    async def list_instance_networks(instance_identifier: str) -> dict[str, Any]:
        """List all VPCs and VPC 2.0 networks attached to an instance.

        Smart identifier resolution: Use instance label, hostname, or ID.

        Args:
            instance_identifier: Instance label, hostname, or ID

        Returns:
            Combined list of VPCs and VPC 2.0 networks attached to the instance
        """
        # Get instance ID using the instances module pattern
        if is_uuid_format(instance_identifier):
            instance_id = instance_identifier
        else:
            instances = await vultr_client.list_instances()
            instance_id = None
            for instance in instances:
                if (
                    instance.get("label") == instance_identifier
                    or instance.get("hostname") == instance_identifier
                ):
                    instance_id = instance["id"]
                    break
            if not instance_id:
                raise ValueError(f"Instance '{instance_identifier}' not found")

        vpcs = await vultr_client.list_instance_vpcs(instance_id)
        vpc2s = await vultr_client.list_instance_vpc2s(instance_id)

        return {
            "instance_id": instance_id,
            "vpcs": vpcs,
            "vpc2s": vpc2s,
            "total_networks": len(vpcs) + len(vpc2s),
        }

    @mcp.tool
    async def list_by_region(region: str) -> dict[str, Any]:
        """List VPCs and VPC 2.0 networks in a specific region.

        Args:
            region: Region code to filter by (e.g., "ewr", "lax", "fra")

        Returns:
            Combined list of VPCs and VPC 2.0 networks in the specified region
        """
        vpcs = await vultr_client.list_vpcs()
        vpc2s = await vultr_client.list_vpc2s()

        region_vpcs = [vpc for vpc in vpcs if vpc.get("region") == region]
        region_vpc2s = [vpc2 for vpc2 in vpc2s if vpc2.get("region") == region]

        return {
            "region": region,
            "vpcs": region_vpcs,
            "vpc2s": region_vpc2s,
            "total_networks": len(region_vpcs) + len(region_vpc2s),
        }

    @mcp.tool
    async def get_network_info(
        identifier: str, vpc_type: str = "auto"
    ) -> dict[str, Any]:
        """Get comprehensive network information for VPC or VPC 2.0.

        Smart identifier resolution: Use VPC/VPC 2.0 description or ID.

        Args:
            identifier: VPC/VPC 2.0 description or ID
            vpc_type: Type to search ("vpc", "vpc2", or "auto" to search both)

        Returns:
            Comprehensive network information with usage recommendations
        """
        if vpc_type == "auto":
            # Try VPC first, then VPC 2.0
            try:
                vpc_id = await get_vpc_id(identifier)
                vpc = await vultr_client.get_vpc(vpc_id)
                network_type = "VPC"
                network_info = vpc
            except ValueError:
                try:
                    vpc2_id = await get_vpc2_id(identifier)
                    vpc2 = await vultr_client.get_vpc2(vpc2_id)
                    network_type = "VPC 2.0"
                    network_info = vpc2
                except ValueError:
                    raise ValueError(
                        f"Network '{identifier}' not found in VPCs or VPC 2.0s"
                    )
        elif vpc_type == "vpc2":
            vpc2_id = await get_vpc2_id(identifier)
            network_info = await vultr_client.get_vpc2(vpc2_id)
            network_type = "VPC 2.0"
        else:
            vpc_id = await get_vpc_id(identifier)
            network_info = await vultr_client.get_vpc(vpc_id)
            network_type = "VPC"

        # Enhanced network information
        enhanced_info = {
            **network_info,
            "network_type": network_type,
            "capabilities": {
                "scalability": "High" if network_type == "VPC 2.0" else "Standard",
                "broadcast_traffic": "Filtered"
                if network_type == "VPC 2.0"
                else "Processed",
                "max_instances": "1000+" if network_type == "VPC 2.0" else "100+",
                "performance": "Enhanced" if network_type == "VPC 2.0" else "Standard",
            },
            "recommendations": [
                f"Use {network_type} for your networking needs",
                "Consider VPC 2.0 for large-scale deployments"
                if network_type == "VPC"
                else "VPC 2.0 provides enhanced scalability",
                "Ensure instances are in the same region for optimal performance",
            ],
        }

        return enhanced_info

    return mcp
