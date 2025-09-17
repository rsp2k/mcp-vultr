"""
Load Balancer Analysis utilities for Vultr Load Balancers.

This module provides custom analysis functionality that is separate from
the core Vultr API implementation. It uses the Vultr API to gather data
but performs configuration analysis and setup automation locally.
"""

from typing import Any


class LoadBalancerAnalyzer:
    """Custom load balancer analysis functionality for Vultr load balancer management."""

    def __init__(self, vultr_client):
        """Initialize with a Vultr load balancer client."""
        self.vultr_client = vultr_client

    async def configure_basic_web_lb(
        self,
        region: str,
        label: str,
        backend_instances: list[str],
        enable_ssl: bool = True,
        ssl_redirect: bool = True,
        domain_zone: str = None,
        domain_sub: str = None,
    ) -> dict[str, Any]:
        """Configure a basic web load balancer with standard HTTP/HTTPS rules.

        Args:
            region: Region code
            label: Label for the load balancer
            backend_instances: List of instance IDs to attach
            enable_ssl: Enable SSL/Auto SSL
            ssl_redirect: Redirect HTTP to HTTPS
            domain_zone: Domain zone for Auto SSL
            domain_sub: Subdomain for Auto SSL

        Returns:
            Created and configured load balancer information with setup details
        """
        try:
            # Create the load balancer
            load_balancer = await self.vultr_client.create_load_balancer(
                region=region,
                label=label,
                instances=backend_instances,
                health_check={
                    "protocol": "http",
                    "port": 80,
                    "path": "/",
                    "check_interval": 15,
                    "response_timeout": 5,
                    "healthy_threshold": 5,
                    "unhealthy_threshold": 3,
                },
                generic_info={
                    "balancing_algorithm": "roundrobin",
                    "ssl_redirect": ssl_redirect,
                    "http2": True,
                    "nodes": 1,
                },
                forwarding_rules=[
                    {
                        "frontend_protocol": "http",
                        "frontend_port": 80,
                        "backend_protocol": "http",
                        "backend_port": 80,
                    },
                    {
                        "frontend_protocol": "https",
                        "frontend_port": 443,
                        "backend_protocol": "http",
                        "backend_port": 80,
                    },
                ]
                if enable_ssl
                else [
                    {
                        "frontend_protocol": "http",
                        "frontend_port": 80,
                        "backend_protocol": "http",
                        "backend_port": 80,
                    }
                ],
            )

            lb_id = load_balancer.get("id")

            configuration = {
                "load_balancer_id": lb_id,
                "label": label,
                "region": region,
                "status": "provisioning",
                "backend_instances": backend_instances,
                "configuration": {
                    "ssl_enabled": enable_ssl,
                    "ssl_redirect": ssl_redirect,
                    "http2_enabled": True,
                    "balancing_algorithm": "roundrobin",
                    "health_check_enabled": True,
                },
                "forwarding_rules": [
                    {
                        "protocol": "HTTP",
                        "port": 80,
                        "backend_port": 80,
                        "purpose": "Web traffic",
                    },
                    {
                        "protocol": "HTTPS",
                        "port": 443,
                        "backend_port": 80,
                        "purpose": "Secure web traffic",
                    },
                ]
                if enable_ssl
                else [
                    {
                        "protocol": "HTTP",
                        "port": 80,
                        "backend_port": 80,
                        "purpose": "Web traffic",
                    }
                ],
                "dns_configuration": {},
                "next_steps": [],
                "monitoring_recommendations": [],
                "security_considerations": [],
            }

            # Configure Auto SSL if domain details provided
            if enable_ssl and domain_zone:
                try:
                    await self.vultr_client.create_ssl_certificate(
                        lb_id, domain_zone, domain_sub
                    )
                    configuration["dns_configuration"] = {
                        "domain": f"{domain_sub}.{domain_zone}"
                        if domain_sub
                        else domain_zone,
                        "cname_target": load_balancer.get("has_ssl", {}).get(
                            "hostname"
                        ),
                        "ssl_status": "Auto SSL configured",
                    }
                except Exception as ssl_error:
                    configuration["dns_configuration"] = {
                        "ssl_error": str(ssl_error),
                        "manual_ssl_required": True,
                    }

            # Generate next steps
            configuration["next_steps"] = self._generate_setup_steps(
                configuration, enable_ssl, domain_zone
            )

            # Generate monitoring recommendations
            configuration["monitoring_recommendations"] = (
                self._generate_monitoring_recommendations()
            )

            # Generate security considerations
            configuration["security_considerations"] = (
                self._generate_security_considerations(enable_ssl, ssl_redirect)
            )

            return configuration

        except Exception as e:
            return {
                "error": str(e),
                "recommendations": [
                    "Check that all backend instances exist and are in the same region",
                    "Verify sufficient account balance for load balancer creation",
                    "Ensure instances are properly configured to handle HTTP traffic on port 80",
                ],
            }

    async def get_health_status(self, load_balancer_id: str) -> dict[str, Any]:
        """Get health status and monitoring information for a load balancer.

        Args:
            load_balancer_id: The load balancer ID or label

        Returns:
            Health status and configuration information
        """
        try:
            # Get load balancer details and instance health
            lb_info = await self.vultr_client.get_load_balancer(load_balancer_id)
            instance_list = await self.vultr_client.list_load_balancer_instances(
                load_balancer_id
            )

            health_status = {
                "load_balancer_id": lb_info.get("id"),
                "label": lb_info.get("label"),
                "status": lb_info.get("status"),
                "health_check_config": lb_info.get("health_check", {}),
                "backend_health": [],
                "overall_health": "unknown",
                "active_backends": 0,
                "total_backends": 0,
                "health_score": 0,
                "alerts": [],
                "recommendations": [],
            }

            # Analyze backend instance health
            healthy_backends = 0
            total_backends = len(instance_list)

            for instance in instance_list:
                instance_health = {
                    "instance_id": instance.get("id"),
                    "instance_label": instance.get("label"),
                    "health_status": instance.get("health_status", "unknown"),
                    "last_health_check": instance.get("last_health_check"),
                    "response_time": instance.get("avg_response_time"),
                }

                if instance.get("health_status") == "healthy":
                    healthy_backends += 1
                elif instance.get("health_status") == "unhealthy":
                    health_status["alerts"].append(
                        f"Instance {instance.get('label', instance.get('id'))} is unhealthy"
                    )

                health_status["backend_health"].append(instance_health)

            health_status["active_backends"] = healthy_backends
            health_status["total_backends"] = total_backends

            # Calculate overall health
            if total_backends == 0:
                health_status["overall_health"] = "no_backends"
                health_status["health_score"] = 0
                health_status["alerts"].append("No backend instances configured")
            elif healthy_backends == 0:
                health_status["overall_health"] = "critical"
                health_status["health_score"] = 0
                health_status["alerts"].append("All backend instances are unhealthy")
            elif healthy_backends == total_backends:
                health_status["overall_health"] = "healthy"
                health_status["health_score"] = 100
            else:
                health_ratio = healthy_backends / total_backends
                if health_ratio >= 0.8:
                    health_status["overall_health"] = "degraded"
                    health_status["health_score"] = int(health_ratio * 100)
                else:
                    health_status["overall_health"] = "unhealthy"
                    health_status["health_score"] = int(health_ratio * 100)
                    health_status["alerts"].append(
                        f"Only {healthy_backends}/{total_backends} backends are healthy"
                    )

            # Generate recommendations based on health status
            health_status["recommendations"] = self._generate_health_recommendations(
                health_status
            )

            return health_status

        except Exception as e:
            return {
                "load_balancer_id": load_balancer_id,
                "error": str(e),
                "recommendations": [
                    "Unable to check load balancer health - verify load balancer exists"
                ],
            }

    async def get_configuration_summary(self, load_balancer_id: str) -> dict[str, Any]:
        """Get a comprehensive configuration summary for a load balancer.

        Args:
            load_balancer_id: The load balancer ID or label

        Returns:
            Detailed configuration summary with optimization recommendations
        """
        try:
            # Get all load balancer configuration details
            lb_info = await self.vultr_client.get_load_balancer(load_balancer_id)
            forwarding_rules = await self.vultr_client.list_forwarding_rules(
                load_balancer_id
            )
            firewall_rules = await self.vultr_client.list_firewall_rules(
                load_balancer_id
            )
            instance_list = await self.vultr_client.list_load_balancer_instances(
                load_balancer_id
            )

            summary = {
                "load_balancer_info": {
                    "id": lb_info.get("id"),
                    "label": lb_info.get("label"),
                    "status": lb_info.get("status"),
                    "region": lb_info.get("region"),
                    "ipv4": lb_info.get("ipv4"),
                    "ipv6": lb_info.get("ipv6"),
                    "balancing_algorithm": lb_info.get("generic_info", {}).get(
                        "balancing_algorithm"
                    ),
                    "ssl_redirect": lb_info.get("generic_info", {}).get("ssl_redirect"),
                    "http2": lb_info.get("generic_info", {}).get("http2"),
                },
                "health_check_config": lb_info.get("health_check", {}),
                "forwarding_rules": [
                    {
                        "rule_id": rule.get("id"),
                        "frontend": f"{rule.get('frontend_protocol')}:{rule.get('frontend_port')}",
                        "backend": f"{rule.get('backend_protocol')}:{rule.get('backend_port')}",
                        "purpose": self._determine_rule_purpose(rule),
                    }
                    for rule in forwarding_rules
                ],
                "firewall_rules": [
                    {
                        "rule_id": rule.get("id"),
                        "port": rule.get("port"),
                        "source": rule.get("source"),
                        "protocol": rule.get("ip_type"),
                    }
                    for rule in firewall_rules
                ],
                "backend_instances": [
                    {
                        "instance_id": instance.get("id"),
                        "label": instance.get("label"),
                        "health_status": instance.get("health_status", "unknown"),
                    }
                    for instance in instance_list
                ],
                "ssl_configuration": lb_info.get("has_ssl", {}),
                "configuration_assessment": "unknown",
                "optimization_opportunities": [],
                "security_recommendations": [],
                "performance_recommendations": [],
            }

            # Assess configuration quality
            summary["configuration_assessment"] = self._assess_configuration_quality(
                summary
            )

            # Generate optimization opportunities
            summary["optimization_opportunities"] = (
                self._identify_lb_optimization_opportunities(summary)
            )

            # Generate security recommendations
            summary["security_recommendations"] = (
                self._generate_lb_security_recommendations(summary)
            )

            # Generate performance recommendations
            summary["performance_recommendations"] = (
                self._generate_lb_performance_recommendations(summary)
            )

            return summary

        except Exception as e:
            return {
                "load_balancer_id": load_balancer_id,
                "error": str(e),
                "recommendations": [
                    "Unable to generate configuration summary - verify load balancer access"
                ],
            }

    def _generate_setup_steps(
        self, config: dict[str, Any], enable_ssl: bool, domain_zone: str
    ) -> list[str]:
        """Generate setup steps for load balancer configuration."""
        steps = [
            "Load balancer is being provisioned",
            "Health checks will begin once provisioning is complete",
            "Configure backend instances to respond to health checks on port 80",
        ]

        if enable_ssl:
            if domain_zone:
                steps.extend(
                    [
                        f"Configure DNS CNAME record for {config.get('dns_configuration', {}).get('domain', 'your-domain')}",
                        "SSL certificate will be automatically provisioned",
                        "Test both HTTP and HTTPS endpoints",
                    ]
                )
            else:
                steps.extend(
                    [
                        "Configure SSL certificate manually",
                        "Update DNS to point to load balancer IP",
                        "Test SSL configuration",
                    ]
                )
        else:
            steps.append("Update DNS to point to load balancer IP")

        steps.extend(
            [
                "Monitor health check status for all backend instances",
                "Test load balancing behavior across instances",
                "Set up monitoring and alerting",
            ]
        )

        return steps

    def _generate_monitoring_recommendations(self) -> list[str]:
        """Generate monitoring recommendations for load balancer."""
        return [
            "Set up alerts for when backend instances become unhealthy",
            "Monitor response times and connection counts",
            "Track SSL certificate expiration dates",
            "Monitor load balancer CPU and memory usage",
            "Set up external monitoring to test load balancer availability",
            "Monitor backend instance distribution for even load balancing",
        ]

    def _generate_security_considerations(
        self, enable_ssl: bool, ssl_redirect: bool
    ) -> list[str]:
        """Generate security considerations for load balancer."""
        considerations = [
            "Ensure backend instances only accept traffic from load balancer",
            "Configure appropriate firewall rules to restrict access",
            "Regularly update SSL certificates",
            "Monitor access logs for suspicious activity",
        ]

        if enable_ssl:
            considerations.extend(
                [
                    "Use strong SSL/TLS configurations (TLS 1.2+)",
                    "Consider implementing HSTS headers",
                ]
            )
            if ssl_redirect:
                considerations.append(
                    "HTTP to HTTPS redirect is configured for security"
                )
            else:
                considerations.append("Consider enabling HTTP to HTTPS redirect")
        else:
            considerations.append(
                "Consider enabling SSL/TLS for encrypted communication"
            )

        return considerations

    def _generate_health_recommendations(
        self, health_status: dict[str, Any]
    ) -> list[str]:
        """Generate recommendations based on health status."""
        recommendations = []

        overall_health = health_status.get("overall_health")

        if overall_health == "critical":
            recommendations.extend(
                [
                    "URGENT: All backends are unhealthy - check backend instance status",
                    "Verify health check configuration is appropriate for your application",
                    "Check network connectivity between load balancer and backends",
                ]
            )
        elif overall_health == "unhealthy":
            recommendations.extend(
                [
                    "Multiple backends are unhealthy - investigate backend issues",
                    "Consider scaling up healthy instances temporarily",
                    "Review health check thresholds and intervals",
                ]
            )
        elif overall_health == "degraded":
            recommendations.extend(
                [
                    "Some backends are unhealthy - monitor closely",
                    "Consider auto-scaling to maintain capacity",
                    "Investigate unhealthy instance root causes",
                ]
            )
        elif overall_health == "healthy":
            recommendations.extend(
                [
                    "Load balancer health is good",
                    "Continue monitoring for any changes",
                    "Consider load testing to verify capacity",
                ]
            )

        # General recommendations
        recommendations.extend(
            [
                "Set up automated alerting for health status changes",
                "Regular health check configuration reviews",
                "Maintain backup instances for high availability",
            ]
        )

        return recommendations

    def _determine_rule_purpose(self, rule: dict[str, Any]) -> str:
        """Determine the purpose of a forwarding rule."""
        frontend_port = rule.get("frontend_port")
        frontend_protocol = rule.get("frontend_protocol", "").lower()

        if frontend_port == 80 and frontend_protocol == "http":
            return "HTTP web traffic"
        elif frontend_port == 443 and frontend_protocol == "https":
            return "HTTPS web traffic"
        elif frontend_port == 22:
            return "SSH access"
        elif frontend_port in [3306, 5432]:
            return "Database access"
        else:
            return "Custom application traffic"

    def _assess_configuration_quality(self, summary: dict[str, Any]) -> str:
        """Assess the overall quality of load balancer configuration."""
        issues = 0

        # Check for basic security
        if not summary.get("ssl_configuration"):
            issues += 1

        # Check for proper health checks
        health_config = summary.get("health_check_config", {})
        if not health_config or not health_config.get("protocol"):
            issues += 1

        # Check for backend instances
        if len(summary.get("backend_instances", [])) < 2:
            issues += 1

        # Check for forwarding rules
        if len(summary.get("forwarding_rules", [])) == 0:
            issues += 1

        if issues == 0:
            return "excellent"
        elif issues <= 1:
            return "good"
        elif issues <= 2:
            return "fair"
        else:
            return "needs_improvement"

    def _identify_lb_optimization_opportunities(
        self, summary: dict[str, Any]
    ) -> list[str]:
        """Identify optimization opportunities for load balancer."""
        opportunities = []

        # SSL optimization
        if not summary.get("ssl_configuration"):
            opportunities.append("Enable SSL/TLS for secure communication")

        # HTTP/2 optimization
        if not summary.get("load_balancer_info", {}).get("http2"):
            opportunities.append("Enable HTTP/2 for improved performance")

        # Health check optimization
        health_config = summary.get("health_check_config", {})
        if health_config.get("check_interval", 30) > 15:
            opportunities.append(
                "Reduce health check interval for faster failure detection"
            )

        # Backend scaling
        backend_count = len(summary.get("backend_instances", []))
        if backend_count < 2:
            opportunities.append("Add more backend instances for high availability")
        elif backend_count == 1:
            opportunities.append(
                "Single backend instance creates single point of failure"
            )

        return (
            opportunities if opportunities else ["Configuration appears well-optimized"]
        )

    def _generate_lb_security_recommendations(
        self, summary: dict[str, Any]
    ) -> list[str]:
        """Generate security recommendations for load balancer."""
        recommendations = []

        # SSL recommendations
        if not summary.get("ssl_configuration"):
            recommendations.append(
                "Implement SSL/TLS certificates for encrypted communication"
            )

        # Firewall recommendations
        firewall_rules = summary.get("firewall_rules", [])
        if not firewall_rules:
            recommendations.append(
                "Configure firewall rules to restrict access to necessary ports only"
            )

        # Redirect recommendations
        if not summary.get("load_balancer_info", {}).get("ssl_redirect"):
            recommendations.append(
                "Enable HTTP to HTTPS redirect for improved security"
            )

        # General security
        recommendations.extend(
            [
                "Regularly update and rotate SSL certificates",
                "Monitor access logs for suspicious activity",
                "Implement rate limiting if available",
                "Ensure backend instances are not directly accessible from internet",
            ]
        )

        return recommendations

    def _generate_lb_performance_recommendations(
        self, summary: dict[str, Any]
    ) -> list[str]:
        """Generate performance recommendations for load balancer."""
        recommendations = []

        # HTTP/2 recommendations
        if not summary.get("load_balancer_info", {}).get("http2"):
            recommendations.append(
                "Enable HTTP/2 for better performance with modern browsers"
            )

        # Health check optimization
        health_config = summary.get("health_check_config", {})
        response_timeout = health_config.get("response_timeout", 5)
        if response_timeout > 5:
            recommendations.append(
                "Consider reducing health check response timeout for faster detection"
            )

        # Load balancing algorithm
        algorithm = summary.get("load_balancer_info", {}).get("balancing_algorithm")
        if algorithm == "roundrobin":
            recommendations.append(
                "Consider least_connections algorithm for better load distribution with varying request processing times"
            )

        # General performance
        recommendations.extend(
            [
                "Monitor backend response times and optimize slow instances",
                "Consider implementing connection pooling at backends",
                "Regular performance testing under expected load",
                "Monitor and optimize health check frequency vs accuracy trade-off",
            ]
        )

        return recommendations
