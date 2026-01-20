"""
Vultr Kubernetes FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr Kubernetes Engine (VKE) clusters.
"""

from typing import Any

from fastmcp import Context, FastMCP

from .kubernetes_analyzer import KubernetesAnalyzer
from .notification_manager import NotificationManager
from .server import VultrResourceNotFoundError


def create_kubernetes_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr Kubernetes cluster management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with Kubernetes management tools
    """
    mcp = FastMCP(name="vultr-kubernetes")
    kubernetes_analyzer = KubernetesAnalyzer(vultr_client)

    # Helper function to check if string is UUID format
    def is_uuid_format(value: str) -> bool:
        """Check if a string looks like a UUID."""
        import re

        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))

    # Helper function to get cluster ID from label or existing ID
    async def get_cluster_id(identifier: str) -> str:
        """
        Get the Kubernetes cluster ID from label or existing ID.

        Args:
            identifier: Cluster label or UUID

        Returns:
            The cluster ID (UUID)

        Raises:
            ValueError: If the cluster is not found
        """
        if is_uuid_format(identifier):
            return identifier

        clusters = await vultr_client.list_kubernetes_clusters()
        for cluster in clusters:
            if cluster.get("label") == identifier:
                return cluster["id"]

        raise ValueError(f"Kubernetes cluster '{identifier}' not found")

    # Helper function to get node pool ID from label within a cluster
    async def get_nodepool_id(
        cluster_identifier: str, nodepool_identifier: str
    ) -> tuple[str, str]:
        """
        Get the node pool ID from label or existing ID.

        Args:
            cluster_identifier: Cluster label or UUID
            nodepool_identifier: Node pool label or UUID

        Returns:
            Tuple of (cluster_id, nodepool_id)

        Raises:
            ValueError: If the cluster or node pool is not found
        """
        cluster_id = await get_cluster_id(cluster_identifier)

        if is_uuid_format(nodepool_identifier):
            return cluster_id, nodepool_identifier

        nodepools = await vultr_client.list_kubernetes_node_pools(cluster_id)
        for nodepool in nodepools:
            if nodepool.get("label") == nodepool_identifier:
                return cluster_id, nodepool["id"]

        raise ValueError(
            f"Node pool '{nodepool_identifier}' not found in cluster '{cluster_identifier}'"
        )

    # Helper function to get node ID from label within a node pool
    async def get_node_id(
        cluster_identifier: str, nodepool_identifier: str, node_identifier: str
    ) -> tuple[str, str, str]:
        """
        Get the node ID from label or existing ID.

        Args:
            cluster_identifier: Cluster label or UUID
            nodepool_identifier: Node pool label or UUID
            node_identifier: Node label or UUID

        Returns:
            Tuple of (cluster_id, nodepool_id, node_id)

        Raises:
            ValueError: If the cluster, node pool, or node is not found
        """
        cluster_id, nodepool_id = await get_nodepool_id(
            cluster_identifier, nodepool_identifier
        )

        if is_uuid_format(node_identifier):
            return cluster_id, nodepool_id, node_identifier

        nodes = await vultr_client.list_kubernetes_nodes(cluster_id, nodepool_id)
        for node in nodes:
            if node.get("label") == node_identifier:
                return cluster_id, nodepool_id, node["id"]

        raise ValueError(
            f"Node '{node_identifier}' not found in node pool '{nodepool_identifier}'"
        )

    # Kubernetes cluster resources
    @mcp.resource("kubernetes://clusters")
    async def list_clusters_resource() -> list[dict[str, Any]]:
        """List all Kubernetes clusters in your Vultr account."""
        try:
            return await vultr_client.list_kubernetes_clusters()
        except Exception:
            # If the API returns an error when no clusters exist, return empty list
            return []

    @mcp.resource("kubernetes://cluster/{cluster_id}")
    async def get_cluster_resource(cluster_id: str) -> dict[str, Any]:
        """Get information about a specific Kubernetes cluster.

        Args:
            cluster_id: The cluster ID or label
        """
        actual_id = await get_cluster_id(cluster_id)
        return await vultr_client.get_kubernetes_cluster(actual_id)

    @mcp.resource("kubernetes://cluster/{cluster_id}/node-pools")
    async def list_node_pools_resource(cluster_id: str) -> list[dict[str, Any]]:
        """List all node pools for a specific cluster.

        Args:
            cluster_id: The cluster ID or label
        """
        actual_id = await get_cluster_id(cluster_id)
        return await vultr_client.list_kubernetes_node_pools(actual_id)

    # Kubernetes cluster tools
    @mcp.tool()
    async def list_kubernetes_clusters() -> list[dict[str, Any]]:
        """
        List all Kubernetes clusters in your Vultr account.

        Returns:
            List of cluster objects with details including:
            - id: Cluster ID
            - label: Cluster label
            - version: Kubernetes version
            - region: Region code
            - status: Cluster status
            - node_pools: List of node pools
            - date_created: Creation date
            - cluster_subnet: Cluster subnet
            - service_subnet: Service subnet
            - ip: Cluster IP address
        """
        return await vultr_client.list_kubernetes_clusters()

    @mcp.tool()
    async def get_kubernetes_cluster(cluster_identifier: str) -> dict[str, Any]:
        """
        Get detailed information about a specific Kubernetes cluster.
        Smart identifier resolution: use cluster label or UUID.

        Args:
            cluster_identifier: The cluster label or ID (e.g., "production-cluster" or UUID)

        Returns:
            Detailed cluster information including configuration and status
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        return await vultr_client.get_kubernetes_cluster(cluster_id)

    @mcp.tool()
    async def create_kubernetes_cluster(
        label: str,
        region: str,
        version: str,
        node_pools: list[dict[str, Any]],
        ctx: Context | None = None,
        enable_firewall: bool = False,
        ha_controlplanes: bool = False,
    ) -> dict[str, Any]:
        """
        Create a new Kubernetes cluster.

        Args:
            label: Label for the cluster
            region: Region code (e.g., 'ewr', 'lax')
            version: Kubernetes version (use get_kubernetes_versions for available options)
            node_pools: List of node pool configurations, each containing:
                - node_quantity: Number of nodes (minimum 1, recommended 3+)
                - plan: Plan ID (e.g., 'vc2-2c-4gb')
                - label: Node pool label
                - tag: Optional tag
                - auto_scaler: Optional auto-scaling configuration
                - min_nodes: Minimum nodes for auto-scaling
                - max_nodes: Maximum nodes for auto-scaling
            ctx: FastMCP context for resource change notifications
            enable_firewall: Enable firewall for cluster
            ha_controlplanes: Enable high availability control planes

        Returns:
            Created cluster information
        """
        result = await vultr_client.create_kubernetes_cluster(
            label=label,
            region=region,
            version=version,
            node_pools=node_pools,
            enable_firewall=enable_firewall,
            ha_controlplanes=ha_controlplanes,
        )

        # Notify clients that Kubernetes cluster list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx,
                operation="create_kubernetes_cluster",
                cluster_id=result.get("id"),
            )

        return result

    @mcp.tool()
    async def update_kubernetes_cluster(
        cluster_identifier: str, ctx: Context | None = None, label: str | None = None
    ) -> dict[str, str]:
        """
        Update a Kubernetes cluster configuration.
        Smart identifier resolution: use cluster label or UUID.

        Args:
            cluster_identifier: The cluster label or ID
            ctx: FastMCP context for resource change notifications
            label: New label for the cluster

        Returns:
            Update status message
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        await vultr_client.update_kubernetes_cluster(cluster_id, label=label)

        # Notify clients that Kubernetes clusters list and specific cluster have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="update_kubernetes_cluster", cluster_id=cluster_id
            )

        return {
            "status": "success",
            "message": f"Cluster {cluster_identifier} updated successfully",
        }

    @mcp.tool()
    async def delete_kubernetes_cluster(
        cluster_identifier: str, ctx: Context
    ) -> dict[str, str]:
        """
        Delete a Kubernetes cluster.
        Smart identifier resolution: use cluster label or UUID.

        Args:
            cluster_identifier: The cluster label or ID to delete
            ctx: FastMCP context for resource change notifications

        Returns:
            Deletion status message
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        await vultr_client.delete_kubernetes_cluster(cluster_id)

        # Notify clients that Kubernetes clusters list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="delete_kubernetes_cluster", cluster_id=cluster_id
            )

        return {
            "status": "success",
            "message": f"Cluster {cluster_identifier} deleted successfully",
        }

    @mcp.tool()
    async def delete_kubernetes_cluster_with_resources(
        cluster_identifier: str, ctx: Context
    ) -> dict[str, str]:
        """
        Delete a Kubernetes cluster and all related resources.
        Smart identifier resolution: use cluster label or UUID.

        Args:
            cluster_identifier: The cluster label or ID to delete
            ctx: FastMCP context for resource change notifications

        Returns:
            Deletion status message
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        await vultr_client.delete_kubernetes_cluster_with_resources(cluster_id)

        # Notify clients that Kubernetes clusters list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="delete_kubernetes_cluster", cluster_id=cluster_id
            )

        return {
            "status": "success",
            "message": f"Cluster {cluster_identifier} and all related resources deleted successfully",
        }

    @mcp.tool()
    async def get_kubernetes_cluster_config(cluster_identifier: str) -> dict[str, Any]:
        """
        Get the kubeconfig for a Kubernetes cluster.
        Smart identifier resolution: use cluster label or UUID.

        Args:
            cluster_identifier: The cluster label or ID

        Returns:
            Kubeconfig content for cluster access
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        return await vultr_client.get_kubernetes_cluster_config(cluster_id)

    @mcp.tool()
    async def get_kubernetes_cluster_resources(
        cluster_identifier: str,
    ) -> dict[str, Any]:
        """
        Get resource usage information for a Kubernetes cluster.
        Smart identifier resolution: use cluster label or UUID.

        Args:
            cluster_identifier: The cluster label or ID

        Returns:
            Cluster resource usage including CPU, memory, and storage
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        return await vultr_client.get_kubernetes_cluster_resources(cluster_id)

    @mcp.tool()
    async def get_kubernetes_available_upgrades(cluster_identifier: str) -> list[str]:
        """
        Get available Kubernetes version upgrades for a cluster.
        Smart identifier resolution: use cluster label or UUID.

        Args:
            cluster_identifier: The cluster label or ID

        Returns:
            List of available Kubernetes versions for upgrade
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        return await vultr_client.get_kubernetes_available_upgrades(cluster_id)

    @mcp.tool()
    async def upgrade_kubernetes_cluster(
        cluster_identifier: str, upgrade_version: str
    ) -> dict[str, str]:
        """
        Start a Kubernetes cluster upgrade.
        Smart identifier resolution: use cluster label or UUID.

        Args:
            cluster_identifier: The cluster label or ID
            upgrade_version: Target Kubernetes version (use get_kubernetes_available_upgrades)

        Returns:
            Upgrade initiation status
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        await vultr_client.upgrade_kubernetes_cluster(cluster_id, upgrade_version)
        return {
            "status": "success",
            "message": f"Cluster {cluster_identifier} upgrade to {upgrade_version} initiated",
        }

    # Node pool management tools
    @mcp.tool()
    async def list_kubernetes_node_pools(
        cluster_identifier: str,
    ) -> list[dict[str, Any]]:
        """
        List all node pools for a Kubernetes cluster.
        Smart identifier resolution: use cluster label or UUID.

        Args:
            cluster_identifier: The cluster label or ID

        Returns:
            List of node pools with configuration and status
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        return await vultr_client.list_kubernetes_node_pools(cluster_id)

    @mcp.tool()
    async def get_kubernetes_node_pool(
        cluster_identifier: str, nodepool_identifier: str
    ) -> dict[str, Any]:
        """
        Get detailed information about a specific node pool.
        Smart identifier resolution: use cluster/node pool labels or UUIDs.

        Args:
            cluster_identifier: The cluster label or ID
            nodepool_identifier: The node pool label or ID

        Returns:
            Detailed node pool information
        """
        cluster_id, nodepool_id = await get_nodepool_id(
            cluster_identifier, nodepool_identifier
        )
        try:
            return await vultr_client.get_kubernetes_node_pool(cluster_id, nodepool_id)
        except VultrResourceNotFoundError:
            nodepools = await vultr_client.list_kubernetes_node_pools(cluster_id)
            if nodepools:
                pool_list = ", ".join(f"{p.get('label', 'unnamed')} ({p.get('id')})" for p in nodepools)
                raise ValueError(
                    f"Node pool '{nodepool_identifier}' not found in cluster '{cluster_identifier}'. "
                    f"Available node pools: {pool_list}"
                ) from None
            else:
                raise ValueError(
                    f"Node pool '{nodepool_identifier}' not found. "
                    f"Cluster '{cluster_identifier}' has no node pools."
                ) from None

    @mcp.tool()
    async def create_kubernetes_node_pool(
        cluster_identifier: str,
        node_quantity: int,
        plan: str,
        label: str,
        ctx: Context | None = None,
        tag: str | None = None,
        auto_scaler: bool | None = None,
        min_nodes: int | None = None,
        max_nodes: int | None = None,
        labels: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new node pool in a Kubernetes cluster.
        Smart identifier resolution: use cluster label or UUID.

        Args:
            cluster_identifier: The cluster label or ID
            node_quantity: Number of nodes (minimum 1, recommended 3+)
            plan: Plan ID (e.g., 'vc2-2c-4gb')
            label: Node pool label (must be unique within cluster)
            ctx: FastMCP context for resource change notifications
            tag: Optional tag for the node pool
            auto_scaler: Enable auto-scaling for this node pool
            min_nodes: Minimum nodes for auto-scaling
            max_nodes: Maximum nodes for auto-scaling
            labels: Map of key/value pairs to apply to all nodes

        Returns:
            Created node pool information
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        result = await vultr_client.create_kubernetes_node_pool(
            cluster_id=cluster_id,
            node_quantity=node_quantity,
            plan=plan,
            label=label,
            tag=tag,
            auto_scaler=auto_scaler,
            min_nodes=min_nodes,
            max_nodes=max_nodes,
            labels=labels,
        )

        # Notify clients that node pools for this cluster have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="create_node_pool", cluster_id=cluster_id
            )

        return result

    @mcp.tool()
    async def update_kubernetes_node_pool(
        cluster_identifier: str,
        nodepool_identifier: str,
        ctx: Context | None = None,
        node_quantity: int | None = None,
        tag: str | None = None,
        auto_scaler: bool | None = None,
        min_nodes: int | None = None,
        max_nodes: int | None = None,
        labels: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """
        Update a node pool configuration.
        Smart identifier resolution: use cluster/node pool labels or UUIDs.

        Args:
            cluster_identifier: The cluster label or ID
            nodepool_identifier: The node pool label or ID
            ctx: FastMCP context for resource change notifications
            node_quantity: New number of nodes
            tag: New tag for the node pool
            auto_scaler: Enable/disable auto-scaling
            min_nodes: Minimum nodes for auto-scaling
            max_nodes: Maximum nodes for auto-scaling
            labels: New map of key/value pairs for nodes

        Returns:
            Update status message
        """
        cluster_id, nodepool_id = await get_nodepool_id(
            cluster_identifier, nodepool_identifier
        )
        await vultr_client.update_kubernetes_node_pool(
            cluster_id,
            nodepool_id,
            node_quantity=node_quantity,
            tag=tag,
            auto_scaler=auto_scaler,
            min_nodes=min_nodes,
            max_nodes=max_nodes,
            labels=labels,
        )

        # Notify clients that node pools for this cluster have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="update_node_pool", cluster_id=cluster_id
            )

        return {
            "status": "success",
            "message": f"Node pool {nodepool_identifier} updated successfully",
        }

    @mcp.tool()
    async def delete_kubernetes_node_pool(
        cluster_identifier: str, nodepool_identifier: str, ctx: Context
    ) -> dict[str, str]:
        """
        Delete a node pool from a Kubernetes cluster.
        Smart identifier resolution: use cluster/node pool labels or UUIDs.

        Args:
            cluster_identifier: The cluster label or ID
            nodepool_identifier: The node pool label or ID to delete
            ctx: FastMCP context for resource change notifications

        Returns:
            Deletion status message
        """
        cluster_id, nodepool_id = await get_nodepool_id(
            cluster_identifier, nodepool_identifier
        )
        try:
            await vultr_client.delete_kubernetes_node_pool(cluster_id, nodepool_id)
        except VultrResourceNotFoundError:
            nodepools = await vultr_client.list_kubernetes_node_pools(cluster_id)
            if nodepools:
                pool_list = ", ".join(f"{p.get('label', 'unnamed')} ({p.get('id')})" for p in nodepools)
                raise ValueError(
                    f"Node pool '{nodepool_identifier}' not found in cluster '{cluster_identifier}'. "
                    f"Available node pools: {pool_list}"
                ) from None
            else:
                raise ValueError(
                    f"Node pool '{nodepool_identifier}' not found. "
                    f"Cluster '{cluster_identifier}' has no node pools."
                ) from None

        # Notify clients that node pools for this cluster have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="delete_node_pool", cluster_id=cluster_id
            )

        return {
            "status": "success",
            "message": f"Node pool {nodepool_identifier} deleted successfully",
        }

    # Node management tools
    @mcp.tool()
    async def list_kubernetes_nodes(
        cluster_identifier: str, nodepool_identifier: str
    ) -> list[dict[str, Any]]:
        """
        List all nodes in a specific node pool.
        Smart identifier resolution: use cluster/node pool labels or UUIDs.

        Args:
            cluster_identifier: The cluster label or ID
            nodepool_identifier: The node pool label or ID

        Returns:
            List of nodes with status and configuration
        """
        cluster_id, nodepool_id = await get_nodepool_id(
            cluster_identifier, nodepool_identifier
        )
        return await vultr_client.list_kubernetes_nodes(cluster_id, nodepool_id)

    @mcp.tool()
    async def get_kubernetes_node(
        cluster_identifier: str, nodepool_identifier: str, node_identifier: str
    ) -> dict[str, Any]:
        """
        Get detailed information about a specific node.
        Smart identifier resolution: use cluster/node pool/node labels or UUIDs.

        Args:
            cluster_identifier: The cluster label or ID
            nodepool_identifier: The node pool label or ID
            node_identifier: The node label or ID

        Returns:
            Detailed node information
        """
        cluster_id, nodepool_id, node_id = await get_node_id(
            cluster_identifier, nodepool_identifier, node_identifier
        )
        try:
            return await vultr_client.get_kubernetes_node(cluster_id, nodepool_id, node_id)
        except VultrResourceNotFoundError:
            nodes = await vultr_client.list_kubernetes_nodes(cluster_id, nodepool_id)
            if nodes:
                node_list = ", ".join(f"{n.get('label', 'unnamed')} ({n.get('id')})" for n in nodes)
                raise ValueError(
                    f"Node '{node_identifier}' not found in node pool '{nodepool_identifier}'. "
                    f"Available nodes: {node_list}"
                ) from None
            else:
                raise ValueError(
                    f"Node '{node_identifier}' not found. "
                    f"Node pool '{nodepool_identifier}' has no nodes."
                ) from None

    @mcp.tool()
    async def delete_kubernetes_node(
        cluster_identifier: str,
        nodepool_identifier: str,
        node_identifier: str,
        ctx: Context | None = None,
    ) -> dict[str, str]:
        """
        Delete a specific node from a node pool.
        Smart identifier resolution: use cluster/node pool/node labels or UUIDs.

        Args:
            cluster_identifier: The cluster label or ID
            nodepool_identifier: The node pool label or ID
            node_identifier: The node label or ID to delete
            ctx: FastMCP context for resource change notifications

        Returns:
            Deletion status message
        """
        cluster_id, nodepool_id, node_id = await get_node_id(
            cluster_identifier, nodepool_identifier, node_identifier
        )
        try:
            await vultr_client.delete_kubernetes_node(cluster_id, nodepool_id, node_id)
        except VultrResourceNotFoundError:
            nodes = await vultr_client.list_kubernetes_nodes(cluster_id, nodepool_id)
            if nodes:
                node_list = ", ".join(f"{n.get('label', 'unnamed')} ({n.get('id')})" for n in nodes)
                raise ValueError(
                    f"Node '{node_identifier}' not found in node pool '{nodepool_identifier}'. "
                    f"Available nodes: {node_list}"
                ) from None
            else:
                raise ValueError(
                    f"Node '{node_identifier}' not found. "
                    f"Node pool '{nodepool_identifier}' has no nodes."
                ) from None

        # Notify clients that node pools for this cluster have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="delete_kubernetes_node", cluster_id=cluster_id
            )

        return {
            "status": "success",
            "message": f"Node {node_identifier} deleted successfully",
        }

    @mcp.tool()
    async def recycle_kubernetes_node(
        cluster_identifier: str, nodepool_identifier: str, node_identifier: str
    ) -> dict[str, str]:
        """
        Recycle (restart) a specific node.
        Smart identifier resolution: use cluster/node pool/node labels or UUIDs.

        Args:
            cluster_identifier: The cluster label or ID
            nodepool_identifier: The node pool label or ID
            node_identifier: The node label or ID to recycle

        Returns:
            Recycle operation status
        """
        cluster_id, nodepool_id, node_id = await get_node_id(
            cluster_identifier, nodepool_identifier, node_identifier
        )
        try:
            await vultr_client.recycle_kubernetes_node(cluster_id, nodepool_id, node_id)
        except VultrResourceNotFoundError:
            nodes = await vultr_client.list_kubernetes_nodes(cluster_id, nodepool_id)
            if nodes:
                node_list = ", ".join(f"{n.get('label', 'unnamed')} ({n.get('id')})" for n in nodes)
                raise ValueError(
                    f"Node '{node_identifier}' not found in node pool '{nodepool_identifier}'. "
                    f"Available nodes: {node_list}"
                ) from None
            else:
                raise ValueError(
                    f"Node '{node_identifier}' not found. "
                    f"Node pool '{nodepool_identifier}' has no nodes."
                ) from None
        return {
            "status": "success",
            "message": f"Node {node_identifier} recycling initiated",
        }

    # Utility and information tools
    @mcp.tool()
    async def get_kubernetes_versions() -> list[str]:
        """
        Get list of available Kubernetes versions.

        Returns:
            List of available Kubernetes versions for new clusters
        """
        return await vultr_client.get_kubernetes_versions()

    @mcp.tool()
    async def get_kubernetes_cluster_status(cluster_identifier: str) -> dict[str, Any]:
        """
        Get comprehensive status information for a Kubernetes cluster.
        Smart identifier resolution: use cluster label or UUID.

        Args:
            cluster_identifier: The cluster label or ID

        Returns:
            Comprehensive cluster status including health, resources, and node status
        """
        return await kubernetes_analyzer.get_cluster_status(cluster_identifier)

    @mcp.tool()
    async def scale_kubernetes_node_pool(
        cluster_identifier: str, nodepool_identifier: str, target_node_count: int
    ) -> dict[str, Any]:
        """
        Scale a node pool to the target number of nodes.
        Smart identifier resolution: use cluster/node pool labels or UUIDs.

        Args:
            cluster_identifier: The cluster label or ID
            nodepool_identifier: The node pool label or ID
            target_node_count: Target number of nodes (minimum 1)

        Returns:
            Scaling operation details and status
        """
        if target_node_count < 1:
            raise ValueError("Target node count must be at least 1")

        cluster_id, nodepool_id = await get_nodepool_id(
            cluster_identifier, nodepool_identifier
        )

        # Get current node pool info
        current_pool = await vultr_client.get_kubernetes_node_pool(
            cluster_id, nodepool_id
        )
        current_count = current_pool.get("node_quantity", 0)

        if current_count == target_node_count:
            return {
                "status": "no_change",
                "message": f"Node pool {nodepool_identifier} already has {target_node_count} nodes",
                "current_nodes": current_count,
                "target_nodes": target_node_count,
            }

        # Update the node pool with new count
        await vultr_client.update_kubernetes_node_pool(
            cluster_id, nodepool_id, node_quantity=target_node_count
        )

        scaling_direction = "up" if target_node_count > current_count else "down"

        return {
            "status": "scaling_initiated",
            "message": f"Scaling node pool {nodepool_identifier} {scaling_direction} from {current_count} to {target_node_count} nodes",
            "current_nodes": current_count,
            "target_nodes": target_node_count,
            "scaling_direction": scaling_direction,
        }

    @mcp.tool()
    async def analyze_kubernetes_cluster_costs(
        cluster_identifier: str,
    ) -> dict[str, Any]:
        """
        Analyze the estimated costs of a Kubernetes cluster.
        Smart identifier resolution: use cluster label or UUID.

        Args:
            cluster_identifier: The cluster label or ID

        Returns:
            Cost analysis including per-node costs and total estimated monthly cost
        """
        return await kubernetes_analyzer.analyze_cluster_costs(cluster_identifier)

    @mcp.tool()
    async def setup_kubernetes_cluster_for_workload(
        label: str,
        region: str,
        ctx: Context | None = None,
        workload_type: str = "web",
        environment: str = "production",
        auto_scaling: bool = True,
    ) -> dict[str, Any]:
        """
        Set up a Kubernetes cluster optimized for specific workload types.

        Args:
            label: Label for the new cluster
            region: Region code (e.g., 'ewr', 'lax')
            ctx: FastMCP context for resource change notifications
            workload_type: Type of workload ('web', 'api', 'data', 'development')
            environment: Environment type ('production', 'staging', 'development')
            auto_scaling: Enable auto-scaling for node pools

        Returns:
            Created cluster information with setup recommendations
        """
        result = await kubernetes_analyzer.setup_cluster_for_workload(
            label, region, workload_type, environment, auto_scaling
        )

        # Notify clients that Kubernetes cluster list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx,
                operation="create_kubernetes_cluster",
                cluster_id=result.get("id"),
            )

        return result

    return mcp
