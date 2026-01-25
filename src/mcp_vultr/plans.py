"""
Vultr Plans FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr plans.
"""

import json
from typing import Any

from fastmcp import FastMCP


def _format_plan_compact(plan: dict[str, Any]) -> str:
    """Format a single plan in compact table format."""
    plan_id = plan.get("id", "unknown")
    vcpus = plan.get("vcpu_count", 0)
    ram_mb = plan.get("ram", 0)
    ram_gb = ram_mb // 1024 if ram_mb >= 1024 else ram_mb
    disk = plan.get("disk", 0)
    disk_type = plan.get("disk_type", "SSD")
    cost = plan.get("monthly_cost", 0)
    locations = plan.get("locations", [])

    # Format locations - show first 5, then count remaining
    if len(locations) > 5:
        loc_str = ", ".join(locations[:5]) + f" +{len(locations)-5} more"
    else:
        loc_str = ", ".join(locations) if locations else "none"

    return f"{plan_id:<20} {vcpus:>2} CPU  {ram_gb:>3}GB RAM  {disk:>4}GB {disk_type:<4}  ${cost:>6.0f}/mo  [{loc_str}]"


def create_plans_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr plans management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with plans management tools
    """
    mcp = FastMCP(name="vultr-plans")

    @mcp.tool()
    async def list_plans(
        plan_type: str | None = None,
        format: str = "compact",
    ) -> str:
        """
        List all available plans. Supports compact table format for reduced token usage.

        Args:
            plan_type: Optional plan type filter (e.g., 'all', 'vc2', 'vhf', 'voc')
            format: Output format - 'compact' (default, table) or 'json' (full details)

        Returns:
            Plans in requested format
        """
        plans = await vultr_client.list_plans(plan_type)

        if format == "compact":
            type_label = plan_type.upper() if plan_type else "ALL"
            lines = [f"; {type_label} plans ({len(plans)} available)"]
            lines.append(f"; {'Plan ID':<20} {'CPU':>6}  {'RAM':>10}  {'Disk':>14}  {'Cost':>10}  Regions")
            lines.append("; " + "-" * 90)
            for plan in sorted(plans, key=lambda p: p.get("monthly_cost", 0)):
                lines.append(_format_plan_compact(plan))
            return "\n".join(lines)
        else:
            return json.dumps(plans)

    @mcp.tool()
    async def get_plan(plan_id: str) -> dict[str, Any]:
        """
        Get details of a specific plan.

        Args:
            plan_id: The plan ID

        Returns:
            Plan details
        """
        return await vultr_client.get_plan(plan_id)

    @mcp.tool()
    async def list_vc2_plans(format: str = "compact") -> str:
        """
        List VC2 (Virtual Cloud Compute) plans.

        Args:
            format: Output format - 'compact' (default) or 'json'

        Returns:
            VC2 plans in requested format
        """
        return await list_plans("vc2", format)

    @mcp.tool()
    async def list_vhf_plans(format: str = "compact") -> str:
        """
        List VHF (High Frequency) plans.

        Args:
            format: Output format - 'compact' (default) or 'json'

        Returns:
            VHF plans in requested format
        """
        return await list_plans("vhf", format)

    @mcp.tool()
    async def list_voc_plans(format: str = "compact") -> str:
        """
        List VOC (Optimized Cloud) plans.

        Args:
            format: Output format - 'compact' (default) or 'json'

        Returns:
            VOC plans in requested format
        """
        return await list_plans("voc", format)

    @mcp.tool()
    async def search_plans_by_specs(
        min_vcpus: int | None = None,
        min_ram: int | None = None,
        min_disk: int | None = None,
        max_monthly_cost: float | None = None,
        format: str = "compact",
    ) -> str:
        """
        Search plans by specifications.

        Args:
            min_vcpus: Minimum number of vCPUs
            min_ram: Minimum RAM in MB
            min_disk: Minimum disk space in GB
            max_monthly_cost: Maximum monthly cost in USD
            format: Output format - 'compact' (default) or 'json'

        Returns:
            Plans matching the criteria in requested format
        """
        all_plans = await vultr_client.list_plans()
        matching_plans = []

        for plan in all_plans:
            # Check vCPUs
            if min_vcpus and plan.get("vcpu_count", 0) < min_vcpus:
                continue

            # Check RAM (convert GB to MB for comparison if needed)
            if min_ram:
                ram_mb = plan.get("ram", 0)
                # If ram is in GB, convert to MB
                if ram_mb < 1000:  # Assuming values less than 1000 are in GB
                    ram_mb = ram_mb * 1024
                if ram_mb < min_ram:
                    continue

            # Check disk space
            if min_disk and plan.get("disk", 0) < min_disk:
                continue

            # Check monthly cost
            if (
                max_monthly_cost
                and plan.get("monthly_cost", float("inf")) > max_monthly_cost
            ):
                continue

            matching_plans.append(plan)

        if format == "compact":
            filters = []
            if min_vcpus:
                filters.append(f"≥{min_vcpus} CPU")
            if min_ram:
                filters.append(f"≥{min_ram}MB RAM")
            if min_disk:
                filters.append(f"≥{min_disk}GB disk")
            if max_monthly_cost:
                filters.append(f"≤${max_monthly_cost}/mo")
            filter_str = ", ".join(filters) if filters else "no filters"

            lines = [f"; Plans matching: {filter_str} ({len(matching_plans)} found)"]
            lines.append(f"; {'Plan ID':<20} {'CPU':>6}  {'RAM':>10}  {'Disk':>14}  {'Cost':>10}  Regions")
            lines.append("; " + "-" * 90)
            for plan in sorted(matching_plans, key=lambda p: p.get("monthly_cost", 0)):
                lines.append(_format_plan_compact(plan))
            return "\n".join(lines)
        else:
            return json.dumps(matching_plans)

    @mcp.tool()
    async def get_plan_by_type_and_spec(
        plan_type: str, vcpus: int, ram_gb: int, format: str = "compact"
    ) -> str:
        """
        Get plans by type and specific vCPU/RAM combination.

        Args:
            plan_type: Plan type (vc2, vhf, voc)
            vcpus: Number of vCPUs
            ram_gb: RAM in GB
            format: Output format - 'compact' (default) or 'json'

        Returns:
            Matching plans in requested format
        """
        plans = await vultr_client.list_plans(plan_type)
        matching_plans = []

        for plan in plans:
            if (
                plan.get("vcpu_count") == vcpus and plan.get("ram") == ram_gb * 1024
            ):  # Convert GB to MB
                matching_plans.append(plan)

        if format == "compact":
            lines = [f"; {plan_type.upper()} plans with {vcpus} CPU, {ram_gb}GB RAM ({len(matching_plans)} found)"]
            lines.append(f"; {'Plan ID':<20} {'CPU':>6}  {'RAM':>10}  {'Disk':>14}  {'Cost':>10}  Regions")
            lines.append("; " + "-" * 90)
            for plan in sorted(matching_plans, key=lambda p: p.get("monthly_cost", 0)):
                lines.append(_format_plan_compact(plan))
            return "\n".join(lines)
        else:
            return json.dumps(matching_plans)

    @mcp.tool()
    async def get_cheapest_plan(plan_type: str | None = None) -> dict[str, Any]:
        """
        Get the cheapest available plan.

        Args:
            plan_type: Optional plan type filter

        Returns:
            Cheapest plan details
        """
        plans = await vultr_client.list_plans(plan_type)

        if not plans:
            raise ValueError("No plans available")

        cheapest = min(plans, key=lambda p: p.get("monthly_cost", float("inf")))
        return cheapest

    @mcp.tool()
    async def get_plans_by_region_availability(region: str, format: str = "compact") -> str:
        """
        Get plans available in a specific region.

        Args:
            region: Region code (e.g., 'ewr', 'lax')
            format: Output format - 'compact' (default) or 'json'

        Returns:
            Plans available in the specified region
        """
        all_plans = await vultr_client.list_plans()
        available_plans = []

        for plan in all_plans:
            locations = plan.get("locations", [])
            if region in locations:
                available_plans.append(plan)

        if format == "compact":
            lines = [f"; Plans available in {region.upper()} ({len(available_plans)} found)"]
            lines.append(f"; {'Plan ID':<20} {'CPU':>6}  {'RAM':>10}  {'Disk':>14}  {'Cost':>10}  Regions")
            lines.append("; " + "-" * 90)
            for plan in sorted(available_plans, key=lambda p: p.get("monthly_cost", 0)):
                lines.append(_format_plan_compact(plan))
            return "\n".join(lines)
        else:
            return json.dumps(available_plans)

    @mcp.tool()
    async def compare_plans(plan_ids: list[str], format: str = "compact") -> str:
        """
        Compare multiple plans side by side.

        Args:
            plan_ids: List of plan IDs to compare
            format: Output format - 'compact' (default) or 'json'

        Returns:
            Plan comparison in requested format
        """
        comparison = []

        for plan_id in plan_ids:
            try:
                plan = await vultr_client.get_plan(plan_id)
                comparison.append(plan)
            except Exception as e:
                comparison.append({"id": plan_id, "error": str(e)})

        if format == "compact":
            lines = [f"; Comparing {len(plan_ids)} plans"]
            lines.append(f"; {'Plan ID':<20} {'CPU':>6}  {'RAM':>10}  {'Disk':>14}  {'Cost':>10}  Regions")
            lines.append("; " + "-" * 90)
            for plan in comparison:
                if "error" in plan:
                    lines.append(f"{plan.get('id', 'unknown'):<20} ERROR: {plan['error']}")
                else:
                    lines.append(_format_plan_compact(plan))
            return "\n".join(lines)
        else:
            return json.dumps(comparison)

    return mcp
