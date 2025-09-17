"""
Vultr MCP Resource Change Notification Manager.

This module provides systematic resource change notifications for FastMCP
to ensure clients receive updates when tools modify Vultr resources.
"""

from typing import Any

from fastmcp import Context


class NotificationManager:
    """
    Manages resource change notifications across all Vultr MCP services.

    This class provides standardized methods for notifying MCP clients
    when resources are created, updated, or deleted through tool actions.
    """

    # Map of operations to their affected resource URI patterns
    OPERATION_RESOURCE_MAP: dict[str, list[str]] = {
        # DNS operations
        "create_domain": ["domains://list"],
        "delete_domain": ["domains://list", "domains://{domain}/records"],
        "update_domain": ["domains://list"],
        "create_record": ["domains://{domain}/records"],
        "update_record": ["domains://{domain}/records"],
        "delete_record": ["domains://{domain}/records"],
        # Instance operations
        "create_instance": ["instances://list"],
        "delete_instance": ["instances://list"],
        "update_instance": ["instances://list", "instances://{instance_id}"],
        "start_instance": ["instances://list", "instances://{instance_id}"],
        "stop_instance": ["instances://list", "instances://{instance_id}"],
        "reboot_instance": ["instances://list", "instances://{instance_id}"],
        # SSH Key operations
        "create_ssh_key": ["ssh-keys://list"],
        "update_ssh_key": ["ssh-keys://list", "ssh-keys://{ssh_key_id}"],
        "delete_ssh_key": ["ssh-keys://list"],
        # Container Registry operations
        "create_registry": ["container-registry://list"],
        "update_registry": [
            "container-registry://list",
            "container-registry://{registry_id}",
        ],
        "delete_registry": ["container-registry://list"],
        # Block Storage operations
        "create_volume": ["block-storage://list"],
        "update_volume": ["block-storage://list", "block-storage://{volume_id}"],
        "delete_volume": ["block-storage://list"],
        "attach_volume": ["block-storage://list", "block-storage://{volume_id}"],
        "detach_volume": ["block-storage://list", "block-storage://{volume_id}"],
        # VPC operations
        "create_vpc": ["vpcs://list"],
        "update_vpc": ["vpcs://list", "vpcs://{vpc_id}"],
        "delete_vpc": ["vpcs://list"],
        # Load Balancer operations
        "create_load_balancer": ["load-balancers://list"],
        "update_load_balancer": [
            "load-balancers://list",
            "load-balancers://{load_balancer_id}",
        ],
        "delete_load_balancer": ["load-balancers://list"],
        "create_forwarding_rule": [
            "load-balancers://{load_balancer_id}/forwarding-rules"
        ],
        "delete_forwarding_rule": [
            "load-balancers://{load_balancer_id}/forwarding-rules"
        ],
        # Kubernetes operations
        "create_kubernetes_cluster": ["kubernetes://clusters"],
        "update_kubernetes_cluster": [
            "kubernetes://clusters",
            "kubernetes://clusters/{cluster_id}",
        ],
        "delete_kubernetes_cluster": ["kubernetes://clusters"],
        "create_node_pool": ["kubernetes://clusters/{cluster_id}/node-pools"],
        "update_node_pool": ["kubernetes://clusters/{cluster_id}/node-pools"],
        "delete_node_pool": ["kubernetes://clusters/{cluster_id}/node-pools"],
        # Database operations
        "create_database": ["databases://list"],
        "update_database": ["databases://list", "databases://{database_id}"],
        "delete_database": ["databases://list"],
        "create_database_user": ["databases://{database_id}/users"],
        "update_database_user": ["databases://{database_id}/users"],
        "delete_database_user": ["databases://{database_id}/users"],
        # Object Storage operations
        "create_object_storage": ["object-storage://list"],
        "update_object_storage": [
            "object-storage://list",
            "object-storage://{object_storage_id}",
        ],
        "delete_object_storage": ["object-storage://list"],
        "regenerate_object_storage_keys": [
            "object-storage://list",
            "object-storage://{object_storage_id}",
        ],
        # Firewall operations
        "create_firewall_group": ["firewall://groups"],
        "update_firewall_group": [
            "firewall://groups",
            "firewall://groups/{firewall_group_id}",
        ],
        "delete_firewall_group": ["firewall://groups"],
        "create_firewall_rule": ["firewall://groups/{firewall_group_id}/rules"],
        "delete_firewall_rule": ["firewall://groups/{firewall_group_id}/rules"],
        # User operations
        "create_user": ["users://list"],
        "update_user": ["users://list", "users://{user_id}"],
        "delete_user": ["users://list"],
        "add_ip_whitelist": ["users://{user_id}/ip-whitelist"],
        "remove_ip_whitelist": ["users://{user_id}/ip-whitelist"],
        # Subaccount operations
        "create_subaccount": ["subaccounts://list"],
        # Snapshot operations
        "create_snapshot": ["snapshots://list"],
        "delete_snapshot": ["snapshots://list"],
        # Reserved IP operations
        "create_reserved_ip": ["reserved-ips://list"],
        "update_reserved_ip": ["reserved-ips://list", "reserved-ips://{reserved_ip}"],
        "delete_reserved_ip": ["reserved-ips://list"],
        # Service Collection operations
        "create_service_collection": ["service-collections://list", "service-collections://projects"],
        "update_service_collection": [
            "service-collections://list",
            "service-collections://{collection_id}",
            "service-collections://projects",
        ],
        "delete_service_collection": ["service-collections://list", "service-collections://projects"],
    }

    @staticmethod
    async def notify_resource_change(
        ctx: Context, operation: str, debug_enabled: bool = False, **params: Any
    ) -> None:
        """
        Send resource change notification to subscribed MCP clients.

        Args:
            ctx: FastMCP Context object for sending notifications
            operation: The operation that was performed (e.g., "create_domain")
            debug_enabled: Whether to print debug information
            **params: Parameters to format resource URIs (e.g., domain="example.com")
        """
        try:
            # Send the notification to FastMCP
            await ctx.send_resource_list_changed()

            if debug_enabled:
                # Get affected resources for debugging
                affected_resources = NotificationManager.OPERATION_RESOURCE_MAP.get(
                    operation, []
                )
                if affected_resources:
                    formatted_resources = []
                    for resource_pattern in affected_resources:
                        try:
                            formatted_resource = resource_pattern.format(**params)
                            formatted_resources.append(formatted_resource)
                        except KeyError:
                            # Some params might be missing for certain patterns
                            formatted_resources.append(resource_pattern)

                    print(
                        f"🔄 Resource notification: {operation} affected {formatted_resources}"
                    )
                else:
                    print(
                        f"🔄 Resource notification: {operation} (no specific resources mapped)"
                    )

        except Exception as e:
            # Don't let notification failures break the main operation
            print(
                f"⚠️ Warning: Failed to send resource change notification for {operation}: {e}"
            )

    @staticmethod
    async def notify_dns_changes(
        ctx: Context,
        operation: str,
        domain: str | None = None,
        record_id: str | None = None,
        debug_enabled: bool = False,
    ) -> None:
        """
        Convenience method for DNS-specific resource change notifications.

        Args:
            ctx: FastMCP Context object
            operation: DNS operation performed
            domain: Domain name involved (if applicable)
            record_id: Record ID involved (if applicable)
            debug_enabled: Whether to print debug information
        """
        await NotificationManager.notify_resource_change(
            ctx=ctx,
            operation=operation,
            debug_enabled=debug_enabled,
            domain=domain,
            record_id=record_id,
        )

    @staticmethod
    async def notify_instance_changes(
        ctx: Context,
        operation: str,
        instance_id: str | None = None,
        debug_enabled: bool = False,
    ) -> None:
        """
        Convenience method for instance-specific resource change notifications.

        Args:
            ctx: FastMCP Context object
            operation: Instance operation performed
            instance_id: Instance ID involved (if applicable)
            debug_enabled: Whether to print debug information
        """
        await NotificationManager.notify_resource_change(
            ctx=ctx,
            operation=operation,
            debug_enabled=debug_enabled,
            instance_id=instance_id,
        )

    @staticmethod
    async def notify_storage_changes(
        ctx: Context,
        operation: str,
        volume_id: str | None = None,
        object_storage_id: str | None = None,
        debug_enabled: bool = False,
    ) -> None:
        """
        Convenience method for storage-specific resource change notifications.

        Args:
            ctx: FastMCP Context object
            operation: Storage operation performed
            volume_id: Block storage volume ID (if applicable)
            object_storage_id: Object storage ID (if applicable)
            debug_enabled: Whether to print debug information
        """
        await NotificationManager.notify_resource_change(
            ctx=ctx,
            operation=operation,
            debug_enabled=debug_enabled,
            volume_id=volume_id,
            object_storage_id=object_storage_id,
        )

    @staticmethod
    def get_affected_resources(operation: str, **params: Any) -> list[str]:
        """
        Get list of resource URIs affected by an operation.

        Args:
            operation: The operation name
            **params: Parameters to format resource URIs

        Returns:
            List of formatted resource URIs
        """
        resource_patterns = NotificationManager.OPERATION_RESOURCE_MAP.get(
            operation, []
        )
        formatted_resources = []

        for pattern in resource_patterns:
            try:
                formatted = pattern.format(**params)
                formatted_resources.append(formatted)
            except KeyError:
                # Some params might be missing, include the pattern as-is
                formatted_resources.append(pattern)

        return formatted_resources
