"""
Vultr DNS FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr DNS domains and records.
"""

from typing import Optional, List, Dict, Any
from fastmcp import FastMCP


def create_dns_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr DNS management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with DNS management tools
    """
    mcp = FastMCP(name="vultr-dns")
    
    # DNS Domain resources
    @mcp.resource("domains://list")
    async def list_domains_resource() -> List[Dict[str, Any]]:
        """List all DNS domains in your Vultr account."""
        return await vultr_client.list_domains()
    
    @mcp.resource("domains://{domain}")
    async def get_domain_resource(domain: str) -> Dict[str, Any]:
        """Get details for a specific DNS domain.
        
        Args:
            domain: The domain name to get details for
        """
        return await vultr_client.get_domain(domain)
    
    @mcp.resource("domains://{domain}/records")
    async def list_records_resource(domain: str) -> List[Dict[str, Any]]:
        """List all DNS records for a domain.
        
        Args:
            domain: The domain name to list records for
        """
        return await vultr_client.list_records(domain)
    
    @mcp.resource("domains://{domain}/records/{record_id}")
    async def get_record_resource(domain: str, record_id: str) -> Dict[str, Any]:
        """Get details for a specific DNS record.
        
        Args:
            domain: The domain name
            record_id: The record ID to get details for
        """
        return await vultr_client.get_record(domain, record_id)
    
    @mcp.resource("domains://{domain}/analysis")
    async def analyze_domain_resource(domain: str) -> Dict[str, Any]:
        """Analyze DNS records for a domain and provide recommendations.
        
        Args:
            domain: The domain name to analyze
        """
        return await vultr_client.analyze_records(domain)
    
    @mcp.resource("domains://{domain}/zone-file")
    async def export_zone_file_resource(domain: str) -> str:
        """Export domain records as standard DNS zone file format.
        
        Args:
            domain: The domain name to export
        """
        return await vultr_client.export_zone_file(domain)
    
    # DNS Domain tools
    @mcp.tool
    async def list_domains() -> List[Dict[str, Any]]:
        """List all DNS domains in your Vultr account.
        
        Returns:
            List of domain objects with details including:
            - domain: Domain name
            - date_created: Creation date
            - dns_sec: DNSSEC status
        """
        return await vultr_client.list_domains()
    
    @mcp.tool
    async def get_domain(domain: str) -> Dict[str, Any]:
        """Get details for a specific DNS domain.
        
        Args:
            domain: The domain name to get details for
            
        Returns:
            Domain details including creation date and DNSSEC status
        """
        return await vultr_client.get_domain(domain)
    
    @mcp.tool
    async def create_domain(domain: str, ip: str, dns_sec: str = "disabled") -> Dict[str, Any]:
        """Create a new DNS domain.
        
        Args:
            domain: The domain name to create
            ip: The default IP address for the domain
            dns_sec: Enable DNSSEC (enabled/disabled, default: disabled)
            
        Returns:
            Created domain information
        """
        return await vultr_client.create_domain(domain, ip, dns_sec)
    
    @mcp.tool
    async def delete_domain(domain: str) -> Dict[str, str]:
        """Delete a DNS domain and all its records.
        
        Args:
            domain: The domain name to delete
            
        Returns:
            Status message confirming deletion
        """
        await vultr_client.delete_domain(domain)
        return {"status": "success", "message": f"Domain {domain} deleted successfully"}
    
    # DNS Record tools
    @mcp.tool
    async def list_records(domain: str) -> List[Dict[str, Any]]:
        """List all DNS records for a domain.
        
        Args:
            domain: The domain name to list records for
            
        Returns:
            List of DNS records with details
        """
        return await vultr_client.list_records(domain)
    
    @mcp.tool
    async def get_record(domain: str, record_id: str) -> Dict[str, Any]:
        """Get details for a specific DNS record.
        
        Args:
            domain: The domain name
            record_id: The record ID to get details for
            
        Returns:
            DNS record details
        """
        return await vultr_client.get_record(domain, record_id)
    
    @mcp.tool
    async def create_record(
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
            
        Returns:
            Created record information
        """
        return await vultr_client.create_record(domain, record_type, name, data, ttl, priority)
    
    @mcp.tool
    async def update_record(
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
            
        Returns:
            Updated record information
        """
        return await vultr_client.update_record(domain, record_id, name, data, ttl, priority)
    
    @mcp.tool
    async def delete_record(domain: str, record_id: str) -> Dict[str, str]:
        """Delete a DNS record.
        
        Args:
            domain: The domain name
            record_id: The record ID to delete
            
        Returns:
            Status message confirming deletion
        """
        await vultr_client.delete_record(domain, record_id)
        return {"status": "success", "message": f"Record {record_id} deleted successfully"}
    
    @mcp.tool
    async def validate_record(
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
            
        Returns:
            Validation results with any errors or warnings
        """
        return await vultr_client.validate_record(record_type, name, data, ttl, priority)
    
    @mcp.tool
    async def analyze_domain(domain: str) -> Dict[str, Any]:
        """Analyze DNS configuration for a domain and provide recommendations.
        
        Args:
            domain: The domain name to analyze
            
        Returns:
            Analysis results with recommendations for improvements
        """
        return await vultr_client.analyze_records(domain)
    
    @mcp.tool
    async def setup_website(domain: str, ip: str, www_enabled: bool = True) -> List[Dict[str, Any]]:
        """Set up basic DNS records for a website.
        
        Args:
            domain: The domain name
            ip: The website IP address
            www_enabled: Whether to create www subdomain record (default: True)
            
        Returns:
            List of created DNS records
        """
        records = []
        
        # Create A record for domain
        records.append(await vultr_client.create_record(domain, "A", "@", ip))
        
        # Create www CNAME if enabled
        if www_enabled:
            records.append(await vultr_client.create_record(domain, "CNAME", "www", domain))
        
        return records
    
    @mcp.tool
    async def export_zone_file(domain: str) -> str:
        """Export domain records as standard DNS zone file format.
        
        Args:
            domain: The domain name to export
            
        Returns:
            DNS zone file content as string
        """
        return await vultr_client.export_zone_file(domain)
    
    @mcp.tool
    async def import_zone_file(domain: str, zone_data: str, dry_run: bool = False) -> List[Dict[str, Any]]:
        """Import DNS records from zone file format.
        
        Args:
            domain: The domain name to import records to
            zone_data: DNS zone file content as string
            dry_run: If True, only validate and return what would be created without making changes
            
        Returns:
            List of created records or validation results
        """
        return await vultr_client.import_zone_file(domain, zone_data, dry_run)
    
    return mcp