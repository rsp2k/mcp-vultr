"""
Vultr Load Balancer FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr Load Balancers.
"""

from typing import Any

from fastmcp import Context, FastMCP

from .load_balancer_analyzer import LoadBalancerAnalyzer
from .notification_manager import NotificationManager


def create_load_balancer_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr Load Balancer management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with load balancer management tools
    """
    mcp = FastMCP(name="vultr-load-balancer")
    lb_analyzer = LoadBalancerAnalyzer(vultr_client)

    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        return bool(len(s) == 36 and s.count("-") == 4)

    # Helper function to get load balancer ID from label or UUID
    async def get_load_balancer_id(identifier: str) -> str:
        """
        Get the load balancer ID from a label or UUID.

        Args:
            identifier: Load balancer label or UUID

        Returns:
            The load balancer ID (UUID)

        Raises:
            ValueError: If the load balancer is not found
        """
        # If it looks like a UUID, return it as-is
        if is_uuid_format(identifier):
            return identifier

        # Otherwise, search for it by label
        load_balancers = await vultr_client.list_load_balancers()
        for lb in load_balancers:
            if lb.get("label") == identifier:
                return lb["id"]

        raise ValueError(f"Load balancer '{identifier}' not found (searched by label)")

    # Load Balancer resources
    @mcp.resource("load-balancers://list")
    async def list_load_balancers_resource() -> list[dict[str, Any]]:
        """List all load balancers in your Vultr account."""
        try:
            return await vultr_client.list_load_balancers()
        except Exception:
            # If the API returns an error when no load balancers exist, return empty list
            return []

    @mcp.resource("load-balancers://{load_balancer_id}")
    async def get_load_balancer_resource(load_balancer_id: str) -> dict[str, Any]:
        """Get information about a specific load balancer.

        Args:
            load_balancer_id: The load balancer ID or label
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.get_load_balancer(actual_id)

    # Load Balancer tools
    @mcp.tool
    async def get(load_balancer_id: str) -> dict[str, Any]:
        """Get detailed information about a specific load balancer.

        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)

        Returns:
            Detailed load balancer information
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.get_load_balancer(actual_id)

    @mcp.tool
    async def create(
        region: str,
        ctx: Context | None = None,
        balancing_algorithm: str = "roundrobin",
        ssl_redirect: bool = False,
        http2: bool = False,
        http3: bool = False,
        proxy_protocol: bool = False,
        timeout: int = 600,
        label: str | None = None,
        nodes: int = 1,
        health_check: dict[str, Any] | None = None,
        forwarding_rules: list[dict[str, Any]] | None = None,
        ssl: dict[str, str] | None = None,
        firewall_rules: list[dict[str, Any]] | None = None,
        auto_ssl: dict[str, str] | None = None,
        global_regions: list[str] | None = None,
        vpc: str | None = None,
        private_network: str | None = None,
        sticky_session: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a new load balancer.

        Args:
            region: Region code (e.g., 'ewr', 'lax')
            ctx: FastMCP context for resource change notifications
            balancing_algorithm: Algorithm to use ('roundrobin' or 'leastconn')
            ssl_redirect: Redirect HTTP traffic to HTTPS
            http2: Enable HTTP/2 support
            http3: Enable HTTP/3 support
            proxy_protocol: Enable proxy protocol
            timeout: Connection timeout in seconds
            label: Label for the load balancer
            nodes: Number of backend nodes
            health_check: Health check configuration dict with keys:
                - protocol: 'http', 'https', 'tcp'
                - port: Port number
                - path: Path for HTTP checks
                - check_interval: Check interval in seconds
                - response_timeout: Response timeout in seconds
                - unhealthy_threshold: Failures before marking unhealthy
                - healthy_threshold: Successes before marking healthy
            forwarding_rules: List of forwarding rule dicts with keys:
                - frontend_protocol: 'http', 'https', 'tcp'
                - frontend_port: Frontend port number
                - backend_protocol: 'http', 'https', 'tcp'
                - backend_port: Backend port number
            ssl: SSL configuration dict with keys:
                - private_key: Private key content
                - certificate: Certificate content
                - chain: Certificate chain content
            firewall_rules: List of firewall rule dicts with keys:
                - port: Port number
                - source: Source IP or CIDR
                - ip_type: 'v4' or 'v6'
            auto_ssl: Auto SSL configuration dict with keys:
                - domain_zone: Domain zone
                - domain_sub: Subdomain
            global_regions: List of global region codes
            vpc: VPC ID to attach to
            private_network: Private network ID (legacy)
            sticky_session: Sticky session configuration with cookie_name

        Returns:
            Created load balancer information
        """
        result = await vultr_client.create_load_balancer(
            region=region,
            balancing_algorithm=balancing_algorithm,
            ssl_redirect=ssl_redirect,
            http2=http2,
            http3=http3,
            proxy_protocol=proxy_protocol,
            timeout=timeout,
            label=label,
            nodes=nodes,
            health_check=health_check,
            forwarding_rules=forwarding_rules,
            ssl=ssl,
            firewall_rules=firewall_rules,
            auto_ssl=auto_ssl,
            global_regions=global_regions,
            vpc=vpc,
            private_network=private_network,
            sticky_session=sticky_session,
        )

        # Notify clients that load balancer list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx,
                operation="create_load_balancer",
                load_balancer_id=result.get("id"),
            )

        return result

    @mcp.tool
    async def update(
        load_balancer_id: str,
        ctx: Context | None = None,
        ssl: dict[str, str] | None = None,
        sticky_session: dict[str, str] | None = None,
        forwarding_rules: list[dict[str, Any]] | None = None,
        health_check: dict[str, Any] | None = None,
        proxy_protocol: bool | None = None,
        timeout: int | None = None,
        ssl_redirect: bool | None = None,
        http2: bool | None = None,
        http3: bool | None = None,
        nodes: int | None = None,
        balancing_algorithm: str | None = None,
        instances: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update an existing load balancer.

        Args:
            load_balancer_id: The load balancer ID or label
            ctx: FastMCP context for resource change notifications
            ssl: SSL configuration dict
            sticky_session: Sticky session configuration
            forwarding_rules: Updated forwarding rules
            health_check: Updated health check configuration
            proxy_protocol: Enable/disable proxy protocol
            timeout: Connection timeout in seconds
            ssl_redirect: Enable/disable SSL redirect
            http2: Enable/disable HTTP/2
            http3: Enable/disable HTTP/3
            nodes: Number of backend nodes
            balancing_algorithm: Balancing algorithm
            instances: List of instance IDs to attach

        Returns:
            Updated load balancer information
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        result = await vultr_client.update_load_balancer(
            load_balancer_id=actual_id,
            ssl=ssl,
            sticky_session=sticky_session,
            forwarding_rules=forwarding_rules,
            health_check=health_check,
            proxy_protocol=proxy_protocol,
            timeout=timeout,
            ssl_redirect=ssl_redirect,
            http2=http2,
            http3=http3,
            nodes=nodes,
            balancing_algorithm=balancing_algorithm,
            instances=instances,
        )

        # Notify clients that load balancer list and specific load balancer have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="update_load_balancer", load_balancer_id=actual_id
            )

        return result

    @mcp.tool
    async def delete(
        load_balancer_id: str, ctx: Context | None = None
    ) -> dict[str, str]:
        """Delete a load balancer.

        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            ctx: FastMCP context for resource change notifications

        Returns:
            Status message confirming deletion
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        await vultr_client.delete_load_balancer(actual_id)

        # Notify clients that load balancer list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="delete_load_balancer", load_balancer_id=actual_id
            )

        return {
            "status": "success",
            "message": f"Load balancer {load_balancer_id} deleted successfully",
        }

    # SSL Management
    @mcp.tool
    async def delete_ssl(
        load_balancer_id: str, ctx: Context | None = None
    ) -> dict[str, str]:
        """Delete SSL certificate from a load balancer.

        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            ctx: FastMCP context for resource change notifications

        Returns:
            Status message confirming SSL deletion
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        await vultr_client.delete_load_balancer_ssl(actual_id)

        # Notify clients that load balancer list and specific load balancer have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="update_load_balancer", load_balancer_id=actual_id
            )

        return {
            "status": "success",
            "message": f"SSL certificate deleted from load balancer {load_balancer_id}",
        }

    @mcp.tool
    async def disable_auto_ssl(load_balancer_id: str) -> dict[str, str]:
        """Disable Auto SSL for a load balancer.

        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)

        Returns:
            Status message confirming Auto SSL disabled
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        await vultr_client.disable_load_balancer_auto_ssl(actual_id)
        return {
            "status": "success",
            "message": f"Auto SSL disabled for load balancer {load_balancer_id}",
        }

    # Forwarding Rules Management
    @mcp.resource("load-balancers://{load_balancer_id}/forwarding-rules")
    async def list_forwarding_rules_resource(
        load_balancer_id: str,
    ) -> list[dict[str, Any]]:
        """List forwarding rules for a load balancer.

        Args:
            load_balancer_id: The load balancer ID or label
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.list_load_balancer_forwarding_rules(actual_id)

    @mcp.tool
    async def list_forwarding_rules(
        load_balancer_id: str,
    ) -> list[dict[str, Any]]:
        """List forwarding rules for a load balancer.

        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)

        Returns:
            List of forwarding rules
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.list_load_balancer_forwarding_rules(actual_id)

    @mcp.tool
    async def create_forwarding_rule(
        load_balancer_id: str,
        frontend_protocol: str,
        frontend_port: int,
        backend_protocol: str,
        backend_port: int,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Create a forwarding rule for a load balancer.

        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            frontend_protocol: Frontend protocol ('http', 'https', 'tcp')
            frontend_port: Frontend port number
            backend_protocol: Backend protocol ('http', 'https', 'tcp')
            backend_port: Backend port number
            ctx: FastMCP context for resource change notifications

        Returns:
            Created forwarding rule information
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        result = await vultr_client.create_load_balancer_forwarding_rule(
            load_balancer_id=actual_id,
            frontend_protocol=frontend_protocol,
            frontend_port=frontend_port,
            backend_protocol=backend_protocol,
            backend_port=backend_port,
        )

        # Notify clients that forwarding rules for this load balancer have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="create_forwarding_rule", load_balancer_id=actual_id
            )

        return result

    @mcp.tool
    async def get_forwarding_rule(
        load_balancer_id: str, forwarding_rule_id: str
    ) -> dict[str, Any]:
        """Get details of a specific forwarding rule.

        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            forwarding_rule_id: The forwarding rule ID

        Returns:
            Forwarding rule details
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.get_load_balancer_forwarding_rule(
            actual_id, forwarding_rule_id
        )

    @mcp.tool
    async def delete_forwarding_rule(
        load_balancer_id: str, forwarding_rule_id: str, ctx: Context
    ) -> dict[str, str]:
        """Delete a forwarding rule from a load balancer.

        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            forwarding_rule_id: The forwarding rule ID
            ctx: FastMCP context for resource change notifications

        Returns:
            Status message confirming deletion
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        await vultr_client.delete_load_balancer_forwarding_rule(
            actual_id, forwarding_rule_id
        )

        # Notify clients that forwarding rules for this load balancer have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="delete_forwarding_rule", load_balancer_id=actual_id
            )

        return {
            "status": "success",
            "message": f"Forwarding rule {forwarding_rule_id} deleted successfully",
        }

    # Firewall Rules Management
    @mcp.resource("load-balancers://{load_balancer_id}/firewall-rules")
    async def list_firewall_rules_resource(
        load_balancer_id: str,
    ) -> list[dict[str, Any]]:
        """List firewall rules for a load balancer.

        Args:
            load_balancer_id: The load balancer ID or label
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.list_load_balancer_firewall_rules(actual_id)

    @mcp.tool
    async def list_firewall_rules(
        load_balancer_id: str,
    ) -> list[dict[str, Any]]:
        """List firewall rules for a load balancer.

        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)

        Returns:
            List of firewall rules
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.list_load_balancer_firewall_rules(actual_id)

    @mcp.tool
    async def get_firewall_rule(
        load_balancer_id: str, firewall_rule_id: str
    ) -> dict[str, Any]:
        """Get details of a specific firewall rule.

        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            firewall_rule_id: The firewall rule ID

        Returns:
            Firewall rule details
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.get_load_balancer_firewall_rule(
            actual_id, firewall_rule_id
        )

    # Helper tools for load balancer configuration
    @mcp.tool
    async def configure_basic_web_lb(
        region: str,
        label: str,
        backend_instances: list[str],
        enable_ssl: bool = True,
        ssl_redirect: bool = True,
        domain_zone: str | None = None,
        domain_sub: str | None = None,
    ) -> dict[str, Any]:
        """Configure a basic web load balancer with standard HTTP/HTTPS rules.

        Args:
            region: Region code (e.g., 'ewr', 'lax')
            label: Label for the load balancer
            backend_instances: List of instance IDs to attach
            enable_ssl: Enable SSL/Auto SSL
            ssl_redirect: Redirect HTTP to HTTPS
            domain_zone: Domain zone for Auto SSL
            domain_sub: Subdomain for Auto SSL

        Returns:
            Created and configured load balancer information
        """
        return await lb_analyzer.configure_basic_web_lb(
            region=region,
            label=label,
            backend_instances=backend_instances,
            enable_ssl=enable_ssl,
            ssl_redirect=ssl_redirect,
            domain_zone=domain_zone,
            domain_sub=domain_sub,
        )

    @mcp.tool
    async def get_health_status(load_balancer_id: str) -> dict[str, Any]:
        """Get health status and monitoring information for a load balancer.

        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)

        Returns:
            Health status and configuration information
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await lb_analyzer.get_health_status(actual_id)

    @mcp.tool
    async def get_configuration_summary(load_balancer_id: str) -> dict[str, Any]:
        """Get a comprehensive configuration summary for a load balancer.

        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)

        Returns:
            Detailed configuration summary
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await lb_analyzer.get_configuration_summary(actual_id)

    return mcp
