"""
DNS Analysis utilities for Vultr domains.

This module provides custom analysis functionality that is separate from
the core Vultr API implementation. It uses the Vultr API to gather data
but performs analysis and recommendations locally.
"""

from typing import Any


class DNSAnalyzer:
    """Custom DNS analysis functionality for Vultr-managed domains."""

    def __init__(self, vultr_client):
        """Initialize with a Vultr DNS client."""
        self.vultr_client = vultr_client

    async def analyze_domain(self, domain: str) -> dict[str, Any]:
        """Analyze DNS configuration for a domain and provide recommendations.

        Args:
            domain: The domain name to analyze

        Returns:
            Analysis results with recommendations for improvements
        """
        try:
            # Get domain info and records using the Vultr API
            domain_info = await self.vultr_client.get_domain(domain)
            records = await self.vultr_client.list_records(domain)

            # Perform analysis locally (not via API)
            analysis = {
                "domain": domain,
                "creation_date": domain_info.get("date_created"),
                "dnssec_enabled": domain_info.get("dns_sec") == "enabled",
                "total_records": len(records),
                "record_types": {},
                "recommendations": [],
            }

            # Count record types
            for record in records:
                record_type = record.get("type", "UNKNOWN")
                analysis["record_types"][record_type] = (
                    analysis["record_types"].get(record_type, 0) + 1
                )

            # Generate recommendations based on our analysis
            analysis["recommendations"] = self._generate_recommendations(analysis)

            return analysis

        except Exception as e:
            return {
                "domain": domain,
                "error": str(e),
                "recommendations": [
                    "Unable to analyze domain - check if domain exists in Vultr DNS"
                ],
            }

    def _generate_recommendations(self, analysis: dict[str, Any]) -> list[str]:
        """Generate recommendations based on DNS analysis.

        Args:
            analysis: The analysis data structure

        Returns:
            List of recommendation strings
        """
        recommendations = []
        record_types = analysis["record_types"]

        # Check for essential records
        if "A" not in record_types and "AAAA" not in record_types:
            recommendations.append("Consider adding A or AAAA records for web hosting")

        if "MX" not in record_types:
            recommendations.append("No MX records found - add if email is needed")

        if not analysis["dnssec_enabled"]:
            recommendations.append("Consider enabling DNSSEC for enhanced security")

        if "TXT" not in record_types:
            recommendations.append(
                "Consider adding TXT records for domain verification and security policies"
            )

        # Check for common security records
        if "CAA" not in record_types:
            recommendations.append(
                "Consider adding CAA records for certificate authority authorization"
            )

        # Check for modern records
        if "AAAA" not in record_types and "A" in record_types:
            recommendations.append("Consider adding AAAA records for IPv6 support")

        # Performance recommendations
        if record_types.get("A", 0) > 5:
            recommendations.append(
                "High number of A records - consider using a CDN or load balancer"
            )

        return recommendations
