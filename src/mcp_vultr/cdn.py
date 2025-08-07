"""
Vultr CDN FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr CDN zones.
"""

from typing import List, Dict, Any, Optional
from fastmcp import FastMCP


def create_cdn_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr CDN management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with CDN management tools
    """
    mcp = FastMCP(name="vultr-cdn")
    
    # Helper function to check if string is UUID format
    def is_uuid_format(value: str) -> bool:
        """Check if a string looks like a UUID."""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))
    
    # Helper function to get CDN zone ID from domain or ID
    async def get_cdn_zone_id(identifier: str) -> str:
        """Get the CDN zone ID from origin domain or existing ID."""
        if is_uuid_format(identifier):
            return identifier
        
        zones = await vultr_client.list_cdn_zones()
        for zone in zones:
            if (zone.get("origin_domain") == identifier or 
                zone.get("cdn_domain") == identifier):
                return zone["id"]
        
        raise ValueError(f"CDN zone '{identifier}' not found")
    
    @mcp.tool()
    async def list_cdn_zones() -> List[Dict[str, Any]]:
        """
        List all CDN zones.
        
        Returns:
            List of CDN zones with details
        """
        return await vultr_client.list_cdn_zones()
    
    @mcp.tool()
    async def get_cdn_zone(zone_identifier: str) -> Dict[str, Any]:
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
        cors_policy: Optional[str] = None,
        gzip_compression: Optional[bool] = None,
        block_ai_bots: Optional[bool] = None,
        block_bad_bots: Optional[bool] = None,
        block_ip_addresses: Optional[List[str]] = None,
        regions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
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
            regions=regions
        )
    
    @mcp.tool()
    async def update_cdn_zone(
        zone_identifier: str,
        cors_policy: Optional[str] = None,
        gzip_compression: Optional[bool] = None,
        block_ai_bots: Optional[bool] = None,
        block_bad_bots: Optional[bool] = None,
        block_ip_addresses: Optional[List[str]] = None,
        regions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
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
            regions=regions
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
    async def purge_cdn_zone(zone_identifier: str) -> Dict[str, Any]:
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
    async def get_cdn_zone_stats(zone_identifier: str) -> Dict[str, Any]:
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
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        per_page: Optional[int] = 25
    ) -> Dict[str, Any]:
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
        certificate_chain: Optional[str] = None
    ) -> Dict[str, Any]:
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
    async def get_cdn_ssl_certificate(zone_identifier: str) -> Dict[str, Any]:
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
    async def get_cdn_available_regions() -> List[Dict[str, Any]]:
        """
        Get list of available CDN regions.
        
        Returns:
            List of available CDN regions with details
        """
        return await vultr_client.get_cdn_available_regions()
    
    @mcp.tool()
    async def analyze_cdn_performance(zone_identifier: str, days: int = 7) -> Dict[str, Any]:
        """
        Analyze CDN zone performance over the specified period.
        Smart identifier resolution: use origin domain, CDN domain, or UUID.
        
        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID
            days: Number of days to analyze (default: 7)
            
        Returns:
            Performance analysis including cache hit ratio, bandwidth usage, and recommendations
        """
        zone_id = await get_cdn_zone_id(zone_identifier)
        
        # Get zone details and stats
        zone_info = await vultr_client.get_cdn_zone(zone_id)
        stats = await vultr_client.get_cdn_zone_stats(zone_id)
        
        # Calculate performance metrics
        total_requests = stats.get("total_requests", 0)
        cache_hits = stats.get("cache_hits", 0)
        bandwidth_used = stats.get("bandwidth_bytes", 0)
        
        cache_hit_ratio = (cache_hits / total_requests * 100) if total_requests > 0 else 0
        avg_daily_requests = total_requests / days if days > 0 else 0
        avg_daily_bandwidth = bandwidth_used / days if days > 0 else 0
        
        # Generate recommendations
        recommendations = []
        if cache_hit_ratio < 80:
            recommendations.append("Cache hit ratio is below 80%. Consider optimizing cache headers.")
        if avg_daily_bandwidth > 1000000000:  # 1GB per day
            recommendations.append("High bandwidth usage detected. Consider image optimization.")
        if zone_info.get("gzip_compression") is False:
            recommendations.append("Enable gzip compression to reduce bandwidth usage.")
        if not zone_info.get("block_bad_bots"):
            recommendations.append("Consider enabling bad bot blocking for better security.")
        
        return {
            "zone_domain": zone_info.get("origin_domain"),
            "analysis_period_days": days,
            "performance_metrics": {
                "total_requests": total_requests,
                "cache_hits": cache_hits,
                "cache_hit_ratio": round(cache_hit_ratio, 2),
                "bandwidth_used_bytes": bandwidth_used,
                "avg_daily_requests": round(avg_daily_requests),
                "avg_daily_bandwidth_bytes": round(avg_daily_bandwidth)
            },
            "current_configuration": {
                "gzip_compression": zone_info.get("gzip_compression"),
                "block_ai_bots": zone_info.get("block_ai_bots"),
                "block_bad_bots": zone_info.get("block_bad_bots"),
                "regions": zone_info.get("regions", [])
            },
            "recommendations": recommendations,
            "status": "excellent" if cache_hit_ratio >= 90 else "good" if cache_hit_ratio >= 80 else "needs_optimization"
        }
    
    @mcp.tool()
    async def setup_cdn_for_website(
        origin_domain: str,
        enable_security: bool = True,
        enable_compression: bool = True,
        regions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
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
        # Create CDN zone with optimized settings
        cdn_zone = await vultr_client.create_cdn_zone(
            origin_domain=origin_domain,
            origin_scheme="https",
            gzip_compression=enable_compression,
            block_ai_bots=enable_security,
            block_bad_bots=enable_security,
            regions=regions
        )
        
        setup_info = {
            "cdn_zone": cdn_zone,
            "cdn_domain": cdn_zone.get("cdn_domain"),
            "next_steps": [
                f"Update your DNS to point to {cdn_zone.get('cdn_domain')}",
                "Test the CDN by accessing your website through the CDN domain",
                "Monitor performance using the CDN statistics",
                "Consider uploading an SSL certificate for HTTPS support"
            ],
            "optimization_tips": [
                "Set appropriate cache headers on your origin server",
                "Optimize images and static assets for better performance",
                "Monitor cache hit ratio and adjust cache settings as needed"
            ]
        }
        
        if enable_security:
            setup_info["security_features"] = [
                "AI/crawler bot blocking enabled",
                "Bad bot blocking enabled"
            ]
        
        if enable_compression:
            setup_info["performance_features"] = [
                "Gzip compression enabled for faster load times"
            ]
        
        return setup_info
    
    @mcp.tool()
    async def get_cdn_zone_summary(zone_identifier: str) -> Dict[str, Any]:
        """
        Get a comprehensive summary of a CDN zone.
        Smart identifier resolution: use origin domain, CDN domain, or UUID.
        
        Args:
            zone_identifier: The CDN zone origin domain, CDN domain, or ID
            
        Returns:
            Comprehensive CDN zone summary including configuration, stats, and SSL info
        """
        zone_id = await get_cdn_zone_id(zone_identifier)
        
        # Get all relevant information
        zone_info = await vultr_client.get_cdn_zone(zone_id)
        
        try:
            stats = await vultr_client.get_cdn_zone_stats(zone_id)
        except Exception:
            stats = {"error": "Stats unavailable"}
        
        try:
            ssl_info = await vultr_client.get_cdn_ssl_certificate(zone_id)
        except Exception:
            ssl_info = {"status": "No SSL certificate configured"}
        
        return {
            "zone_info": zone_info,
            "statistics": stats,
            "ssl_certificate": ssl_info,
            "summary": {
                "origin_domain": zone_info.get("origin_domain"),
                "cdn_domain": zone_info.get("cdn_domain"),
                "status": zone_info.get("status"),
                "regions": zone_info.get("regions", []),
                "security_enabled": zone_info.get("block_bad_bots", False),
                "compression_enabled": zone_info.get("gzip_compression", False),
                "ssl_configured": ssl_info.get("status") != "No SSL certificate configured"
            }
        }
    
    return mcp