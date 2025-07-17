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

    # Zone File Management Methods
    async def export_zone_file(self, domain: str) -> str:
        """
        Export domain records as standard DNS zone file format.
        
        Args:
            domain: The domain name to export
            
        Returns:
            DNS zone file content as string
        """
        # Get domain info and records
        domain_info = await self.get_domain(domain)
        records = await self.list_records(domain)
        
        # Build zone file content
        lines = []
        
        # Zone file header
        lines.append(f"; Zone file for {domain}")
        lines.append(f"; Generated by mcp-vultr")
        lines.append(f"$ORIGIN {domain}.")
        lines.append(f"$TTL 3600")
        lines.append("")
        
        # Sort records by type for better organization
        record_types = ["SOA", "NS", "A", "AAAA", "CNAME", "MX", "TXT", "SRV"]
        sorted_records = []
        
        for record_type in record_types:
            type_records = [r for r in records if r.get("type") == record_type]
            sorted_records.extend(type_records)
        
        # Add any remaining record types not in our list
        remaining = [r for r in records if r.get("type") not in record_types]
        sorted_records.extend(remaining)
        
        # Convert records to zone file format
        for record in sorted_records:
            name = record.get("name", "@")
            ttl = record.get("ttl", 3600)
            record_type = record.get("type")
            data = record.get("data", "")
            priority = record.get("priority")
            
            # Handle different record types
            if record_type == "MX":
                line = f"{name}\t{ttl}\tIN\t{record_type}\t{priority}\t{data}"
            elif record_type == "SRV":
                # SRV format: priority weight port target
                srv_parts = data.split()
                if len(srv_parts) >= 3:
                    weight = srv_parts[0] if len(srv_parts) > 3 else "0"
                    port = srv_parts[-2] if len(srv_parts) > 2 else "80"
                    target = srv_parts[-1]
                    line = f"{name}\t{ttl}\tIN\t{record_type}\t{priority}\t{weight}\t{port}\t{target}"
                else:
                    line = f"{name}\t{ttl}\tIN\t{record_type}\t{priority}\t{data}"
            elif record_type == "TXT":
                # Ensure TXT data is quoted
                if not (data.startswith('"') and data.endswith('"')):
                    data = f'"{data}"'
                line = f"{name}\t{ttl}\tIN\t{record_type}\t{data}"
            else:
                line = f"{name}\t{ttl}\tIN\t{record_type}\t{data}"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    async def import_zone_file(self, domain: str, zone_data: str, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Import DNS records from zone file format.
        
        Args:
            domain: The domain name to import records to
            zone_data: DNS zone file content as string
            dry_run: If True, only validate and return what would be created
            
        Returns:
            List of created records or validation results
        """
        results = []
        lines = zone_data.strip().split('\n')
        
        current_ttl = 3600
        current_origin = domain
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith(';'):
                continue
            
            # Handle $TTL directive
            if line.startswith('$TTL'):
                try:
                    current_ttl = int(line.split()[1])
                except (IndexError, ValueError):
                    results.append({
                        "error": f"Line {line_num}: Invalid $TTL directive",
                        "line": line
                    })
                continue
            
            # Handle $ORIGIN directive
            if line.startswith('$ORIGIN'):
                try:
                    current_origin = line.split()[1].rstrip('.')
                except IndexError:
                    results.append({
                        "error": f"Line {line_num}: Invalid $ORIGIN directive",
                        "line": line
                    })
                continue
            
            # Skip SOA records (managed by Vultr)
            if '\tSOA\t' in line or ' SOA ' in line:
                continue
            
            # Parse DNS record
            try:
                record = self._parse_zone_line(line, current_ttl, current_origin)
                if record:
                    if dry_run:
                        results.append({
                            "action": "create",
                            "type": record["type"],
                            "name": record["name"],
                            "data": record["data"],
                            "ttl": record.get("ttl"),
                            "priority": record.get("priority")
                        })
                    else:
                        # Create the record
                        created = await self.create_record(
                            domain=domain,
                            record_type=record["type"],
                            name=record["name"],
                            data=record["data"],
                            ttl=record.get("ttl"),
                            priority=record.get("priority")
                        )
                        results.append(created)
            except Exception as e:
                results.append({
                    "error": f"Line {line_num}: {str(e)}",
                    "line": line
                })
        
        return results
    
    def _parse_zone_line(self, line: str, default_ttl: int, origin: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single zone file line into a DNS record.
        
        Args:
            line: Zone file line to parse
            default_ttl: Default TTL if not specified
            origin: Current origin domain
            
        Returns:
            Dictionary with record data or None if invalid
        """
        # Split line into parts, handling quoted strings
        parts = []
        current_part = ""
        in_quotes = False
        
        for char in line:
            if char == '"' and (not current_part or current_part[-1] != '\\'):
                in_quotes = not in_quotes
                current_part += char
            elif char in [' ', '\t'] and not in_quotes:
                if current_part:
                    parts.append(current_part)
                    current_part = ""
            else:
                current_part += char
        
        if current_part:
            parts.append(current_part)
        
        if len(parts) < 4:
            return None
        
        # Parse parts: name [ttl] [class] type data [data...]
        name = parts[0]
        record_type = None
        data_start_idx = 0
        ttl = default_ttl
        
        # Find the record type (should be one of the standard types)
        valid_types = ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SRV", "PTR"]
        for i, part in enumerate(parts[1:], 1):
            if part.upper() in valid_types:
                record_type = part.upper()
                data_start_idx = i + 1
                break
            elif part.upper() == "IN":
                continue  # Skip class
            elif part.isdigit():
                ttl = int(part)
        
        if not record_type or data_start_idx >= len(parts):
            return None
        
        # Handle @ symbol for root domain
        if name == "@":
            name = ""
        elif name.endswith("."):
            name = name[:-1]  # Remove trailing dot
        
        # Get record data
        data_parts = parts[data_start_idx:]
        priority = None
        
        if record_type == "MX":
            if len(data_parts) >= 2:
                priority = int(data_parts[0])
                data = data_parts[1]
            else:
                return None
        elif record_type == "SRV":
            if len(data_parts) >= 4:
                priority = int(data_parts[0])
                weight = data_parts[1]
                port = data_parts[2]
                target = data_parts[3]
                data = f"{weight} {port} {target}"
            else:
                return None
        elif record_type == "TXT":
            # Join all parts and remove quotes
            data = " ".join(data_parts)
            if data.startswith('"') and data.endswith('"'):
                data = data[1:-1]
        else:
            data = " ".join(data_parts)
        
        return {
            "name": name,
            "type": record_type,
            "data": data,
            "ttl": ttl,
            "priority": priority
        }
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all backups in your account.
        
        Returns:
            List of backup objects
        """
        result = await self._make_request("GET", "/backups")
        return result.get("backups", [])
    
    async def get_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Get information about a specific backup.
        
        Args:
            backup_id: The backup ID to get information for
            
        Returns:
            Backup information
        """
        return await self._make_request("GET", f"/backups/{backup_id}")
    
    async def list_ssh_keys(self) -> List[Dict[str, Any]]:
        """
        List all SSH keys in your account.
        
        Returns:
            List of SSH key objects
        """
        result = await self._make_request("GET", "/ssh-keys")
        return result.get("ssh_keys", [])
    
    async def get_ssh_key(self, ssh_key_id: str) -> Dict[str, Any]:
        """
        Get information about a specific SSH key.
        
        Args:
            ssh_key_id: The SSH key ID to get information for
            
        Returns:
            SSH key information
        """
        return await self._make_request("GET", f"/ssh-keys/{ssh_key_id}")
    
    async def create_ssh_key(self, name: str, ssh_key: str) -> Dict[str, Any]:
        """
        Create a new SSH key.
        
        Args:
            name: Name for the SSH key
            ssh_key: The SSH public key
            
        Returns:
            Created SSH key information
        """
        data = {
            "name": name,
            "ssh_key": ssh_key
        }
        return await self._make_request("POST", "/ssh-keys", data=data)
    
    async def update_ssh_key(self, ssh_key_id: str, name: Optional[str] = None, ssh_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Update an existing SSH key.
        
        Args:
            ssh_key_id: The SSH key ID to update
            name: New name for the SSH key (optional)
            ssh_key: New SSH public key (optional)
            
        Returns:
            Updated SSH key information
        """
        data = {}
        if name is not None:
            data["name"] = name
        if ssh_key is not None:
            data["ssh_key"] = ssh_key
        
        return await self._make_request("PATCH", f"/ssh-keys/{ssh_key_id}", data=data)
    
    async def delete_ssh_key(self, ssh_key_id: str) -> None:
        """
        Delete an SSH key.
        
        Args:
            ssh_key_id: The SSH key ID to delete
        """
        await self._make_request("DELETE", f"/ssh-keys/{ssh_key_id}")
    
    # Instance management methods
    async def list_instances(self) -> List[Dict[str, Any]]:
        """
        List all instances in your account.
        
        Returns:
            List of instance objects
        """
        result = await self._make_request("GET", "/instances")
        return result.get("instances", [])
    
    async def get_instance(self, instance_id: str) -> Dict[str, Any]:
        """
        Get information about a specific instance.
        
        Args:
            instance_id: The instance ID to get information for
            
        Returns:
            Instance information
        """
        return await self._make_request("GET", f"/instances/{instance_id}")
    
    async def create_instance(
        self,
        region: str,
        plan: str,
        label: Optional[str] = None,
        os_id: Optional[int] = None,
        iso_id: Optional[str] = None,
        script_id: Optional[str] = None,
        snapshot_id: Optional[str] = None,
        enable_ipv6: bool = False,
        enable_private_network: bool = False,
        attach_private_network: Optional[List[str]] = None,
        ssh_key_ids: Optional[List[str]] = None,
        backups: bool = False,
        app_id: Optional[int] = None,
        user_data: Optional[str] = None,
        ddos_protection: bool = False,
        activation_email: bool = False,
        hostname: Optional[str] = None,
        tag: Optional[str] = None,
        firewall_group_id: Optional[str] = None,
        reserved_ipv4: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new instance.
        
        Args:
            region: Region code
            plan: Plan ID
            label: Label for the instance
            os_id: Operating System ID
            iso_id: ISO ID for custom installation
            script_id: Startup script ID
            snapshot_id: Snapshot ID to restore from
            enable_ipv6: Enable IPv6
            enable_private_network: Enable private networking
            attach_private_network: List of private network IDs to attach
            ssh_key_ids: List of SSH key IDs to install
            backups: Enable automatic backups
            app_id: Application ID to install
            user_data: Cloud-init user data
            ddos_protection: Enable DDoS protection
            activation_email: Send activation email
            hostname: Hostname for the instance
            tag: Tag for the instance
            firewall_group_id: Firewall group ID
            reserved_ipv4: Reserved IPv4 address to use
            
        Returns:
            Created instance information
        """
        data = {
            "region": region,
            "plan": plan
        }
        
        # Add optional parameters
        if label is not None:
            data["label"] = label
        if os_id is not None:
            data["os_id"] = os_id
        if iso_id is not None:
            data["iso_id"] = iso_id
        if script_id is not None:
            data["script_id"] = script_id
        if snapshot_id is not None:
            data["snapshot_id"] = snapshot_id
        if enable_ipv6:
            data["enable_ipv6"] = enable_ipv6
        if enable_private_network:
            data["enable_private_network"] = enable_private_network
        if attach_private_network:
            data["attach_private_network"] = attach_private_network
        if ssh_key_ids:
            data["sshkey_id"] = ssh_key_ids
        if backups:
            data["backups"] = "enabled"
        if app_id is not None:
            data["app_id"] = app_id
        if user_data is not None:
            data["user_data"] = user_data
        if ddos_protection:
            data["ddos_protection"] = ddos_protection
        if activation_email:
            data["activation_email"] = activation_email
        if hostname is not None:
            data["hostname"] = hostname
        if tag is not None:
            data["tag"] = tag
        if firewall_group_id is not None:
            data["firewall_group_id"] = firewall_group_id
        if reserved_ipv4 is not None:
            data["reserved_ipv4"] = reserved_ipv4
            
        return await self._make_request("POST", "/instances", data=data)
    
    async def update_instance(
        self,
        instance_id: str,
        label: Optional[str] = None,
        tag: Optional[str] = None,
        plan: Optional[str] = None,
        enable_ipv6: Optional[bool] = None,
        backups: Optional[bool] = None,
        ddos_protection: Optional[bool] = None,
        firewall_group_id: Optional[str] = None,
        user_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing instance.
        
        Args:
            instance_id: The instance ID to update
            label: New label for the instance
            tag: New tag for the instance
            plan: New plan ID (for resizing)
            enable_ipv6: Enable/disable IPv6
            backups: Enable/disable automatic backups
            ddos_protection: Enable/disable DDoS protection
            firewall_group_id: New firewall group ID
            user_data: New cloud-init user data
            
        Returns:
            Updated instance information
        """
        data = {}
        if label is not None:
            data["label"] = label
        if tag is not None:
            data["tag"] = tag
        if plan is not None:
            data["plan"] = plan
        if enable_ipv6 is not None:
            data["enable_ipv6"] = enable_ipv6
        if backups is not None:
            data["backups"] = "enabled" if backups else "disabled"
        if ddos_protection is not None:
            data["ddos_protection"] = ddos_protection
        if firewall_group_id is not None:
            data["firewall_group_id"] = firewall_group_id
        if user_data is not None:
            data["user_data"] = user_data
            
        return await self._make_request("PATCH", f"/instances/{instance_id}", data=data)
    
    async def delete_instance(self, instance_id: str) -> None:
        """
        Delete an instance.
        
        Args:
            instance_id: The instance ID to delete
        """
        await self._make_request("DELETE", f"/instances/{instance_id}")
    
    async def start_instance(self, instance_id: str) -> None:
        """
        Start a stopped instance.
        
        Args:
            instance_id: The instance ID to start
        """
        await self._make_request("POST", f"/instances/{instance_id}/start")
    
    async def stop_instance(self, instance_id: str) -> None:
        """
        Stop a running instance.
        
        Args:
            instance_id: The instance ID to stop
        """
        await self._make_request("POST", f"/instances/{instance_id}/halt")
    
    async def reboot_instance(self, instance_id: str) -> None:
        """
        Reboot an instance.
        
        Args:
            instance_id: The instance ID to reboot
        """
        await self._make_request("POST", f"/instances/{instance_id}/reboot")
    
    async def reinstall_instance(self, instance_id: str, hostname: Optional[str] = None) -> Dict[str, Any]:
        """
        Reinstall an instance's operating system.
        
        Args:
            instance_id: The instance ID to reinstall
            hostname: New hostname for the instance
            
        Returns:
            Reinstall status information
        """
        data = {}
        if hostname is not None:
            data["hostname"] = hostname
            
        return await self._make_request("POST", f"/instances/{instance_id}/reinstall", data=data)
    
    async def get_instance_bandwidth(self, instance_id: str) -> Dict[str, Any]:
        """
        Get bandwidth usage for an instance.
        
        Args:
            instance_id: The instance ID
            
        Returns:
            Bandwidth usage information
        """
        return await self._make_request("GET", f"/instances/{instance_id}/bandwidth")
    
    async def list_instance_ipv4(self, instance_id: str) -> List[Dict[str, Any]]:
        """
        List IPv4 addresses for an instance.
        
        Args:
            instance_id: The instance ID
            
        Returns:
            List of IPv4 addresses
        """
        result = await self._make_request("GET", f"/instances/{instance_id}/ipv4")
        return result.get("ipv4s", [])
    
    async def create_instance_ipv4(self, instance_id: str, reboot: bool = True) -> Dict[str, Any]:
        """
        Create a new IPv4 address for an instance.
        
        Args:
            instance_id: The instance ID
            reboot: Whether to reboot the instance
            
        Returns:
            Created IPv4 information
        """
        data = {"reboot": reboot}
        return await self._make_request("POST", f"/instances/{instance_id}/ipv4", data=data)
    
    async def delete_instance_ipv4(self, instance_id: str, ipv4: str) -> None:
        """
        Delete an IPv4 address from an instance.
        
        Args:
            instance_id: The instance ID
            ipv4: The IPv4 address to delete
        """
        await self._make_request("DELETE", f"/instances/{instance_id}/ipv4/{ipv4}")
    
    async def list_instance_ipv6(self, instance_id: str) -> List[Dict[str, Any]]:
        """
        List IPv6 addresses for an instance.
        
        Args:
            instance_id: The instance ID
            
        Returns:
            List of IPv6 addresses
        """
        result = await self._make_request("GET", f"/instances/{instance_id}/ipv6")
        return result.get("ipv6s", [])
    
    # Firewall management methods
    async def list_firewall_groups(self) -> List[Dict[str, Any]]:
        """
        List all firewall groups in your account.
        
        Returns:
            List of firewall group objects
        """
        result = await self._make_request("GET", "/firewalls")
        return result.get("firewall_groups", [])
    
    async def get_firewall_group(self, firewall_group_id: str) -> Dict[str, Any]:
        """
        Get information about a specific firewall group.
        
        Args:
            firewall_group_id: The firewall group ID to get information for
            
        Returns:
            Firewall group information
        """
        return await self._make_request("GET", f"/firewalls/{firewall_group_id}")
    
    async def create_firewall_group(self, description: str) -> Dict[str, Any]:
        """
        Create a new firewall group.
        
        Args:
            description: Description for the firewall group
            
        Returns:
            Created firewall group information
        """
        data = {"description": description}
        return await self._make_request("POST", "/firewalls", data=data)
    
    async def update_firewall_group(self, firewall_group_id: str, description: str) -> None:
        """
        Update a firewall group description.
        
        Args:
            firewall_group_id: The firewall group ID to update
            description: New description for the firewall group
        """
        data = {"description": description}
        await self._make_request("PUT", f"/firewalls/{firewall_group_id}", data=data)
    
    async def delete_firewall_group(self, firewall_group_id: str) -> None:
        """
        Delete a firewall group.
        
        Args:
            firewall_group_id: The firewall group ID to delete
        """
        await self._make_request("DELETE", f"/firewalls/{firewall_group_id}")
    
    async def list_firewall_rules(self, firewall_group_id: str) -> List[Dict[str, Any]]:
        """
        List all rules in a firewall group.
        
        Args:
            firewall_group_id: The firewall group ID
            
        Returns:
            List of firewall rules
        """
        result = await self._make_request("GET", f"/firewalls/{firewall_group_id}/rules")
        return result.get("firewall_rules", [])
    
    async def get_firewall_rule(self, firewall_group_id: str, firewall_rule_id: str) -> Dict[str, Any]:
        """
        Get information about a specific firewall rule.
        
        Args:
            firewall_group_id: The firewall group ID
            firewall_rule_id: The firewall rule ID
            
        Returns:
            Firewall rule information
        """
        return await self._make_request("GET", f"/firewalls/{firewall_group_id}/rules/{firewall_rule_id}")
    
    async def create_firewall_rule(
        self,
        firewall_group_id: str,
        ip_type: str,
        protocol: str,
        subnet: str,
        subnet_size: int,
        port: Optional[str] = None,
        source: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new firewall rule.
        
        Args:
            firewall_group_id: The firewall group ID
            ip_type: IP type (v4 or v6)
            protocol: Protocol (tcp, udp, icmp, gre)
            subnet: IP subnet
            subnet_size: Subnet size (0-32 for IPv4, 0-128 for IPv6)
            port: Port or port range (e.g., "80" or "8000:8999")
            source: Source type (e.g., "cloudflare")
            notes: Notes for the rule
            
        Returns:
            Created firewall rule information
        """
        data = {
            "ip_type": ip_type,
            "protocol": protocol,
            "subnet": subnet,
            "subnet_size": subnet_size
        }
        
        if port is not None:
            data["port"] = port
        if source is not None:
            data["source"] = source
        if notes is not None:
            data["notes"] = notes
            
        return await self._make_request("POST", f"/firewalls/{firewall_group_id}/rules", data=data)
    
    async def delete_firewall_rule(self, firewall_group_id: str, firewall_rule_id: str) -> None:
        """
        Delete a firewall rule.
        
        Args:
            firewall_group_id: The firewall group ID
            firewall_rule_id: The firewall rule ID to delete
        """
        await self._make_request("DELETE", f"/firewalls/{firewall_group_id}/rules/{firewall_rule_id}")
    
    # Snapshot management methods
    async def list_snapshots(self) -> List[Dict[str, Any]]:
        """
        List all snapshots in your account.
        
        Returns:
            List of snapshot objects
        """
        result = await self._make_request("GET", "/snapshots")
        return result.get("snapshots", [])
    
    async def get_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Get information about a specific snapshot.
        
        Args:
            snapshot_id: The snapshot ID to get information for
            
        Returns:
            Snapshot information
        """
        return await self._make_request("GET", f"/snapshots/{snapshot_id}")
    
    async def create_snapshot(self, instance_id: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a snapshot from an instance.
        
        Args:
            instance_id: The instance ID to snapshot
            description: Description for the snapshot
            
        Returns:
            Created snapshot information
        """
        data = {"instance_id": instance_id}
        if description is not None:
            data["description"] = description
            
        return await self._make_request("POST", "/snapshots", data=data)
    
    async def create_snapshot_from_url(self, url: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a snapshot from a URL.
        
        Args:
            url: The URL of the snapshot to create
            description: Description for the snapshot
            
        Returns:
            Created snapshot information
        """
        data = {"url": url}
        if description is not None:
            data["description"] = description
            
        return await self._make_request("POST", "/snapshots/create-from-url", data=data)
    
    async def update_snapshot(self, snapshot_id: str, description: str) -> None:
        """
        Update a snapshot description.
        
        Args:
            snapshot_id: The snapshot ID to update
            description: New description for the snapshot
        """
        data = {"description": description}
        await self._make_request("PUT", f"/snapshots/{snapshot_id}", data=data)
    
    async def delete_snapshot(self, snapshot_id: str) -> None:
        """
        Delete a snapshot.
        
        Args:
            snapshot_id: The snapshot ID to delete
        """
        await self._make_request("DELETE", f"/snapshots/{snapshot_id}")
    
    # Region information methods
    async def list_regions(self) -> List[Dict[str, Any]]:
        """
        List all available regions.
        
        Returns:
            List of region objects
        """
        result = await self._make_request("GET", "/regions")
        return result.get("regions", [])
    
    async def list_availability(self, region_id: str) -> Dict[str, Any]:
        """
        Get availability information for a specific region.
        
        Args:
            region_id: The region ID to check availability for
            
        Returns:
            Availability information including available plans
        """
        return await self._make_request("GET", f"/regions/{region_id}/availability")
    
    # Reserved IP Methods
    async def list_reserved_ips(self) -> List[Dict[str, Any]]:
        """
        List all reserved IPs.
        
        Returns:
            List of reserved IP objects
        """
        result = await self._make_request("GET", "/reserved-ips")
        return result.get("reserved_ips", [])
    
    async def get_reserved_ip(self, reserved_ip: str) -> Dict[str, Any]:
        """
        Get details of a specific reserved IP.
        
        Args:
            reserved_ip: The reserved IP address
            
        Returns:
            Reserved IP details
        """
        return await self._make_request("GET", f"/reserved-ips/{reserved_ip}")
    
    async def create_reserved_ip(
        self,
        region: str,
        ip_type: str = "v4",
        label: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new reserved IP.
        
        Args:
            region: The region ID where to reserve the IP
            ip_type: Type of IP to reserve ("v4" or "v6")
            label: Optional label for the reserved IP
            
        Returns:
            Created reserved IP information
        """
        data = {
            "region": region,
            "ip_type": ip_type
        }
        if label is not None:
            data["label"] = label
            
        result = await self._make_request("POST", "/reserved-ips", data=data)
        return result.get("reserved_ip", {})
    
    async def update_reserved_ip(self, reserved_ip: str, label: str) -> None:
        """
        Update a reserved IP's label.
        
        Args:
            reserved_ip: The reserved IP address
            label: New label for the reserved IP
        """
        data = {"label": label}
        await self._make_request("PATCH", f"/reserved-ips/{reserved_ip}", data=data)
    
    async def delete_reserved_ip(self, reserved_ip: str) -> None:
        """
        Delete a reserved IP.
        
        Args:
            reserved_ip: The reserved IP address to delete
        """
        await self._make_request("DELETE", f"/reserved-ips/{reserved_ip}")
    
    async def attach_reserved_ip(self, reserved_ip: str, instance_id: str) -> None:
        """
        Attach a reserved IP to an instance.
        
        Args:
            reserved_ip: The reserved IP address
            instance_id: The instance ID to attach to
        """
        data = {"instance_id": instance_id}
        await self._make_request("POST", f"/reserved-ips/{reserved_ip}/attach", data=data)
    
    async def detach_reserved_ip(self, reserved_ip: str) -> None:
        """
        Detach a reserved IP from its instance.
        
        Args:
            reserved_ip: The reserved IP address to detach
        """
        await self._make_request("POST", f"/reserved-ips/{reserved_ip}/detach")
    
    async def convert_instance_ip_to_reserved(self, ip_address: str, instance_id: str, label: Optional[str] = None) -> Dict[str, Any]:
        """
        Convert an instance IP to a reserved IP.
        
        Args:
            ip_address: The IP address to convert
            instance_id: The instance ID that owns the IP
            label: Optional label for the reserved IP
            
        Returns:
            Created reserved IP information
        """
        data = {
            "ip_address": ip_address,
            "instance_id": instance_id
        }
        if label is not None:
            data["label"] = label
            
        result = await self._make_request("POST", "/reserved-ips/convert", data=data)
        return result.get("reserved_ip", {})


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
    server = Server("mcp-vultr")
    
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
