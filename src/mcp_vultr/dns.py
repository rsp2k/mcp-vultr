"""
Vultr DNS FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr DNS domains and records.
"""

from typing import Any

from fastmcp import Context, FastMCP

from .dns_analyzer import DNSAnalyzer
from .notification_manager import NotificationManager
from .server import VultrValidationError, VultrResourceNotFoundError


def create_dns_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr DNS management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with DNS management tools
    """
    mcp = FastMCP(name="vultr-dns")
    dns_analyzer = DNSAnalyzer(vultr_client)

    # DNS Domain resources
    @mcp.resource("domains://list")
    async def list_domains_resource() -> list[dict[str, Any]]:
        """List all DNS domains in your Vultr account."""
        try:
            return await vultr_client.list_domains()
        except Exception:
            # If the API returns an error when no domains exist, return empty list
            return []

    @mcp.resource("domains://{domain}")
    async def get_domain_resource(domain: str) -> dict[str, Any]:
        """Get details for a specific DNS domain.

        Args:
            domain: The domain name to get details for
        """
        return await vultr_client.get_domain(domain)

    @mcp.resource("domains://{domain}/records")
    async def list_records_resource(domain: str) -> list[dict[str, Any]]:
        """List all DNS records for a domain.

        Args:
            domain: The domain name to list records for
        """
        return await vultr_client.list_records(domain)

    @mcp.resource("domains://{domain}/records/{record_id}")
    async def get_record_resource(domain: str, record_id: str) -> dict[str, Any]:
        """Get details for a specific DNS record.

        Args:
            domain: The domain name
            record_id: The record ID to get details for
        """
        return await vultr_client.get_record(domain, record_id)

    @mcp.resource("domains://{domain}/analysis")
    async def analyze_domain_resource(domain: str) -> dict[str, Any]:
        """Analyze DNS records for a domain and provide recommendations.

        Args:
            domain: The domain name to analyze
        """
        return await dns_analyzer.analyze_domain(domain)

    @mcp.resource("domains://{domain}/zone-file")
    async def export_zone_file_resource(domain: str) -> str:
        """Export domain records as standard DNS zone file format.

        Args:
            domain: The domain name to export
        """
        return await vultr_client.export_zone_file(domain)

    # DNS Domain tools
    @mcp.tool
    async def get_domain(domain: str) -> dict[str, Any]:
        """Get details for a specific DNS domain.

        Args:
            domain: The domain name to get details for

        Returns:
            Domain details including creation date and DNSSEC status
        """
        return await vultr_client.get_domain(domain)

    @mcp.tool
    async def create_domain(
        domain: str, ip: str, ctx: Context | None = None, dns_sec: str = "disabled"
    ) -> dict[str, Any]:
        """Create a new DNS domain.

        Args:
            domain: The domain name to create
            ip: The default IP address for the domain
            ctx: FastMCP context for resource change notifications
            dns_sec: Enable DNSSEC (enabled/disabled, default: disabled)

        Returns:
            Created domain information
        """
        result = await vultr_client.create_domain(domain, ip, dns_sec)

        # Notify clients that domain list has changed
        if ctx is not None:
            await NotificationManager.notify_dns_changes(
                ctx=ctx, operation="create_domain", domain=domain
            )

        return result

    @mcp.tool
    async def delete_domain(domain: str, ctx: Context | None = None) -> dict[str, str]:
        """Delete a DNS domain and all its records.

        Args:
            domain: The domain name to delete
            ctx: FastMCP context for resource change notifications

        Returns:
            Status message confirming deletion
        """
        await vultr_client.delete_domain(domain)

        # Notify clients that both domain list and domain records have changed
        if ctx is not None:
            await NotificationManager.notify_dns_changes(
                ctx=ctx, operation="delete_domain", domain=domain
            )

        return {"status": "success", "message": f"Domain {domain} deleted successfully"}

    # DNS Record tools
    @mcp.tool
    async def list_records(domain: str) -> list[dict[str, Any]]:
        """List all DNS records for a domain.

        Args:
            domain: The domain name to list records for

        Returns:
            List of DNS records with details
        """
        return await vultr_client.list_records(domain)

    @mcp.tool
    async def get_record(domain: str, record_id: str) -> dict[str, Any]:
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
        ctx: Context | None = None,
        ttl: int = 300,
        priority: int | None = None,
    ) -> dict[str, Any]:
        """Create a new DNS record.

        Args:
            domain: The domain name
            record_type: Record type (A, AAAA, CNAME, MX, TXT, NS, SRV)
            name: Record name/subdomain
            data: Record data/value
            ctx: FastMCP context for resource change notifications
            ttl: Time to live in seconds (default: 300)
            priority: Priority for MX/SRV records

        Returns:
            Created record information
        """
        try:
            result = await vultr_client.create_record(
                domain, record_type, name, data, ttl, priority
            )
        except VultrValidationError as e:
            # Provide clearer error messages for common cases
            error_msg = str(e.message).lower() if hasattr(e, 'message') else str(e).lower()
            display_name = name if name != "@" else domain

            if "duplicate" in error_msg or "exists" in error_msg or "already" in error_msg:
                raise ValueError(
                    f"Record already exists: {record_type} record for '{display_name}' "
                    f"with data '{data}' already exists in {domain}. "
                    f"Use update_record to modify it, or delete_record first."
                ) from None
            elif "invalid" in error_msg:
                raise ValueError(
                    f"Invalid record: {e.message if hasattr(e, 'message') else e}"
                ) from None
            else:
                raise ValueError(
                    f"Failed to create {record_type} record for '{display_name}': "
                    f"{e.message if hasattr(e, 'message') else e}"
                ) from None
        except VultrResourceNotFoundError:
            raise ValueError(
                f"Domain '{domain}' not found. Create the domain first with create_domain."
            ) from None

        # Notify clients that records for this domain have changed
        if ctx is not None:
            await NotificationManager.notify_dns_changes(
                ctx=ctx, operation="create_record", domain=domain
            )

        return result

    @mcp.tool
    async def update_record(
        domain: str,
        record_id: str,
        ctx: Context | None = None,
        name: str | None = None,
        data: str | None = None,
        ttl: int | None = None,
        priority: int | None = None,
    ) -> dict[str, Any]:
        """Update an existing DNS record.

        Args:
            domain: The domain name
            record_id: The record ID to update
            ctx: FastMCP context for resource change notifications
            name: New record name (optional)
            data: New record data (optional)
            ttl: New TTL value (optional)
            priority: New priority for MX/SRV records (optional)

        Returns:
            Updated record information
        """
        result = await vultr_client.update_record(
            domain, record_id, name, data, ttl, priority
        )

        # Notify clients that records for this domain have changed
        if ctx is not None:
            await NotificationManager.notify_dns_changes(
                ctx=ctx, operation="update_record", domain=domain, record_id=record_id
            )

        return result

    @mcp.tool
    async def delete_record(
        domain: str, record_id: str, ctx: Context | None = None
    ) -> dict[str, str]:
        """Delete a DNS record.

        Args:
            domain: The domain name
            record_id: The record ID to delete
            ctx: FastMCP context for resource change notifications

        Returns:
            Status message confirming deletion
        """
        await vultr_client.delete_record(domain, record_id)

        # Notify clients that records for this domain have changed
        if ctx is not None:
            await NotificationManager.notify_dns_changes(
                ctx=ctx, operation="delete_record", domain=domain, record_id=record_id
            )

        return {
            "status": "success",
            "message": f"Record {record_id} deleted successfully",
        }

    @mcp.tool
    async def validate_record(
        record_type: str,
        name: str,
        data: str,
        ttl: int = 300,
        priority: int | None = None,
    ) -> dict[str, Any]:
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
        return await vultr_client.validate_record(
            record_type, name, data, ttl, priority
        )

    @mcp.tool
    async def analyze_domain(domain: str) -> dict[str, Any]:
        """Analyze DNS configuration for a domain and provide recommendations.

        Args:
            domain: The domain name to analyze

        Returns:
            Analysis results with recommendations for improvements
        """
        return await dns_analyzer.analyze_domain(domain)

    @mcp.tool
    async def setup_website(
        domain: str, ip: str, www_enabled: bool = True
    ) -> list[dict[str, Any]]:
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
            records.append(
                await vultr_client.create_record(domain, "CNAME", "www", domain)
            )

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
    async def import_zone_file(
        domain: str, zone_data: str, dry_run: bool = False
    ) -> list[dict[str, Any]]:
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
