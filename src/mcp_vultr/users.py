"""
Vultr Users FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr users,
API keys, permissions, and security settings.
"""

from typing import Any

from fastmcp import Context, FastMCP

from .notification_manager import NotificationManager


def create_users_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr users management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with user management tools
    """
    mcp = FastMCP(name="vultr-users")

    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        return bool(len(s) == 36 and s.count("-") == 4)

    # Helper function to get user ID from email or UUID
    async def get_user_id(identifier: str) -> str:
        """
        Get the user ID from an email address or UUID.

        Args:
            identifier: User email address or UUID

        Returns:
            The user ID (UUID)

        Raises:
            ValueError: If the user is not found
        """
        # If it looks like a UUID, return it as-is
        if is_uuid_format(identifier):
            return identifier

        # Otherwise, search for it by email
        users = await vultr_client.list_users()
        for user in users:
            if user.get("email") == identifier:
                return user["id"]

        raise ValueError(f"User '{identifier}' not found (searched by email)")

    # User resources
    @mcp.resource("users://list")
    async def list_users_resource() -> list[dict[str, Any]]:
        """List all users in your Vultr account."""
        try:
            return await vultr_client.list_users()
        except Exception:
            # If the API returns an error when no users exist, return empty list
            return []

    @mcp.resource("users://{user_id}")
    async def get_user_resource(user_id: str) -> dict[str, Any]:
        """Get information about a specific user.

        Args:
            user_id: The user ID or email address
        """
        actual_id = await get_user_id(user_id)
        return await vultr_client.get_user(actual_id)

    @mcp.resource("users://{user_id}/ip-whitelist")
    async def get_user_ip_whitelist_resource(user_id: str) -> list[dict[str, Any]]:
        """Get IP whitelist for a specific user.

        Args:
            user_id: The user ID or email address
        """
        actual_id = await get_user_id(user_id)
        return await vultr_client.get_user_ip_whitelist(actual_id)

    # User management tools
    @mcp.tool
    async def get(user_id: str) -> dict[str, Any]:
        """Get detailed information about a specific user.

        Args:
            user_id: The user ID (UUID) or email address (e.g., "user@example.com" or UUID)

        Returns:
            Detailed user information including permissions and settings
        """
        actual_id = await get_user_id(user_id)
        return await vultr_client.get_user(actual_id)

    @mcp.tool
    async def create(
        email: str,
        first_name: str,
        last_name: str,
        password: str,
        ctx: Context | None = None,
        api_enabled: bool = True,
        service_user: bool = False,
        acls: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new user.

        Args:
            email: User's email address
            first_name: User's first name
            last_name: User's last name
            password: User's password
            ctx: FastMCP context for resource change notifications
            ctx: FastMCP context for resource change notifications
            api_enabled: Enable API access for this user
            service_user: Create as service user (API-only, no portal login)
            acls: List of permissions to grant. Available permissions:
                 - manage_users: Manage other users
                 - subscriptions_view: View subscriptions
                 - subscriptions: Manage subscriptions
                 - provisioning: Provision resources
                 - billing: Access billing information
                 - support: Access support tickets
                 - abuse: Handle abuse reports
                 - dns: Manage DNS
                 - upgrade: Upgrade plans
                 - objstore: Manage object storage
                 - loadbalancer: Manage load balancers
                 - firewall: Manage firewalls
                 - alerts: Manage alerts

        Returns:
            Created user information, including API key if service_user is True
        """
        if acls is None:
            acls = ["subscriptions_view"]  # Default minimal permissions

        result = await vultr_client.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            api_enabled=api_enabled,
            service_user=service_user,
            acls=acls,
        )

        # Notify clients that user list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="create_user", user_id=result.get("id")
            )

        return result

    @mcp.tool
    async def update(
        user_id: str,
        ctx: Context | None = None,
        api_enabled: bool | None = None,
        acls: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update an existing user's settings.

        Args:
            user_id: The user ID (UUID) or email address to update
            ctx: FastMCP context for resource change notifications
            api_enabled: Enable/disable API access
            acls: List of permissions to grant. Available permissions:
                 - manage_users: Manage other users
                 - subscriptions_view: View subscriptions
                 - subscriptions: Manage subscriptions
                 - provisioning: Provision resources
                 - billing: Access billing information
                 - support: Access support tickets
                 - abuse: Handle abuse reports
                 - dns: Manage DNS
                 - upgrade: Upgrade plans
                 - objstore: Manage object storage
                 - loadbalancer: Manage load balancers
                 - firewall: Manage firewalls
                 - alerts: Manage alerts

        Returns:
            Updated user information
        """
        actual_id = await get_user_id(user_id)
        result = await vultr_client.update_user(
            user_id=actual_id, api_enabled=api_enabled, acls=acls
        )

        # Notify clients that user list and specific user have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="update_user", user_id=actual_id
            )

        return result

    @mcp.tool
    async def delete(user_id: str, ctx: Context | None = None) -> dict[str, str]:
        """Delete a user.

        Args:
            user_id: The user ID (UUID) or email address to delete
            ctx: FastMCP context for resource change notifications

        Returns:
            Status message confirming deletion
        """
        actual_id = await get_user_id(user_id)
        await vultr_client.delete_user(actual_id)

        # Notify clients that user list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="delete_user", user_id=actual_id
            )

        return {"status": "success", "message": f"User {user_id} deleted successfully"}

    # IP Whitelist management tools
    @mcp.tool
    async def get_ip_whitelist(user_id: str) -> list[dict[str, Any]]:
        """Get the IP whitelist for a user.

        Args:
            user_id: The user ID (UUID) or email address

        Returns:
            List of IP whitelist entries with subnet, subnet_size, date_added, and ip_type
        """
        actual_id = await get_user_id(user_id)
        return await vultr_client.get_user_ip_whitelist(actual_id)

    @mcp.tool
    async def get_ip_whitelist_entry(
        user_id: str, subnet: str, subnet_size: int
    ) -> dict[str, Any]:
        """Get a specific IP whitelist entry for a user.

        Args:
            user_id: The user ID (UUID) or email address
            subnet: The IP address or subnet (e.g., "8.8.8.0")
            subnet_size: The subnet size (e.g., 24 for /24)

        Returns:
            IP whitelist entry details
        """
        actual_id = await get_user_id(user_id)
        return await vultr_client.get_user_ip_whitelist_entry(
            actual_id, subnet, subnet_size
        )

    @mcp.tool
    async def add_ip_whitelist_entry(
        user_id: str, subnet: str, subnet_size: int, ctx: Context
    ) -> dict[str, str]:
        """Add an IP address or subnet to a user's whitelist.

        Args:
            user_id: The user ID (UUID) or email address
            subnet: The IP address or subnet to add (e.g., "8.8.8.0", "192.168.1.100")
            subnet_size: The subnet size (e.g., 24 for /24, 32 for single IP)
            ctx: FastMCP context for resource change notifications

        Returns:
            Status message confirming addition
        """
        actual_id = await get_user_id(user_id)
        await vultr_client.add_user_ip_whitelist_entry(actual_id, subnet, subnet_size)

        # Notify clients that user IP whitelist has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="update_user", user_id=actual_id
            )

        return {
            "status": "success",
            "message": f"IP {subnet}/{subnet_size} added to whitelist for user {user_id}",
        }

    @mcp.tool
    async def remove_ip_whitelist_entry(
        user_id: str, subnet: str, subnet_size: int, ctx: Context
    ) -> dict[str, str]:
        """Remove an IP address or subnet from a user's whitelist.

        Args:
            user_id: The user ID (UUID) or email address
            subnet: The IP address or subnet to remove (e.g., "8.8.8.0", "192.168.1.100")
            subnet_size: The subnet size (e.g., 24 for /24, 32 for single IP)
            ctx: FastMCP context for resource change notifications

        Returns:
            Status message confirming removal
        """
        actual_id = await get_user_id(user_id)
        await vultr_client.remove_user_ip_whitelist_entry(
            actual_id, subnet, subnet_size
        )

        # Notify clients that user IP whitelist has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="update_user", user_id=actual_id
            )

        return {
            "status": "success",
            "message": f"IP {subnet}/{subnet_size} removed from whitelist for user {user_id}",
        }

    # Helper and management tools
    @mcp.tool
    async def setup_standard_user(
        email: str,
        first_name: str,
        last_name: str,
        password: str,
        permissions_level: str = "basic",
    ) -> dict[str, Any]:
        """Set up a new user with standard permission sets.

        Args:
            email: User's email address
            first_name: User's first name
            last_name: User's last name
            password: User's password
            ctx: FastMCP context for resource change notifications
            permissions_level: Permission level - "basic", "developer", "admin", or "readonly"
                - basic: subscriptions_view, dns, support
                - readonly: subscriptions_view, support
                - developer: subscriptions_view, subscriptions, provisioning, dns, support, objstore, loadbalancer, firewall
                - admin: all permissions except manage_users
                - superadmin: all permissions including manage_users

        Returns:
            Created user information with applied permissions
        """
        # Define permission sets
        permission_sets = {
            "readonly": ["subscriptions_view", "support"],
            "basic": ["subscriptions_view", "dns", "support"],
            "developer": [
                "subscriptions_view",
                "subscriptions",
                "provisioning",
                "dns",
                "support",
                "objstore",
                "loadbalancer",
                "firewall",
            ],
            "admin": [
                "subscriptions_view",
                "subscriptions",
                "provisioning",
                "billing",
                "support",
                "abuse",
                "dns",
                "upgrade",
                "objstore",
                "loadbalancer",
                "firewall",
                "alerts",
            ],
            "superadmin": [
                "manage_users",
                "subscriptions_view",
                "subscriptions",
                "provisioning",
                "billing",
                "support",
                "abuse",
                "dns",
                "upgrade",
                "objstore",
                "loadbalancer",
                "firewall",
                "alerts",
            ],
        }

        if permissions_level not in permission_sets:
            raise ValueError(
                f"Invalid permissions_level. Must be one of: {list(permission_sets.keys())}"
            )

        acls = permission_sets[permissions_level]

        return await vultr_client.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            api_enabled=True,
            service_user=False,
            acls=acls,
        )

    @mcp.tool
    async def setup_service_user(
        email: str,
        first_name: str,
        last_name: str,
        ctx: Context | None = None,
        permissions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Set up a new service user (API-only access) with specified permissions.

        Args:
            email: Service user's email address
            first_name: Service user's first name
            last_name: Service user's last name
            ctx: FastMCP context for resource change notifications
            permissions: List of permissions to grant. If None, grants basic API access.

        Returns:
            Created service user information including API key
        """
        if permissions is None:
            permissions = ["subscriptions_view", "provisioning", "dns"]

        # Generate a secure password for the service user (won't be used for login)
        import secrets
        import string

        password = "".join(
            secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*")
            for _ in range(16)
        )

        result = await vultr_client.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            api_enabled=True,
            service_user=True,
            acls=permissions,
        )

        # Notify clients that user list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="create_user", user_id=result.get("id")
            )

        return result

    @mcp.tool
    async def analyze_user_permissions(user_id: str) -> dict[str, Any]:
        """Analyze a user's current permissions and provide recommendations.

        Args:
            user_id: The user ID (UUID) or email address to analyze

        Returns:
            Analysis of user permissions including:
            - current_permissions: List of current permissions
            - permission_analysis: Analysis of each permission
            - security_recommendations: Security recommendations
            - suggested_changes: Suggested permission changes
        """
        actual_id = await get_user_id(user_id)
        user = await vultr_client.get_user(actual_id)

        current_permissions = user.get("acls", [])

        # Analyze permissions
        permission_descriptions = {
            "manage_users": "Can create, modify, and delete other users - HIGH PRIVILEGE",
            "subscriptions_view": "Can view subscription information - SAFE",
            "subscriptions": "Can manage subscriptions and resources - MODERATE PRIVILEGE",
            "provisioning": "Can create and destroy infrastructure - HIGH PRIVILEGE",
            "billing": "Can access billing information - MODERATE PRIVILEGE",
            "support": "Can access support tickets - SAFE",
            "abuse": "Can handle abuse reports - MODERATE PRIVILEGE",
            "dns": "Can manage DNS records - MODERATE PRIVILEGE",
            "upgrade": "Can upgrade plans and services - MODERATE PRIVILEGE",
            "objstore": "Can manage object storage - MODERATE PRIVILEGE",
            "loadbalancer": "Can manage load balancers - MODERATE PRIVILEGE",
            "firewall": "Can manage firewall rules - HIGH PRIVILEGE",
            "alerts": "Can manage alerts and notifications - SAFE",
        }

        permission_analysis = []
        high_privilege_count = 0

        for perm in current_permissions:
            description = permission_descriptions.get(perm, "Unknown permission")
            if "HIGH PRIVILEGE" in description:
                high_privilege_count += 1
            permission_analysis.append(
                {
                    "permission": perm,
                    "description": description,
                    "risk_level": "HIGH"
                    if "HIGH PRIVILEGE" in description
                    else "MODERATE"
                    if "MODERATE PRIVILEGE" in description
                    else "LOW",
                }
            )

        # Generate recommendations
        recommendations = []

        if "manage_users" in current_permissions:
            recommendations.append(
                "User has user management privileges - ensure this is necessary"
            )

        if high_privilege_count > 3:
            recommendations.append(
                "User has multiple high-privilege permissions - consider principle of least privilege"
            )

        if user.get("api_enabled") and not user.get("service_user"):
            whitelist = await vultr_client.get_user_ip_whitelist(actual_id)
            if not whitelist:
                recommendations.append(
                    "API-enabled user has no IP whitelist - consider adding IP restrictions"
                )

        if (
            "provisioning" in current_permissions
            and "billing" not in current_permissions
        ):
            recommendations.append(
                "User can provision resources but can't see billing - may cause cost control issues"
            )

        # Suggest permission changes
        suggested_changes = []
        if len(current_permissions) == 0:
            suggested_changes.append(
                "Add 'subscriptions_view' for basic account visibility"
            )

        if (
            "firewall" in current_permissions
            and "provisioning" not in current_permissions
        ):
            suggested_changes.append(
                "Consider adding 'provisioning' since user manages security but can't create resources"
            )

        return {
            "user_id": actual_id,
            "user_email": user.get("email"),
            "api_enabled": user.get("api_enabled"),
            "service_user": user.get("service_user"),
            "current_permissions": current_permissions,
            "permission_analysis": permission_analysis,
            "security_recommendations": recommendations,
            "suggested_changes": suggested_changes,
            "high_privilege_permissions": [
                p["permission"]
                for p in permission_analysis
                if p["risk_level"] == "HIGH"
            ],
            "permission_count": len(current_permissions),
        }

    @mcp.tool
    async def list_available_permissions() -> dict[str, Any]:
        """List all available permissions that can be granted to users.

        Returns:
            Dictionary of available permissions with descriptions and risk levels
        """
        permissions = {
            "manage_users": {
                "description": "Create, modify, and delete other users",
                "risk_level": "HIGH",
                "category": "User Management",
            },
            "subscriptions_view": {
                "description": "View subscription information",
                "risk_level": "LOW",
                "category": "Billing",
            },
            "subscriptions": {
                "description": "Manage subscriptions and resources",
                "risk_level": "MODERATE",
                "category": "Billing",
            },
            "provisioning": {
                "description": "Create and destroy infrastructure resources",
                "risk_level": "HIGH",
                "category": "Infrastructure",
            },
            "billing": {
                "description": "Access billing information and payment methods",
                "risk_level": "MODERATE",
                "category": "Billing",
            },
            "support": {
                "description": "Access and manage support tickets",
                "risk_level": "LOW",
                "category": "Support",
            },
            "abuse": {
                "description": "Handle abuse reports and compliance issues",
                "risk_level": "MODERATE",
                "category": "Support",
            },
            "dns": {
                "description": "Manage DNS records and domains",
                "risk_level": "MODERATE",
                "category": "Infrastructure",
            },
            "upgrade": {
                "description": "Upgrade plans and services",
                "risk_level": "MODERATE",
                "category": "Billing",
            },
            "objstore": {
                "description": "Manage object storage buckets and files",
                "risk_level": "MODERATE",
                "category": "Infrastructure",
            },
            "loadbalancer": {
                "description": "Manage load balancers and configurations",
                "risk_level": "MODERATE",
                "category": "Infrastructure",
            },
            "firewall": {
                "description": "Manage firewall rules and security groups",
                "risk_level": "HIGH",
                "category": "Security",
            },
            "alerts": {
                "description": "Manage alerts and notifications",
                "risk_level": "LOW",
                "category": "Monitoring",
            },
        }

        return {
            "permissions": permissions,
            "categories": list({p["category"] for p in permissions.values()}),
            "risk_levels": ["LOW", "MODERATE", "HIGH"],
            "recommended_minimal_set": ["subscriptions_view", "support"],
            "recommended_developer_set": [
                "subscriptions_view",
                "subscriptions",
                "provisioning",
                "dns",
                "support",
            ],
            "recommended_admin_set": [
                "subscriptions_view",
                "subscriptions",
                "provisioning",
                "billing",
                "support",
                "dns",
                "upgrade",
                "objstore",
                "loadbalancer",
            ],
        }

    return mcp
