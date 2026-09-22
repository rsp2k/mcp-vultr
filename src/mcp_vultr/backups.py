"""
Vultr Backups FastMCP Module.

Account-level backup listing, plus the per-instance automatic backup schedule.

Turning backups on or off is a property of the instance itself
(`instance_update` with `backups`), while *when* they run is this separate
schedule endpoint. Both are needed: a schedule on an instance with backups
disabled does nothing.
"""

from typing import Any

from fastmcp import Context, FastMCP

from .lookup import resolve_id
from .notification_manager import NotificationManager

#: Schedule types Vultr accepts. The `daily_alt_*` pair means "every other
#: day", on even or odd days of the month respectively.
SCHEDULE_TYPES = ("daily", "weekly", "monthly", "daily_alt_even", "daily_alt_odd")

#: Types that need a day selector, and which one.
REQUIRED_DAY_FIELD = {"weekly": "dow", "monthly": "dom"}


def create_backups_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr backups management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with backup management tools
    """
    mcp = FastMCP(name="vultr-backups")

    async def resolve_instance_id(identifier: str) -> str:
        """
        Resolve an instance label, hostname or UUID to an instance ID.

        Refuses an ambiguous name rather than picking one. See
        mcp_vultr.lookup for why.

        Args:
            identifier: Instance label, hostname, or UUID

        Returns:
            The instance ID

        Raises:
            ValueError: If nothing matches, or more than one thing does
        """
        return await resolve_id(
            identifier,
            vultr_client.list_instances,
            ("label", "hostname"),
            "Instance",
        )

    def validate_schedule(
        schedule_type: str, hour: int | None, dow: int | None, dom: int | None
    ) -> None:
        """Reject a schedule the API would reject, with a clearer message."""
        if schedule_type not in SCHEDULE_TYPES:
            raise ValueError(
                f"Unknown schedule type '{schedule_type}'. "
                f"Expected one of: {', '.join(SCHEDULE_TYPES)}"
            )

        if hour is not None and not 0 <= hour <= 23:
            raise ValueError(f"hour must be between 0 and 23 (UTC), got {hour}")

        if dom is not None and not 1 <= dom <= 28:
            raise ValueError(
                f"dom must be between 1 and 28, got {dom}. Vultr stops at 28 so "
                f"a monthly backup runs in every month."
            )

        required = REQUIRED_DAY_FIELD.get(schedule_type)
        if required == "dow" and dow is None:
            raise ValueError("A weekly schedule needs dow (day of week)")
        if required == "dom" and dom is None:
            raise ValueError("A monthly schedule needs dom (day of month)")

    # Backup resources
    @mcp.resource("backups://list")
    async def list_backups_resource() -> list[dict[str, Any]]:
        """List all backups in your Vultr account."""
        # Don't swallow errors - let auth/permission errors propagate
        return await vultr_client.list_backups()

    @mcp.resource("backups://{backup_id}")
    async def get_backup_resource(backup_id: str) -> dict[str, Any]:
        """Get information about a specific backup.

        Args:
            backup_id: The backup ID to get information for
        """
        return await vultr_client.get_backup(backup_id)

    @mcp.resource("backups://schedule/{instance_identifier}")
    async def get_schedule_resource(instance_identifier: str) -> dict[str, Any]:
        """Get the automatic backup schedule for an instance.

        Args:
            instance_identifier: Instance label, hostname, or ID
        """
        instance_id = await resolve_instance_id(instance_identifier)
        return await vultr_client.get_backup_schedule(instance_id)

    # Backup tools
    @mcp.tool
    async def list_all() -> list[dict[str, Any]]:
        """List all backups in your Vultr account.

        Returns:
            Backups, each with id, date_created, description, size and status
        """
        return await vultr_client.list_backups()

    @mcp.tool
    async def get(backup_id: str) -> dict[str, Any]:
        """Get details of a specific backup.

        Args:
            backup_id: The backup ID

        Returns:
            Backup details
        """
        return await vultr_client.get_backup(backup_id)

    @mcp.tool
    async def get_schedule(instance_identifier: str) -> dict[str, Any]:
        """Get the automatic backup schedule for an instance.

        Smart identifier resolution: use the instance label, hostname or ID.
        All times are UTC.

        Args:
            instance_identifier: Instance label, hostname, or ID

        Returns:
            Schedule with enabled, type, hour, dow, dom and
            next_scheduled_time_utc. When enabled is false the instance has
            backups turned off and the schedule is not running.
        """
        instance_id = await resolve_instance_id(instance_identifier)
        return await vultr_client.get_backup_schedule(instance_id)

    @mcp.tool
    async def set_schedule(
        instance_identifier: str,
        schedule_type: str,
        ctx: Context | None = None,
        hour: int | None = None,
        dow: int | None = None,
        dom: int | None = None,
    ) -> dict[str, Any]:
        """Set the automatic backup schedule for an instance.

        Smart identifier resolution: use the instance label, hostname or ID.
        A name matching more than one instance is refused rather than guessed.

        This sets *when* backups run. It does not turn backups on: an instance
        with backups disabled keeps the schedule but never runs it. Use
        instance_update with backups=true for that.

        All times are UTC.

        Args:
            instance_identifier: Instance label, hostname, or ID
            schedule_type: daily, weekly, monthly, daily_alt_even (even days of
                the month) or daily_alt_odd (odd days)
            ctx: FastMCP context for resource change notifications
            hour: Hour of day to run, 0-23, UTC
            dow: Day of week, required for a weekly schedule. Vultr's own
                tooling documents this range inconsistently (0-6 in the CLI,
                1-7 elsewhere), so the value is passed through unchecked and
                the API decides. Read the schedule back to confirm the day.
            dom: Day of month, 1-28, required for a monthly schedule

        Returns:
            The schedule as it stands after the change
        """
        validate_schedule(schedule_type, hour, dow, dom)
        instance_id = await resolve_instance_id(instance_identifier)

        await vultr_client.set_backup_schedule(
            instance_id, schedule_type, hour=hour, dow=dow, dom=dom
        )

        if ctx is not None:
            await NotificationManager.notify_instance_changes(
                ctx=ctx, operation="update_instance", instance_id=instance_id
            )

        # Read back rather than echoing the request, so the caller sees what
        # Vultr actually stored, including next_scheduled_time_utc.
        return await vultr_client.get_backup_schedule(instance_id)

    return mcp
