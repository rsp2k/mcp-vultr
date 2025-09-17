"""
CDN Analysis utilities for Vultr CDN zones.

This module provides custom analysis functionality that is separate from
the core Vultr API implementation. It uses the Vultr API to gather data
but performs analysis and optimization recommendations locally.
"""

from typing import Any


class CDNAnalyzer:
    """Custom CDN analysis functionality for Vultr CDN zone management."""

    def __init__(self, vultr_client):
        """Initialize with a Vultr CDN client."""
        self.vultr_client = vultr_client

    async def analyze_performance(
        self, zone_identifier: str, days: int = 7
    ) -> dict[str, Any]:
        """Analyze CDN zone performance over the specified period.

        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID
            days: Number of days to analyze

        Returns:
            Performance analysis including cache hit ratio, bandwidth usage, and recommendations
        """
        try:
            # Get CDN zone info and statistics
            zone_info = await self.vultr_client.get_cdn_zone(zone_identifier)
            zone_stats = await self.vultr_client.get_cdn_zone_stats(zone_identifier)

            analysis = {
                "zone_id": zone_info.get("id"),
                "origin_domain": zone_info.get("origin_domain"),
                "cdn_domain": zone_info.get("cdn_domain"),
                "analysis_period_days": days,
                "performance_metrics": {},
                "performance_score": 0,
                "bottlenecks": [],
                "recommendations": [],
            }

            # Analyze performance metrics
            bandwidth_usage = zone_stats.get("bandwidth_usage", 0)
            request_count = zone_stats.get("request_count", 0)
            cache_hit_ratio = zone_stats.get("cache_hit_ratio", 0)
            avg_response_time = zone_stats.get("avg_response_time", 0)

            analysis["performance_metrics"] = {
                "bandwidth_usage_gb": bandwidth_usage / (1024**3)
                if bandwidth_usage
                else 0,
                "total_requests": request_count,
                "cache_hit_ratio_percent": cache_hit_ratio * 100
                if cache_hit_ratio
                else 0,
                "average_response_time_ms": avg_response_time,
                "requests_per_day": request_count / days if days > 0 else 0,
            }

            # Calculate performance score
            performance_factors = []

            # Cache hit ratio scoring (40% of total score)
            if cache_hit_ratio >= 0.9:
                performance_factors.append(40)
            elif cache_hit_ratio >= 0.8:
                performance_factors.append(32)
                analysis["bottlenecks"].append("Cache hit ratio could be improved")
            elif cache_hit_ratio >= 0.7:
                performance_factors.append(24)
                analysis["bottlenecks"].append("Low cache hit ratio detected")
            else:
                performance_factors.append(10)
                analysis["bottlenecks"].append(
                    "Very low cache hit ratio - caching issues"
                )

            # Response time scoring (30% of total score)
            if avg_response_time <= 100:
                performance_factors.append(30)
            elif avg_response_time <= 200:
                performance_factors.append(24)
            elif avg_response_time <= 500:
                performance_factors.append(18)
                analysis["bottlenecks"].append("Elevated response times detected")
            else:
                performance_factors.append(8)
                analysis["bottlenecks"].append(
                    "High response times - performance issues"
                )

            # Request distribution scoring (20% of total score)
            requests_per_day = analysis["performance_metrics"]["requests_per_day"]
            if requests_per_day > 0:
                performance_factors.append(
                    20
                )  # Assume good distribution if there are requests
            else:
                performance_factors.append(5)
                analysis["bottlenecks"].append("No traffic detected")

            # SSL/Security scoring (10% of total score)
            ssl_cert = zone_info.get("ssl_cert")
            if ssl_cert and ssl_cert.get("status") == "active":
                performance_factors.append(10)
            else:
                performance_factors.append(5)
                analysis["bottlenecks"].append("SSL certificate issues")

            analysis["performance_score"] = sum(performance_factors)

            # Generate performance recommendations
            analysis["recommendations"] = self._generate_performance_recommendations(
                cache_hit_ratio, avg_response_time, bandwidth_usage, zone_info
            )

            return analysis

        except Exception as e:
            return {
                "zone_identifier": zone_identifier,
                "error": str(e),
                "recommendations": [
                    "Unable to analyze CDN performance - check if CDN zone exists"
                ],
            }

    async def get_zone_summary(self, zone_identifier: str) -> dict[str, Any]:
        """Get a comprehensive summary of a CDN zone.

        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID

        Returns:
            Comprehensive CDN zone summary including configuration, stats, and SSL info
        """
        try:
            # Get zone info, statistics, and SSL certificate info
            zone_info = await self.vultr_client.get_cdn_zone(zone_identifier)
            zone_stats = await self.vultr_client.get_cdn_zone_stats(zone_identifier)

            try:
                ssl_info = await self.vultr_client.get_cdn_ssl_certificate(
                    zone_identifier
                )
            except:
                ssl_info = None

            summary = {
                "zone_configuration": {
                    "zone_id": zone_info.get("id"),
                    "origin_domain": zone_info.get("origin_domain"),
                    "cdn_domain": zone_info.get("cdn_domain"),
                    "origin_scheme": zone_info.get("origin_scheme"),
                    "gzip_compression": zone_info.get("gzip_compression", False),
                    "block_ai_bots": zone_info.get("block_ai_bots", False),
                    "block_bad_bots": zone_info.get("block_bad_bots", False),
                    "cors_policy": zone_info.get("cors_policy"),
                    "regions": zone_info.get("regions", []),
                },
                "performance_summary": {
                    "bandwidth_usage_gb": zone_stats.get("bandwidth_usage", 0)
                    / (1024**3),
                    "total_requests": zone_stats.get("request_count", 0),
                    "cache_hit_ratio": zone_stats.get("cache_hit_ratio", 0),
                    "average_response_time": zone_stats.get("avg_response_time", 0),
                },
                "ssl_status": {
                    "ssl_enabled": ssl_info is not None,
                    "ssl_status": ssl_info.get("status") if ssl_info else "No SSL",
                    "ssl_issuer": ssl_info.get("issuer") if ssl_info else None,
                    "ssl_expires": ssl_info.get("expires") if ssl_info else None,
                },
                "health_assessment": "unknown",
                "optimization_opportunities": [],
                "security_recommendations": [],
            }

            # Assess overall health
            cache_ratio = zone_stats.get("cache_hit_ratio", 0)
            response_time = zone_stats.get("avg_response_time", 0)

            if cache_ratio >= 0.8 and response_time <= 200:
                summary["health_assessment"] = "excellent"
            elif cache_ratio >= 0.7 and response_time <= 500:
                summary["health_assessment"] = "good"
            elif cache_ratio >= 0.5 and response_time <= 1000:
                summary["health_assessment"] = "fair"
            else:
                summary["health_assessment"] = "needs_attention"

            # Generate optimization opportunities
            summary["optimization_opportunities"] = (
                self._identify_optimization_opportunities(zone_info, zone_stats)
            )

            # Generate security recommendations
            summary["security_recommendations"] = (
                self._generate_security_recommendations(zone_info, ssl_info)
            )

            return summary

        except Exception as e:
            return {
                "zone_identifier": zone_identifier,
                "error": str(e),
                "recommendations": [
                    "Unable to generate CDN zone summary - check zone access"
                ],
            }

    async def setup_for_website(
        self,
        origin_domain: str,
        enable_security: bool = True,
        enable_compression: bool = True,
        regions: list[str] = None,
    ) -> dict[str, Any]:
        """Set up a CDN zone with optimal settings for a website.

        Args:
            origin_domain: Origin domain for the website
            enable_security: Enable bot blocking and security features
            enable_compression: Enable gzip compression
            regions: List of regions to enable (if not specified, uses global)

        Returns:
            Setup configuration and next steps
        """
        setup_config = {
            "origin_domain": origin_domain,
            "origin_scheme": "https",
            "recommended_settings": {
                "gzip_compression": enable_compression,
                "block_ai_bots": enable_security,
                "block_bad_bots": enable_security,
                "cors_policy": "permissive" if not enable_security else "restrictive",
                "regions": regions or ["global"],
            },
            "setup_steps": [
                f"Create CDN zone for {origin_domain}",
                "Configure origin settings (HTTPS recommended)",
                "Enable gzip compression for better performance"
                if enable_compression
                else "Consider enabling gzip compression",
                "Enable bot protection features"
                if enable_security
                else "Consider enabling security features",
                "Configure SSL certificate for secure delivery",
                "Update DNS to point to CDN domain",
                "Test CDN functionality and cache behavior",
            ],
            "post_setup_tasks": [
                "Configure cache headers on origin server for optimal caching",
                "Set up monitoring and alerting for CDN performance",
                "Implement cache purging strategy for content updates",
                "Consider implementing additional security headers",
                "Monitor cache hit ratio and optimize as needed",
            ],
            "performance_tips": [
                "Use appropriate cache headers (Cache-Control, ETag)",
                "Optimize images and static assets before CDN caching",
                "Consider implementing HTTP/2 push for critical resources",
                "Monitor Core Web Vitals impact of CDN",
                "Set up geographic performance monitoring",
            ],
            "security_considerations": [
                "Enable SSL/TLS for end-to-end encryption",
                "Configure appropriate CORS policies",
                "Consider implementing WAF rules if available",
                "Monitor for suspicious traffic patterns",
                "Keep SSL certificates updated",
            ],
        }

        return setup_config

    def _generate_performance_recommendations(
        self,
        cache_hit_ratio: float,
        avg_response_time: float,
        bandwidth_usage: int,
        zone_info: dict[str, Any],
    ) -> list[str]:
        """Generate performance optimization recommendations."""
        recommendations = []

        # Cache optimization
        if cache_hit_ratio < 0.7:
            recommendations.extend(
                [
                    "Low cache hit ratio detected - review cache headers on origin server",
                    "Consider implementing longer cache TTLs for static content",
                    "Review which content types are being cached",
                ]
            )
        elif cache_hit_ratio < 0.85:
            recommendations.append(
                "Cache hit ratio is good but could be optimized further"
            )

        # Response time optimization
        if avg_response_time > 500:
            recommendations.extend(
                [
                    "High response times detected - optimize origin server performance",
                    "Consider enabling gzip compression if not already enabled",
                    "Review origin server location relative to CDN edge locations",
                ]
            )
        elif avg_response_time > 200:
            recommendations.append(
                "Response times could be improved with origin optimization"
            )

        # Compression recommendations
        if not zone_info.get("gzip_compression"):
            recommendations.append(
                "Enable gzip compression for better performance and bandwidth savings"
            )

        # Security and performance
        if not zone_info.get("block_bad_bots"):
            recommendations.append(
                "Consider enabling bot blocking to reduce unnecessary traffic"
            )

        # Regional optimization
        regions = zone_info.get("regions", [])
        if len(regions) < 3:
            recommendations.append(
                "Consider enabling more regions for better global performance"
            )

        return (
            recommendations
            if recommendations
            else ["CDN performance appears optimized"]
        )

    def _identify_optimization_opportunities(
        self, zone_info: dict[str, Any], zone_stats: dict[str, Any]
    ) -> list[str]:
        """Identify optimization opportunities for the CDN zone."""
        opportunities = []

        # Compression opportunities
        if not zone_info.get("gzip_compression"):
            opportunities.append(
                "Enable gzip compression to reduce bandwidth usage by 60-80%"
            )

        # Caching opportunities
        cache_ratio = zone_stats.get("cache_hit_ratio", 0)
        if cache_ratio < 0.8:
            opportunities.append(
                "Improve cache configuration to increase hit ratio and reduce origin load"
            )

        # Security opportunities
        if not zone_info.get("block_bad_bots"):
            opportunities.append(
                "Enable bot blocking to reduce unnecessary traffic and improve performance"
            )

        # Regional optimization
        regions = zone_info.get("regions", [])
        if not regions or len(regions) < 2:
            opportunities.append(
                "Enable multiple regions for better global performance and redundancy"
            )

        # SSL optimization
        if zone_info.get("origin_scheme") != "https":
            opportunities.append("Use HTTPS origin for better security and performance")

        return (
            opportunities
            if opportunities
            else ["No obvious optimization opportunities identified"]
        )

    def _generate_security_recommendations(
        self, zone_info: dict[str, Any], ssl_info: dict[str, Any] = None
    ) -> list[str]:
        """Generate security recommendations for the CDN zone."""
        recommendations = []

        # SSL recommendations
        if not ssl_info:
            recommendations.append("Set up SSL certificate for secure content delivery")
        elif ssl_info.get("status") != "active":
            recommendations.append("Fix SSL certificate issues for secure delivery")

        # Origin security
        if zone_info.get("origin_scheme") != "https":
            recommendations.append(
                "Use HTTPS for origin communication to ensure end-to-end encryption"
            )

        # Bot protection
        if not zone_info.get("block_bad_bots"):
            recommendations.append("Enable bad bot blocking for improved security")

        if not zone_info.get("block_ai_bots"):
            recommendations.append(
                "Consider enabling AI bot blocking if content scraping is a concern"
            )

        # CORS policy
        cors_policy = zone_info.get("cors_policy")
        if not cors_policy:
            recommendations.append(
                "Configure CORS policy for better cross-origin security"
            )
        elif cors_policy == "permissive":
            recommendations.append(
                "Review CORS policy - consider more restrictive settings for better security"
            )

        # General security
        recommendations.extend(
            [
                "Regularly monitor CDN logs for suspicious activity",
                "Keep SSL certificates updated and monitor expiration dates",
                "Consider implementing additional security headers at origin",
            ]
        )

        return recommendations
