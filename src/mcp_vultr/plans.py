"""
Vultr Plans FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr plans.
"""

from typing import Any

from fastmcp import FastMCP


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
    async def list_plans(plan_type: str | None = None) -> list[dict[str, Any]]:
        """
        List all available plans.

        Args:
            plan_type: Optional plan type filter (e.g., 'all', 'vc2', 'vhf', 'voc')

        Returns:
            List of available plans
        """
        return await vultr_client.list_plans(plan_type)

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
    async def list_vc2_plans() -> list[dict[str, Any]]:
        """
        List VC2 (Virtual Cloud Compute) plans.

        Returns:
            List of VC2 plans
        """
        return await vultr_client.list_plans("vc2")

    @mcp.tool()
    async def list_vhf_plans() -> list[dict[str, Any]]:
        """
        List VHF (High Frequency) plans.

        Returns:
            List of VHF plans
        """
        return await vultr_client.list_plans("vhf")

    @mcp.tool()
    async def list_voc_plans() -> list[dict[str, Any]]:
        """
        List VOC (Optimized Cloud) plans.

        Returns:
            List of VOC plans
        """
        return await vultr_client.list_plans("voc")

    @mcp.tool()
    async def search_plans_by_specs(
        min_vcpus: int | None = None,
        min_ram: int | None = None,
        min_disk: int | None = None,
        max_monthly_cost: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search plans by specifications.

        Args:
            min_vcpus: Minimum number of vCPUs
            min_ram: Minimum RAM in MB
            min_disk: Minimum disk space in GB
            max_monthly_cost: Maximum monthly cost in USD

        Returns:
            List of plans matching the criteria
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

        return matching_plans

    @mcp.tool()
    async def get_plan_by_type_and_spec(
        plan_type: str, vcpus: int, ram_gb: int
    ) -> list[dict[str, Any]]:
        """
        Get plans by type and specific vCPU/RAM combination.

        Args:
            plan_type: Plan type (vc2, vhf, voc)
            vcpus: Number of vCPUs
            ram_gb: RAM in GB

        Returns:
            List of matching plans
        """
        plans = await vultr_client.list_plans(plan_type)
        matching_plans = []

        for plan in plans:
            if (
                plan.get("vcpu_count") == vcpus and plan.get("ram") == ram_gb * 1024
            ):  # Convert GB to MB
                matching_plans.append(plan)

        return matching_plans

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
    async def get_plans_by_region_availability(region: str) -> list[dict[str, Any]]:
        """
        Get plans available in a specific region.

        Args:
            region: Region code (e.g., 'ewr', 'lax')

        Returns:
            List of plans available in the specified region
        """
        all_plans = await vultr_client.list_plans()
        available_plans = []

        for plan in all_plans:
            locations = plan.get("locations", [])
            if region in locations:
                available_plans.append(plan)

        return available_plans

    @mcp.tool()
    async def compare_plans(plan_ids: list[str]) -> list[dict[str, Any]]:
        """
        Compare multiple plans side by side.

        Args:
            plan_ids: List of plan IDs to compare

        Returns:
            List of plan details for comparison
        """
        comparison = []

        for plan_id in plan_ids:
            try:
                plan = await vultr_client.get_plan(plan_id)
                comparison.append(plan)
            except Exception as e:
                comparison.append({"id": plan_id, "error": str(e)})

        return comparison

    return mcp
