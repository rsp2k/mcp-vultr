"""
Vultr CDN FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr CDN zones.
"""

from typing import Any

from fastmcp import FastMCP

from .cdn_analyzer import CDNAnalyzer


def create_cdn_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr CDN management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with CDN management tools
    """
    mcp = FastMCP(name="vultr-cdn")
    cdn_analyzer = CDNAnalyzer(vultr_client)

    # Helper function to check if string is UUID format
    def is_uuid_format(value: str) -> bool:
        """Check if a string looks like a UUID."""
        import re

        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))

    # Helper function to get CDN zone ID from domain or ID
    async def get_cdn_zone_id(identifier: str) -> str:
        """Get the CDN zone ID from origin domain or existing ID."""
        if is_uuid_format(identifier):
            return identifier

        zones = await vultr_client.list_cdn_zones()
        for zone in zones:
            if (
                zone.get("origin_domain") == identifier
                or zone.get("cdn_domain") == identifier
            ):
                return zone["id"]

        raise ValueError(f"CDN zone '{identifier}' not found")

    @mcp.tool()
    async def list_cdn_zones() -> list[dict[str, Any]]:
        """
        List all CDN zones.

        Returns:
            List of CDN zones with details
        """
        return await vultr_client.list_cdn_zones()

    @mcp.tool()
    async def get_cdn_zone(zone_identifier: str) -> dict[str, Any]:
        """
        Get details of a specific CDN zone.
        Smart identifier resolution: use origin domain, CDN domain, or UUID.

        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID

        Returns:
            CDN zone details
        """
        zone_id = await get_cdn_zone_id(zone_identifier)
        return await vultr_client.get_cdn_zone(zone_id)

    @mcp.tool()
    async def create_cdn_zone(
        origin_domain: str,
        origin_scheme: str = "https",
        cors_policy: str | None = None,
        gzip_compression: bool | None = None,
        block_ai_bots: bool | None = None,
        block_bad_bots: bool | None = None,
        block_ip_addresses: list[str] | None = None,
        regions: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new CDN zone.

        Args:
            origin_domain: Origin domain for the CDN
            origin_scheme: Origin scheme (http or https)
            cors_policy: CORS policy configuration
            gzip_compression: Enable gzip compression
            block_ai_bots: Block AI/crawler bots
            block_bad_bots: Block known bad bots
            block_ip_addresses: List of IP addresses to block
            regions: List of regions to enable CDN in

        Returns:
            Created CDN zone details
        """
        return await vultr_client.create_cdn_zone(
            origin_domain=origin_domain,
            origin_scheme=origin_scheme,
            cors_policy=cors_policy,
            gzip_compression=gzip_compression,
            block_ai_bots=block_ai_bots,
            block_bad_bots=block_bad_bots,
            block_ip_addresses=block_ip_addresses,
            regions=regions,
        )

    @mcp.tool()
    async def update_cdn_zone(
        zone_identifier: str,
        cors_policy: str | None = None,
        gzip_compression: bool | None = None,
        block_ai_bots: bool | None = None,
        block_bad_bots: bool | None = None,
        block_ip_addresses: list[str] | None = None,
        regions: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Update a CDN zone configuration.
        Smart identifier resolution: use origin domain, CDN domain, or UUID.

        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID
            cors_policy: CORS policy configuration
            gzip_compression: Enable gzip compression
            block_ai_bots: Block AI/crawler bots
            block_bad_bots: Block known bad bots
            block_ip_addresses: List of IP addresses to block
            regions: List of regions to enable CDN in

        Returns:
            Updated CDN zone details
        """
        zone_id = await get_cdn_zone_id(zone_identifier)
        return await vultr_client.update_cdn_zone(
            zone_id,
            cors_policy=cors_policy,
            gzip_compression=gzip_compression,
            block_ai_bots=block_ai_bots,
            block_bad_bots=block_bad_bots,
            block_ip_addresses=block_ip_addresses,
            regions=regions,
        )

    @mcp.tool()
    async def delete_cdn_zone(zone_identifier: str) -> str:
        """
        Delete a CDN zone.
        Smart identifier resolution: use origin domain, CDN domain, or UUID.

        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID to delete

        Returns:
            Success message
        """
        zone_id = await get_cdn_zone_id(zone_identifier)
        await vultr_client.delete_cdn_zone(zone_id)
        return f"Successfully deleted CDN zone {zone_identifier}"

    @mcp.tool()
    async def purge_cdn_zone(zone_identifier: str) -> dict[str, Any]:
        """
        Purge all cached content from a CDN zone.
        Smart identifier resolution: use origin domain, CDN domain, or UUID.

        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID

        Returns:
            Purge operation details
        """
        zone_id = await get_cdn_zone_id(zone_identifier)
        return await vultr_client.purge_cdn_zone(zone_id)

    @mcp.tool()
    async def get_cdn_zone_stats(zone_identifier: str) -> dict[str, Any]:
        """
        Get statistics for a CDN zone.
        Smart identifier resolution: use origin domain, CDN domain, or UUID.

        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID

        Returns:
            CDN zone statistics including bandwidth, requests, and cache hit ratio
        """
        zone_id = await get_cdn_zone_id(zone_identifier)
        return await vultr_client.get_cdn_zone_stats(zone_id)

    @mcp.tool()
    async def get_cdn_zone_logs(
        zone_identifier: str,
        start_date: str | None = None,
        end_date: str | None = None,
        per_page: int | None = 25,
    ) -> dict[str, Any]:
        """
        Get access logs for a CDN zone.
        Smart identifier resolution: use origin domain, CDN domain, or UUID.

        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID
            start_date: Start date for logs (ISO format: YYYY-MM-DD)
            end_date: End date for logs (ISO format: YYYY-MM-DD)
            per_page: Number of items per page (default: 25)

        Returns:
            CDN zone access logs with request details
        """
        zone_id = await get_cdn_zone_id(zone_identifier)
        return await vultr_client.get_cdn_zone_logs(
            zone_id, start_date, end_date, per_page
        )

    @mcp.tool()
    async def create_cdn_ssl_certificate(
        zone_identifier: str,
        certificate: str,
        private_key: str,
        certificate_chain: str | None = None,
    ) -> dict[str, Any]:
        """
        Upload SSL certificate for a CDN zone.
        Smart identifier resolution: use origin domain, CDN domain, or UUID.

        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID
            certificate: SSL certificate content (PEM format)
            private_key: Private key content (PEM format)
            certificate_chain: Certificate chain (optional, PEM format)

        Returns:
            SSL certificate details
        """
        zone_id = await get_cdn_zone_id(zone_identifier)
        return await vultr_client.create_cdn_ssl_certificate(
            zone_id, certificate, private_key, certificate_chain
        )

    @mcp.tool()
    async def get_cdn_ssl_certificate(zone_identifier: str) -> dict[str, Any]:
        """
        Get SSL certificate information for a CDN zone.
        Smart identifier resolution: use origin domain, CDN domain, or UUID.

        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID

        Returns:
            SSL certificate information including expiry and status
        """
        zone_id = await get_cdn_zone_id(zone_identifier)
        return await vultr_client.get_cdn_ssl_certificate(zone_id)

    @mcp.tool()
    async def delete_cdn_ssl_certificate(zone_identifier: str) -> str:
        """
        Remove SSL certificate from a CDN zone.
        Smart identifier resolution: use origin domain, CDN domain, or UUID.

        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID

        Returns:
            Success message
        """
        zone_id = await get_cdn_zone_id(zone_identifier)
        await vultr_client.delete_cdn_ssl_certificate(zone_id)
        return f"Successfully removed SSL certificate from CDN zone {zone_identifier}"

    @mcp.tool()
    async def get_cdn_available_regions() -> list[dict[str, Any]]:
        """
        Get list of available CDN regions.

        Returns:
            List of available CDN regions with details
        """
        return await vultr_client.get_cdn_available_regions()

    @mcp.tool()
    async def analyze_cdn_performance(
        zone_identifier: str, days: int = 7
    ) -> dict[str, Any]:
        """
        Analyze CDN zone performance over the specified period.
        Smart identifier resolution: use origin domain, CDN domain, or UUID.

        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID
            days: Number of days to analyze (default: 7)

        Returns:
            Performance analysis including cache hit ratio, bandwidth usage, and recommendations
        """
        return await cdn_analyzer.analyze_performance(zone_identifier, days)

    @mcp.tool()
    async def setup_cdn_for_website(
        origin_domain: str,
        enable_security: bool = True,
        enable_compression: bool = True,
        regions: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Set up a CDN zone with optimal settings for a website.

        Args:
            origin_domain: Origin domain for the website
            enable_security: Enable bot blocking and security features
            enable_compression: Enable gzip compression
            regions: List of regions to enable (if not specified, uses global)

        Returns:
            Created CDN zone with setup details and next steps
        """
        return await cdn_analyzer.setup_for_website(
            origin_domain=origin_domain,
            enable_security=enable_security,
            enable_compression=enable_compression,
            regions=regions,
        )

    @mcp.tool()
    async def get_cdn_zone_summary(zone_identifier: str) -> dict[str, Any]:
        """
        Get a comprehensive summary of a CDN zone.
        Smart identifier resolution: use origin domain, CDN domain, or UUID.

        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID

        Returns:
            Comprehensive CDN zone summary including configuration, stats, and SSL info
        """
        return await cdn_analyzer.get_zone_summary(zone_identifier)

    return mcp
