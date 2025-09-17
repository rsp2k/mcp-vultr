"""
Kubernetes Analysis utilities for Vultr Kubernetes Engine (VKE).

This module provides custom analysis functionality that is separate from
the core Vultr API implementation. It uses the Vultr API to gather data
but performs analysis and recommendations locally.
"""

from typing import Any


class KubernetesAnalyzer:
    """Custom Kubernetes analysis functionality for VKE cluster management."""

    def __init__(self, vultr_client):
        """Initialize with a Vultr Kubernetes client."""
        self.vultr_client = vultr_client

    async def get_cluster_status(self, cluster_identifier: str) -> dict[str, Any]:
        """Get comprehensive status information for a Kubernetes cluster.

        Args:
            cluster_identifier: The cluster label or ID

        Returns:
            Comprehensive cluster status including health, resources, and node status
        """
        try:
            # Get cluster details and node pools
            cluster = await self.vultr_client.get_kubernetes_cluster(cluster_identifier)
            node_pools = await self.vultr_client.list_kubernetes_node_pools(
                cluster_identifier
            )

            status = {
                "cluster_id": cluster.get("id"),
                "cluster_label": cluster.get("label"),
                "cluster_status": cluster.get("status"),
                "kubernetes_version": cluster.get("version"),
                "region": cluster.get("region"),
                "node_pools": [],
                "total_nodes": 0,
                "health_score": 0,
                "recommendations": [],
            }

            # Analyze node pools
            healthy_nodes = 0
            total_nodes = 0

            for pool in node_pools:
                pool_status = {
                    "pool_id": pool.get("id"),
                    "pool_label": pool.get("label"),
                    "node_quantity": pool.get("node_quantity", 0),
                    "plan": pool.get("plan"),
                    "status": pool.get("status"),
                    "auto_scaler": pool.get("auto_scaler", False),
                }

                pool_nodes = pool.get("node_quantity", 0)
                total_nodes += pool_nodes

                # Assume nodes are healthy if pool status is active
                if pool.get("status") == "active":
                    healthy_nodes += pool_nodes

                status["node_pools"].append(pool_status)

            status["total_nodes"] = total_nodes

            # Calculate health score
            if total_nodes > 0:
                status["health_score"] = int((healthy_nodes / total_nodes) * 100)

            # Generate recommendations
            status["recommendations"] = self._generate_cluster_recommendations(
                cluster, node_pools
            )

            return status

        except Exception as e:
            return {
                "cluster_identifier": cluster_identifier,
                "error": str(e),
                "recommendations": [
                    "Unable to analyze cluster - check if cluster exists and is accessible"
                ],
            }

    async def analyze_cluster_costs(self, cluster_identifier: str) -> dict[str, Any]:
        """Analyze the estimated costs of a Kubernetes cluster.

        Args:
            cluster_identifier: The cluster label or ID

        Returns:
            Cost analysis including per-node costs and total estimated monthly cost
        """
        try:
            cluster = await self.vultr_client.get_kubernetes_cluster(cluster_identifier)
            node_pools = await self.vultr_client.list_kubernetes_node_pools(
                cluster_identifier
            )

            cost_analysis = {
                "cluster_id": cluster.get("id"),
                "cluster_label": cluster.get("label"),
                "node_pool_costs": [],
                "total_monthly_estimate": 0.0,
                "optimization_opportunities": [],
                "recommendations": [],
            }

            total_cost = 0.0

            for pool in node_pools:
                node_quantity = pool.get("node_quantity", 0)
                plan_id = pool.get("plan")

                # Estimate cost per node (this would need actual plan pricing)
                estimated_cost_per_node = self._estimate_node_cost(plan_id)
                pool_monthly_cost = estimated_cost_per_node * node_quantity

                pool_cost = {
                    "pool_label": pool.get("label"),
                    "plan": plan_id,
                    "node_quantity": node_quantity,
                    "cost_per_node": estimated_cost_per_node,
                    "monthly_cost": pool_monthly_cost,
                }

                cost_analysis["node_pool_costs"].append(pool_cost)
                total_cost += pool_monthly_cost

            cost_analysis["total_monthly_estimate"] = total_cost

            # Generate cost optimization recommendations
            cost_analysis["optimization_opportunities"] = (
                self._identify_cost_optimizations(node_pools, total_cost)
            )
            cost_analysis["recommendations"] = self._generate_cost_recommendations(
                total_cost, len(node_pools)
            )

            return cost_analysis

        except Exception as e:
            return {
                "cluster_identifier": cluster_identifier,
                "error": str(e),
                "recommendations": [
                    "Unable to analyze cluster costs - check cluster access"
                ],
            }

    async def setup_cluster_for_workload(
        self,
        label: str,
        region: str,
        workload_type: str = "web",
        environment: str = "production",
        auto_scaling: bool = True,
    ) -> dict[str, Any]:
        """Set up a Kubernetes cluster optimized for specific workload types.

        Args:
            label: Label for the new cluster
            region: Region code
            workload_type: Type of workload ('web', 'api', 'data', 'development')
            environment: Environment type ('production', 'staging', 'development')
            auto_scaling: Enable auto-scaling for node pools

        Returns:
            Setup configuration and recommendations
        """
        # Generate optimized configuration based on workload type
        config = self._generate_workload_config(
            workload_type, environment, auto_scaling
        )

        setup_plan = {
            "cluster_label": label,
            "region": region,
            "workload_type": workload_type,
            "environment": environment,
            "recommended_config": config,
            "estimated_monthly_cost": config.get("estimated_cost", 0),
            "setup_steps": [
                f"Create cluster '{label}' in region '{region}'",
                f"Configure {len(config['node_pools'])} node pool(s) for {workload_type} workload",
                "Enable high availability control planes for production"
                if environment == "production"
                else "Use single control plane for cost optimization",
                "Configure auto-scaling" if auto_scaling else "Use fixed node count",
                "Set up monitoring and logging",
                "Configure networking and security policies",
            ],
            "post_setup_recommendations": [
                "Install monitoring tools (Prometheus, Grafana)",
                "Configure ingress controller for external access",
                "Set up CI/CD pipeline integration",
                "Implement backup and disaster recovery",
                "Configure resource quotas and limits",
            ],
        }

        return setup_plan

    def _generate_cluster_recommendations(
        self, cluster: dict[str, Any], node_pools: list[dict[str, Any]]
    ) -> list[str]:
        """Generate recommendations based on cluster configuration."""
        recommendations = []

        # Check cluster version
        version = cluster.get("version", "")
        if version and "1.26" in version or "1.25" in version:
            recommendations.append(
                "Consider upgrading to a newer Kubernetes version for latest features and security"
            )

        # Check node pool configuration
        if len(node_pools) == 1:
            recommendations.append(
                "Consider adding multiple node pools for better workload isolation"
            )

        total_nodes = sum(pool.get("node_quantity", 0) for pool in node_pools)
        if total_nodes < 3:
            recommendations.append(
                "Consider scaling to at least 3 nodes for high availability"
            )

        # Check auto-scaling
        auto_scaled_pools = sum(1 for pool in node_pools if pool.get("auto_scaler"))
        if auto_scaled_pools == 0:
            recommendations.append(
                "Consider enabling auto-scaling for dynamic workload handling"
            )

        return (
            recommendations if recommendations else ["Cluster configuration looks good"]
        )

    def _estimate_node_cost(self, plan_id: str) -> float:
        """Estimate monthly cost per node based on plan ID."""
        # This is a simplified estimation - would need actual pricing data
        cost_mapping = {
            "vc2-1c-1gb": 6.0,
            "vc2-1c-2gb": 12.0,
            "vc2-2c-4gb": 24.0,
            "vc2-4c-8gb": 48.0,
            "vc2-8c-16gb": 96.0,
            "vhf-1c-1gb": 6.0,
            "vhf-2c-2gb": 12.0,
            "vhf-4c-4gb": 24.0,
        }
        return cost_mapping.get(plan_id, 50.0)  # Default estimate

    def _identify_cost_optimizations(
        self, node_pools: list[dict[str, Any]], total_cost: float
    ) -> list[str]:
        """Identify cost optimization opportunities."""
        optimizations = []

        if total_cost > 200:
            optimizations.append("High cluster cost - consider rightsizing node pools")

        # Check for over-provisioning
        large_pools = [pool for pool in node_pools if pool.get("node_quantity", 0) > 5]
        if large_pools:
            optimizations.append(
                "Large node pools detected - verify actual resource utilization"
            )

        # Check for auto-scaling
        non_autoscaled = [pool for pool in node_pools if not pool.get("auto_scaler")]
        if non_autoscaled:
            optimizations.append(
                "Enable auto-scaling to optimize costs during low usage periods"
            )

        return (
            optimizations
            if optimizations
            else ["No obvious cost optimizations identified"]
        )

    def _generate_cost_recommendations(
        self, total_cost: float, pool_count: int
    ) -> list[str]:
        """Generate cost-related recommendations."""
        recommendations = []

        if total_cost > 500:
            recommendations.append(
                "High monthly cost - consider reserved instances or volume discounts"
            )
        elif total_cost < 50:
            recommendations.append(
                "Low cost cluster - suitable for development/testing"
            )

        if pool_count > 3:
            recommendations.append(
                "Many node pools - ensure each serves a distinct purpose"
            )

        return recommendations

    def _generate_workload_config(
        self, workload_type: str, environment: str, auto_scaling: bool
    ) -> dict[str, Any]:
        """Generate optimized configuration for specific workload types."""
        configs = {
            "web": {
                "kubernetes_version": "1.28",
                "ha_controlplanes": environment == "production",
                "node_pools": [
                    {
                        "label": "web-workers",
                        "node_quantity": 3 if environment == "production" else 2,
                        "plan": "vc2-2c-4gb",
                        "auto_scaler": auto_scaling,
                        "min_nodes": 2 if auto_scaling else None,
                        "max_nodes": 10 if auto_scaling else None,
                    }
                ],
                "estimated_cost": 72.0 if environment == "production" else 48.0,
            },
            "api": {
                "kubernetes_version": "1.28",
                "ha_controlplanes": environment == "production",
                "node_pools": [
                    {
                        "label": "api-workers",
                        "node_quantity": 3 if environment == "production" else 2,
                        "plan": "vc2-4c-8gb",
                        "auto_scaler": auto_scaling,
                        "min_nodes": 2 if auto_scaling else None,
                        "max_nodes": 8 if auto_scaling else None,
                    }
                ],
                "estimated_cost": 144.0 if environment == "production" else 96.0,
            },
            "data": {
                "kubernetes_version": "1.28",
                "ha_controlplanes": True,
                "node_pools": [
                    {
                        "label": "data-workers",
                        "node_quantity": 3,
                        "plan": "vc2-8c-16gb",
                        "auto_scaler": False,  # Data workloads prefer stable resources
                        "min_nodes": None,
                        "max_nodes": None,
                    }
                ],
                "estimated_cost": 288.0,
            },
            "development": {
                "kubernetes_version": "1.28",
                "ha_controlplanes": False,
                "node_pools": [
                    {
                        "label": "dev-workers",
                        "node_quantity": 1,
                        "plan": "vc2-1c-2gb",
                        "auto_scaler": auto_scaling,
                        "min_nodes": 1 if auto_scaling else None,
                        "max_nodes": 3 if auto_scaling else None,
                    }
                ],
                "estimated_cost": 12.0,
            },
        }

        return configs.get(workload_type, configs["web"])
