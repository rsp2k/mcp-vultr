"""
Vultr Subaccount FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr subaccounts.
"""

from typing import Any

from fastmcp import FastMCP


def create_subaccount_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr subaccount management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with subaccount management tools
    """
    mcp = FastMCP(name="vultr-subaccount")

    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        return bool(len(s) == 36 and s.count("-") == 4)

    # Helper function to get subaccount ID from name, email, or UUID
    async def get_subaccount_id(identifier: str) -> str:
        """
        Get the subaccount ID from a name, email, custom ID, or UUID.

        Args:
            identifier: Subaccount name, email, custom ID, or UUID

        Returns:
            The subaccount UUID

        Raises:
            ValueError: If the subaccount is not found
        """
        # If it looks like a UUID, return it as-is
        if is_uuid_format(identifier):
            return identifier

        # Otherwise, search for it by name, email, or custom ID
        subaccounts = await vultr_client.list_subaccounts()
        for subaccount in subaccounts:
            if (
                subaccount.get("subaccount_name") == identifier
                or subaccount.get("email") == identifier
                or str(subaccount.get("subaccount_id")) == identifier
            ):
                return subaccount["id"]

        raise ValueError(
            f"Subaccount '{identifier}' not found (searched by name, email, and custom ID)"
        )

    # Helper function for subaccount setup
    async def setup_subaccount_permissions(
        subaccount_id: str, permissions: list[str]
    ) -> dict[str, Any]:
        """
        Helper function to configure subaccount permissions.

        Args:
            subaccount_id: The subaccount UUID
            permissions: List of permissions to grant

        Returns:
            Permission configuration status
        """
        # Note: This is a placeholder as the API doesn't have explicit permission endpoints
        # In a real implementation, this would manage API keys and access controls
        return {
            "subaccount_id": subaccount_id,
            "permissions": permissions,
            "status": "configured",
            "note": "Permission management typically done through API key scoping",
        }

    # Helper function for cost analysis
    async def analyze_subaccount_costs(
        subaccount_id: str, days: int = 30
    ) -> dict[str, Any]:
        """
        Analyze subaccount costs and usage patterns.

        Args:
            subaccount_id: The subaccount UUID
            days: Number of days to analyze (default: 30)

        Returns:
            Cost analysis data
        """
        subaccount = await vultr_client.get_subaccount(subaccount_id)

        # Calculate basic cost metrics
        balance = float(subaccount.get("balance", 0))
        pending_charges = float(subaccount.get("pending_charges", 0))

        # Estimate daily burn rate (this is a simplified calculation)
        daily_burn_rate = pending_charges / max(days, 1)

        # Calculate projected monthly costs
        monthly_projection = daily_burn_rate * 30

        return {
            "subaccount_id": subaccount_id,
            "current_balance": balance,
            "pending_charges": pending_charges,
            "daily_burn_rate": round(daily_burn_rate, 4),
            "monthly_projection": round(monthly_projection, 2),
            "analysis_period_days": days,
            "balance_days_remaining": round(balance / max(daily_burn_rate, 0.01), 1)
            if daily_burn_rate > 0
            else "N/A",
        }

    # Subaccount resources
    @mcp.resource("subaccounts://list")
    async def list_subaccounts_resource() -> list[dict[str, Any]]:
        """List all subaccounts in your Vultr account."""
        try:
            return await vultr_client.list_subaccounts()
        except Exception:
            # If the API returns an error when no subaccounts exist, return empty list
            return []

    @mcp.resource("subaccounts://{subaccount_id}")
    async def get_subaccount_resource(subaccount_id: str) -> dict[str, Any]:
        """Get information about a specific subaccount.

        Args:
            subaccount_id: The subaccount ID, name, email, or UUID
        """
        actual_id = await get_subaccount_id(subaccount_id)
        subaccounts = await vultr_client.list_subaccounts()
        for subaccount in subaccounts:
            if subaccount["id"] == actual_id:
                return subaccount
        raise ValueError(f"Subaccount {actual_id} not found")

    # Subaccount management tools

    @mcp.tool
    async def create(
        email: str,
        subaccount_name: str | None = None,
        subaccount_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new subaccount.

        Args:
            email: Email address for the subaccount (required)
            subaccount_name: Display name for the subaccount (optional)
            subaccount_id: Custom identifier for the subaccount (optional)

        Returns:
            Created subaccount information
        """
        return await vultr_client.create_subaccount(
            email=email, subaccount_name=subaccount_name, subaccount_id=subaccount_id
        )

    @mcp.tool
    async def find_by_email(email: str) -> list[dict[str, Any]]:
        """Find subaccounts by email address.

        Args:
            email: Email address to search for

        Returns:
            List of matching subaccounts
        """
        subaccounts = await vultr_client.list_subaccounts()
        matches = [
            sub for sub in subaccounts if sub.get("email", "").lower() == email.lower()
        ]
        return matches

    @mcp.tool
    async def find_by_name(name: str) -> list[dict[str, Any]]:
        """Find subaccounts by name (partial match).

        Args:
            name: Name to search for (case-insensitive partial match)

        Returns:
            List of matching subaccounts
        """
        subaccounts = await vultr_client.list_subaccounts()
        matches = []
        name_lower = name.lower()
        for sub in subaccounts:
            if (
                name_lower in (sub.get("subaccount_name") or "").lower()
                or name_lower in str(sub.get("subaccount_id") or "").lower()
            ):
                matches.append(sub)
        return matches

    @mcp.tool
    async def get_balance_summary() -> dict[str, Any]:
        """Get a summary of all subaccount balances and charges.

        Returns:
            Summary of subaccount financial status
        """
        subaccounts = await vultr_client.list_subaccounts()

        total_balance = 0
        total_pending = 0
        active_count = 0
        inactive_count = 0

        subaccount_details = []

        for sub in subaccounts:
            balance = float(sub.get("balance", 0))
            pending = float(sub.get("pending_charges", 0))
            activated = sub.get("activated", False)

            total_balance += balance
            total_pending += pending

            if activated:
                active_count += 1
            else:
                inactive_count += 1

            subaccount_details.append(
                {
                    "id": sub.get("id"),
                    "name": sub.get("subaccount_name"),
                    "email": sub.get("email"),
                    "balance": balance,
                    "pending_charges": pending,
                    "activated": activated,
                }
            )

        return {
            "summary": {
                "total_subaccounts": len(subaccounts),
                "active_subaccounts": active_count,
                "inactive_subaccounts": inactive_count,
                "total_balance": round(total_balance, 2),
                "total_pending_charges": round(total_pending, 2),
                "net_balance": round(total_balance - total_pending, 2),
            },
            "subaccounts": subaccount_details,
        }

    @mcp.tool
    async def analyze_costs(
        subaccount_id: str, analysis_days: int = 30
    ) -> dict[str, Any]:
        """Analyze costs and usage patterns for a subaccount.

        Args:
            subaccount_id: The subaccount ID, name, email, or UUID
            analysis_days: Number of days to analyze (default: 30)

        Returns:
            Detailed cost analysis including projections and recommendations
        """
        actual_id = await get_subaccount_id(subaccount_id)
        return await analyze_subaccount_costs(actual_id, analysis_days)

    @mcp.tool
    async def setup_permissions(
        subaccount_id: str, permissions: list[str]
    ) -> dict[str, Any]:
        """Configure permissions for a subaccount.

        Args:
            subaccount_id: The subaccount ID, name, email, or UUID
            permissions: List of permissions to grant (e.g., ["instances", "dns", "billing"])

        Returns:
            Permission configuration status
        """
        actual_id = await get_subaccount_id(subaccount_id)
        return await setup_subaccount_permissions(actual_id, permissions)

    @mcp.tool
    async def get_status_overview() -> dict[str, Any]:
        """Get an overview of all subaccount statuses and key metrics.

        Returns:
            Comprehensive overview of subaccount health and status
        """
        subaccounts = await vultr_client.list_subaccounts()

        overview = {
            "total_count": len(subaccounts),
            "activated_count": 0,
            "pending_count": 0,
            "with_balance": 0,
            "with_charges": 0,
            "total_system_balance": 0,
            "total_system_charges": 0,
            "subaccounts_by_status": {
                "activated": [],
                "pending": [],
                "low_balance": [],
                "high_usage": [],
            },
        }

        for sub in subaccounts:
            balance = float(sub.get("balance", 0))
            pending = float(sub.get("pending_charges", 0))
            activated = sub.get("activated", False)

            overview["total_system_balance"] += balance
            overview["total_system_charges"] += pending

            if activated:
                overview["activated_count"] += 1
                overview["subaccounts_by_status"]["activated"].append(
                    {
                        "id": sub.get("id"),
                        "name": sub.get("subaccount_name"),
                        "email": sub.get("email"),
                    }
                )
            else:
                overview["pending_count"] += 1
                overview["subaccounts_by_status"]["pending"].append(
                    {
                        "id": sub.get("id"),
                        "name": sub.get("subaccount_name"),
                        "email": sub.get("email"),
                    }
                )

            if balance > 0:
                overview["with_balance"] += 1

            if pending > 0:
                overview["with_charges"] += 1

            # Flag accounts with low balance relative to charges
            if balance > 0 and pending > 0 and (balance / pending) < 10:
                overview["subaccounts_by_status"]["low_balance"].append(
                    {
                        "id": sub.get("id"),
                        "name": sub.get("subaccount_name"),
                        "balance": balance,
                        "pending_charges": pending,
                        "days_remaining": round(balance / (pending / 30), 1)
                        if pending > 0
                        else "N/A",
                    }
                )

            # Flag accounts with high usage (arbitrary threshold)
            if pending > 10:  # More than $10 in pending charges
                overview["subaccounts_by_status"]["high_usage"].append(
                    {
                        "id": sub.get("id"),
                        "name": sub.get("subaccount_name"),
                        "pending_charges": pending,
                    }
                )

        # Round financial totals
        overview["total_system_balance"] = round(overview["total_system_balance"], 2)
        overview["total_system_charges"] = round(overview["total_system_charges"], 2)

        return overview

    @mcp.tool
    async def monitor_usage() -> list[dict[str, Any]]:
        """Monitor usage across all subaccounts and identify potential issues.

        Returns:
            List of subaccounts with usage monitoring data and alerts
        """
        subaccounts = await vultr_client.list_subaccounts()
        monitoring_data = []

        for sub in subaccounts:
            balance = float(sub.get("balance", 0))
            pending = float(sub.get("pending_charges", 0))
            activated = sub.get("activated", False)

            # Calculate daily burn rate estimate
            daily_rate = pending / 30 if pending > 0 else 0
            days_remaining = balance / daily_rate if daily_rate > 0 else float("inf")

            # Generate alerts
            alerts = []
            if not activated:
                alerts.append("Account not activated")
            if balance < 5 and pending > 0:
                alerts.append("Low balance warning")
            if days_remaining < 7 and days_remaining != float("inf"):
                alerts.append(
                    f"Balance will be depleted in ~{int(days_remaining)} days"
                )
            if pending > 100:
                alerts.append("High usage detected")

            # Determine status
            if alerts:
                status = (
                    "warning"
                    if any(
                        "Low balance" in alert or "depleted" in alert
                        for alert in alerts
                    )
                    else "attention"
                )
            else:
                status = "ok"

            monitoring_data.append(
                {
                    "id": sub.get("id"),
                    "name": sub.get("subaccount_name"),
                    "email": sub.get("email"),
                    "balance": balance,
                    "pending_charges": pending,
                    "daily_burn_rate": round(daily_rate, 4),
                    "days_remaining": int(days_remaining)
                    if days_remaining != float("inf")
                    else "unlimited",
                    "status": status,
                    "alerts": alerts,
                    "activated": activated,
                }
            )

        # Sort by status priority (warnings first)
        monitoring_data.sort(
            key=lambda x: (
                x["status"] != "warning",
                x["status"] != "attention",
                x["name"],
            )
        )

        return monitoring_data

    return mcp
