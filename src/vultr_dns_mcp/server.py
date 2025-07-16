"""
Vultr DNS MCP Server Implementation.

This module contains the main VultrDNSServer class and MCP server implementation
for managing DNS records through the Vultr API.
"""

import ipaddress
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent
from pydantic import BaseModel


class VultrAPIError(Exception):
    """Base exception for Vultr API errors."""
    
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Vultr API error {status_code}: {message}")


class VultrAuthError(VultrAPIError):
    """Raised when API authentication fails (401, 403)."""
    pass


class VultrRateLimitError(VultrAPIError):
    """Raised when API rate limit is exceeded (429)."""
    pass


class VultrResourceNotFoundError(VultrAPIError):
    """Raised when requested resource is not found (404)."""
    pass


class VultrValidationError(VultrAPIError):
    """Raised when request validation fails (400, 422)."""
    pass


class VultrDNSServer:
    """
    Vultr DNS API client for managing domains and DNS records.
    
    This class provides async methods for all DNS operations including
    domain management and record CRUD operations.
    """
    
    API_BASE = "https://api.vultr.com/v2"
    
    def __init__(self, api_key: str):
        """
        Initialize the Vultr DNS server.
        
        Args:
            api_key: Your Vultr API key
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the Vultr API."""
        url = f"{self.API_BASE}{endpoint}"
        
        # Configure timeout: 30 seconds total, 10 seconds to connect
        timeout = httpx.Timeout(30.0, connect=10.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data
            )
            
            if response.status_code not in [200, 201, 204]:
                # Raise specific exceptions based on status code
                if response.status_code == 401:
                    raise VultrAuthError(response.status_code, "Invalid API key")
                elif response.status_code == 403:
                    raise VultrAuthError(response.status_code, "Insufficient permissions")
                elif response.status_code == 404:
                    raise VultrResourceNotFoundError(response.status_code, "Resource not found")
                elif response.status_code == 429:
                    raise VultrRateLimitError(response.status_code, "Rate limit exceeded")
                elif response.status_code in [400, 422]:
                    raise VultrValidationError(response.status_code, response.text)
                else:
                    raise VultrAPIError(response.status_code, response.text)
            
            if response.status_code == 204:
                return {}
            
            return response.json()

    # Domain Management Methods
    async def list_domains(self) -> List[Dict[str, Any]]:
        """List all DNS domains."""
        result = await self._make_request("GET", "/domains")
        return result.get("domains", [])
    
    async def get_domain(self, domain: str) -> Dict[str, Any]:
        """Get details for a specific domain."""
        return await self._make_request("GET", f"/domains/{domain}")
    
    async def create_domain(self, domain: str, ip: str) -> Dict[str, Any]:
        """Create a new DNS domain."""
        data = {"domain": domain, "ip": ip}
        return await self._make_request("POST", "/domains", data)
    
    async def delete_domain(self, domain: str) -> Dict[str, Any]:
        """Delete a DNS domain."""
        return await self._make_request("DELETE", f"/domains/{domain}")
    
    # DNS Record Management Methods
    async def list_records(self, domain: str) -> List[Dict[str, Any]]:
        """List all DNS records for a domain."""
        result = await self._make_request("GET", f"/domains/{domain}/records")
        return result.get("records", [])
    
    async def get_record(self, domain: str, record_id: str) -> Dict[str, Any]:
        """Get a specific DNS record."""
        return await self._make_request("GET", f"/domains/{domain}/records/{record_id}")
    
    async def create_record(
        self, 
        domain: str, 
        record_type: str, 
        name: str, 
        data: str, 
        ttl: Optional[int] = None, 
        priority: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new DNS record."""
        payload = {
            "type": record_type,
            "name": name,
            "data": data
        }
        
        if ttl is not None:
            payload["ttl"] = ttl
        if priority is not None:
            payload["priority"] = priority
            
        return await self._make_request("POST", f"/domains/{domain}/records", payload)
    
    async def update_record(
        self, 
        domain: str, 
        record_id: str, 
        record_type: str, 
        name: str, 
        data: str, 
        ttl: Optional[int] = None, 
        priority: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update an existing DNS record."""
        payload = {
            "type": record_type,
            "name": name,
            "data": data
        }
        
        if ttl is not None:
            payload["ttl"] = ttl
        if priority is not None:
            payload["priority"] = priority
            
        return await self._make_request("PATCH", f"/domains/{domain}/records/{record_id}", payload)
    
    async def delete_record(self, domain: str, record_id: str) -> Dict[str, Any]:
        """Delete a DNS record."""
        return await self._make_request("DELETE", f"/domains/{domain}/records/{record_id}")


def create_mcp_server(api_key: Optional[str] = None) -> Server:
    """
    Create and configure an MCP server for Vultr DNS management.
    
    Args:
        api_key: Vultr API key. If not provided, will read from VULTR_API_KEY env var.
        
    Returns:
        Configured MCP server instance
        
    Raises:
        ValueError: If API key is not provided and not found in environment
    """
    if api_key is None:
        api_key = os.getenv("VULTR_API_KEY")
    
    if not api_key:
        raise ValueError(
            "VULTR_API_KEY must be provided either as parameter or environment variable"
        )
    
    # Initialize MCP server
    server = Server("vultr-dns-mcp")
    
    # Initialize Vultr client
    vultr_client = VultrDNSServer(api_key)
    
    # Add resources for client discovery
    @server.list_resources()
    async def list_resources() -> List[Resource]:
        """List available resources."""
        return [
            Resource(
                uri="vultr://domains",
                name="DNS Domains",
                description="All DNS domains in your Vultr account",
                mimeType="application/json"
            ),
            Resource(
                uri="vultr://capabilities", 
                name="Server Capabilities",
                description="Vultr DNS server capabilities and supported features",
                mimeType="application/json"
            )
        ]
    
    @server.read_resource()
    async def read_resource(uri: str) -> str:
        """Read a specific resource."""
        if uri == "vultr://domains":
            try:
                domains = await vultr_client.list_domains()
                return str(domains)
            except Exception as e:
                return f"Error loading domains: {str(e)}"
        
        elif uri == "vultr://capabilities":
            capabilities = {
                "supported_record_types": [
                    {
                        "type": "A",
                        "description": "IPv4 address record",
                        "example": "192.168.1.100",
                        "requires_priority": False
                    },
                    {
                        "type": "AAAA", 
                        "description": "IPv6 address record",
                        "example": "2001:db8::1",
                        "requires_priority": False
                    },
                    {
                        "type": "CNAME",
                        "description": "Canonical name record (alias)",
                        "example": "example.com",
                        "requires_priority": False
                    },
                    {
                        "type": "MX",
                        "description": "Mail exchange record",
                        "example": "mail.example.com",
                        "requires_priority": True
                    },
                    {
                        "type": "TXT",
                        "description": "Text record for verification and SPF",
                        "example": "v=spf1 include:_spf.google.com ~all",
                        "requires_priority": False
                    },
                    {
                        "type": "NS",
                        "description": "Name server record",
                        "example": "ns1.example.com",
                        "requires_priority": False
                    },
                    {
                        "type": "SRV",
                        "description": "Service record",
                        "example": "0 5 443 example.com",
                        "requires_priority": True
                    }
                ],
                "operations": {
                    "domains": ["list", "create", "delete", "get"],
                    "records": ["list", "create", "update", "delete", "get"]
                },
                "default_ttl": 300,
                "min_ttl": 60,
                "max_ttl": 86400
            }
            return str(capabilities)
        
        elif uri.startswith("vultr://records/"):
            domain = uri.replace("vultr://records/", "")
            try:
                records = await vultr_client.list_records(domain)
                return str({
                    "domain": domain,
                    "records": records,
                    "record_count": len(records)
                })
            except Exception as e:
                return f"Error loading records for {domain}: {str(e)}"
        
        return "Resource not found"
    
    # Define MCP tools
    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List available tools."""
        return [
            Tool(
                name="list_dns_domains",
                description="List all DNS domains in your Vultr account",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_dns_domain",
                description="Get detailed information for a specific DNS domain",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name to retrieve (e.g., 'example.com')"
                        }
                    },
                    "required": ["domain"]
                }
            ),
            Tool(
                name="create_dns_domain",
                description="Create a new DNS domain with a default A record",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name to create (e.g., 'newdomain.com')"
                        },
                        "ip": {
                            "type": "string",
                            "description": "IPv4 address for the default A record (e.g., '192.168.1.100')"
                        }
                    },
                    "required": ["domain", "ip"]
                }
            ),
            Tool(
                name="delete_dns_domain",
                description="Delete a DNS domain and ALL its associated records",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name to delete (e.g., 'example.com')"
                        }
                    },
                    "required": ["domain"]
                }
            ),
            Tool(
                name="list_dns_records",
                description="List all DNS records for a specific domain",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name (e.g., 'example.com')"
                        }
                    },
                    "required": ["domain"]
                }
            ),
            Tool(
                name="get_dns_record",
                description="Get detailed information for a specific DNS record",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name (e.g., 'example.com')"
                        },
                        "record_id": {
                            "type": "string",
                            "description": "The unique record identifier"
                        }
                    },
                    "required": ["domain", "record_id"]
                }
            ),
            Tool(
                name="create_dns_record",
                description="Create a new DNS record for a domain",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name (e.g., 'example.com')"
                        },
                        "record_type": {
                            "type": "string",
                            "description": "Record type (A, AAAA, CNAME, MX, TXT, NS, SRV)"
                        },
                        "name": {
                            "type": "string",
                            "description": "Record name/subdomain"
                        },
                        "data": {
                            "type": "string",
                            "description": "Record value"
                        },
                        "ttl": {
                            "type": "integer",
                            "description": "Time to live in seconds (60-86400, default: 300)"
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Priority for MX/SRV records (0-65535)"
                        }
                    },
                    "required": ["domain", "record_type", "name", "data"]
                }
            ),
            Tool(
                name="update_dns_record",
                description="Update an existing DNS record with new configuration",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name (e.g., 'example.com')"
                        },
                        "record_id": {
                            "type": "string",
                            "description": "The unique identifier of the record to update"
                        },
                        "record_type": {
                            "type": "string",
                            "description": "New record type (A, AAAA, CNAME, MX, TXT, NS, SRV)"
                        },
                        "name": {
                            "type": "string",
                            "description": "New record name/subdomain"
                        },
                        "data": {
                            "type": "string",
                            "description": "New record value"
                        },
                        "ttl": {
                            "type": "integer",
                            "description": "New TTL in seconds (60-86400, optional)"
                        },
                        "priority": {
                            "type": "integer",
                            "description": "New priority for MX/SRV records (optional)"
                        }
                    },
                    "required": ["domain", "record_id", "record_type", "name", "data"]
                }
            ),
            Tool(
                name="delete_dns_record",
                description="Delete a specific DNS record",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name (e.g., 'example.com')"
                        },
                        "record_id": {
                            "type": "string",
                            "description": "The unique identifier of the record to delete"
                        }
                    },
                    "required": ["domain", "record_id"]
                }
            ),
            Tool(
                name="validate_dns_record",
                description="Validate DNS record parameters before creation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "record_type": {
                            "type": "string",
                            "description": "The record type (A, AAAA, CNAME, MX, TXT, NS, SRV)"
                        },
                        "name": {
                            "type": "string",
                            "description": "The record name/subdomain"
                        },
                        "data": {
                            "type": "string",
                            "description": "The record data/value"
                        },
                        "ttl": {
                            "type": "integer",
                            "description": "Time to live in seconds (optional)"
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Priority for MX/SRV records (optional)"
                        }
                    },
                    "required": ["record_type", "name", "data"]
                }
            ),
            Tool(
                name="analyze_dns_records",
                description="Analyze DNS configuration for a domain and provide insights",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name to analyze (e.g., 'example.com')"
                        }
                    },
                    "required": ["domain"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle tool calls."""
        try:
            if name == "list_dns_domains":
                domains = await vultr_client.list_domains()
                return [TextContent(type="text", text=str(domains))]
            
            elif name == "get_dns_domain":
                domain = arguments["domain"]
                result = await vultr_client.get_domain(domain)
                return [TextContent(type="text", text=str(result))]
            
            elif name == "create_dns_domain":
                domain = arguments["domain"]
                ip = arguments["ip"]
                result = await vultr_client.create_domain(domain, ip)
                return [TextContent(type="text", text=str(result))]
            
            elif name == "delete_dns_domain":
                domain = arguments["domain"]
                await vultr_client.delete_domain(domain)
                return [TextContent(type="text", text=f"Domain {domain} deleted successfully")]
            
            elif name == "list_dns_records":
                domain = arguments["domain"]
                records = await vultr_client.list_records(domain)
                return [TextContent(type="text", text=str(records))]
            
            elif name == "get_dns_record":
                domain = arguments["domain"]
                record_id = arguments["record_id"]
                result = await vultr_client.get_record(domain, record_id)
                return [TextContent(type="text", text=str(result))]
            
            elif name == "create_dns_record":
                domain = arguments["domain"]
                record_type = arguments["record_type"]
                name = arguments["name"]
                data = arguments["data"]
                ttl = arguments.get("ttl")
                priority = arguments.get("priority")
                result = await vultr_client.create_record(domain, record_type, name, data, ttl, priority)
                return [TextContent(type="text", text=str(result))]
            
            elif name == "update_dns_record":
                domain = arguments["domain"]
                record_id = arguments["record_id"]
                record_type = arguments["record_type"]
                name = arguments["name"]
                data = arguments["data"]
                ttl = arguments.get("ttl")
                priority = arguments.get("priority")
                result = await vultr_client.update_record(domain, record_id, record_type, name, data, ttl, priority)
                return [TextContent(type="text", text=str(result))]
            
            elif name == "delete_dns_record":
                domain = arguments["domain"]
                record_id = arguments["record_id"]
                await vultr_client.delete_record(domain, record_id)
                return [TextContent(type="text", text=f"DNS record {record_id} deleted successfully")]
            
            elif name == "validate_dns_record":
                record_type = arguments["record_type"]
                name = arguments["name"]
                data = arguments["data"]
                ttl = arguments.get("ttl")
                priority = arguments.get("priority")
                
                validation_result = {
                    "valid": True,
                    "errors": [],
                    "warnings": [],
                    "suggestions": []
                }
                
                # Validate record type
                valid_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'SRV']
                if record_type.upper() not in valid_types:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Invalid record type. Must be one of: {', '.join(valid_types)}")
                
                record_type = record_type.upper()
                
                # Validate TTL
                if ttl is not None:
                    if ttl < 60 or ttl > 86400:
                        validation_result["warnings"].append("TTL should be between 60 and 86400 seconds")
                    elif ttl < 300:
                        validation_result["warnings"].append("Low TTL values may impact DNS performance")
                
                # Record-specific validation
                if record_type == 'A':
                    try:
                        ipaddress.IPv4Address(data)
                    except ipaddress.AddressValueError:
                        validation_result["valid"] = False
                        validation_result["errors"].append("Invalid IPv4 address format")
                
                elif record_type == 'AAAA':
                    try:
                        ipv6_addr = ipaddress.IPv6Address(data)
                        # Add helpful suggestions for IPv6 addresses
                        if ipv6_addr.ipv4_mapped:
                            validation_result["suggestions"].append("Consider using a native IPv6 address instead of IPv4-mapped format")
                        elif ipv6_addr.compressed != data:
                            validation_result["suggestions"].append(f"Consider using compressed format: {ipv6_addr.compressed}")
                        
                        # Check for common special addresses
                        if ipv6_addr.is_loopback:
                            validation_result["warnings"].append("This is the IPv6 loopback address (::1)")
                        elif ipv6_addr.is_link_local:
                            validation_result["warnings"].append("This is an IPv6 link-local address (fe80::/10)")
                        elif ipv6_addr.is_private:
                            validation_result["warnings"].append("This is an IPv6 private address")
                            
                    except ipaddress.AddressValueError as e:
                        validation_result["valid"] = False
                        validation_result["errors"].append(f"Invalid IPv6 address: {str(e)}")
                
                elif record_type == 'CNAME':
                    if name == '@' or name == '':
                        validation_result["valid"] = False
                        validation_result["errors"].append("CNAME records cannot be used for root domain (@)")
                
                elif record_type == 'MX':
                    if priority is None:
                        validation_result["valid"] = False
                        validation_result["errors"].append("MX records require a priority value")
                    elif priority < 0 or priority > 65535:
                        validation_result["valid"] = False
                        validation_result["errors"].append("MX priority must be between 0 and 65535")
                
                elif record_type == 'SRV':
                    if priority is None:
                        validation_result["valid"] = False
                        validation_result["errors"].append("SRV records require a priority value")
                    srv_parts = data.split()
                    if len(srv_parts) != 3:
                        validation_result["valid"] = False
                        validation_result["errors"].append("SRV data must be in format: 'weight port target'")
                
                result = {
                    "record_type": record_type,
                    "name": name,
                    "data": data,
                    "ttl": ttl,
                    "priority": priority,
                    "validation": validation_result
                }
                return [TextContent(type="text", text=str(result))]
            
            elif name == "analyze_dns_records":
                domain = arguments["domain"]
                records = await vultr_client.list_records(domain)
                
                # Analyze records
                record_types = {}
                total_records = len(records)
                ttl_values = []
                has_root_a = False
                has_www = False
                has_mx = False
                has_spf = False
                
                for record in records:
                    record_type = record.get('type', 'UNKNOWN')
                    record_name = record.get('name', '')
                    record_data = record.get('data', '')
                    ttl = record.get('ttl', 300)
                    
                    record_types[record_type] = record_types.get(record_type, 0) + 1
                    ttl_values.append(ttl)
                    
                    if record_type == 'A' and record_name in ['@', domain]:
                        has_root_a = True
                    if record_name == 'www':
                        has_www = True
                    if record_type == 'MX':
                        has_mx = True
                    if record_type == 'TXT' and 'spf1' in record_data.lower():
                        has_spf = True
                
                # Generate recommendations
                recommendations = []
                issues = []
                
                if not has_root_a:
                    recommendations.append("Consider adding an A record for the root domain (@)")
                if not has_www:
                    recommendations.append("Consider adding a www subdomain (A or CNAME record)")
                if not has_mx and total_records > 1:
                    recommendations.append("Consider adding MX records if you plan to use email")
                if has_mx and not has_spf:
                    recommendations.append("Add SPF record (TXT) to prevent email spoofing")
                
                avg_ttl = sum(ttl_values) / len(ttl_values) if ttl_values else 0
                low_ttl_count = sum(1 for ttl in ttl_values if ttl < 300)
                
                if low_ttl_count > total_records * 0.5:
                    issues.append("Many records have very low TTL values, which may impact performance")
                
                result = {
                    "domain": domain,
                    "analysis": {
                        "total_records": total_records,
                        "record_types": record_types,
                        "average_ttl": round(avg_ttl),
                        "configuration_status": {
                            "has_root_domain": has_root_a,
                            "has_www_subdomain": has_www,
                            "has_email_mx": has_mx,
                            "has_spf_protection": has_spf
                        }
                    },
                    "recommendations": recommendations,
                    "potential_issues": issues,
                    "records_detail": records
                }
                return [TextContent(type="text", text=str(result))]
            
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    return server


async def run_server(api_key: Optional[str] = None) -> None:
    """
    Create and run a Vultr DNS MCP server.
    
    Args:
        api_key: Vultr API key. If not provided, will read from VULTR_API_KEY env var.
    """
    server = create_mcp_server(api_key)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, None)
