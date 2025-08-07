"""
Vultr Kubernetes FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr Kubernetes Engine (VKE) clusters.
"""

from typing import List, Dict, Any, Optional
from fastmcp import FastMCP


def create_kubernetes_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr Kubernetes cluster management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with Kubernetes management tools
    """
    mcp = FastMCP(name="vultr-kubernetes")
    
    # Helper function to check if string is UUID format
    def is_uuid_format(value: str) -> bool:
        """Check if a string looks like a UUID."""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
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
    async def get_nodepool_id(cluster_identifier: str, nodepool_identifier: str) -> tuple[str, str]:
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
        
        raise ValueError(f"Node pool '{nodepool_identifier}' not found in cluster '{cluster_identifier}'")
    
    # Helper function to get node ID from label within a node pool
    async def get_node_id(cluster_identifier: str, nodepool_identifier: str, node_identifier: str) -> tuple[str, str, str]:
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
        cluster_id, nodepool_id = await get_nodepool_id(cluster_identifier, nodepool_identifier)
        
        if is_uuid_format(node_identifier):
            return cluster_id, nodepool_id, node_identifier
        
        nodes = await vultr_client.list_kubernetes_nodes(cluster_id, nodepool_id)
        for node in nodes:
            if node.get("label") == node_identifier:
                return cluster_id, nodepool_id, node["id"]
        
        raise ValueError(f"Node '{node_identifier}' not found in node pool '{nodepool_identifier}'")
    
    # Kubernetes cluster resources
    @mcp.resource("kubernetes://clusters")
    async def list_clusters_resource() -> List[Dict[str, Any]]:
        """List all Kubernetes clusters in your Vultr account."""
        return await vultr_client.list_kubernetes_clusters()
    
    @mcp.resource("kubernetes://cluster/{cluster_id}")
    async def get_cluster_resource(cluster_id: str) -> Dict[str, Any]:
        """Get information about a specific Kubernetes cluster.
        
        Args:
            cluster_id: The cluster ID or label
        """
        actual_id = await get_cluster_id(cluster_id)
        return await vultr_client.get_kubernetes_cluster(actual_id)
    
    @mcp.resource("kubernetes://cluster/{cluster_id}/node-pools")
    async def list_node_pools_resource(cluster_id: str) -> List[Dict[str, Any]]:
        """List all node pools for a specific cluster.
        
        Args:
            cluster_id: The cluster ID or label
        """
        actual_id = await get_cluster_id(cluster_id)
        return await vultr_client.list_kubernetes_node_pools(actual_id)
    
    # Kubernetes cluster tools
    @mcp.tool()
    async def list_kubernetes_clusters() -> List[Dict[str, Any]]:
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
    async def get_kubernetes_cluster(cluster_identifier: str) -> Dict[str, Any]:
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
        node_pools: List[Dict[str, Any]],
        enable_firewall: bool = False,
        ha_controlplanes: bool = False
    ) -> Dict[str, Any]:
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
            enable_firewall: Enable firewall for cluster
            ha_controlplanes: Enable high availability control planes
            
        Returns:
            Created cluster information
        """
        return await vultr_client.create_kubernetes_cluster(
            label=label,
            region=region,
            version=version,
            node_pools=node_pools,
            enable_firewall=enable_firewall,
            ha_controlplanes=ha_controlplanes
        )
    
    @mcp.tool()
    async def update_kubernetes_cluster(
        cluster_identifier: str,
        label: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Update a Kubernetes cluster configuration.
        Smart identifier resolution: use cluster label or UUID.
        
        Args:
            cluster_identifier: The cluster label or ID
            label: New label for the cluster
            
        Returns:
            Update status message
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        await vultr_client.update_kubernetes_cluster(cluster_id, label=label)
        return {"status": "success", "message": f"Cluster {cluster_identifier} updated successfully"}
    
    @mcp.tool()
    async def delete_kubernetes_cluster(cluster_identifier: str) -> Dict[str, str]:
        """
        Delete a Kubernetes cluster.
        Smart identifier resolution: use cluster label or UUID.
        
        Args:
            cluster_identifier: The cluster label or ID to delete
            
        Returns:
            Deletion status message
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        await vultr_client.delete_kubernetes_cluster(cluster_id)
        return {"status": "success", "message": f"Cluster {cluster_identifier} deleted successfully"}
    
    @mcp.tool()
    async def delete_kubernetes_cluster_with_resources(cluster_identifier: str) -> Dict[str, str]:
        """
        Delete a Kubernetes cluster and all related resources.
        Smart identifier resolution: use cluster label or UUID.
        
        Args:
            cluster_identifier: The cluster label or ID to delete
            
        Returns:
            Deletion status message
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        await vultr_client.delete_kubernetes_cluster_with_resources(cluster_id)
        return {"status": "success", "message": f"Cluster {cluster_identifier} and all related resources deleted successfully"}
    
    @mcp.tool()
    async def get_kubernetes_cluster_config(cluster_identifier: str) -> Dict[str, Any]:
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
    async def get_kubernetes_cluster_resources(cluster_identifier: str) -> Dict[str, Any]:
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
    async def get_kubernetes_available_upgrades(cluster_identifier: str) -> List[str]:
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
        cluster_identifier: str,
        upgrade_version: str
    ) -> Dict[str, str]:
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
        return {"status": "success", "message": f"Cluster {cluster_identifier} upgrade to {upgrade_version} initiated"}
    
    # Node pool management tools
    @mcp.tool()
    async def list_kubernetes_node_pools(cluster_identifier: str) -> List[Dict[str, Any]]:
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
        cluster_identifier: str,
        nodepool_identifier: str
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific node pool.
        Smart identifier resolution: use cluster/node pool labels or UUIDs.
        
        Args:
            cluster_identifier: The cluster label or ID
            nodepool_identifier: The node pool label or ID
            
        Returns:
            Detailed node pool information
        """
        cluster_id, nodepool_id = await get_nodepool_id(cluster_identifier, nodepool_identifier)
        return await vultr_client.get_kubernetes_node_pool(cluster_id, nodepool_id)
    
    @mcp.tool()
    async def create_kubernetes_node_pool(
        cluster_identifier: str,
        node_quantity: int,
        plan: str,
        label: str,
        tag: Optional[str] = None,
        auto_scaler: Optional[bool] = None,
        min_nodes: Optional[int] = None,
        max_nodes: Optional[int] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new node pool in a Kubernetes cluster.
        Smart identifier resolution: use cluster label or UUID.
        
        Args:
            cluster_identifier: The cluster label or ID
            node_quantity: Number of nodes (minimum 1, recommended 3+)
            plan: Plan ID (e.g., 'vc2-2c-4gb')
            label: Node pool label (must be unique within cluster)
            tag: Optional tag for the node pool
            auto_scaler: Enable auto-scaling for this node pool
            min_nodes: Minimum nodes for auto-scaling
            max_nodes: Maximum nodes for auto-scaling
            labels: Map of key/value pairs to apply to all nodes
            
        Returns:
            Created node pool information
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        return await vultr_client.create_kubernetes_node_pool(
            cluster_id=cluster_id,
            node_quantity=node_quantity,
            plan=plan,
            label=label,
            tag=tag,
            auto_scaler=auto_scaler,
            min_nodes=min_nodes,
            max_nodes=max_nodes,
            labels=labels
        )
    
    @mcp.tool()
    async def update_kubernetes_node_pool(
        cluster_identifier: str,
        nodepool_identifier: str,
        node_quantity: Optional[int] = None,
        tag: Optional[str] = None,
        auto_scaler: Optional[bool] = None,
        min_nodes: Optional[int] = None,
        max_nodes: Optional[int] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Update a node pool configuration.
        Smart identifier resolution: use cluster/node pool labels or UUIDs.
        
        Args:
            cluster_identifier: The cluster label or ID
            nodepool_identifier: The node pool label or ID
            node_quantity: New number of nodes
            tag: New tag for the node pool
            auto_scaler: Enable/disable auto-scaling
            min_nodes: Minimum nodes for auto-scaling
            max_nodes: Maximum nodes for auto-scaling
            labels: New map of key/value pairs for nodes
            
        Returns:
            Update status message
        """
        cluster_id, nodepool_id = await get_nodepool_id(cluster_identifier, nodepool_identifier)
        await vultr_client.update_kubernetes_node_pool(
            cluster_id,
            nodepool_id,
            node_quantity=node_quantity,
            tag=tag,
            auto_scaler=auto_scaler,
            min_nodes=min_nodes,
            max_nodes=max_nodes,
            labels=labels
        )
        return {"status": "success", "message": f"Node pool {nodepool_identifier} updated successfully"}
    
    @mcp.tool()
    async def delete_kubernetes_node_pool(
        cluster_identifier: str,
        nodepool_identifier: str
    ) -> Dict[str, str]:
        """
        Delete a node pool from a Kubernetes cluster.
        Smart identifier resolution: use cluster/node pool labels or UUIDs.
        
        Args:
            cluster_identifier: The cluster label or ID
            nodepool_identifier: The node pool label or ID to delete
            
        Returns:
            Deletion status message
        """
        cluster_id, nodepool_id = await get_nodepool_id(cluster_identifier, nodepool_identifier)
        await vultr_client.delete_kubernetes_node_pool(cluster_id, nodepool_id)
        return {"status": "success", "message": f"Node pool {nodepool_identifier} deleted successfully"}
    
    # Node management tools
    @mcp.tool()
    async def list_kubernetes_nodes(
        cluster_identifier: str,
        nodepool_identifier: str
    ) -> List[Dict[str, Any]]:
        """
        List all nodes in a specific node pool.
        Smart identifier resolution: use cluster/node pool labels or UUIDs.
        
        Args:
            cluster_identifier: The cluster label or ID
            nodepool_identifier: The node pool label or ID
            
        Returns:
            List of nodes with status and configuration
        """
        cluster_id, nodepool_id = await get_nodepool_id(cluster_identifier, nodepool_identifier)
        return await vultr_client.list_kubernetes_nodes(cluster_id, nodepool_id)
    
    @mcp.tool()
    async def get_kubernetes_node(
        cluster_identifier: str,
        nodepool_identifier: str,
        node_identifier: str
    ) -> Dict[str, Any]:
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
        cluster_id, nodepool_id, node_id = await get_node_id(cluster_identifier, nodepool_identifier, node_identifier)
        return await vultr_client.get_kubernetes_node(cluster_id, nodepool_id, node_id)
    
    @mcp.tool()
    async def delete_kubernetes_node(
        cluster_identifier: str,
        nodepool_identifier: str,
        node_identifier: str
    ) -> Dict[str, str]:
        """
        Delete a specific node from a node pool.
        Smart identifier resolution: use cluster/node pool/node labels or UUIDs.
        
        Args:
            cluster_identifier: The cluster label or ID
            nodepool_identifier: The node pool label or ID
            node_identifier: The node label or ID to delete
            
        Returns:
            Deletion status message
        """
        cluster_id, nodepool_id, node_id = await get_node_id(cluster_identifier, nodepool_identifier, node_identifier)
        await vultr_client.delete_kubernetes_node(cluster_id, nodepool_id, node_id)
        return {"status": "success", "message": f"Node {node_identifier} deleted successfully"}
    
    @mcp.tool()
    async def recycle_kubernetes_node(
        cluster_identifier: str,
        nodepool_identifier: str,
        node_identifier: str
    ) -> Dict[str, str]:
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
        cluster_id, nodepool_id, node_id = await get_node_id(cluster_identifier, nodepool_identifier, node_identifier)
        await vultr_client.recycle_kubernetes_node(cluster_id, nodepool_id, node_id)
        return {"status": "success", "message": f"Node {node_identifier} recycling initiated"}
    
    # Utility and information tools
    @mcp.tool()
    async def get_kubernetes_versions() -> List[str]:
        """
        Get list of available Kubernetes versions.
        
        Returns:
            List of available Kubernetes versions for new clusters
        """
        return await vultr_client.get_kubernetes_versions()
    
    @mcp.tool()
    async def get_kubernetes_cluster_status(cluster_identifier: str) -> Dict[str, Any]:
        """
        Get comprehensive status information for a Kubernetes cluster.
        Smart identifier resolution: use cluster label or UUID.
        
        Args:
            cluster_identifier: The cluster label or ID
            
        Returns:
            Comprehensive cluster status including health, resources, and node status
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        
        # Get cluster details
        cluster_info = await vultr_client.get_kubernetes_cluster(cluster_id)
        
        # Get resource usage
        try:
            resources = await vultr_client.get_kubernetes_cluster_resources(cluster_id)
        except Exception:
            resources = {"error": "Resources unavailable"}
        
        # Get node pools and their status
        try:
            node_pools = await vultr_client.list_kubernetes_node_pools(cluster_id)
            
            # Get node details for each pool
            node_pool_details = []
            for pool in node_pools:
                try:
                    nodes = await vultr_client.list_kubernetes_nodes(cluster_id, pool["id"])
                    pool_info = {
                        "pool": pool,
                        "nodes": nodes,
                        "node_count": len(nodes),
                        "healthy_nodes": len([n for n in nodes if n.get("status") == "active"])
                    }
                    node_pool_details.append(pool_info)
                except Exception:
                    node_pool_details.append({
                        "pool": pool,
                        "nodes": [],
                        "error": "Could not fetch nodes"
                    })
                    
        except Exception:
            node_pool_details = [{"error": "Could not fetch node pools"}]
        
        # Calculate overall health
        total_nodes = sum(detail.get("node_count", 0) for detail in node_pool_details)
        healthy_nodes = sum(detail.get("healthy_nodes", 0) for detail in node_pool_details)
        
        cluster_health = "healthy"
        if total_nodes == 0:
            cluster_health = "no_nodes"
        elif healthy_nodes < total_nodes:
            cluster_health = "degraded"
        elif cluster_info.get("status") != "active":
            cluster_health = "unhealthy"
        
        return {
            "cluster_info": cluster_info,
            "health_status": cluster_health,
            "total_nodes": total_nodes,
            "healthy_nodes": healthy_nodes,
            "resources": resources,
            "node_pools": node_pool_details,
            "summary": {
                "cluster_id": cluster_id,
                "label": cluster_info.get("label"),
                "version": cluster_info.get("version"),
                "region": cluster_info.get("region"),
                "status": cluster_info.get("status"),
                "ip": cluster_info.get("ip"),
                "node_pool_count": len(node_pools) if isinstance(node_pools, list) else 0
            }
        }
    
    @mcp.tool()
    async def scale_kubernetes_node_pool(
        cluster_identifier: str,
        nodepool_identifier: str,
        target_node_count: int
    ) -> Dict[str, Any]:
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
            
        cluster_id, nodepool_id = await get_nodepool_id(cluster_identifier, nodepool_identifier)
        
        # Get current node pool info
        current_pool = await vultr_client.get_kubernetes_node_pool(cluster_id, nodepool_id)
        current_count = current_pool.get("node_quantity", 0)
        
        if current_count == target_node_count:
            return {
                "status": "no_change",
                "message": f"Node pool {nodepool_identifier} already has {target_node_count} nodes",
                "current_nodes": current_count,
                "target_nodes": target_node_count
            }
        
        # Update the node pool with new count
        await vultr_client.update_kubernetes_node_pool(
            cluster_id,
            nodepool_id,
            node_quantity=target_node_count
        )
        
        scaling_direction = "up" if target_node_count > current_count else "down"
        
        return {
            "status": "scaling_initiated",
            "message": f"Scaling node pool {nodepool_identifier} {scaling_direction} from {current_count} to {target_node_count} nodes",
            "current_nodes": current_count,
            "target_nodes": target_node_count,
            "scaling_direction": scaling_direction
        }
    
    @mcp.tool()
    async def analyze_kubernetes_cluster_costs(cluster_identifier: str) -> Dict[str, Any]:
        """
        Analyze the estimated costs of a Kubernetes cluster.
        Smart identifier resolution: use cluster label or UUID.
        
        Args:
            cluster_identifier: The cluster label or ID
            
        Returns:
            Cost analysis including per-node costs and total estimated monthly cost
        """
        cluster_id = await get_cluster_id(cluster_identifier)
        
        # Get cluster and node pool information
        cluster_info = await vultr_client.get_kubernetes_cluster(cluster_id)
        node_pools = await vultr_client.list_kubernetes_node_pools(cluster_id)
        
        # Calculate costs (Note: This would need actual pricing data from Vultr API)
        # For now, we'll provide structure and placeholder calculations
        
        cost_breakdown = []
        total_monthly_cost = 0
        total_nodes = 0
        
        for pool in node_pools:
            node_count = pool.get("node_quantity", 0)
            plan = pool.get("plan", "unknown")
            
            # Placeholder cost calculation - would need real pricing API
            estimated_cost_per_node = 10.00  # Placeholder $10/month per node
            pool_monthly_cost = node_count * estimated_cost_per_node
            
            cost_breakdown.append({
                "node_pool_label": pool.get("label"),
                "plan": plan,
                "node_count": node_count,
                "estimated_cost_per_node": estimated_cost_per_node,
                "estimated_monthly_cost": pool_monthly_cost
            })
            
            total_monthly_cost += pool_monthly_cost
            total_nodes += node_count
        
        # Add control plane costs (if HA is enabled)
        ha_enabled = cluster_info.get("ha_controlplanes", False)
        control_plane_cost = 20.00 if ha_enabled else 0.00  # Placeholder
        total_monthly_cost += control_plane_cost
        
        return {
            "cluster_label": cluster_info.get("label"),
            "total_nodes": total_nodes,
            "ha_control_plane": ha_enabled,
            "cost_breakdown": {
                "node_pools": cost_breakdown,
                "control_plane_cost": control_plane_cost,
                "total_monthly_estimate": total_monthly_cost
            },
            "cost_optimization_tips": [
                "Consider using smaller plans for development clusters",
                "Use auto-scaling to optimize costs based on demand",
                "Monitor resource usage and scale down unused capacity",
                "Review node pool configurations regularly"
            ],
            "note": "Cost estimates are approximate. Check Vultr pricing for accurate costs."
        }
    
    @mcp.tool()
    async def setup_kubernetes_cluster_for_workload(
        label: str,
        region: str,
        workload_type: str = "web",
        environment: str = "production",
        auto_scaling: bool = True
    ) -> Dict[str, Any]:
        """
        Set up a Kubernetes cluster optimized for specific workload types.
        
        Args:
            label: Label for the new cluster
            region: Region code (e.g., 'ewr', 'lax')
            workload_type: Type of workload ('web', 'api', 'data', 'development')
            environment: Environment type ('production', 'staging', 'development')
            auto_scaling: Enable auto-scaling for node pools
            
        Returns:
            Created cluster information with setup recommendations
        """
        # Get available Kubernetes versions and use the latest stable
        versions = await vultr_client.get_kubernetes_versions()
        latest_version = versions[0] if versions else "v1.28.0"  # Fallback
        
        # Configure based on workload type and environment
        workload_configs = {
            "web": {
                "node_pools": [{
                    "label": "web-workers",
                    "plan": "vc2-2c-4gb" if environment == "production" else "vc2-1c-2gb",
                    "node_quantity": 3 if environment == "production" else 2,
                    "auto_scaler": auto_scaling,
                    "min_nodes": 2 if auto_scaling else None,
                    "max_nodes": 6 if auto_scaling else None
                }]
            },
            "api": {
                "node_pools": [{
                    "label": "api-workers",
                    "plan": "vc2-4c-8gb" if environment == "production" else "vc2-2c-4gb",
                    "node_quantity": 3 if environment == "production" else 2,
                    "auto_scaler": auto_scaling,
                    "min_nodes": 2 if auto_scaling else None,
                    "max_nodes": 8 if auto_scaling else None
                }]
            },
            "data": {
                "node_pools": [{
                    "label": "data-workers",
                    "plan": "vc2-8c-16gb" if environment == "production" else "vc2-4c-8gb",
                    "node_quantity": 3 if environment == "production" else 2,
                    "auto_scaler": auto_scaling,
                    "min_nodes": 3 if auto_scaling else None,
                    "max_nodes": 10 if auto_scaling else None
                }]
            },
            "development": {
                "node_pools": [{
                    "label": "dev-workers",
                    "plan": "vc2-1c-1gb",
                    "node_quantity": 1,
                    "auto_scaler": False,
                    "min_nodes": None,
                    "max_nodes": None
                }]
            }
        }
        
        config = workload_configs.get(workload_type, workload_configs["web"])
        
        # Create the cluster
        cluster = await vultr_client.create_kubernetes_cluster(
            label=label,
            region=region,
            version=latest_version,
            node_pools=config["node_pools"],
            enable_firewall=environment == "production",
            ha_controlplanes=environment == "production"
        )
        
        # Generate setup recommendations
        recommendations = {
            "next_steps": [
                "Download kubeconfig using get_kubernetes_cluster_config",
                "Install kubectl and configure cluster access",
                "Set up ingress controller for external access",
                "Configure monitoring and logging solutions"
            ],
            "workload_specific_tips": {
                "web": [
                    "Consider setting up horizontal pod autoscaling",
                    "Use ingress controllers for load balancing",
                    "Implement CDN for static assets"
                ],
                "api": [
                    "Configure API rate limiting",
                    "Set up service mesh for microservices",
                    "Implement proper authentication and authorization"
                ],
                "data": [
                    "Use persistent volumes for data storage",
                    "Consider StatefulSets for database workloads",
                    "Implement backup strategies for persistent data"
                ],
                "development": [
                    "Use namespaces to separate environments",
                    "Consider using development tools like Skaffold",
                    "Set up CI/CD pipelines for automated deployments"
                ]
            }.get(workload_type, []),
            "security_recommendations": [
                "Enable network policies for pod-to-pod communication",
                "Use RBAC for access control",
                "Regularly update cluster and node versions",
                "Scan container images for vulnerabilities"
            ] if environment == "production" else [
                "Set up basic RBAC",
                "Use namespaces for isolation"
            ]
        }
        
        return {
            "cluster": cluster,
            "configuration": {
                "workload_type": workload_type,
                "environment": environment,
                "auto_scaling_enabled": auto_scaling,
                "ha_control_plane": environment == "production",
                "firewall_enabled": environment == "production"
            },
            "recommendations": recommendations
        }
    
    return mcp