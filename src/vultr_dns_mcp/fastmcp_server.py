"""
Vultr DNS FastMCP Server Implementation.

This module contains the FastMCP server implementation for managing DNS records 
through the Vultr API using the FastMCP framework.
"""

import os
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP
from .server import VultrDNSServer


def create_vultr_mcp_server(api_key: Optional[str] = None) -> FastMCP:
    """
    Create a FastMCP server for Vultr DNS management.
    
    Args:
        api_key: Vultr API key. If not provided, will read from VULTR_API_KEY env var.
        
    Returns:
        Configured FastMCP server instance
    """
    if not api_key:
        api_key = os.getenv("VULTR_API_KEY")
    
    if not api_key:
        raise ValueError(
            "VULTR_API_KEY must be provided either as parameter or environment variable"
        )
    
    # Create FastMCP server
    mcp = FastMCP(name="vultr-dns-mcp")
    
    # Initialize Vultr client
    vultr_client = VultrDNSServer(api_key)
    
    @mcp.resource("dns://domains")
    async def list_dns_domains() -> List[Dict[str, Any]]:
        """List all DNS domains in your Vultr account."""
        return await vultr_client.list_domains()
    
    @mcp.resource("dns://domains/{domain}")
    async def get_dns_domain(domain: str) -> Dict[str, Any]:
        """Get details for a specific DNS domain.
        
        Args:
            domain: The domain name to get details for
        """
        return await vultr_client.get_domain(domain)
    
    @mcp.tool
    async def create_dns_domain(domain: str, ip: str, dns_sec: str = "disabled") -> Dict[str, Any]:
        """Create a new DNS domain.
        
        Args:
            domain: The domain name to create
            ip: The default IP address for the domain
            dns_sec: Enable DNSSEC (enabled/disabled, default: disabled)
        """
        return await vultr_client.create_domain(domain, ip, dns_sec)
    
    @mcp.tool
    async def delete_dns_domain(domain: str) -> Dict[str, str]:
        """Delete a DNS domain and all its records.
        
        Args:
            domain: The domain name to delete
        """
        await vultr_client.delete_domain(domain)
        return {"status": "success", "message": f"Domain {domain} deleted successfully"}
    
    @mcp.resource("dns://domains/{domain}/records")
    async def list_dns_records(domain: str) -> List[Dict[str, Any]]:
        """List all DNS records for a domain.
        
        Args:
            domain: The domain name to list records for
        """
        return await vultr_client.list_records(domain)
    
    @mcp.resource("dns://domains/{domain}/records/{record_id}")
    async def get_dns_record(domain: str, record_id: str) -> Dict[str, Any]:
        """Get details for a specific DNS record.
        
        Args:
            domain: The domain name
            record_id: The record ID to get details for
        """
        return await vultr_client.get_record(domain, record_id)
    
    @mcp.tool
    async def create_dns_record(
        domain: str,
        record_type: str,
        name: str,
        data: str,
        ttl: int = 300,
        priority: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new DNS record.
        
        Args:
            domain: The domain name
            record_type: Record type (A, AAAA, CNAME, MX, TXT, NS, SRV)
            name: Record name/subdomain
            data: Record data/value
            ttl: Time to live in seconds (default: 300)
            priority: Priority for MX/SRV records
        """
        return await vultr_client.create_record(domain, record_type, name, data, ttl, priority)
    
    @mcp.tool
    async def update_dns_record(
        domain: str,
        record_id: str,
        name: Optional[str] = None,
        data: Optional[str] = None,
        ttl: Optional[int] = None,
        priority: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update an existing DNS record.
        
        Args:
            domain: The domain name
            record_id: The record ID to update
            name: New record name (optional)
            data: New record data (optional)
            ttl: New TTL value (optional)
            priority: New priority for MX/SRV records (optional)
        """
        return await vultr_client.update_record(domain, record_id, name, data, ttl, priority)
    
    @mcp.tool
    async def delete_dns_record(domain: str, record_id: str) -> Dict[str, str]:
        """Delete a DNS record.
        
        Args:
            domain: The domain name
            record_id: The record ID to delete
        """
        await vultr_client.delete_record(domain, record_id)
        return {"status": "success", "message": f"Record {record_id} deleted successfully"}
    
    @mcp.tool
    async def validate_dns_record(
        record_type: str,
        name: str,
        data: str,
        ttl: int = 300,
        priority: Optional[int] = None
    ) -> Dict[str, Any]:
        """Validate a DNS record before creation.
        
        Args:
            record_type: Record type (A, AAAA, CNAME, MX, TXT, NS, SRV)
            name: Record name/subdomain
            data: Record data/value
            ttl: Time to live in seconds
            priority: Priority for MX/SRV records
        """
        return await vultr_client.validate_record(record_type, name, data, ttl, priority)
    
    @mcp.resource("dns://domains/{domain}/analysis")
    async def analyze_dns_records(domain: str) -> Dict[str, Any]:
        """Analyze DNS records for a domain and provide recommendations.
        
        Args:
            domain: The domain name to analyze
        """
        return await vultr_client.analyze_records(domain)
    
    @mcp.tool
    async def setup_website_dns(domain: str, ip: str, www_enabled: bool = True) -> List[Dict[str, Any]]:
        """Set up basic DNS records for a website.
        
        Args:
            domain: The domain name
            ip: The website IP address
            www_enabled: Whether to create www subdomain record (default: True)
        """
        records = []
        
        # Create A record for domain
        records.append(await vultr_client.create_record(domain, "A", "@", ip))
        
        # Create www CNAME if enabled
        if www_enabled:
            records.append(await vultr_client.create_record(domain, "CNAME", "www", domain))
        
        return records
    
    # Tool wrappers for resources (for compatibility with Claude Desktop)
    @mcp.tool
    async def list_domains_tool() -> List[Dict[str, Any]]:
        """List all DNS domains in your Vultr account.
        
        This is a tool wrapper for the dns://domains resource.
        """
        return await vultr_client.list_domains()
    
    @mcp.tool
    async def get_domain_tool(domain: str) -> Dict[str, Any]:
        """Get details for a specific DNS domain.
        
        Args:
            domain: The domain name to get details for
            
        This is a tool wrapper for the dns://domains/{domain} resource.
        """
        return await vultr_client.get_domain(domain)
    
    @mcp.tool
    async def list_records_tool(domain: str) -> List[Dict[str, Any]]:
        """List all DNS records for a domain.
        
        Args:
            domain: The domain name to list records for
            
        This is a tool wrapper for the dns://domains/{domain}/records resource.
        """
        return await vultr_client.list_records(domain)
    
    @mcp.tool
    async def get_record_tool(domain: str, record_id: str) -> Dict[str, Any]:
        """Get details for a specific DNS record.
        
        Args:
            domain: The domain name
            record_id: The record ID to get details for
            
        This is a tool wrapper for the dns://domains/{domain}/records/{record_id} resource.
        """
        return await vultr_client.get_record(domain, record_id)
    
    @mcp.tool
    async def analyze_domain_tool(domain: str) -> Dict[str, Any]:
        """Analyze DNS configuration for a domain and provide recommendations.
        
        Args:
            domain: The domain name to analyze
            
        This is a tool wrapper for the dns://domains/{domain}/analysis resource.
        """
        return await vultr_client.analyze_records(domain)
    
    return mcp


def run_server(api_key: Optional[str] = None) -> None:
    """
    Create and run a Vultr DNS FastMCP server.
    
    Args:
        api_key: Vultr API key. If not provided, will read from VULTR_API_KEY env var.
    """
    mcp = create_vultr_mcp_server(api_key)
    mcp.run()


if __name__ == "__main__":
    run_server()