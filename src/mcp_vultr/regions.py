"""
Vultr Regions FastMCP Module.

This module contains FastMCP tools and resources for retrieving Vultr region information.
"""

from typing import Any, List

from fastmcp import FastMCP


def create_regions_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr regions information.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with region information tools
    """
    mcp = FastMCP(name="vultr-regions")

    # Region resources
    @mcp.resource("regions://list")
    async def list_regions_resource() -> List[dict[str, Any]]:
        """List all available Vultr regions."""
        return await vultr_client.list_regions()

    @mcp.resource("regions://{region_id}/availability")
    async def get_availability_resource(region_id: str) -> dict[str, Any]:
        """Get availability information for a specific region.

        Args:
            region_id: The region ID to check availability for
        """
        return await vultr_client.list_availability(region_id)

    # Region tools
    @mcp.tool
    async def list() -> List[dict[str, Any]]:
        """List all available Vultr regions.

        Returns:
            List of region objects with details including:
            - id: Region ID (e.g., "ewr", "lax", "nrt")
            - city: City name
            - country: Country code
            - continent: Continent name
            - options: Available options (e.g., ["ddos_protection"])
        """
        return await vultr_client.list_regions()

    @mcp.tool
    async def get_availability(region_id: str) -> dict[str, Any]:
        """Get availability information for a specific region.

        Args:
            region_id: The region ID to check availability for (e.g., "ewr", "lax")

        Returns:
            Availability information including:
            - available_plans: List of available plan IDs in this region

        This is useful for checking which instance plans are available
        in a specific region before creating instances.
        """
        return await vultr_client.list_availability(region_id)

    @mcp.tool
    async def find_regions_with_plan(plan_id: str) -> List[dict[str, Any]]:
        """Find all regions where a specific plan is available.

        Args:
            plan_id: The plan ID to search for (e.g., "vc2-1c-1gb")

        Returns:
            List of regions where the plan is available, with region details
        """
        all_regions = await vultr_client.list_regions()
        available_regions = []

        for region in all_regions:
            try:
                availability = await vultr_client.list_availability(region["id"])
                if plan_id in availability.get("available_plans", []):
                    available_regions.append(region)
            except Exception:
                # Skip regions that might have availability check issues
                continue

        return available_regions

    @mcp.tool
    async def list_by_continent(continent: str) -> List[dict[str, Any]]:
        """List all regions in a specific continent.

        Args:
            continent: Continent name (e.g., "North America", "Europe", "Asia", "Australia")

        Returns:
            List of regions in the specified continent
        """
        all_regions = await vultr_client.list_regions()
        return [
            r
            for r in all_regions
            if r.get("continent", "").lower() == continent.lower()
        ]

    @mcp.tool
    async def list_with_ddos_protection() -> List[dict[str, Any]]:
        """List all regions that support DDoS protection.

        Returns:
            List of regions with DDoS protection capability
        """
        all_regions = await vultr_client.list_regions()
        return [r for r in all_regions if "ddos_protection" in r.get("options", [])]

    return mcp
