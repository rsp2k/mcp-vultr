"""
Vultr DNS MCP Server Implementation.

This module contains the main VultrDNSServer class and MCP server implementation
for managing DNS records through the Vultr API.
"""

import ipaddress
import os
import time
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

from .cache import CacheManager
from .metrics import record_api_call
from .retry import NetworkError, RateLimitError, retry_api_call
from .vultr_logging import get_logger, log_api_request


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
            "Content-Type": "application/json",
        }
        self.logger = get_logger(__name__)
        self.cache = CacheManager()

    @retry_api_call
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request to the Vultr API with caching, retry, and structured logging."""
        url = f"{self.API_BASE}{endpoint}"
        start_time = time.time()

        # Check cache for GET requests
        cache_hit = False
        if method.upper() == "GET":
            cached_result = self.cache.get(method, endpoint, params)
            if cached_result is not None:
                cache_hit = True
                response_time = time.time() - start_time

                # Record cache hit metrics
                record_api_call(
                    endpoint, method, response_time, success=True, cache_hit=True
                )

                self.logger.debug(
                    "Cache hit for API request", method=method, endpoint=endpoint
                )
                return cached_result

        # Configure timeout: 30 seconds total, 10 seconds to connect
        timeout = httpx.Timeout(30.0, connect=10.0)

        self.logger.debug(
            "Making API request",
            method=method,
            endpoint=endpoint,
            has_data=data is not None,
            has_params=params is not None,
        )

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    params=params,
                )

                response_time = time.time() - start_time

                # Log the API request
                log_api_request(
                    self.logger,
                    method=method,
                    url=url,
                    status_code=response.status_code,
                    response_time=response_time,
                    endpoint=endpoint,
                )

                if response.status_code not in [200, 201, 204]:
                    # Record failed API call metrics
                    record_api_call(
                        endpoint,
                        method,
                        response_time,
                        success=False,
                        cache_hit=cache_hit,
                    )

                    # Raise specific exceptions based on status code
                    if response.status_code == 401:
                        raise VultrAuthError(response.status_code, "Invalid API key")
                    elif response.status_code == 403:
                        raise VultrAuthError(
                            response.status_code, "Insufficient permissions"
                        )
                    elif response.status_code == 404:
                        raise VultrResourceNotFoundError(
                            response.status_code, "Resource not found"
                        )
                    elif response.status_code == 429:
                        raise RateLimitError(f"Rate limit exceeded: {response.text}")
                    elif response.status_code in [400, 422]:
                        raise VultrValidationError(response.status_code, response.text)
                    else:
                        raise VultrAPIError(response.status_code, response.text)

                result = {} if response.status_code == 204 else response.json()

                # Cache successful GET requests
                if method.upper() == "GET" and result:
                    self.cache.set(method, endpoint, params, result)

                # Record successful API call metrics
                record_api_call(
                    endpoint, method, response_time, success=True, cache_hit=cache_hit
                )

                return result

            except httpx.TimeoutException as e:
                response_time = time.time() - start_time

                # Record timeout metrics
                record_api_call(
                    endpoint, method, response_time, success=False, cache_hit=cache_hit
                )

                self.logger.error(
                    "API request timeout",
                    method=method,
                    url=url,
                    response_time=response_time,
                    error=str(e),
                )
                raise NetworkError(f"Request timeout after {response_time:.2f}s")
            except httpx.RequestError as e:
                response_time = time.time() - start_time

                # Record network error metrics
                record_api_call(
                    endpoint, method, response_time, success=False, cache_hit=cache_hit
                )

                self.logger.error(
                    "API request failed",
                    method=method,
                    url=url,
                    response_time=response_time,
                    error=str(e),
                )
                raise NetworkError(f"Request failed: {e}")

    # Domain Management Methods
    async def list_domains(self) -> list[dict[str, Any]]:
        """List all DNS domains."""
        result = await self._make_request("GET", "/domains")
        return result.get("domains", [])

    async def get_domain(self, domain: str) -> dict[str, Any]:
        """Get details for a specific domain."""
        return await self._make_request("GET", f"/domains/{domain}")

    async def create_domain(self, domain: str, ip: str) -> dict[str, Any]:
        """Create a new DNS domain."""
        data = {"domain": domain, "ip": ip}
        return await self._make_request("POST", "/domains", data)

    async def delete_domain(self, domain: str) -> dict[str, Any]:
        """Delete a DNS domain."""
        return await self._make_request("DELETE", f"/domains/{domain}")

    # DNS Record Management Methods
    async def list_records(self, domain: str) -> list[dict[str, Any]]:
        """List all DNS records for a domain."""
        result = await self._make_request("GET", f"/domains/{domain}/records")
        return result.get("records", [])

    async def get_record(self, domain: str, record_id: str) -> dict[str, Any]:
        """Get a specific DNS record."""
        return await self._make_request("GET", f"/domains/{domain}/records/{record_id}")

    async def create_record(
        self,
        domain: str,
        record_type: str,
        name: str,
        data: str,
        ttl: int | None = None,
        priority: int | None = None,
    ) -> dict[str, Any]:
        """Create a new DNS record."""
        payload = {"type": record_type, "name": name, "data": data}

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
        ttl: int | None = None,
        priority: int | None = None,
    ) -> dict[str, Any]:
        """Update an existing DNS record."""
        payload = {"type": record_type, "name": name, "data": data}

        if ttl is not None:
            payload["ttl"] = ttl
        if priority is not None:
            payload["priority"] = priority

        return await self._make_request(
            "PATCH", f"/domains/{domain}/records/{record_id}", payload
        )

    async def delete_record(self, domain: str, record_id: str) -> dict[str, Any]:
        """Delete a DNS record."""
        return await self._make_request(
            "DELETE", f"/domains/{domain}/records/{record_id}"
        )

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
        await self.get_domain(domain)
        records = await self.list_records(domain)

        # Build zone file content
        lines = []

        # Zone file header
        lines.append(f"; Zone file for {domain}")
        lines.append("; Generated by mcp-vultr")
        lines.append(f"$ORIGIN {domain}.")
        lines.append("$TTL 3600")
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

    async def import_zone_file(
        self, domain: str, zone_data: str, dry_run: bool = False
    ) -> list[dict[str, Any]]:
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
        lines = zone_data.strip().split("\n")

        current_ttl = 3600
        current_origin = domain

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith(";"):
                continue

            # Handle $TTL directive
            if line.startswith("$TTL"):
                try:
                    current_ttl = int(line.split()[1])
                except (IndexError, ValueError):
                    results.append(
                        {
                            "error": f"Line {line_num}: Invalid $TTL directive",
                            "line": line,
                        }
                    )
                continue

            # Handle $ORIGIN directive
            if line.startswith("$ORIGIN"):
                try:
                    current_origin = line.split()[1].rstrip(".")
                except IndexError:
                    results.append(
                        {
                            "error": f"Line {line_num}: Invalid $ORIGIN directive",
                            "line": line,
                        }
                    )
                continue

            # Skip SOA records (managed by Vultr)
            if "\tSOA\t" in line or " SOA " in line:
                continue

            # Parse DNS record
            try:
                record = self._parse_zone_line(line, current_ttl, current_origin)
                if record:
                    if dry_run:
                        results.append(
                            {
                                "action": "create",
                                "type": record["type"],
                                "name": record["name"],
                                "data": record["data"],
                                "ttl": record.get("ttl"),
                                "priority": record.get("priority"),
                            }
                        )
                    else:
                        # Create the record
                        created = await self.create_record(
                            domain=domain,
                            record_type=record["type"],
                            name=record["name"],
                            data=record["data"],
                            ttl=record.get("ttl"),
                            priority=record.get("priority"),
                        )
                        results.append(created)
            except Exception as e:
                results.append({"error": f"Line {line_num}: {str(e)}", "line": line})

        return results

    def _parse_zone_line(
        self,
        line: str,
        default_ttl: int,
        origin: str,  # noqa: ARG002
    ) -> dict[str, Any] | None:
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
            if char == '"' and (not current_part or current_part[-1] != "\\"):
                in_quotes = not in_quotes
                current_part += char
            elif char in [" ", "\t"] and not in_quotes:
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
            "priority": priority,
        }

    async def list_backups(self) -> list[dict[str, Any]]:
        """
        List all backups in your account.

        Returns:
            List of backup objects
        """
        result = await self._make_request("GET", "/backups")
        return result.get("backups", [])

    async def get_backup(self, backup_id: str) -> dict[str, Any]:
        """
        Get information about a specific backup.

        Args:
            backup_id: The backup ID to get information for

        Returns:
            Backup information
        """
        return await self._make_request("GET", f"/backups/{backup_id}")

    async def list_ssh_keys(self) -> list[dict[str, Any]]:
        """
        List all SSH keys in your account.

        Returns:
            List of SSH key objects
        """
        result = await self._make_request("GET", "/ssh-keys")
        return result.get("ssh_keys", [])

    async def get_ssh_key(self, ssh_key_id: str) -> dict[str, Any]:
        """
        Get information about a specific SSH key.

        Args:
            ssh_key_id: The SSH key ID to get information for

        Returns:
            SSH key information
        """
        return await self._make_request("GET", f"/ssh-keys/{ssh_key_id}")

    async def create_ssh_key(self, name: str, ssh_key: str) -> dict[str, Any]:
        """
        Create a new SSH key.

        Args:
            name: Name for the SSH key
            ssh_key: The SSH public key

        Returns:
            Created SSH key information
        """
        data = {"name": name, "ssh_key": ssh_key}
        return await self._make_request("POST", "/ssh-keys", data=data)

    async def update_ssh_key(
        self, ssh_key_id: str, name: str | None = None, ssh_key: str | None = None
    ) -> dict[str, Any]:
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
    async def list_instances(self) -> list[dict[str, Any]]:
        """
        List all instances in your account.

        Returns:
            List of instance objects
        """
        result = await self._make_request("GET", "/instances")
        return result.get("instances", [])

    async def get_instance(self, instance_id: str) -> dict[str, Any]:
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
        label: str | None = None,
        os_id: int | None = None,
        iso_id: str | None = None,
        script_id: str | None = None,
        snapshot_id: str | None = None,
        enable_ipv6: bool = False,
        enable_private_network: bool = False,
        attach_private_network: list[str] | None = None,
        ssh_key_ids: list[str] | None = None,
        backups: bool = False,
        app_id: int | None = None,
        user_data: str | None = None,
        ddos_protection: bool = False,
        activation_email: bool = False,
        hostname: str | None = None,
        tag: str | None = None,
        firewall_group_id: str | None = None,
        reserved_ipv4: str | None = None,
    ) -> dict[str, Any]:
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
        data = {"region": region, "plan": plan}

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
        label: str | None = None,
        tag: str | None = None,
        plan: str | None = None,
        enable_ipv6: bool | None = None,
        backups: bool | None = None,
        ddos_protection: bool | None = None,
        firewall_group_id: str | None = None,
        user_data: str | None = None,
    ) -> dict[str, Any]:
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

    async def reinstall_instance(
        self, instance_id: str, hostname: str | None = None
    ) -> dict[str, Any]:
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

        return await self._make_request(
            "POST", f"/instances/{instance_id}/reinstall", data=data
        )

    async def get_instance_bandwidth(self, instance_id: str) -> dict[str, Any]:
        """
        Get bandwidth usage for an instance.

        Args:
            instance_id: The instance ID

        Returns:
            Bandwidth usage information
        """
        return await self._make_request("GET", f"/instances/{instance_id}/bandwidth")

    async def list_instance_ipv4(self, instance_id: str) -> list[dict[str, Any]]:
        """
        List IPv4 addresses for an instance.

        Args:
            instance_id: The instance ID

        Returns:
            List of IPv4 addresses
        """
        result = await self._make_request("GET", f"/instances/{instance_id}/ipv4")
        return result.get("ipv4s", [])

    async def create_instance_ipv4(
        self, instance_id: str, reboot: bool = True
    ) -> dict[str, Any]:
        """
        Create a new IPv4 address for an instance.

        Args:
            instance_id: The instance ID
            reboot: Whether to reboot the instance

        Returns:
            Created IPv4 information
        """
        data = {"reboot": reboot}
        return await self._make_request(
            "POST", f"/instances/{instance_id}/ipv4", data=data
        )

    async def delete_instance_ipv4(self, instance_id: str, ipv4: str) -> None:
        """
        Delete an IPv4 address from an instance.

        Args:
            instance_id: The instance ID
            ipv4: The IPv4 address to delete
        """
        await self._make_request("DELETE", f"/instances/{instance_id}/ipv4/{ipv4}")

    async def list_instance_ipv6(self, instance_id: str) -> list[dict[str, Any]]:
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
    async def list_firewall_groups(self) -> list[dict[str, Any]]:
        """
        List all firewall groups in your account.

        Returns:
            List of firewall group objects
        """
        result = await self._make_request("GET", "/firewalls")
        return result.get("firewall_groups", [])

    async def get_firewall_group(self, firewall_group_id: str) -> dict[str, Any]:
        """
        Get information about a specific firewall group.

        Args:
            firewall_group_id: The firewall group ID to get information for

        Returns:
            Firewall group information
        """
        return await self._make_request("GET", f"/firewalls/{firewall_group_id}")

    async def create_firewall_group(self, description: str) -> dict[str, Any]:
        """
        Create a new firewall group.

        Args:
            description: Description for the firewall group

        Returns:
            Created firewall group information
        """
        data = {"description": description}
        return await self._make_request("POST", "/firewalls", data=data)

    async def update_firewall_group(
        self, firewall_group_id: str, description: str
    ) -> None:
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

    async def list_firewall_rules(self, firewall_group_id: str) -> list[dict[str, Any]]:
        """
        List all rules in a firewall group.

        Args:
            firewall_group_id: The firewall group ID

        Returns:
            List of firewall rules
        """
        result = await self._make_request(
            "GET", f"/firewalls/{firewall_group_id}/rules"
        )
        return result.get("firewall_rules", [])

    async def get_firewall_rule(
        self, firewall_group_id: str, firewall_rule_id: str
    ) -> dict[str, Any]:
        """
        Get information about a specific firewall rule.

        Args:
            firewall_group_id: The firewall group ID
            firewall_rule_id: The firewall rule ID

        Returns:
            Firewall rule information
        """
        return await self._make_request(
            "GET", f"/firewalls/{firewall_group_id}/rules/{firewall_rule_id}"
        )

    async def create_firewall_rule(
        self,
        firewall_group_id: str,
        ip_type: str,
        protocol: str,
        subnet: str,
        subnet_size: int,
        port: str | None = None,
        source: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
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
            "subnet_size": subnet_size,
        }

        if port is not None:
            data["port"] = port
        if source is not None:
            data["source"] = source
        if notes is not None:
            data["notes"] = notes

        return await self._make_request(
            "POST", f"/firewalls/{firewall_group_id}/rules", data=data
        )

    async def delete_firewall_rule(
        self, firewall_group_id: str, firewall_rule_id: str
    ) -> None:
        """
        Delete a firewall rule.

        Args:
            firewall_group_id: The firewall group ID
            firewall_rule_id: The firewall rule ID to delete
        """
        await self._make_request(
            "DELETE", f"/firewalls/{firewall_group_id}/rules/{firewall_rule_id}"
        )

    # Snapshot management methods
    async def list_snapshots(self) -> list[dict[str, Any]]:
        """
        List all snapshots in your account.

        Returns:
            List of snapshot objects
        """
        result = await self._make_request("GET", "/snapshots")
        return result.get("snapshots", [])

    async def get_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        """
        Get information about a specific snapshot.

        Args:
            snapshot_id: The snapshot ID to get information for

        Returns:
            Snapshot information
        """
        return await self._make_request("GET", f"/snapshots/{snapshot_id}")

    async def create_snapshot(
        self, instance_id: str, description: str | None = None
    ) -> dict[str, Any]:
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

    async def create_snapshot_from_url(
        self, url: str, description: str | None = None
    ) -> dict[str, Any]:
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
    async def list_regions(self) -> list[dict[str, Any]]:
        """
        List all available regions.

        Returns:
            List of region objects
        """
        result = await self._make_request("GET", "/regions")
        return result.get("regions", [])

    async def list_availability(self, region_id: str) -> dict[str, Any]:
        """
        Get availability information for a specific region.

        Args:
            region_id: The region ID to check availability for

        Returns:
            Availability information including available plans
        """
        return await self._make_request("GET", f"/regions/{region_id}/availability")

    # Reserved IP Methods
    async def list_reserved_ips(self) -> list[dict[str, Any]]:
        """
        List all reserved IPs.

        Returns:
            List of reserved IP objects
        """
        result = await self._make_request("GET", "/reserved-ips")
        return result.get("reserved_ips", [])

    async def get_reserved_ip(self, reserved_ip: str) -> dict[str, Any]:
        """
        Get details of a specific reserved IP.

        Args:
            reserved_ip: The reserved IP address

        Returns:
            Reserved IP details
        """
        return await self._make_request("GET", f"/reserved-ips/{reserved_ip}")

    async def create_reserved_ip(
        self, region: str, ip_type: str = "v4", label: str | None = None
    ) -> dict[str, Any]:
        """
        Create a new reserved IP.

        Args:
            region: The region ID where to reserve the IP
            ip_type: Type of IP to reserve ("v4" or "v6")
            label: Optional label for the reserved IP

        Returns:
            Created reserved IP information
        """
        data = {"region": region, "ip_type": ip_type}
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
        await self._make_request(
            "POST", f"/reserved-ips/{reserved_ip}/attach", data=data
        )

    async def detach_reserved_ip(self, reserved_ip: str) -> None:
        """
        Detach a reserved IP from its instance.

        Args:
            reserved_ip: The reserved IP address to detach
        """
        await self._make_request("POST", f"/reserved-ips/{reserved_ip}/detach")

    async def convert_instance_ip_to_reserved(
        self, ip_address: str, instance_id: str, label: str | None = None
    ) -> dict[str, Any]:
        """
        Convert an instance IP to a reserved IP.

        Args:
            ip_address: The IP address to convert
            instance_id: The instance ID that owns the IP
            label: Optional label for the reserved IP

        Returns:
            Created reserved IP information
        """
        data = {"ip_address": ip_address, "instance_id": instance_id}
        if label is not None:
            data["label"] = label

        result = await self._make_request("POST", "/reserved-ips/convert", data=data)
        return result.get("reserved_ip", {})

    # Container Registry API Methods
    async def list_container_registries(self) -> list[dict[str, Any]]:
        """
        List all container registry subscriptions.

        Returns:
            List of container registry information
        """
        result = await self._make_request("GET", "/registry")
        return result.get("registries", [])

    async def get_container_registry(self, registry_id: str) -> dict[str, Any]:
        """
        Get container registry details.

        Args:
            registry_id: The container registry ID

        Returns:
            Container registry information
        """
        result = await self._make_request("GET", f"/registry/{registry_id}")
        return result.get("registry", {})

    async def create_container_registry(
        self, name: str, plan: str, region: str
    ) -> dict[str, Any]:
        """
        Create a new container registry subscription.

        Args:
            name: Name for the container registry
            plan: Registry plan (e.g., "start_up", "business", "premium")
            region: Region for the registry

        Returns:
            Created container registry information
        """
        data = {"name": name, "plan": plan, "region": region}
        result = await self._make_request("POST", "/registry", data=data)
        return result.get("registry", {})

    async def update_container_registry(self, registry_id: str, plan: str) -> None:
        """
        Update container registry plan.

        Args:
            registry_id: The container registry ID
            plan: New registry plan
        """
        data = {"plan": plan}
        await self._make_request("PUT", f"/registry/{registry_id}", data=data)

    async def delete_container_registry(self, registry_id: str) -> None:
        """
        Delete a container registry subscription.

        Args:
            registry_id: The container registry ID to delete
        """
        await self._make_request("DELETE", f"/registry/{registry_id}")

    async def list_registry_plans(self) -> list[dict[str, Any]]:
        """
        List all available container registry plans.

        Returns:
            List of available plans
        """
        result = await self._make_request("GET", "/registry/plan/list")
        return result.get("plans", [])

    async def generate_docker_credentials(
        self,
        registry_id: str,
        expiry_seconds: int | None = None,
        read_write: bool = True,
    ) -> dict[str, Any]:
        """
        Generate Docker credentials for container registry.

        Args:
            registry_id: The container registry ID
            expiry_seconds: Expiration time in seconds (optional)
            read_write: Whether to grant read-write access (default: True)

        Returns:
            Docker credentials information
        """
        params = {"read_write": str(read_write).lower()}
        if expiry_seconds is not None:
            params["expiry_seconds"] = str(expiry_seconds)

        result = await self._make_request(
            "OPTIONS", f"/registry/{registry_id}/docker-credentials", params=params
        )
        return result

    async def generate_kubernetes_credentials(
        self,
        registry_id: str,
        expiry_seconds: int | None = None,
        read_write: bool = True,
        base64_encode: bool = True,
    ) -> dict[str, Any]:
        """
        Generate Kubernetes credentials for container registry.

        Args:
            registry_id: The container registry ID
            expiry_seconds: Expiration time in seconds (optional)
            read_write: Whether to grant read-write access (default: True)
            base64_encode: Whether to base64 encode the credentials (default: True)

        Returns:
            Kubernetes credentials YAML
        """
        params = {
            "read_write": str(read_write).lower(),
            "base64_encode": str(base64_encode).lower(),
        }
        if expiry_seconds is not None:
            params["expiry_seconds"] = str(expiry_seconds)

        result = await self._make_request(
            "OPTIONS",
            f"/registry/{registry_id}/docker-credentials/kubernetes",
            params=params,
        )
        return result

    # Block Storage API Methods
    async def list_block_storage(self) -> list[dict[str, Any]]:
        """
        List all block storage volumes in your account.

        Returns:
            List of block storage volume information
        """
        result = await self._make_request("GET", "/blocks")
        return result.get("blocks", [])

    async def get_block_storage(self, block_id: str) -> dict[str, Any]:
        """
        Get block storage volume details.

        Args:
            block_id: The block storage volume ID

        Returns:
            Block storage volume information
        """
        result = await self._make_request("GET", f"/blocks/{block_id}")
        return result.get("block", {})

    async def create_block_storage(
        self,
        region: str,
        size_gb: int,
        label: str | None = None,
        block_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new block storage volume.

        Args:
            region: Region ID where the volume will be created
            size_gb: Size in GB (10-40000 depending on block_type)
            label: Optional label for the volume
            block_type: Optional block storage type

        Returns:
            Created block storage volume information
        """
        data = {"region": region, "size_gb": size_gb}
        if label is not None:
            data["label"] = label
        if block_type is not None:
            data["block_type"] = block_type

        result = await self._make_request("POST", "/blocks", data=data)
        return result.get("block", {})

    async def update_block_storage(
        self, block_id: str, size_gb: int | None = None, label: str | None = None
    ) -> None:
        """
        Update block storage volume configuration.

        Args:
            block_id: The block storage volume ID
            size_gb: New size in GB (can only increase)
            label: New label for the volume
        """
        data = {}
        if size_gb is not None:
            data["size_gb"] = size_gb
        if label is not None:
            data["label"] = label

        if data:  # Only make request if there are changes
            await self._make_request("PATCH", f"/blocks/{block_id}", data=data)

    async def delete_block_storage(self, block_id: str) -> None:
        """
        Delete a block storage volume.

        Args:
            block_id: The block storage volume ID to delete
        """
        await self._make_request("DELETE", f"/blocks/{block_id}")

    async def attach_block_storage(
        self, block_id: str, instance_id: str, live: bool = True
    ) -> None:
        """
        Attach block storage volume to an instance.

        Args:
            block_id: The block storage volume ID
            instance_id: The instance ID to attach to
            live: Whether to attach without rebooting the instance (default: True)
        """
        data = {"instance_id": instance_id, "live": live}
        await self._make_request("POST", f"/blocks/{block_id}/attach", data=data)

    async def detach_block_storage(self, block_id: str, live: bool = True) -> None:
        """
        Detach block storage volume from its instance.

        Args:
            block_id: The block storage volume ID
            live: Whether to detach without rebooting the instance (default: True)
        """
        data = {"live": live}
        await self._make_request("POST", f"/blocks/{block_id}/detach", data=data)

    # VPC API Methods
    async def list_vpcs(self) -> list[dict[str, Any]]:
        """
        List all VPCs in your account.

        Returns:
            List of VPC information
        """
        result = await self._make_request("GET", "/vpcs")
        return result.get("vpcs", [])

    async def get_vpc(self, vpc_id: str) -> dict[str, Any]:
        """
        Get VPC details.

        Args:
            vpc_id: The VPC ID

        Returns:
            VPC information
        """
        result = await self._make_request("GET", f"/vpcs/{vpc_id}")
        return result.get("vpc", {})

    async def create_vpc(
        self,
        region: str,
        description: str,
        v4_subnet: str | None = None,
        v4_subnet_mask: int | None = None,
    ) -> dict[str, Any]:
        """
        Create a new VPC.

        Args:
            region: Region ID where the VPC will be created
            description: Description/label for the VPC
            v4_subnet: IPv4 subnet for the VPC (e.g., "10.0.0.0")
            v4_subnet_mask: IPv4 subnet mask (e.g., 24)

        Returns:
            Created VPC information
        """
        data = {"region": region, "description": description}
        if v4_subnet is not None:
            data["v4_subnet"] = v4_subnet
        if v4_subnet_mask is not None:
            data["v4_subnet_mask"] = v4_subnet_mask

        result = await self._make_request("POST", "/vpcs", data=data)
        return result.get("vpc", {})

    async def update_vpc(self, vpc_id: str, description: str) -> None:
        """
        Update VPC description.

        Args:
            vpc_id: The VPC ID
            description: New description for the VPC
        """
        data = {"description": description}
        await self._make_request("PUT", f"/vpcs/{vpc_id}", data=data)

    async def delete_vpc(self, vpc_id: str) -> None:
        """
        Delete a VPC.

        Args:
            vpc_id: The VPC ID to delete
        """
        await self._make_request("DELETE", f"/vpcs/{vpc_id}")

    # VPC 2.0 API Methods
    async def list_vpc2s(self) -> list[dict[str, Any]]:
        """
        List all VPC 2.0 networks in your account.

        Returns:
            List of VPC 2.0 information
        """
        result = await self._make_request("GET", "/vpc2")
        return result.get("vpc2s", [])

    async def get_vpc2(self, vpc2_id: str) -> dict[str, Any]:
        """
        Get VPC 2.0 details.

        Args:
            vpc2_id: The VPC 2.0 ID

        Returns:
            VPC 2.0 information
        """
        result = await self._make_request("GET", f"/vpc2/{vpc2_id}")
        return result.get("vpc2", {})

    async def create_vpc2(
        self,
        region: str,
        description: str,
        ip_type: str = "v4",
        ip_block: str | None = None,
        prefix_length: int | None = None,
    ) -> dict[str, Any]:
        """
        Create a new VPC 2.0 network.

        Args:
            region: Region ID where the VPC 2.0 will be created
            description: Description/label for the VPC 2.0
            ip_type: IP type ("v4" or "v6")
            ip_block: IP block for the VPC 2.0 (e.g., "10.0.0.0")
            prefix_length: Prefix length (e.g., 24 for /24)

        Returns:
            Created VPC 2.0 information
        """
        data = {"region": region, "description": description, "ip_type": ip_type}
        if ip_block is not None:
            data["ip_block"] = ip_block
        if prefix_length is not None:
            data["prefix_length"] = prefix_length

        result = await self._make_request("POST", "/vpc2", data=data)
        return result.get("vpc2", {})

    async def update_vpc2(self, vpc2_id: str, description: str) -> None:
        """
        Update VPC 2.0 description.

        Args:
            vpc2_id: The VPC 2.0 ID
            description: New description for the VPC 2.0
        """
        data = {"description": description}
        await self._make_request("PUT", f"/vpc2/{vpc2_id}", data=data)

    async def delete_vpc2(self, vpc2_id: str) -> None:
        """
        Delete a VPC 2.0 network.

        Args:
            vpc2_id: The VPC 2.0 ID to delete
        """
        await self._make_request("DELETE", f"/vpc2/{vpc2_id}")

    # VPC Instance Attachment Methods
    async def attach_vpc_to_instance(self, instance_id: str, vpc_id: str) -> None:
        """
        Attach a VPC to an instance.

        Args:
            instance_id: The instance ID
            vpc_id: The VPC ID to attach
        """
        data = {"vpc_id": vpc_id}
        await self._make_request(
            "POST", f"/instances/{instance_id}/vpcs/attach", data=data
        )

    async def detach_vpc_from_instance(self, instance_id: str, vpc_id: str) -> None:
        """
        Detach a VPC from an instance.

        Args:
            instance_id: The instance ID
            vpc_id: The VPC ID to detach
        """
        data = {"vpc_id": vpc_id}
        await self._make_request(
            "POST", f"/instances/{instance_id}/vpcs/detach", data=data
        )

    async def attach_vpc2_to_instance(
        self, instance_id: str, vpc2_id: str, ip_address: str | None = None
    ) -> None:
        """
        Attach a VPC 2.0 to an instance.

        Args:
            instance_id: The instance ID
            vpc2_id: The VPC 2.0 ID to attach
            ip_address: Optional specific IP address to assign
        """
        data = {"vpc2_id": vpc2_id}
        if ip_address is not None:
            data["ip_address"] = ip_address
        await self._make_request(
            "POST", f"/instances/{instance_id}/vpc2/attach", data=data
        )

    async def detach_vpc2_from_instance(self, instance_id: str, vpc2_id: str) -> None:
        """
        Detach a VPC 2.0 from an instance.

        Args:
            instance_id: The instance ID
            vpc2_id: The VPC 2.0 ID to detach
        """
        data = {"vpc2_id": vpc2_id}
        await self._make_request(
            "POST", f"/instances/{instance_id}/vpc2/detach", data=data
        )

    async def list_instance_vpcs(self, instance_id: str) -> list[dict[str, Any]]:
        """
        List VPCs attached to an instance.

        Args:
            instance_id: The instance ID

        Returns:
            List of VPCs attached to the instance
        """
        result = await self._make_request("GET", f"/instances/{instance_id}/vpcs")
        return result.get("vpcs", [])

    async def list_instance_vpc2s(self, instance_id: str) -> list[dict[str, Any]]:
        """
        List VPC 2.0 networks attached to an instance.

        Args:
            instance_id: The instance ID

        Returns:
            List of VPC 2.0 networks attached to the instance
        """
        result = await self._make_request("GET", f"/instances/{instance_id}/vpc2")
        return result.get("vpc2s", [])

    # =============================================================================
    # ISO Management Methods
    # =============================================================================

    async def list_isos(self) -> list[dict[str, Any]]:
        """
        List all available ISO images.

        Returns:
            List of ISO images
        """
        result = await self._make_request("GET", "/iso")
        return result.get("isos", [])

    async def get_iso(self, iso_id: str) -> dict[str, Any]:
        """
        Get details of a specific ISO image.

        Args:
            iso_id: The ISO ID

        Returns:
            ISO image details
        """
        result = await self._make_request("GET", f"/iso/{iso_id}")
        return result.get("iso", {})

    async def create_iso(self, url: str) -> dict[str, Any]:
        """
        Create a new ISO image from URL.

        Args:
            url: The URL to create the ISO from

        Returns:
            Created ISO details
        """
        data = {"url": url}
        result = await self._make_request("POST", "/iso", data=data)
        return result.get("iso", {})

    async def delete_iso(self, iso_id: str) -> None:
        """
        Delete an ISO image.

        Args:
            iso_id: The ISO ID to delete
        """
        await self._make_request("DELETE", f"/iso/{iso_id}")

    # =============================================================================
    # Operating System Methods
    # =============================================================================

    async def list_operating_systems(self) -> list[dict[str, Any]]:
        """
        List all available operating systems.

        Returns:
            List of operating systems
        """
        result = await self._make_request("GET", "/os")
        return result.get("os", [])

    async def get_operating_system(self, os_id: str) -> dict[str, Any]:
        """
        Get details of a specific operating system.

        Args:
            os_id: The operating system ID

        Returns:
            Operating system details
        """
        # The OS endpoint doesn't have individual get, so filter from list
        operating_systems = await self.list_operating_systems()
        for os_item in operating_systems:
            if str(os_item.get("id")) == str(os_id):
                return os_item
        raise VultrResourceNotFoundError(404, f"Operating system {os_id} not found")

    # =============================================================================
    # Plans Methods
    # =============================================================================

    async def list_plans(self, plan_type: str | None = None) -> list[dict[str, Any]]:
        """
        List all available plans.

        Args:
            plan_type: Optional plan type filter (e.g., 'all', 'vc2', 'vhf', 'voc')

        Returns:
            List of plans
        """
        params = {}
        if plan_type:
            params["type"] = plan_type

        result = await self._make_request("GET", "/plans", params=params)
        return result.get("plans", [])

    async def get_plan(self, plan_id: str) -> dict[str, Any]:
        """
        Get details of a specific plan.

        Args:
            plan_id: The plan ID

        Returns:
            Plan details
        """
        # The plans endpoint doesn't have individual get, so filter from list
        plans = await self.list_plans()
        for plan in plans:
            if plan.get("id") == plan_id:
                return plan
        raise VultrResourceNotFoundError(404, f"Plan {plan_id} not found")

    # =============================================================================
    # Applications Methods
    # =============================================================================

    async def list_applications(
        self, app_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        List all available applications (marketplace and one-click).

        Args:
            app_type: Optional filter by type ('marketplace', 'one-click', or None for all)

        Returns:
            List of applications
        """
        params = {}
        if app_type:
            params["type"] = app_type

        result = await self._make_request("GET", "/applications", params=params)
        return result.get("applications", [])

    async def get_marketplace_app_variables(self, image_id: str) -> dict[str, Any]:
        """
        Get configuration variables for a marketplace application.

        Args:
            image_id: The marketplace application image ID

        Returns:
            Application variables information
        """
        result = await self._make_request(
            "GET", f"/marketplace/apps/{image_id}/variables"
        )
        return result

    # =============================================================================
    # Startup Scripts Methods
    # =============================================================================

    def _decode_script_content(self, script_data: dict[str, Any]) -> dict[str, Any]:
        """
        Decode base64 encoded script content from Vultr API response.

        The Vultr API returns script content as base64 encoded strings.
        This method decodes it back to plain text for easier use.

        Args:
            script_data: Script dictionary from API response

        Returns:
            Script dictionary with decoded content
        """
        import base64

        if "script" in script_data and script_data["script"]:
            try:
                decoded = base64.b64decode(script_data["script"]).decode("utf-8")
                script_data = dict(script_data)  # Make a copy
                script_data["script"] = decoded
            except Exception:
                # If decoding fails, leave as-is (might already be plain text)
                pass
        return script_data

    async def list_startup_scripts(self) -> list[dict[str, Any]]:
        """
        List all startup scripts.

        Returns:
            List of startup scripts with decoded script content
        """
        result = await self._make_request("GET", "/startup-scripts")
        scripts = result.get("startup_scripts", [])
        return [self._decode_script_content(s) for s in scripts]

    async def get_startup_script(self, script_id: str) -> dict[str, Any]:
        """
        Get details of a specific startup script.

        Args:
            script_id: The startup script ID

        Returns:
            Startup script details with decoded script content
        """
        result = await self._make_request("GET", f"/startup-scripts/{script_id}")
        script = result.get("startup_script", {})
        return self._decode_script_content(script)

    async def create_startup_script(
        self, name: str, script: str, script_type: str = "boot"
    ) -> dict[str, Any]:
        """
        Create a new startup script.

        Args:
            name: Name for the startup script
            script: The script content (plain text - will be base64 encoded automatically)
            script_type: Type of script ('boot' or 'pxe')

        Returns:
            Created startup script details
        """
        import base64

        # Vultr API requires base64 encoded script content
        script_b64 = base64.b64encode(script.encode("utf-8")).decode("utf-8")
        data = {"name": name, "script": script_b64, "type": script_type}
        result = await self._make_request("POST", "/startup-scripts", data=data)
        return result.get("startup_script", {})

    async def update_startup_script(
        self, script_id: str, name: str | None = None, script: str | None = None
    ) -> dict[str, Any]:
        """
        Update a startup script.

        Args:
            script_id: The startup script ID
            name: New name for the script
            script: New script content (plain text - will be base64 encoded automatically)

        Returns:
            Updated startup script details
        """
        import base64

        data = {}
        if name is not None:
            data["name"] = name
        if script is not None:
            # Vultr API requires base64 encoded script content
            data["script"] = base64.b64encode(script.encode("utf-8")).decode("utf-8")

        result = await self._make_request(
            "PATCH", f"/startup-scripts/{script_id}", data=data
        )
        return result.get("startup_script", {})

    async def delete_startup_script(self, script_id: str) -> None:
        """
        Delete a startup script.

        Args:
            script_id: The startup script ID to delete
        """
        await self._make_request("DELETE", f"/startup-scripts/{script_id}")

    # =============================================================================
    # Billing Methods
    # =============================================================================

    async def get_account_info(self) -> dict[str, Any]:
        """
        Get account information including billing details.

        Returns:
            Account information and billing details
        """
        result = await self._make_request("GET", "/account")
        return result.get("account", {})

    async def list_billing_history(
        self,
        date_range: int | None = None,
        cursor: str | None = None,
        per_page: int | None = None,
    ) -> dict[str, Any]:
        """
        List billing history.

        Args:
            date_range: Number of days to include (default: 30)
            cursor: Cursor for pagination
            per_page: Number of items per page

        Returns:
            Billing history with pagination info
        """
        params = {}
        if date_range is not None:
            params["date_range"] = date_range
        if cursor is not None:
            params["cursor"] = cursor
        if per_page is not None:
            params["per_page"] = per_page

        return await self._make_request("GET", "/billing/history", params=params)

    async def list_invoices(
        self, cursor: str | None = None, per_page: int | None = None
    ) -> dict[str, Any]:
        """
        List invoices.

        Args:
            cursor: Cursor for pagination
            per_page: Number of items per page

        Returns:
            List of invoices with pagination info
        """
        params = {}
        if cursor is not None:
            params["cursor"] = cursor
        if per_page is not None:
            params["per_page"] = per_page

        return await self._make_request("GET", "/billing/invoices", params=params)

    async def get_invoice(self, invoice_id: str) -> dict[str, Any]:
        """
        Get a specific invoice.

        Args:
            invoice_id: The invoice ID

        Returns:
            Invoice details
        """
        result = await self._make_request("GET", f"/billing/invoices/{invoice_id}")
        return result.get("invoice", {})

    async def list_invoice_items(
        self,
        invoice_id: str,
        cursor: str | None = None,
        per_page: int | None = None,
    ) -> dict[str, Any]:
        """
        List items in a specific invoice.

        Args:
            invoice_id: The invoice ID
            cursor: Cursor for pagination
            per_page: Number of items per page

        Returns:
            Invoice items with pagination info
        """
        params = {}
        if cursor is not None:
            params["cursor"] = cursor
        if per_page is not None:
            params["per_page"] = per_page

        return await self._make_request(
            "GET", f"/billing/invoices/{invoice_id}/items", params=params
        )

    async def get_current_balance(self) -> dict[str, Any]:
        """
        Get current account balance.

        Returns:
            Current account balance information
        """
        account = await self.get_account_info()
        return {
            "balance": account.get("balance", 0),
            "pending_charges": account.get("pending_charges", 0),
            "last_payment_date": account.get("last_payment_date"),
            "last_payment_amount": account.get("last_payment_amount"),
        }

    async def get_monthly_usage_summary(self, year: int, month: int) -> dict[str, Any]:
        """
        Get monthly usage summary for billing analysis.

        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)

        Returns:
            Monthly usage and cost summary
        """
        # Get billing history for the specified month
        # Calculate date range from start of month to end of month
        import calendar
        from datetime import datetime

        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, calendar.monthrange(year, month)[1])
        current_date = datetime.now()

        # Calculate days from start of month to now (or end of month if past)
        if end_date > current_date:
            days = (current_date - start_date).days + 1
        else:
            days = (end_date - start_date).days + 1

        billing_data = await self.list_billing_history(date_range=days)

        # Process billing history to create summary
        billing_history = billing_data.get("billing_history", [])

        total_cost = 0
        service_costs = {}
        transaction_count = 0

        for item in billing_history:
            if item.get("date"):
                item_date = datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
                if item_date.year == year and item_date.month == month:
                    amount = float(item.get("amount", 0))
                    total_cost += amount
                    transaction_count += 1

                    description = item.get("description", "Unknown")
                    service_type = description.split()[0] if description else "Unknown"

                    if service_type not in service_costs:
                        service_costs[service_type] = 0
                    service_costs[service_type] += amount

        return {
            "year": year,
            "month": month,
            "total_cost": round(total_cost, 2),
            "transaction_count": transaction_count,
            "service_breakdown": service_costs,
            "average_daily_cost": round(total_cost / max(days, 1), 2)
            if days > 0
            else 0,
        }

    # =============================================================================
    # Bare Metal Server Methods
    # =============================================================================

    async def list_bare_metal_servers(self) -> list[dict[str, Any]]:
        """
        List all bare metal servers.

        Returns:
            List of bare metal servers
        """
        result = await self._make_request("GET", "/bare-metals")
        return result.get("bare_metals", [])

    async def get_bare_metal_server(self, baremetal_id: str) -> dict[str, Any]:
        """
        Get details of a specific bare metal server.

        Args:
            baremetal_id: The bare metal server ID

        Returns:
            Bare metal server details
        """
        result = await self._make_request("GET", f"/bare-metals/{baremetal_id}")
        return result.get("bare_metal", {})

    async def create_bare_metal_server(
        self,
        region: str,
        plan: str,
        os_id: str | None = None,
        iso_id: str | None = None,
        script_id: str | None = None,
        ssh_key_ids: list[str] | None = None,
        label: str | None = None,
        tag: str | None = None,
        user_data: str | None = None,
        enable_ipv6: bool | None = None,
        enable_private_network: bool | None = None,
        attach_private_network: list[str] | None = None,
        attach_vpc: list[str] | None = None,
        attach_vpc2: list[str] | None = None,
        enable_ddos_protection: bool | None = None,
        hostname: str | None = None,
        persistent_pxe: bool | None = None,
    ) -> dict[str, Any]:
        """
        Create a new bare metal server.

        Args:
            region: Region to deploy in
            plan: Bare metal plan ID
            os_id: Operating system ID
            iso_id: ISO ID for custom installation
            script_id: Startup script ID
            ssh_key_ids: List of SSH key IDs
            label: Server label
            tag: Server tag
            user_data: Cloud-init user data
            enable_ipv6: Enable IPv6
            enable_private_network: Enable private network
            attach_private_network: Private network IDs to attach
            attach_vpc: VPC IDs to attach
            attach_vpc2: VPC 2.0 IDs to attach
            enable_ddos_protection: Enable DDoS protection
            hostname: Server hostname
            persistent_pxe: Enable persistent PXE

        Returns:
            Created bare metal server details
        """
        data = {"region": region, "plan": plan}

        if os_id is not None:
            data["os_id"] = os_id
        if iso_id is not None:
            data["iso_id"] = iso_id
        if script_id is not None:
            data["script_id"] = script_id
        if ssh_key_ids is not None:
            data["sshkey_id"] = ssh_key_ids
        if label is not None:
            data["label"] = label
        if tag is not None:
            data["tag"] = tag
        if user_data is not None:
            data["user_data"] = user_data
        if enable_ipv6 is not None:
            data["enable_ipv6"] = enable_ipv6
        if enable_private_network is not None:
            data["enable_private_network"] = enable_private_network
        if attach_private_network is not None:
            data["attach_private_network"] = attach_private_network
        if attach_vpc is not None:
            data["attach_vpc"] = attach_vpc
        if attach_vpc2 is not None:
            data["attach_vpc2"] = attach_vpc2
        if enable_ddos_protection is not None:
            data["enable_ddos_protection"] = enable_ddos_protection
        if hostname is not None:
            data["hostname"] = hostname
        if persistent_pxe is not None:
            data["persistent_pxe"] = persistent_pxe

        result = await self._make_request("POST", "/bare-metals", data=data)
        return result.get("bare_metal", {})

    async def update_bare_metal_server(
        self,
        baremetal_id: str,
        label: str | None = None,
        tag: str | None = None,
        user_data: str | None = None,
        enable_ddos_protection: bool | None = None,
    ) -> dict[str, Any]:
        """
        Update a bare metal server.

        Args:
            baremetal_id: The bare metal server ID
            label: New label
            tag: New tag
            user_data: New user data
            enable_ddos_protection: Enable/disable DDoS protection

        Returns:
            Updated bare metal server details
        """
        data = {}
        if label is not None:
            data["label"] = label
        if tag is not None:
            data["tag"] = tag
        if user_data is not None:
            data["user_data"] = user_data
        if enable_ddos_protection is not None:
            data["enable_ddos_protection"] = enable_ddos_protection

        result = await self._make_request(
            "PATCH", f"/bare-metals/{baremetal_id}", data=data
        )
        return result.get("bare_metal", {})

    async def delete_bare_metal_server(self, baremetal_id: str) -> None:
        """
        Delete a bare metal server.

        Args:
            baremetal_id: The bare metal server ID to delete
        """
        await self._make_request("DELETE", f"/bare-metals/{baremetal_id}")

    async def start_bare_metal_server(self, baremetal_id: str) -> None:
        """
        Start a bare metal server.

        Args:
            baremetal_id: The bare metal server ID
        """
        await self._make_request("POST", f"/bare-metals/{baremetal_id}/start")

    async def stop_bare_metal_server(self, baremetal_id: str) -> None:
        """
        Stop a bare metal server.

        Args:
            baremetal_id: The bare metal server ID
        """
        await self._make_request("POST", f"/bare-metals/{baremetal_id}/halt")

    async def reboot_bare_metal_server(self, baremetal_id: str) -> None:
        """
        Reboot a bare metal server.

        Args:
            baremetal_id: The bare metal server ID
        """
        await self._make_request("POST", f"/bare-metals/{baremetal_id}/reboot")

    async def reinstall_bare_metal_server(
        self, baremetal_id: str, hostname: str | None = None
    ) -> dict[str, Any]:
        """
        Reinstall a bare metal server.

        Args:
            baremetal_id: The bare metal server ID
            hostname: New hostname for the server

        Returns:
            Reinstall operation details
        """
        data = {}
        if hostname is not None:
            data["hostname"] = hostname

        result = await self._make_request(
            "POST", f"/bare-metals/{baremetal_id}/reinstall", data=data
        )
        return result.get("bare_metal", {})

    async def get_bare_metal_bandwidth(self, baremetal_id: str) -> dict[str, Any]:
        """
        Get bandwidth usage for a bare metal server.

        Args:
            baremetal_id: The bare metal server ID

        Returns:
            Bandwidth usage information
        """
        result = await self._make_request(
            "GET", f"/bare-metals/{baremetal_id}/bandwidth"
        )
        return result.get("bandwidth", {})

    async def get_bare_metal_neighbors(self, baremetal_id: str) -> list[dict[str, Any]]:
        """
        Get neighbors (other servers on same physical host) for a bare metal server.

        Args:
            baremetal_id: The bare metal server ID

        Returns:
            List of neighboring servers
        """
        result = await self._make_request(
            "GET", f"/bare-metals/{baremetal_id}/neighbors"
        )
        return result.get("neighbors", [])

    async def get_bare_metal_user_data(self, baremetal_id: str) -> dict[str, Any]:
        """
        Get user data for a bare metal server.

        Args:
            baremetal_id: The bare metal server ID

        Returns:
            User data information
        """
        result = await self._make_request(
            "GET", f"/bare-metals/{baremetal_id}/user-data"
        )
        return result.get("user_data", {})

    async def list_bare_metal_plans(
        self, plan_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        List available bare metal plans.

        Args:
            plan_type: Optional plan type filter

        Returns:
            List of bare metal plans
        """
        params = {}
        if plan_type:
            params["type"] = plan_type

        result = await self._make_request("GET", "/plans-metal", params=params)
        return result.get("plans_metal", [])

    async def get_bare_metal_plan(self, plan_id: str) -> dict[str, Any]:
        """
        Get details of a specific bare metal plan.

        Args:
            plan_id: The plan ID

        Returns:
            Bare metal plan details
        """
        plans = await self.list_bare_metal_plans()
        for plan in plans:
            if plan.get("id") == plan_id:
                return plan
        raise VultrResourceNotFoundError(404, f"Bare metal plan {plan_id} not found")

    # =============================================================================
    # CDN Methods
    # =============================================================================

    async def list_cdn_zones(self) -> list[dict[str, Any]]:
        """
        List all CDN zones.

        Returns:
            List of CDN zones
        """
        result = await self._make_request("GET", "/cdns")
        return result.get("cdns", [])

    async def get_cdn_zone(self, cdn_id: str) -> dict[str, Any]:
        """
        Get details of a specific CDN zone.

        Args:
            cdn_id: The CDN zone ID

        Returns:
            CDN zone details
        """
        result = await self._make_request("GET", f"/cdns/{cdn_id}")
        return result.get("cdn", {})

    async def create_cdn_zone(
        self,
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
        data = {"origin_domain": origin_domain, "origin_scheme": origin_scheme}

        if cors_policy is not None:
            data["cors_policy"] = cors_policy
        if gzip_compression is not None:
            data["gzip_compression"] = gzip_compression
        if block_ai_bots is not None:
            data["block_ai_bots"] = block_ai_bots
        if block_bad_bots is not None:
            data["block_bad_bots"] = block_bad_bots
        if block_ip_addresses is not None:
            data["block_ip_addresses"] = block_ip_addresses
        if regions is not None:
            data["regions"] = regions

        result = await self._make_request("POST", "/cdns", data=data)
        return result.get("cdn", {})

    async def update_cdn_zone(
        self,
        cdn_id: str,
        cors_policy: str | None = None,
        gzip_compression: bool | None = None,
        block_ai_bots: bool | None = None,
        block_bad_bots: bool | None = None,
        block_ip_addresses: list[str] | None = None,
        regions: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Update a CDN zone configuration.

        Args:
            cdn_id: The CDN zone ID
            cors_policy: CORS policy configuration
            gzip_compression: Enable gzip compression
            block_ai_bots: Block AI/crawler bots
            block_bad_bots: Block known bad bots
            block_ip_addresses: List of IP addresses to block
            regions: List of regions to enable CDN in

        Returns:
            Updated CDN zone details
        """
        data = {}

        if cors_policy is not None:
            data["cors_policy"] = cors_policy
        if gzip_compression is not None:
            data["gzip_compression"] = gzip_compression
        if block_ai_bots is not None:
            data["block_ai_bots"] = block_ai_bots
        if block_bad_bots is not None:
            data["block_bad_bots"] = block_bad_bots
        if block_ip_addresses is not None:
            data["block_ip_addresses"] = block_ip_addresses
        if regions is not None:
            data["regions"] = regions

        result = await self._make_request("PATCH", f"/cdns/{cdn_id}", data=data)
        return result.get("cdn", {})

    async def delete_cdn_zone(self, cdn_id: str) -> None:
        """
        Delete a CDN zone.

        Args:
            cdn_id: The CDN zone ID to delete
        """
        await self._make_request("DELETE", f"/cdns/{cdn_id}")

    async def purge_cdn_zone(self, cdn_id: str) -> dict[str, Any]:
        """
        Purge all cached content from a CDN zone.

        Args:
            cdn_id: The CDN zone ID

        Returns:
            Purge operation details
        """
        result = await self._make_request("POST", f"/cdns/{cdn_id}/purge")
        return result.get("purge", {})

    async def get_cdn_zone_stats(self, cdn_id: str) -> dict[str, Any]:
        """
        Get statistics for a CDN zone.

        Args:
            cdn_id: The CDN zone ID

        Returns:
            CDN zone statistics
        """
        result = await self._make_request("GET", f"/cdns/{cdn_id}/stats")
        return result.get("stats", {})

    async def get_cdn_zone_logs(
        self,
        cdn_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        per_page: int | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """
        Get access logs for a CDN zone.

        Args:
            cdn_id: The CDN zone ID
            start_date: Start date for logs (ISO format)
            end_date: End date for logs (ISO format)
            per_page: Number of items per page
            cursor: Cursor for pagination

        Returns:
            CDN zone access logs
        """
        params = {}
        if start_date is not None:
            params["start_date"] = start_date
        if end_date is not None:
            params["end_date"] = end_date
        if per_page is not None:
            params["per_page"] = per_page
        if cursor is not None:
            params["cursor"] = cursor

        result = await self._make_request("GET", f"/cdns/{cdn_id}/logs", params=params)
        return result.get("logs", {})

    async def create_cdn_ssl_certificate(
        self,
        cdn_id: str,
        certificate: str,
        private_key: str,
        certificate_chain: str | None = None,
    ) -> dict[str, Any]:
        """
        Upload SSL certificate for a CDN zone.

        Args:
            cdn_id: The CDN zone ID
            certificate: SSL certificate content
            private_key: Private key content
            certificate_chain: Certificate chain (optional)

        Returns:
            SSL certificate details
        """
        data = {"certificate": certificate, "private_key": private_key}

        if certificate_chain is not None:
            data["certificate_chain"] = certificate_chain

        result = await self._make_request("POST", f"/cdns/{cdn_id}/ssl", data=data)
        return result.get("ssl", {})

    async def get_cdn_ssl_certificate(self, cdn_id: str) -> dict[str, Any]:
        """
        Get SSL certificate information for a CDN zone.

        Args:
            cdn_id: The CDN zone ID

        Returns:
            SSL certificate information
        """
        result = await self._make_request("GET", f"/cdns/{cdn_id}/ssl")
        return result.get("ssl", {})

    async def delete_cdn_ssl_certificate(self, cdn_id: str) -> None:
        """
        Remove SSL certificate from a CDN zone.

        Args:
            cdn_id: The CDN zone ID
        """
        await self._make_request("DELETE", f"/cdns/{cdn_id}/ssl")

    async def get_cdn_available_regions(self) -> list[dict[str, Any]]:
        """
        Get list of available CDN regions.

        Returns:
            List of available CDN regions
        """
        result = await self._make_request("GET", "/cdns/regions")
        return result.get("regions", [])

    # Kubernetes Engine (VKE) API Methods
    async def list_kubernetes_clusters(self) -> list[dict[str, Any]]:
        """
        List all Kubernetes clusters.

        Returns:
            List of Kubernetes cluster information
        """
        result = await self._make_request("GET", "/kubernetes/clusters")
        return result.get("vke_clusters", [])

    async def get_kubernetes_cluster(self, cluster_id: str) -> dict[str, Any]:
        """
        Get Kubernetes cluster details.

        Args:
            cluster_id: The cluster ID

        Returns:
            Kubernetes cluster information
        """
        result = await self._make_request("GET", f"/kubernetes/clusters/{cluster_id}")
        return result.get("vke_cluster", {})

    async def create_kubernetes_cluster(
        self,
        label: str,
        region: str,
        version: str,
        node_pools: list[dict[str, Any]],
        enable_firewall: bool = False,
        ha_controlplanes: bool = False,
    ) -> dict[str, Any]:
        """
        Create a new Kubernetes cluster.

        Args:
            label: Label for the cluster
            region: Region code
            version: Kubernetes version
            node_pools: List of node pool configurations
            enable_firewall: Enable firewall for cluster
            ha_controlplanes: Enable high availability control planes

        Returns:
            Created cluster information
        """
        data = {
            "label": label,
            "region": region,
            "version": version,
            "node_pools": node_pools,
        }
        if enable_firewall:
            data["enable_firewall"] = enable_firewall
        if ha_controlplanes:
            data["ha_controlplanes"] = ha_controlplanes

        result = await self._make_request("POST", "/kubernetes/clusters", data)
        return result.get("vke_cluster", {})

    async def update_kubernetes_cluster(
        self, cluster_id: str, label: str | None = None
    ) -> None:
        """
        Update a Kubernetes cluster.

        Args:
            cluster_id: The cluster ID
            label: New label for the cluster
        """
        data = {}
        if label is not None:
            data["label"] = label

        if data:
            await self._make_request(
                "PATCH", f"/kubernetes/clusters/{cluster_id}", data
            )

    async def delete_kubernetes_cluster(self, cluster_id: str) -> None:
        """
        Delete a Kubernetes cluster.

        Args:
            cluster_id: The cluster ID
        """
        await self._make_request("DELETE", f"/kubernetes/clusters/{cluster_id}")

    async def delete_kubernetes_cluster_with_resources(self, cluster_id: str) -> None:
        """
        Delete a Kubernetes cluster and all related resources.

        Args:
            cluster_id: The cluster ID
        """
        await self._make_request(
            "DELETE", f"/kubernetes/clusters/{cluster_id}/delete-with-linked-resources"
        )

    async def get_kubernetes_cluster_config(self, cluster_id: str) -> dict[str, Any]:
        """
        Get the kubeconfig for a Kubernetes cluster.

        Args:
            cluster_id: The cluster ID

        Returns:
            Kubeconfig content
        """
        result = await self._make_request(
            "GET", f"/kubernetes/clusters/{cluster_id}/config"
        )
        return result

    async def get_kubernetes_cluster_resources(self, cluster_id: str) -> dict[str, Any]:
        """
        Get resource usage information for a Kubernetes cluster.

        Args:
            cluster_id: The cluster ID

        Returns:
            Cluster resource usage
        """
        result = await self._make_request(
            "GET", f"/kubernetes/clusters/{cluster_id}/resources"
        )
        return result.get("resources", {})

    async def get_kubernetes_available_upgrades(self, cluster_id: str) -> list[str]:
        """
        Get available Kubernetes version upgrades for a cluster.

        Args:
            cluster_id: The cluster ID

        Returns:
            List of available versions for upgrade
        """
        result = await self._make_request(
            "GET", f"/kubernetes/clusters/{cluster_id}/available-upgrades"
        )
        return result.get("available_upgrades", [])

    async def upgrade_kubernetes_cluster(
        self, cluster_id: str, upgrade_version: str
    ) -> None:
        """
        Start a Kubernetes cluster upgrade.

        Args:
            cluster_id: The cluster ID
            upgrade_version: Target Kubernetes version
        """
        data = {"upgrade_version": upgrade_version}
        await self._make_request(
            "POST", f"/kubernetes/clusters/{cluster_id}/upgrades", data
        )

    async def get_kubernetes_versions(self) -> list[str]:
        """
        Get list of available Kubernetes versions.

        Returns:
            List of available Kubernetes versions
        """
        result = await self._make_request("GET", "/kubernetes/versions")
        return result.get("versions", [])

    # Kubernetes Node Pool API Methods
    async def list_kubernetes_node_pools(self, cluster_id: str) -> list[dict[str, Any]]:
        """
        List all node pools for a Kubernetes cluster.

        Args:
            cluster_id: The cluster ID

        Returns:
            List of node pools
        """
        result = await self._make_request(
            "GET", f"/kubernetes/clusters/{cluster_id}/node-pools"
        )
        return result.get("node_pools", [])

    async def get_kubernetes_node_pool(
        self, cluster_id: str, nodepool_id: str
    ) -> dict[str, Any]:
        """
        Get node pool details.

        Args:
            cluster_id: The cluster ID
            nodepool_id: The node pool ID

        Returns:
            Node pool information
        """
        result = await self._make_request(
            "GET", f"/kubernetes/clusters/{cluster_id}/node-pools/{nodepool_id}"
        )
        return result.get("node_pool", {})

    async def create_kubernetes_node_pool(
        self,
        cluster_id: str,
        node_quantity: int,
        plan: str,
        label: str,
        tag: str | None = None,
        auto_scaler: bool | None = None,
        min_nodes: int | None = None,
        max_nodes: int | None = None,
        labels: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new node pool in a Kubernetes cluster.

        Args:
            cluster_id: The cluster ID
            node_quantity: Number of nodes
            plan: Plan ID
            label: Node pool label
            tag: Optional tag
            auto_scaler: Enable auto-scaling
            min_nodes: Minimum nodes for auto-scaling
            max_nodes: Maximum nodes for auto-scaling
            labels: Node labels map

        Returns:
            Created node pool information
        """
        data = {"node_quantity": node_quantity, "plan": plan, "label": label}
        if tag is not None:
            data["tag"] = tag
        if auto_scaler is not None:
            data["auto_scaler"] = auto_scaler
        if min_nodes is not None:
            data["min_nodes"] = min_nodes
        if max_nodes is not None:
            data["max_nodes"] = max_nodes
        if labels is not None:
            data["labels"] = labels

        result = await self._make_request(
            "POST", f"/kubernetes/clusters/{cluster_id}/node-pools", data
        )
        return result.get("node_pool", {})

    async def update_kubernetes_node_pool(
        self,
        cluster_id: str,
        nodepool_id: str,
        node_quantity: int | None = None,
        tag: str | None = None,
        auto_scaler: bool | None = None,
        min_nodes: int | None = None,
        max_nodes: int | None = None,
        labels: dict[str, str] | None = None,
    ) -> None:
        """
        Update a node pool configuration.

        Args:
            cluster_id: The cluster ID
            nodepool_id: The node pool ID
            node_quantity: New number of nodes
            tag: New tag
            auto_scaler: Enable/disable auto-scaling
            min_nodes: Minimum nodes for auto-scaling
            max_nodes: Maximum nodes for auto-scaling
            labels: Node labels map
        """
        data = {}
        if node_quantity is not None:
            data["node_quantity"] = node_quantity
        if tag is not None:
            data["tag"] = tag
        if auto_scaler is not None:
            data["auto_scaler"] = auto_scaler
        if min_nodes is not None:
            data["min_nodes"] = min_nodes
        if max_nodes is not None:
            data["max_nodes"] = max_nodes
        if labels is not None:
            data["labels"] = labels

        if data:
            await self._make_request(
                "PATCH",
                f"/kubernetes/clusters/{cluster_id}/node-pools/{nodepool_id}",
                data,
            )

    async def delete_kubernetes_node_pool(
        self, cluster_id: str, nodepool_id: str
    ) -> None:
        """
        Delete a node pool from a Kubernetes cluster.

        Args:
            cluster_id: The cluster ID
            nodepool_id: The node pool ID
        """
        await self._make_request(
            "DELETE", f"/kubernetes/clusters/{cluster_id}/node-pools/{nodepool_id}"
        )

    # Kubernetes Node API Methods
    async def list_kubernetes_nodes(
        self, cluster_id: str, nodepool_id: str
    ) -> list[dict[str, Any]]:
        """
        List all nodes in a specific node pool.

        Args:
            cluster_id: The cluster ID
            nodepool_id: The node pool ID

        Returns:
            List of nodes
        """
        result = await self._make_request(
            "GET", f"/kubernetes/clusters/{cluster_id}/node-pools/{nodepool_id}/nodes"
        )
        return result.get("nodes", [])

    async def get_kubernetes_node(
        self, cluster_id: str, nodepool_id: str, node_id: str
    ) -> dict[str, Any]:
        """
        Get node details.

        Args:
            cluster_id: The cluster ID
            nodepool_id: The node pool ID
            node_id: The node ID

        Returns:
            Node information
        """
        result = await self._make_request(
            "GET",
            f"/kubernetes/clusters/{cluster_id}/node-pools/{nodepool_id}/nodes/{node_id}",
        )
        return result.get("node", {})

    async def delete_kubernetes_node(
        self, cluster_id: str, nodepool_id: str, node_id: str
    ) -> None:
        """
        Delete a specific node from a node pool.

        Args:
            cluster_id: The cluster ID
            nodepool_id: The node pool ID
            node_id: The node ID
        """
        await self._make_request(
            "DELETE",
            f"/kubernetes/clusters/{cluster_id}/node-pools/{nodepool_id}/nodes/{node_id}",
        )

    async def recycle_kubernetes_node(
        self, cluster_id: str, nodepool_id: str, node_id: str
    ) -> None:
        """
        Recycle (restart) a specific node.

        Args:
            cluster_id: The cluster ID
            nodepool_id: The node pool ID
            node_id: The node ID
        """
        await self._make_request(
            "POST",
            f"/kubernetes/clusters/{cluster_id}/node-pools/{nodepool_id}/nodes/{node_id}/recycle",
        )

    # Load Balancer API Methods
    async def list_load_balancers(self) -> list[dict[str, Any]]:
        """
        List all load balancers.

        Returns:
            List of load balancer information
        """
        result = await self._make_request("GET", "/load-balancers")
        return result.get("load_balancers", [])

    async def get_load_balancer(self, load_balancer_id: str) -> dict[str, Any]:
        """
        Get load balancer details.

        Args:
            load_balancer_id: The load balancer ID

        Returns:
            Load balancer information
        """
        result = await self._make_request("GET", f"/load-balancers/{load_balancer_id}")
        return result.get("load_balancer", {})

    async def create_load_balancer(
        self,
        region: str,
        balancing_algorithm: str = "roundrobin",
        ssl_redirect: bool = False,
        http2: bool = False,
        http3: bool = False,
        proxy_protocol: bool = False,
        timeout: int = 600,
        label: str | None = None,
        nodes: int = 1,
        health_check: dict[str, Any] | None = None,
        forwarding_rules: list[dict[str, Any]] | None = None,
        ssl: dict[str, str] | None = None,
        firewall_rules: list[dict[str, Any]] | None = None,
        auto_ssl: dict[str, str] | None = None,
        global_regions: list[str] | None = None,
        vpc: str | None = None,
        private_network: str | None = None,
        sticky_session: dict[str, str] | None = None,
        instances: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new load balancer.

        Args:
            region: Region code
            balancing_algorithm: Algorithm to use ('roundrobin' or 'leastconn')
            ssl_redirect: Redirect HTTP traffic to HTTPS
            http2: Enable HTTP/2 support
            http3: Enable HTTP/3 support
            proxy_protocol: Enable proxy protocol
            timeout: Connection timeout in seconds
            label: Label for the load balancer
            nodes: Number of backend nodes
            health_check: Health check configuration
            forwarding_rules: List of forwarding rules
            ssl: SSL configuration
            firewall_rules: List of firewall rules
            auto_ssl: Auto SSL configuration
            global_regions: List of global region codes
            vpc: VPC ID to attach to
            private_network: Private network ID (legacy)
            sticky_session: Sticky session configuration
            instances: List of instance IDs to attach

        Returns:
            Created load balancer information
        """
        data = {
            "region": region,
            "balancing_algorithm": balancing_algorithm,
            "ssl_redirect": ssl_redirect,
            "http2": http2,
            "http3": http3,
            "proxy_protocol": proxy_protocol,
            "timeout": timeout,
            "nodes": nodes,
        }

        if label is not None:
            data["label"] = label
        if health_check is not None:
            data["health_check"] = health_check
        if forwarding_rules is not None:
            data["forwarding_rules"] = forwarding_rules
        if ssl is not None:
            data["ssl"] = ssl
        if firewall_rules is not None:
            data["firewall_rules"] = firewall_rules
        if auto_ssl is not None:
            data["auto_ssl"] = auto_ssl
        if global_regions is not None:
            data["global_regions"] = global_regions
        if vpc is not None:
            data["vpc"] = vpc
        if private_network is not None:
            data["private_network"] = private_network
        if sticky_session is not None:
            data["sticky_session"] = sticky_session
        if instances is not None:
            data["instances"] = instances

        result = await self._make_request("POST", "/load-balancers", data)
        return result.get("load_balancer", {})

    async def update_load_balancer(
        self,
        load_balancer_id: str,
        ssl: dict[str, str] | None = None,
        sticky_session: dict[str, str] | None = None,
        forwarding_rules: list[dict[str, Any]] | None = None,
        health_check: dict[str, Any] | None = None,
        proxy_protocol: bool | None = None,
        timeout: int | None = None,
        ssl_redirect: bool | None = None,
        http2: bool | None = None,
        http3: bool | None = None,
        nodes: int | None = None,
        balancing_algorithm: str | None = None,
        instances: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing load balancer.

        Args:
            load_balancer_id: The load balancer ID
            ssl: SSL configuration
            sticky_session: Sticky session configuration
            forwarding_rules: Updated forwarding rules
            health_check: Updated health check configuration
            proxy_protocol: Enable/disable proxy protocol
            timeout: Connection timeout in seconds
            ssl_redirect: Enable/disable SSL redirect
            http2: Enable/disable HTTP/2
            http3: Enable/disable HTTP/3
            nodes: Number of backend nodes
            balancing_algorithm: Balancing algorithm
            instances: List of instance IDs to attach

        Returns:
            Updated load balancer information
        """
        data = {}

        if ssl is not None:
            data["ssl"] = ssl
        if sticky_session is not None:
            data["sticky_session"] = sticky_session
        if forwarding_rules is not None:
            data["forwarding_rules"] = forwarding_rules
        if health_check is not None:
            data["health_check"] = health_check
        if proxy_protocol is not None:
            data["proxy_protocol"] = proxy_protocol
        if timeout is not None:
            data["timeout"] = timeout
        if ssl_redirect is not None:
            data["ssl_redirect"] = ssl_redirect
        if http2 is not None:
            data["http2"] = http2
        if http3 is not None:
            data["http3"] = http3
        if nodes is not None:
            data["nodes"] = nodes
        if balancing_algorithm is not None:
            data["balancing_algorithm"] = balancing_algorithm
        if instances is not None:
            data["instances"] = instances

        result = await self._make_request(
            "PATCH", f"/load-balancers/{load_balancer_id}", data
        )
        return result.get("load_balancer", {})

    async def delete_load_balancer(self, load_balancer_id: str) -> None:
        """
        Delete a load balancer.

        Args:
            load_balancer_id: The load balancer ID
        """
        await self._make_request("DELETE", f"/load-balancers/{load_balancer_id}")

    async def delete_load_balancer_ssl(self, load_balancer_id: str) -> None:
        """
        Delete SSL certificate from a load balancer.

        Args:
            load_balancer_id: The load balancer ID
        """
        await self._make_request("DELETE", f"/load-balancers/{load_balancer_id}/ssl")

    async def disable_load_balancer_auto_ssl(self, load_balancer_id: str) -> None:
        """
        Disable Auto SSL for a load balancer.

        Args:
            load_balancer_id: The load balancer ID
        """
        await self._make_request(
            "DELETE", f"/load-balancers/{load_balancer_id}/auto_ssl"
        )

    # Load Balancer Forwarding Rules API Methods
    async def list_load_balancer_forwarding_rules(
        self, load_balancer_id: str
    ) -> list[dict[str, Any]]:
        """
        List forwarding rules for a load balancer.

        Args:
            load_balancer_id: The load balancer ID

        Returns:
            List of forwarding rules
        """
        result = await self._make_request(
            "GET", f"/load-balancers/{load_balancer_id}/forwarding-rules"
        )
        return result.get("forwarding_rules", [])

    async def create_load_balancer_forwarding_rule(
        self,
        load_balancer_id: str,
        frontend_protocol: str,
        frontend_port: int,
        backend_protocol: str,
        backend_port: int,
    ) -> dict[str, Any]:
        """
        Create a forwarding rule for a load balancer.

        Args:
            load_balancer_id: The load balancer ID
            frontend_protocol: Frontend protocol
            frontend_port: Frontend port number
            backend_protocol: Backend protocol
            backend_port: Backend port number

        Returns:
            Created forwarding rule information
        """
        data = {
            "frontend_protocol": frontend_protocol,
            "frontend_port": frontend_port,
            "backend_protocol": backend_protocol,
            "backend_port": backend_port,
        }

        result = await self._make_request(
            "POST", f"/load-balancers/{load_balancer_id}/forwarding-rules", data
        )
        return result.get("forwarding_rule", {})

    async def get_load_balancer_forwarding_rule(
        self, load_balancer_id: str, forwarding_rule_id: str
    ) -> dict[str, Any]:
        """
        Get details of a specific forwarding rule.

        Args:
            load_balancer_id: The load balancer ID
            forwarding_rule_id: The forwarding rule ID

        Returns:
            Forwarding rule details
        """
        result = await self._make_request(
            "GET",
            f"/load-balancers/{load_balancer_id}/forwarding-rules/{forwarding_rule_id}",
        )
        return result.get("forwarding_rule", {})

    async def delete_load_balancer_forwarding_rule(
        self, load_balancer_id: str, forwarding_rule_id: str
    ) -> None:
        """
        Delete a forwarding rule from a load balancer.

        Args:
            load_balancer_id: The load balancer ID
            forwarding_rule_id: The forwarding rule ID
        """
        await self._make_request(
            "DELETE",
            f"/load-balancers/{load_balancer_id}/forwarding-rules/{forwarding_rule_id}",
        )

    # Load Balancer Firewall Rules API Methods
    async def list_load_balancer_firewall_rules(
        self, load_balancer_id: str
    ) -> list[dict[str, Any]]:
        """
        List firewall rules for a load balancer.

        Args:
            load_balancer_id: The load balancer ID

        Returns:
            List of firewall rules
        """
        result = await self._make_request(
            "GET", f"/load-balancers/{load_balancer_id}/firewall-rules"
        )
        return result.get("firewall_rules", [])

    async def get_load_balancer_firewall_rule(
        self, load_balancer_id: str, firewall_rule_id: str
    ) -> dict[str, Any]:
        """
        Get details of a specific firewall rule.

        Args:
            load_balancer_id: The load balancer ID
            firewall_rule_id: The firewall rule ID

        Returns:
            Firewall rule details
        """
        result = await self._make_request(
            "GET",
            f"/load-balancers/{load_balancer_id}/firewall-rules/{firewall_rule_id}",
        )
        return result.get("firewall_rule", {})

    # Managed Database API Methods
    async def list_managed_databases(self) -> list[dict[str, Any]]:
        """
        List all managed databases.

        Returns:
            List of managed database information
        """
        result = await self._make_request("GET", "/databases")
        return result.get("databases", [])

    async def get_managed_database(self, database_id: str) -> dict[str, Any]:
        """
        Get managed database details.

        Args:
            database_id: The database ID

        Returns:
            Database information
        """
        result = await self._make_request("GET", f"/databases/{database_id}")
        return result.get("database", {})

    async def create_managed_database(
        self,
        database_engine: str,
        database_engine_version: str,
        region: str,
        plan: str,
        label: str,
        tag: str | None = None,
        vpc_id: str | None = None,
        trusted_ips: list[str] | None = None,
        mysql_sql_modes: list[str] | None = None,
        mysql_require_primary_key: bool | None = None,
        mysql_slow_query_log: bool | None = None,
        valkey_eviction_policy: str | None = None,
        kafka_rest_enabled: bool | None = None,
        kafka_schema_registry_enabled: bool | None = None,
        kafka_connect_enabled: bool | None = None,
    ) -> dict[str, Any]:
        """
        Create a new managed database.

        Args:
            database_engine: Database engine (mysql, pg, valkey, kafka)
            database_engine_version: Engine version
            region: Region code
            plan: Plan ID
            label: Database label
            tag: Optional tag
            vpc_id: VPC ID
            trusted_ips: List of trusted IP addresses
            mysql_sql_modes: MySQL SQL modes
            mysql_require_primary_key: Require primary key (MySQL)
            mysql_slow_query_log: Enable slow query log (MySQL)
            valkey_eviction_policy: Eviction policy (Valkey)
            kafka_rest_enabled: Enable Kafka REST
            kafka_schema_registry_enabled: Enable Schema Registry
            kafka_connect_enabled: Enable Kafka Connect

        Returns:
            Created database information
        """
        data = {
            "database_engine": database_engine,
            "database_engine_version": database_engine_version,
            "region": region,
            "plan": plan,
            "label": label,
        }

        if tag is not None:
            data["tag"] = tag
        if vpc_id is not None:
            data["vpc_id"] = vpc_id
        if trusted_ips is not None:
            data["trusted_ips"] = trusted_ips
        if mysql_sql_modes is not None:
            data["mysql_sql_modes"] = mysql_sql_modes
        if mysql_require_primary_key is not None:
            data["mysql_require_primary_key"] = mysql_require_primary_key
        if mysql_slow_query_log is not None:
            data["mysql_slow_query_log"] = mysql_slow_query_log
        if valkey_eviction_policy is not None:
            data["valkey_eviction_policy"] = valkey_eviction_policy
        if kafka_rest_enabled is not None:
            data["kafka_rest_enabled"] = kafka_rest_enabled
        if kafka_schema_registry_enabled is not None:
            data["kafka_schema_registry_enabled"] = kafka_schema_registry_enabled
        if kafka_connect_enabled is not None:
            data["kafka_connect_enabled"] = kafka_connect_enabled

        result = await self._make_request("POST", "/databases", data)
        return result.get("database", {})

    async def update_managed_database(
        self,
        database_id: str,
        region: str | None = None,
        plan: str | None = None,
        label: str | None = None,
        tag: str | None = None,
        vpc_id: str | None = None,
        timezone: str | None = None,
        trusted_ips: list[str] | None = None,
        mysql_sql_modes: list[str] | None = None,
        mysql_require_primary_key: bool | None = None,
        mysql_slow_query_log: bool | None = None,
        valkey_eviction_policy: str | None = None,
        kafka_rest_enabled: bool | None = None,
        kafka_schema_registry_enabled: bool | None = None,
        kafka_connect_enabled: bool | None = None,
    ) -> dict[str, Any]:
        """
        Update a managed database.

        Args:
            database_id: The database ID
            region: New region
            plan: New plan
            label: New label
            tag: New tag
            vpc_id: New VPC ID
            timezone: Database timezone
            trusted_ips: Updated trusted IPs
            mysql_sql_modes: MySQL SQL modes
            mysql_require_primary_key: Require primary key setting
            mysql_slow_query_log: Slow query log setting
            valkey_eviction_policy: Eviction policy
            kafka_rest_enabled: Kafka REST setting
            kafka_schema_registry_enabled: Schema Registry setting
            kafka_connect_enabled: Kafka Connect setting

        Returns:
            Updated database information
        """
        data = {}

        if region is not None:
            data["region"] = region
        if plan is not None:
            data["plan"] = plan
        if label is not None:
            data["label"] = label
        if tag is not None:
            data["tag"] = tag
        if vpc_id is not None:
            data["vpc_id"] = vpc_id
        if timezone is not None:
            data["timezone"] = timezone
        if trusted_ips is not None:
            data["trusted_ips"] = trusted_ips
        if mysql_sql_modes is not None:
            data["mysql_sql_modes"] = mysql_sql_modes
        if mysql_require_primary_key is not None:
            data["mysql_require_primary_key"] = mysql_require_primary_key
        if mysql_slow_query_log is not None:
            data["mysql_slow_query_log"] = mysql_slow_query_log
        if valkey_eviction_policy is not None:
            data["valkey_eviction_policy"] = valkey_eviction_policy
        if kafka_rest_enabled is not None:
            data["kafka_rest_enabled"] = kafka_rest_enabled
        if kafka_schema_registry_enabled is not None:
            data["kafka_schema_registry_enabled"] = kafka_schema_registry_enabled
        if kafka_connect_enabled is not None:
            data["kafka_connect_enabled"] = kafka_connect_enabled

        result = await self._make_request("PUT", f"/databases/{database_id}", data)
        return result.get("database", {})

    async def delete_managed_database(self, database_id: str) -> None:
        """
        Delete a managed database.

        Args:
            database_id: The database ID
        """
        await self._make_request("DELETE", f"/databases/{database_id}")

    async def get_database_usage(self, database_id: str) -> dict[str, Any]:
        """
        Get database usage statistics.

        Args:
            database_id: The database ID

        Returns:
            Usage information
        """
        result = await self._make_request("GET", f"/databases/{database_id}/usage")
        return result.get("usage", {})

    # Database User Management
    async def list_database_users(self, database_id: str) -> list[dict[str, Any]]:
        """
        List database users.

        Args:
            database_id: The database ID

        Returns:
            List of database users
        """
        result = await self._make_request("GET", f"/databases/{database_id}/users")
        return result.get("users", [])

    async def create_database_user(
        self,
        database_id: str,
        username: str,
        password: str | None = None,
        encryption: str | None = None,
        access_level: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a database user.

        Args:
            database_id: The database ID
            username: Username for the new user
            password: Password (auto-generated if not provided)
            encryption: Password encryption type
            access_level: Permission level

        Returns:
            Created user information
        """
        data = {"username": username}

        if password is not None:
            data["password"] = password
        if encryption is not None:
            data["encryption"] = encryption
        if access_level is not None:
            data["access_level"] = access_level

        result = await self._make_request(
            "POST", f"/databases/{database_id}/users", data
        )
        return result.get("user", {})

    async def get_database_user(
        self, database_id: str, username: str
    ) -> dict[str, Any]:
        """
        Get database user details.

        Args:
            database_id: The database ID
            username: The username

        Returns:
            User information
        """
        result = await self._make_request(
            "GET", f"/databases/{database_id}/users/{username}"
        )
        return result.get("user", {})

    async def update_database_user(
        self,
        database_id: str,
        username: str,
        password: str | None = None,
        access_level: str | None = None,
    ) -> dict[str, Any]:
        """
        Update a database user.

        Args:
            database_id: The database ID
            username: The username to update
            password: New password
            access_level: New permission level

        Returns:
            Updated user information
        """
        data = {}

        if password is not None:
            data["password"] = password
        if access_level is not None:
            data["access_level"] = access_level

        result = await self._make_request(
            "PUT", f"/databases/{database_id}/users/{username}", data
        )
        return result.get("user", {})

    async def delete_database_user(self, database_id: str, username: str) -> None:
        """
        Delete a database user.

        Args:
            database_id: The database ID
            username: The username to delete
        """
        await self._make_request("DELETE", f"/databases/{database_id}/users/{username}")

    async def update_database_user_access_control(
        self,
        database_id: str,
        username: str,
        acl_categories: list[str] | None = None,
        acl_channels: list[str] | None = None,
        acl_commands: list[str] | None = None,
        acl_keys: list[str] | None = None,
    ) -> None:
        """
        Update database user access control (Valkey/Redis).

        Args:
            database_id: The database ID
            username: The username
            acl_categories: ACL categories
            acl_channels: ACL channels
            acl_commands: ACL commands
            acl_keys: ACL keys
        """
        data = {}

        if acl_categories is not None:
            data["acl_categories"] = acl_categories
        if acl_channels is not None:
            data["acl_channels"] = acl_channels
        if acl_commands is not None:
            data["acl_commands"] = acl_commands
        if acl_keys is not None:
            data["acl_keys"] = acl_keys

        await self._make_request(
            "PUT", f"/databases/{database_id}/users/{username}/access-control", data
        )

    # Logical Database Management
    async def list_logical_databases(self, database_id: str) -> list[dict[str, Any]]:
        """
        List logical databases.

        Args:
            database_id: The database ID

        Returns:
            List of logical databases
        """
        result = await self._make_request("GET", f"/databases/{database_id}/dbs")
        return result.get("dbs", [])

    async def create_logical_database(
        self, database_id: str, name: str
    ) -> dict[str, Any]:
        """
        Create a logical database.

        Args:
            database_id: The database ID
            name: Name for the logical database

        Returns:
            Created logical database information
        """
        data = {"name": name}
        result = await self._make_request("POST", f"/databases/{database_id}/dbs", data)
        return result.get("db", {})

    async def get_logical_database(
        self, database_id: str, db_name: str
    ) -> dict[str, Any]:
        """
        Get logical database details.

        Args:
            database_id: The database ID
            db_name: The logical database name

        Returns:
            Logical database information
        """
        result = await self._make_request(
            "GET", f"/databases/{database_id}/dbs/{db_name}"
        )
        return result.get("db", {})

    async def delete_logical_database(self, database_id: str, db_name: str) -> None:
        """
        Delete a logical database.

        Args:
            database_id: The database ID
            db_name: The logical database name
        """
        await self._make_request("DELETE", f"/databases/{database_id}/dbs/{db_name}")

    # Connection Pool Management
    async def list_connection_pools(self, database_id: str) -> list[dict[str, Any]]:
        """
        List connection pools.

        Args:
            database_id: The database ID

        Returns:
            List of connection pools
        """
        result = await self._make_request(
            "GET", f"/databases/{database_id}/connection-pools"
        )
        return result.get("connection_pools", [])

    async def create_connection_pool(
        self,
        database_id: str,
        name: str,
        database: str,
        username: str,
        mode: str,
        size: int,
    ) -> dict[str, Any]:
        """
        Create a connection pool.

        Args:
            database_id: The database ID
            name: Pool name
            database: Target database
            username: Database username
            mode: Pool mode
            size: Pool size

        Returns:
            Created pool information
        """
        data = {
            "name": name,
            "database": database,
            "username": username,
            "mode": mode,
            "size": size,
        }
        result = await self._make_request(
            "POST", f"/databases/{database_id}/connection-pools", data
        )
        return result.get("connection_pool", {})

    async def get_connection_pool(
        self, database_id: str, pool_name: str
    ) -> dict[str, Any]:
        """
        Get connection pool details.

        Args:
            database_id: The database ID
            pool_name: The pool name

        Returns:
            Connection pool information
        """
        result = await self._make_request(
            "GET", f"/databases/{database_id}/connection-pools/{pool_name}"
        )
        return result.get("connection_pool", {})

    async def update_connection_pool(
        self,
        database_id: str,
        pool_name: str,
        database: str | None = None,
        username: str | None = None,
        mode: str | None = None,
        size: int | None = None,
    ) -> dict[str, Any]:
        """
        Update a connection pool.

        Args:
            database_id: The database ID
            pool_name: The pool name
            database: New target database
            username: New username
            mode: New mode
            size: New size

        Returns:
            Updated pool information
        """
        data = {}

        if database is not None:
            data["database"] = database
        if username is not None:
            data["username"] = username
        if mode is not None:
            data["mode"] = mode
        if size is not None:
            data["size"] = size

        result = await self._make_request(
            "PUT", f"/databases/{database_id}/connection-pools/{pool_name}", data
        )
        return result.get("connection_pool", {})

    async def delete_connection_pool(self, database_id: str, pool_name: str) -> None:
        """
        Delete a connection pool.

        Args:
            database_id: The database ID
            pool_name: The pool name
        """
        await self._make_request(
            "DELETE", f"/databases/{database_id}/connection-pools/{pool_name}"
        )

    # Database Backup Management
    async def list_database_backups(self, database_id: str) -> list[dict[str, Any]]:
        """
        List database backups.

        Args:
            database_id: The database ID

        Returns:
            List of backups
        """
        result = await self._make_request("GET", f"/databases/{database_id}/backups")
        return result.get("backups", [])

    async def restore_database_from_backup(
        self,
        database_id: str,
        backup_label: str,
        database_label: str,
        plan: str,
        region: str,
        vpc_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Restore database from backup.

        Args:
            database_id: The source database ID
            backup_label: The backup label
            database_label: Label for new database
            plan: Plan for new database
            region: Region for new database
            vpc_id: VPC ID

        Returns:
            Restoration information
        """
        data = {
            "backup_label": backup_label,
            "label": database_label,
            "plan": plan,
            "region": region,
        }

        if vpc_id is not None:
            data["vpc_id"] = vpc_id

        result = await self._make_request(
            "POST", f"/databases/{database_id}/restore", data
        )
        return result.get("database", {})

    async def fork_database(
        self,
        database_id: str,
        label: str,
        region: str,
        plan: str,
        vpc_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fork a database.

        Args:
            database_id: The source database ID
            label: Label for forked database
            region: Region for new database
            plan: Plan for new database
            vpc_id: VPC ID

        Returns:
            Forked database information
        """
        data = {"label": label, "region": region, "plan": plan}

        if vpc_id is not None:
            data["vpc_id"] = vpc_id

        result = await self._make_request(
            "POST", f"/databases/{database_id}/fork", data
        )
        return result.get("database", {})

    # Read Replica Management
    async def create_read_replica(
        self, database_id: str, label: str, region: str, plan: str
    ) -> dict[str, Any]:
        """
        Create a read replica.

        Args:
            database_id: The source database ID
            label: Label for read replica
            region: Region for replica
            plan: Plan for replica

        Returns:
            Read replica information
        """
        data = {"label": label, "region": region, "plan": plan}

        result = await self._make_request(
            "POST", f"/databases/{database_id}/read-replica", data
        )
        return result.get("database", {})

    async def promote_read_replica(self, database_id: str) -> None:
        """
        Promote a read replica to standalone.

        Args:
            database_id: The read replica database ID
        """
        await self._make_request(
            "POST", f"/databases/{database_id}/promote-read-replica"
        )

    # Database Plans
    async def list_database_plans(self) -> list[dict[str, Any]]:
        """
        List database plans.

        Returns:
            List of available database plans
        """
        result = await self._make_request("GET", "/databases/plans")
        return result.get("plans", [])

    # Maintenance and Migration
    async def list_database_versions(self, database_id: str) -> list[dict[str, Any]]:
        """
        List available database versions for upgrade.

        Args:
            database_id: The database ID

        Returns:
            List of available versions
        """
        result = await self._make_request(
            "GET", f"/databases/{database_id}/version-upgrade"
        )
        return result.get("available_versions", [])

    async def start_version_upgrade(self, database_id: str, version: str) -> None:
        """
        Start database version upgrade.

        Args:
            database_id: The database ID
            version: Target version
        """
        data = {"version": version}
        await self._make_request(
            "POST", f"/databases/{database_id}/version-upgrade", data
        )

    async def get_maintenance_updates(self, database_id: str) -> list[dict[str, Any]]:
        """
        Get maintenance updates.

        Args:
            database_id: The database ID

        Returns:
            List of maintenance updates
        """
        result = await self._make_request(
            "GET", f"/databases/{database_id}/maintenance"
        )
        return result.get("available_updates", [])

    async def start_maintenance(self, database_id: str) -> None:
        """
        Start maintenance on database.

        Args:
            database_id: The database ID
        """
        await self._make_request("POST", f"/databases/{database_id}/maintenance")

    async def get_migration_status(self, database_id: str) -> dict[str, Any]:
        """
        Get migration status.

        Args:
            database_id: The database ID

        Returns:
            Migration status
        """
        result = await self._make_request("GET", f"/databases/{database_id}/migration")
        return result.get("migration", {})

    async def start_migration(
        self,
        database_id: str,
        host: str,
        port: int,
        username: str,
        password: str,
        database: str,
        ssl: bool = True,
    ) -> None:
        """
        Start database migration.

        Args:
            database_id: The destination database ID
            host: Source host
            port: Source port
            username: Source username
            password: Source password
            database: Source database
            ssl: Use SSL
        """
        data = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "database": database,
            "ssl": ssl,
        }
        await self._make_request("POST", f"/databases/{database_id}/migration", data)

    async def stop_migration(self, database_id: str) -> None:
        """
        Stop database migration.

        Args:
            database_id: The database ID
        """
        await self._make_request("DELETE", f"/databases/{database_id}/migration")

    # Kafka-specific methods
    async def list_kafka_topics(self, database_id: str) -> list[dict[str, Any]]:
        """
        List Kafka topics.

        Args:
            database_id: The Kafka database ID

        Returns:
            List of topics
        """
        result = await self._make_request("GET", f"/databases/{database_id}/topics")
        return result.get("topics", [])

    async def create_kafka_topic(
        self,
        database_id: str,
        name: str,
        partitions: int = 3,
        replication: int = 2,
        retention_hours: int = 168,
        retention_bytes: int = 1073741824,
    ) -> dict[str, Any]:
        """
        Create a Kafka topic.

        Args:
            database_id: The Kafka database ID
            name: Topic name
            partitions: Number of partitions
            replication: Replication factor
            retention_hours: Retention hours
            retention_bytes: Retention bytes

        Returns:
            Created topic information
        """
        data = {
            "name": name,
            "partitions": partitions,
            "replication": replication,
            "retention_hours": retention_hours,
            "retention_bytes": retention_bytes,
        }
        result = await self._make_request(
            "POST", f"/databases/{database_id}/topics", data
        )
        return result.get("topic", {})

    async def get_kafka_topic(
        self, database_id: str, topic_name: str
    ) -> dict[str, Any]:
        """
        Get Kafka topic details.

        Args:
            database_id: The Kafka database ID
            topic_name: The topic name

        Returns:
            Topic information
        """
        result = await self._make_request(
            "GET", f"/databases/{database_id}/topics/{topic_name}"
        )
        return result.get("topic", {})

    async def update_kafka_topic(
        self,
        database_id: str,
        topic_name: str,
        partitions: int | None = None,
        replication: int | None = None,
        retention_hours: int | None = None,
        retention_bytes: int | None = None,
    ) -> dict[str, Any]:
        """
        Update Kafka topic.

        Args:
            database_id: The Kafka database ID
            topic_name: The topic name
            partitions: Number of partitions
            replication: Replication factor
            retention_hours: Retention hours
            retention_bytes: Retention bytes

        Returns:
            Updated topic information
        """
        data = {}

        if partitions is not None:
            data["partitions"] = partitions
        if replication is not None:
            data["replication"] = replication
        if retention_hours is not None:
            data["retention_hours"] = retention_hours
        if retention_bytes is not None:
            data["retention_bytes"] = retention_bytes

        result = await self._make_request(
            "PUT", f"/databases/{database_id}/topics/{topic_name}", data
        )
        return result.get("topic", {})

    async def delete_kafka_topic(self, database_id: str, topic_name: str) -> None:
        """
        Delete Kafka topic.

        Args:
            database_id: The Kafka database ID
            topic_name: The topic name
        """
        await self._make_request(
            "DELETE", f"/databases/{database_id}/topics/{topic_name}"
        )

    # Storage Gateway API Methods
    async def list_storage_gateways(self) -> list[dict[str, Any]]:
        """
        List all storage gateways in your account.

        Returns:
            List of storage gateway information
        """
        result = await self._make_request("GET", "/storage-gateways")
        return result.get("storage_gateway", [])

    async def get_storage_gateway(self, gateway_id: str) -> dict[str, Any]:
        """
        Get storage gateway details.

        Args:
            gateway_id: The storage gateway ID

        Returns:
            Storage gateway information
        """
        result = await self._make_request("GET", f"/storage-gateways/{gateway_id}")
        return result.get("storage_gateway", {})

    async def create_storage_gateway(
        self,
        label: str,
        gateway_type: str,
        region: str,
        export_config: dict[str, Any],
        network_config: dict[str, Any],
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new storage gateway.

        Args:
            label: Label for the storage gateway
            gateway_type: Type of storage gateway (e.g., "nfs4")
            region: Region code
            export_config: Export configuration
            network_config: Network configuration
            tags: Optional list of tags

        Returns:
            Created storage gateway information
        """
        data = {
            "label": label,
            "type": gateway_type,
            "region": region,
            "export_config": export_config,
            "network_config": network_config,
        }
        if tags is not None:
            data["tags"] = tags

        result = await self._make_request("POST", "/storage-gateways", data=data)
        return result.get("storage_gateway", {})

    async def update_storage_gateway(
        self,
        gateway_id: str,
        label: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """
        Update storage gateway configuration.

        Args:
            gateway_id: The storage gateway ID
            label: New label for the gateway
            tags: New tags for the gateway
        """
        data = {}
        if label is not None:
            data["label"] = label
        if tags is not None:
            data["tags"] = tags

        if data:
            await self._make_request(
                "PUT", f"/storage-gateways/{gateway_id}", data=data
            )

    async def delete_storage_gateway(self, gateway_id: str) -> None:
        """
        Delete a storage gateway.

        Args:
            gateway_id: The storage gateway ID to delete
        """
        await self._make_request("DELETE", f"/storage-gateways/{gateway_id}")

    async def add_storage_gateway_export(
        self, gateway_id: str, export_config: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Add a new export to a storage gateway.

        Args:
            gateway_id: The storage gateway ID
            export_config: Export configuration

        Returns:
            Created export information
        """
        # The API expects an array of exports
        data = [export_config]
        result = await self._make_request(
            "POST", f"/storage-gateways/{gateway_id}/exports", data=data
        )
        return result.get(
            "vpc", {}
        )  # Note: API response uses "vpc" key based on schema

    async def delete_storage_gateway_export(
        self, gateway_id: str, export_id: int
    ) -> None:
        """
        Delete an export from a storage gateway.

        Args:
            gateway_id: The storage gateway ID
            export_id: The export ID to delete
        """
        await self._make_request(
            "DELETE", f"/storage-gateways/{gateway_id}/exports/{export_id}"
        )

    # Object Storage Methods
    async def list_object_storage(self) -> list[dict[str, Any]]:
        """
        List all Object Storage instances.

        Returns:
            List of Object Storage instances
        """
        result = await self._make_request("GET", "/object-storage")
        return result.get("object_storages", [])

    async def get_object_storage(self, object_storage_id: str) -> dict[str, Any]:
        """
        Get Object Storage details.

        Args:
            object_storage_id: The Object Storage ID

        Returns:
            Object Storage information
        """
        result = await self._make_request("GET", f"/object-storage/{object_storage_id}")
        return result.get("object_storage", {})

    async def create_object_storage(
        self, cluster_id: int, label: str
    ) -> dict[str, Any]:
        """
        Create a new Object Storage instance.

        Args:
            cluster_id: The cluster ID where the Object Storage will be created
            label: Label for the Object Storage instance

        Returns:
            Created Object Storage information
        """
        data = {"cluster_id": cluster_id, "label": label}
        result = await self._make_request("POST", "/object-storage", data=data)
        return result.get("object_storage", {})

    async def update_object_storage(self, object_storage_id: str, label: str) -> None:
        """
        Update Object Storage label.

        Args:
            object_storage_id: The Object Storage ID
            label: New label for the Object Storage
        """
        data = {"label": label}
        await self._make_request(
            "PUT", f"/object-storage/{object_storage_id}", data=data
        )

    async def delete_object_storage(self, object_storage_id: str) -> None:
        """
        Delete an Object Storage instance.

        Args:
            object_storage_id: The Object Storage ID to delete
        """
        await self._make_request("DELETE", f"/object-storage/{object_storage_id}")

    async def regenerate_object_storage_keys(
        self, object_storage_id: str
    ) -> dict[str, Any]:
        """
        Regenerate the access keys for an Object Storage instance.

        Args:
            object_storage_id: The Object Storage ID

        Returns:
            Object Storage information with new keys
        """
        result = await self._make_request(
            "POST", f"/object-storage/{object_storage_id}/regenerate-keys"
        )
        return result.get("object_storage", {})

    async def list_object_storage_clusters(self) -> list[dict[str, Any]]:
        """
        List all Object Storage clusters.

        Returns:
            List of Object Storage clusters
        """
        result = await self._make_request("GET", "/object-storage/clusters")
        return result.get("object_storage_clusters", [])

    async def list_object_storage_cluster_tiers(
        self, cluster_id: int
    ) -> list[dict[str, Any]]:
        """
        List all available tiers for a specific Object Storage cluster.

        Args:
            cluster_id: The cluster ID

        Returns:
            List of available tiers for the cluster
        """
        result = await self._make_request(
            "GET", f"/object-storage/clusters/{cluster_id}/tiers"
        )
        return result.get("tiers", [])

    # Serverless Inference methods
    async def list_inference_subscriptions(self) -> list[dict[str, Any]]:
        """
        List all Serverless Inference subscriptions in your account.

        Returns:
            List of inference subscription objects
        """
        result = await self._make_request("GET", "/inference")
        return result.get("subscriptions", [])

    async def get_inference_subscription(self, inference_id: str) -> dict[str, Any]:
        """
        Get information about a Serverless Inference subscription.

        Args:
            inference_id: The inference subscription ID

        Returns:
            Inference subscription information
        """
        result = await self._make_request("GET", f"/inference/{inference_id}")
        return result.get("subscription", {})

    async def create_inference_subscription(self, label: str) -> dict[str, Any]:
        """
        Create a new Serverless Inference subscription.

        Args:
            label: Label for the inference subscription

        Returns:
            Created inference subscription information
        """
        data = {"label": label}
        result = await self._make_request("POST", "/inference", data=data)
        return result.get("subscription", {})

    async def update_inference_subscription(
        self, inference_id: str, label: str
    ) -> dict[str, Any]:
        """
        Update a Serverless Inference subscription.

        Args:
            inference_id: The inference subscription ID
            label: New label for the subscription

        Returns:
            Updated inference subscription information
        """
        data = {"label": label}
        result = await self._make_request(
            "PATCH", f"/inference/{inference_id}", data=data
        )
        return result.get("subscription", {})

    async def delete_inference_subscription(self, inference_id: str) -> None:
        """
        Delete a Serverless Inference subscription.

        Args:
            inference_id: The inference subscription ID to delete
        """
        await self._make_request("DELETE", f"/inference/{inference_id}")

    async def get_inference_usage(self, inference_id: str) -> dict[str, Any]:
        """
        Get usage information for a Serverless Inference subscription.

        Args:
            inference_id: The inference subscription ID

        Returns:
            Usage information including token counts and limits
        """
        result = await self._make_request("GET", f"/inference/{inference_id}/usage")
        return result.get("usage", {})

    # =============================================================================
    # Subaccount Management Methods
    # =============================================================================

    async def list_subaccounts(self) -> list[dict[str, Any]]:
        """
        List all subaccounts.

        Returns:
            List of subaccounts with their details
        """
        result = await self._make_request("GET", "/subaccounts")
        return result.get("subaccounts", [])

    async def create_subaccount(
        self,
        email: str,
        subaccount_name: str | None = None,
        subaccount_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new subaccount.

        Args:
            email: Email address for the subaccount
            subaccount_name: Display name for the subaccount
            subaccount_id: Custom identifier for the subaccount

        Returns:
            Created subaccount details
        """
        data = {"email": email}
        if subaccount_name:
            data["subaccount_name"] = subaccount_name
        if subaccount_id:
            data["subaccount_id"] = subaccount_id

        result = await self._make_request("POST", "/subaccounts", data=data)
        return result.get("subaccount", {})

    # =============================================================================
    # User Management Methods
    # =============================================================================

    async def list_users(self) -> list[dict[str, Any]]:
        """
        List all users in your account.

        Returns:
            List of user objects with details
        """
        result = await self._make_request("GET", "/users")
        return result.get("users", [])

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """
        Get user information.

        Args:
            user_id: The user ID

        Returns:
            User information
        """
        result = await self._make_request("GET", f"/users/{user_id}")
        return result.get("user", {})

    async def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        password: str,
        api_enabled: bool = True,
        service_user: bool = False,
        acls: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new user.

        Args:
            email: User's email address
            first_name: User's first name
            last_name: User's last name
            password: User's password
            api_enabled: Enable API access
            service_user: Create as service user (API-only)
            acls: List of permissions

        Returns:
            Created user information
        """
        data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "password": password,
            "api_enabled": api_enabled,
            "service_user": service_user,
        }

        if acls is not None:
            data["acls"] = acls

        result = await self._make_request("POST", "/users", data=data)
        return result.get("user", {})

    async def update_user(
        self,
        user_id: str,
        api_enabled: bool | None = None,
        acls: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Update a user's settings.

        Args:
            user_id: The user ID
            api_enabled: Enable/disable API access
            acls: List of permissions

        Returns:
            Updated user information
        """
        data = {}

        if api_enabled is not None:
            data["api_enabled"] = api_enabled
        if acls is not None:
            data["acls"] = acls

        result = await self._make_request("PATCH", f"/users/{user_id}", data=data)
        return result.get("user", {})

    async def delete_user(self, user_id: str) -> None:
        """
        Delete a user.

        Args:
            user_id: The user ID to delete
        """
        await self._make_request("DELETE", f"/users/{user_id}")

    # User IP Whitelist Management
    async def get_user_ip_whitelist(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get IP whitelist for a user.

        Args:
            user_id: The user ID

        Returns:
            List of IP whitelist entries
        """
        result = await self._make_request("GET", f"/users/{user_id}/ip-whitelist")
        return result.get("ip_whitelist", [])

    async def get_user_ip_whitelist_entry(
        self, user_id: str, subnet: str, subnet_size: int
    ) -> dict[str, Any]:
        """
        Get a specific IP whitelist entry for a user.

        Args:
            user_id: The user ID
            subnet: The IP address or subnet
            subnet_size: The subnet size

        Returns:
            IP whitelist entry details
        """
        params = {"subnet": subnet, "subnet_size": subnet_size}
        result = await self._make_request(
            "GET", f"/users/{user_id}/ip-whitelist/entry", params=params
        )
        return result.get("ip_whitelist_entry", {})

    async def add_user_ip_whitelist_entry(
        self, user_id: str, subnet: str, subnet_size: int
    ) -> None:
        """
        Add an IP address or subnet to a user's whitelist.

        Args:
            user_id: The user ID
            subnet: The IP address or subnet to add
            subnet_size: The subnet size
        """
        data = {"subnet": subnet, "subnet_size": subnet_size}
        await self._make_request("POST", f"/users/{user_id}/ip-whitelist", data=data)

    async def remove_user_ip_whitelist_entry(
        self, user_id: str, subnet: str, subnet_size: int
    ) -> None:
        """
        Remove an IP address or subnet from a user's whitelist.

        Args:
            user_id: The user ID
            subnet: The IP address or subnet to remove
            subnet_size: The subnet size
        """
        data = {"subnet": subnet, "subnet_size": subnet_size}
        await self._make_request("DELETE", f"/users/{user_id}/ip-whitelist", data=data)


def create_mcp_server(api_key: str | None = None) -> Server:
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
    async def list_resources() -> list[Resource]:
        """List available resources."""
        return [
            Resource(
                uri="vultr://domains",
                name="DNS Domains",
                description="All DNS domains in your Vultr account",
                mimeType="application/json",
            ),
            Resource(
                uri="vultr://capabilities",
                name="Server Capabilities",
                description="Vultr DNS server capabilities and supported features",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        """Read a specific resource."""
        # Convert AnyUrl to string if needed
        uri_str = str(uri)

        if uri_str == "vultr://domains":
            try:
                domains = await vultr_client.list_domains()
                return str(domains)
            except Exception as e:
                return f"Error loading domains: {str(e)}"

        elif uri_str == "vultr://capabilities":
            capabilities = {
                "supported_record_types": [
                    {
                        "type": "A",
                        "description": "IPv4 address record",
                        "example": "192.168.1.100",
                        "requires_priority": False,
                    },
                    {
                        "type": "AAAA",
                        "description": "IPv6 address record",
                        "example": "2001:db8::1",
                        "requires_priority": False,
                    },
                    {
                        "type": "CNAME",
                        "description": "Canonical name record (alias)",
                        "example": "example.com",
                        "requires_priority": False,
                    },
                    {
                        "type": "MX",
                        "description": "Mail exchange record",
                        "example": "mail.example.com",
                        "requires_priority": True,
                    },
                    {
                        "type": "TXT",
                        "description": "Text record for verification and SPF",
                        "example": "v=spf1 include:_spf.google.com ~all",
                        "requires_priority": False,
                    },
                    {
                        "type": "NS",
                        "description": "Name server record",
                        "example": "ns1.example.com",
                        "requires_priority": False,
                    },
                    {
                        "type": "SRV",
                        "description": "Service record",
                        "example": "0 5 443 example.com",
                        "requires_priority": True,
                    },
                ],
                "operations": {
                    "domains": ["list", "create", "delete", "get"],
                    "records": ["list", "create", "update", "delete", "get"],
                },
                "default_ttl": 300,
                "min_ttl": 60,
                "max_ttl": 86400,
            }
            return str(capabilities)

        elif uri_str.startswith("vultr://records/"):
            domain = uri_str.replace("vultr://records/", "")
            try:
                records = await vultr_client.list_records(domain)
                return str(
                    {"domain": domain, "records": records, "record_count": len(records)}
                )
            except Exception as e:
                return f"Error loading records for {domain}: {str(e)}"

        return "Resource not found"

    # Define MCP tools
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="list_dns_domains",
                description="List all DNS domains in your Vultr account",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="get_dns_domain",
                description="Get detailed information for a specific DNS domain",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name to retrieve (e.g., 'example.com')",
                        }
                    },
                    "required": ["domain"],
                },
            ),
            Tool(
                name="create_dns_domain",
                description="Create a new DNS domain with a default A record",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name to create (e.g., 'newdomain.com')",
                        },
                        "ip": {
                            "type": "string",
                            "description": "IPv4 address for the default A record (e.g., '192.168.1.100')",
                        },
                    },
                    "required": ["domain", "ip"],
                },
            ),
            Tool(
                name="delete_dns_domain",
                description="Delete a DNS domain and ALL its associated records",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name to delete (e.g., 'example.com')",
                        }
                    },
                    "required": ["domain"],
                },
            ),
            Tool(
                name="list_dns_records",
                description="List all DNS records for a specific domain",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name (e.g., 'example.com')",
                        }
                    },
                    "required": ["domain"],
                },
            ),
            Tool(
                name="get_dns_record",
                description="Get detailed information for a specific DNS record",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name (e.g., 'example.com')",
                        },
                        "record_id": {
                            "type": "string",
                            "description": "The unique record identifier",
                        },
                    },
                    "required": ["domain", "record_id"],
                },
            ),
            Tool(
                name="create_dns_record",
                description="Create a new DNS record for a domain",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name (e.g., 'example.com')",
                        },
                        "record_type": {
                            "type": "string",
                            "description": "Record type (A, AAAA, CNAME, MX, TXT, NS, SRV)",
                        },
                        "name": {
                            "type": "string",
                            "description": "Record name/subdomain",
                        },
                        "data": {"type": "string", "description": "Record value"},
                        "ttl": {
                            "type": "integer",
                            "description": "Time to live in seconds (60-86400, default: 300)",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Priority for MX/SRV records (0-65535)",
                        },
                    },
                    "required": ["domain", "record_type", "name", "data"],
                },
            ),
            Tool(
                name="update_dns_record",
                description="Update an existing DNS record with new configuration",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name (e.g., 'example.com')",
                        },
                        "record_id": {
                            "type": "string",
                            "description": "The unique identifier of the record to update",
                        },
                        "record_type": {
                            "type": "string",
                            "description": "New record type (A, AAAA, CNAME, MX, TXT, NS, SRV)",
                        },
                        "name": {
                            "type": "string",
                            "description": "New record name/subdomain",
                        },
                        "data": {"type": "string", "description": "New record value"},
                        "ttl": {
                            "type": "integer",
                            "description": "New TTL in seconds (60-86400, optional)",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "New priority for MX/SRV records (optional)",
                        },
                    },
                    "required": ["domain", "record_id", "record_type", "name", "data"],
                },
            ),
            Tool(
                name="delete_dns_record",
                description="Delete a specific DNS record",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name (e.g., 'example.com')",
                        },
                        "record_id": {
                            "type": "string",
                            "description": "The unique identifier of the record to delete",
                        },
                    },
                    "required": ["domain", "record_id"],
                },
            ),
            Tool(
                name="validate_dns_record",
                description="Validate DNS record parameters before creation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "record_type": {
                            "type": "string",
                            "description": "The record type (A, AAAA, CNAME, MX, TXT, NS, SRV)",
                        },
                        "name": {
                            "type": "string",
                            "description": "The record name/subdomain",
                        },
                        "data": {
                            "type": "string",
                            "description": "The record data/value",
                        },
                        "ttl": {
                            "type": "integer",
                            "description": "Time to live in seconds (optional)",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Priority for MX/SRV records (optional)",
                        },
                    },
                    "required": ["record_type", "name", "data"],
                },
            ),
            Tool(
                name="analyze_dns_records",
                description="Analyze DNS configuration for a domain and provide insights",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name to analyze (e.g., 'example.com')",
                        }
                    },
                    "required": ["domain"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
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
                return [
                    TextContent(
                        type="text", text=f"Domain {domain} deleted successfully"
                    )
                ]

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
                result = await vultr_client.create_record(
                    domain, record_type, name, data, ttl, priority
                )
                return [TextContent(type="text", text=str(result))]

            elif name == "update_dns_record":
                domain = arguments["domain"]
                record_id = arguments["record_id"]
                record_type = arguments["record_type"]
                name = arguments["name"]
                data = arguments["data"]
                ttl = arguments.get("ttl")
                priority = arguments.get("priority")
                result = await vultr_client.update_record(
                    domain, record_id, record_type, name, data, ttl, priority
                )
                return [TextContent(type="text", text=str(result))]

            elif name == "delete_dns_record":
                domain = arguments["domain"]
                record_id = arguments["record_id"]
                await vultr_client.delete_record(domain, record_id)
                return [
                    TextContent(
                        type="text", text=f"DNS record {record_id} deleted successfully"
                    )
                ]

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
                    "suggestions": [],
                }

                # Validate record type
                valid_types = ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SRV"]
                if record_type.upper() not in valid_types:
                    validation_result["valid"] = False
                    validation_result["errors"].append(
                        f"Invalid record type. Must be one of: {', '.join(valid_types)}"
                    )

                record_type = record_type.upper()

                # Validate TTL
                if ttl is not None:
                    if ttl < 60 or ttl > 86400:
                        validation_result["warnings"].append(
                            "TTL should be between 60 and 86400 seconds"
                        )
                    elif ttl < 300:
                        validation_result["warnings"].append(
                            "Low TTL values may impact DNS performance"
                        )

                # Record-specific validation
                if record_type == "A":
                    try:
                        ipaddress.IPv4Address(data)
                    except ipaddress.AddressValueError:
                        validation_result["valid"] = False
                        validation_result["errors"].append(
                            "Invalid IPv4 address format"
                        )

                elif record_type == "AAAA":
                    try:
                        ipv6_addr = ipaddress.IPv6Address(data)
                        # Add helpful suggestions for IPv6 addresses
                        if ipv6_addr.ipv4_mapped:
                            validation_result["suggestions"].append(
                                "Consider using a native IPv6 address instead of IPv4-mapped format"
                            )
                        elif ipv6_addr.compressed != data:
                            validation_result["suggestions"].append(
                                f"Consider using compressed format: {ipv6_addr.compressed}"
                            )

                        # Check for common special addresses
                        if ipv6_addr.is_loopback:
                            validation_result["warnings"].append(
                                "This is the IPv6 loopback address (::1)"
                            )
                        elif ipv6_addr.is_link_local:
                            validation_result["warnings"].append(
                                "This is an IPv6 link-local address (fe80::/10)"
                            )
                        elif ipv6_addr.is_private:
                            validation_result["warnings"].append(
                                "This is an IPv6 private address"
                            )

                    except ipaddress.AddressValueError as e:
                        validation_result["valid"] = False
                        validation_result["errors"].append(
                            f"Invalid IPv6 address: {str(e)}"
                        )

                elif record_type == "CNAME":
                    if name == "@" or name == "":
                        validation_result["valid"] = False
                        validation_result["errors"].append(
                            "CNAME records cannot be used for root domain (@)"
                        )

                elif record_type == "MX":
                    if priority is None:
                        validation_result["valid"] = False
                        validation_result["errors"].append(
                            "MX records require a priority value"
                        )
                    elif priority < 0 or priority > 65535:
                        validation_result["valid"] = False
                        validation_result["errors"].append(
                            "MX priority must be between 0 and 65535"
                        )

                elif record_type == "SRV":
                    if priority is None:
                        validation_result["valid"] = False
                        validation_result["errors"].append(
                            "SRV records require a priority value"
                        )
                    srv_parts = data.split()
                    if len(srv_parts) != 3:
                        validation_result["valid"] = False
                        validation_result["errors"].append(
                            "SRV data must be in format: 'weight port target'"
                        )

                result = {
                    "record_type": record_type,
                    "name": name,
                    "data": data,
                    "ttl": ttl,
                    "priority": priority,
                    "validation": validation_result,
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
                    record_type = record.get("type", "UNKNOWN")
                    record_name = record.get("name", "")
                    record_data = record.get("data", "")
                    ttl = record.get("ttl", 300)

                    record_types[record_type] = record_types.get(record_type, 0) + 1
                    ttl_values.append(ttl)

                    if record_type == "A" and record_name in ["@", domain]:
                        has_root_a = True
                    if record_name == "www":
                        has_www = True
                    if record_type == "MX":
                        has_mx = True
                    if record_type == "TXT" and "spf1" in record_data.lower():
                        has_spf = True

                # Generate recommendations
                recommendations = []
                issues = []

                if not has_root_a:
                    recommendations.append(
                        "Consider adding an A record for the root domain (@)"
                    )
                if not has_www:
                    recommendations.append(
                        "Consider adding a www subdomain (A or CNAME record)"
                    )
                if not has_mx and total_records > 1:
                    recommendations.append(
                        "Consider adding MX records if you plan to use email"
                    )
                if has_mx and not has_spf:
                    recommendations.append(
                        "Add SPF record (TXT) to prevent email spoofing"
                    )

                avg_ttl = sum(ttl_values) / len(ttl_values) if ttl_values else 0
                low_ttl_count = sum(1 for ttl in ttl_values if ttl < 300)

                if low_ttl_count > total_records * 0.5:
                    issues.append(
                        "Many records have very low TTL values, which may impact performance"
                    )

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
                            "has_spf_protection": has_spf,
                        },
                    },
                    "recommendations": recommendations,
                    "potential_issues": issues,
                    "records_detail": records,
                }
                return [TextContent(type="text", text=str(result))]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


async def run_server(api_key: str | None = None) -> None:
    """
    Create and run a Vultr DNS MCP server.

    Args:
        api_key: Vultr API key. If not provided, will read from VULTR_API_KEY env var.
    """
    server = create_mcp_server(api_key)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, None)
