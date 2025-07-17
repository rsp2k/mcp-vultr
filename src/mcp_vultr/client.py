"""
Vultr DNS Client - Convenience client for Vultr DNS operations.

This module provides a high-level client interface for common DNS operations
without requiring the full MCP server setup.
"""

from typing import Any, Dict, List, Optional, Union

from .server import VultrDNSServer


class VultrDNSClient:
    """
    High-level client for Vultr DNS operations.
    
    This client provides convenient methods for common DNS operations
    with built-in validation and error handling.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the Vultr DNS client.
        
        Args:
            api_key: Your Vultr API key
        """
        self.server = VultrDNSServer(api_key)
    
    async def domains(self) -> List[Dict[str, Any]]:
        """Get all domains in your account."""
        return await self.server.list_domains()
    
    async def domain(self, name: str) -> Dict[str, Any]:
        """Get details for a specific domain."""
        return await self.server.get_domain(name)
    
    async def add_domain(self, domain: str, ip: str) -> Dict[str, Any]:
        """
        Add a new domain with default A record.
        
        Args:
            domain: Domain name to add
            ip: IPv4 address for default A record
        """
        return await self.server.create_domain(domain, ip)
    
    async def remove_domain(self, domain: str) -> bool:
        """
        Remove a domain and all its records.
        
        Args:
            domain: Domain name to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self.server.delete_domain(domain)
            return True
        except Exception:
            return False
    
    async def records(self, domain: str) -> List[Dict[str, Any]]:
        """Get all DNS records for a domain."""
        return await self.server.list_records(domain)
    
    async def record(self, domain: str, record_id: str) -> Dict[str, Any]:
        """Get details for a specific DNS record."""
        return await self.server.get_record(domain, record_id)
    
    async def add_record(
        self,
        domain: str,
        record_type: str,
        name: str,
        value: str,
        ttl: Optional[int] = None,
        priority: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Add a new DNS record.
        
        Args:
            domain: Domain name
            record_type: Type of record (A, AAAA, CNAME, MX, TXT, NS, SRV)
            name: Record name/subdomain
            value: Record value
            ttl: Time to live (optional)
            priority: Priority for MX/SRV records (optional)
        """
        return await self.server.create_record(
            domain, record_type, name, value, ttl, priority
        )
    
    async def update_record(
        self,
        domain: str,
        record_id: str,
        record_type: str,
        name: str,
        value: str,
        ttl: Optional[int] = None,
        priority: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update an existing DNS record.
        
        Args:
            domain: Domain name
            record_id: ID of record to update
            record_type: Type of record
            name: Record name/subdomain
            value: Record value
            ttl: Time to live (optional)
            priority: Priority for MX/SRV records (optional)
        """
        return await self.server.update_record(
            domain, record_id, record_type, name, value, ttl, priority
        )
    
    async def remove_record(self, domain: str, record_id: str) -> bool:
        """
        Remove a DNS record.
        
        Args:
            domain: Domain name
            record_id: ID of record to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self.server.delete_record(domain, record_id)
            return True
        except Exception:
            return False
    
    # Convenience methods for common record types
    async def add_a_record(
        self, 
        domain: str, 
        name: str, 
        ip: str, 
        ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add an A record pointing to an IPv4 address."""
        return await self.add_record(domain, "A", name, ip, ttl)
    
    async def add_aaaa_record(
        self, 
        domain: str, 
        name: str, 
        ip: str, 
        ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add an AAAA record pointing to an IPv6 address."""
        return await self.add_record(domain, "AAAA", name, ip, ttl)
    
    async def add_cname_record(
        self, 
        domain: str, 
        name: str, 
        target: str, 
        ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add a CNAME record pointing to another domain."""
        return await self.add_record(domain, "CNAME", name, target, ttl)
    
    async def add_mx_record(
        self, 
        domain: str, 
        name: str, 
        mail_server: str, 
        priority: int,
        ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add an MX record for email routing."""
        return await self.add_record(domain, "MX", name, mail_server, ttl, priority)
    
    async def add_txt_record(
        self, 
        domain: str, 
        name: str, 
        text: str, 
        ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add a TXT record for verification or policies."""
        return await self.add_record(domain, "TXT", name, text, ttl)
    
    # Utility methods
    async def find_records_by_type(
        self, 
        domain: str, 
        record_type: str
    ) -> List[Dict[str, Any]]:
        """Find all records of a specific type for a domain."""
        records = await self.records(domain)
        return [r for r in records if r.get('type', '').upper() == record_type.upper()]
    
    async def find_records_by_name(
        self, 
        domain: str, 
        name: str
    ) -> List[Dict[str, Any]]:
        """Find all records with a specific name for a domain."""
        records = await self.records(domain)
        return [r for r in records if r.get('name', '') == name]
    
    async def get_domain_summary(self, domain: str) -> Dict[str, Any]:
        """
        Get a comprehensive summary of a domain's configuration.
        
        Returns:
            Dictionary with domain info, record counts, and basic analysis
        """
        try:
            domain_info = await self.domain(domain)
            records = await self.records(domain)
            
            # Count record types
            record_counts = {}
            for record in records:
                record_type = record.get('type', 'UNKNOWN')
                record_counts[record_type] = record_counts.get(record_type, 0) + 1
            
            # Basic configuration checks
            has_root_a = any(
                r.get('type') == 'A' and r.get('name') in ['@', domain] 
                for r in records
            )
            has_www = any(r.get('name') == 'www' for r in records)
            has_mail = any(r.get('type') == 'MX' for r in records)
            
            return {
                "domain": domain,
                "domain_info": domain_info,
                "total_records": len(records),
                "record_types": record_counts,
                "configuration": {
                    "has_root_record": has_root_a,
                    "has_www_subdomain": has_www,
                    "has_email_setup": has_mail
                },
                "records": records
            }
            
        except Exception as e:
            return {"error": str(e), "domain": domain}
    
    async def setup_basic_website(
        self, 
        domain: str, 
        ip: str, 
        include_www: bool = True,
        ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Set up basic DNS records for a website.
        
        Args:
            domain: Domain name
            ip: Server IP address
            include_www: Whether to create www subdomain (default: True)
            ttl: TTL for records (optional)
            
        Returns:
            Dictionary with results of record creation
        """
        results = {"domain": domain, "created_records": [], "errors": []}
        
        try:
            # Create root A record
            root_result = await self.add_a_record(domain, "@", ip, ttl)
            if "error" not in root_result:
                results["created_records"].append(f"A record for root domain")
            else:
                results["errors"].append(f"Root A record: {root_result['error']}")
            
            # Create www record if requested
            if include_www:
                www_result = await self.add_a_record(domain, "www", ip, ttl)
                if "error" not in www_result:
                    results["created_records"].append(f"A record for www subdomain")
                else:
                    results["errors"].append(f"WWW A record: {www_result['error']}")
            
        except Exception as e:
            results["errors"].append(f"Setup failed: {str(e)}")
        
        return results
    
    async def setup_email(
        self, 
        domain: str, 
        mail_server: str, 
        priority: int = 10,
        ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Set up basic email DNS records.
        
        Args:
            domain: Domain name
            mail_server: Mail server hostname
            priority: MX record priority (default: 10)
            ttl: TTL for records (optional)
            
        Returns:
            Dictionary with results of record creation
        """
        results = {"domain": domain, "created_records": [], "errors": []}
        
        try:
            # Create MX record
            mx_result = await self.add_mx_record(domain, "@", mail_server, priority, ttl)
            if "error" not in mx_result:
                results["created_records"].append(f"MX record for {mail_server}")
            else:
                results["errors"].append(f"MX record: {mx_result['error']}")
            
        except Exception as e:
            results["errors"].append(f"Email setup failed: {str(e)}")
        
        return results
