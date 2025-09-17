"""
Vultr Marketplace FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr marketplace applications.
"""

from typing import Any

from fastmcp import FastMCP


def create_marketplace_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr marketplace applications management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with marketplace management tools
    """
    mcp = FastMCP(name="vultr-marketplace")

    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        return bool(len(s) == 36 and s.count("-") == 4)

    # Helper function to get application ID from name or image_id
    async def get_application_id(identifier: str) -> str:
        """
        Get the application ID or image_id from a name, short_name, or image_id.

        Args:
            identifier: Application name, short_name, or image_id

        Returns:
            The application ID or image_id (for marketplace apps)

        Raises:
            ValueError: If the application is not found
        """
        # For marketplace apps, we might get image_id directly
        if identifier.count("-") >= 1 and not is_uuid_format(identifier):
            # This looks like an image_id (e.g., "openlitespeed-wordpress")
            return identifier

        # Otherwise, search for it by name or short_name
        applications = await vultr_client.list_applications()
        for app in applications:
            if (
                app.get("name", "").lower() == identifier.lower()
                or app.get("short_name", "").lower() == identifier.lower()
                or app.get("image_id") == identifier
                or str(app.get("id")) == identifier
            ):
                # Return image_id for marketplace apps, id for one-click apps
                if app.get("type") == "marketplace":
                    return app.get("image_id", str(app.get("id")))
                else:
                    return str(app.get("id"))

        raise ValueError(
            f"Application '{identifier}' not found (searched by name, short_name, and image_id)"
        )

    # Helper function to filter applications by type and criteria
    async def filter_applications(
        app_type: str | None = None,
        vendor: str | None = None,
        search_term: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Filter applications by various criteria.

        Args:
            app_type: Filter by type ('marketplace', 'one-click', or None for all)
            vendor: Filter by vendor name
            search_term: Search in name and description

        Returns:
            Filtered list of applications
        """
        applications = await vultr_client.list_applications(app_type=app_type)

        if vendor:
            applications = [
                app
                for app in applications
                if app.get("vendor", "").lower() == vendor.lower()
            ]

        if search_term:
            search_lower = search_term.lower()
            applications = [
                app
                for app in applications
                if search_lower in app.get("name", "").lower()
                or search_lower in app.get("deploy_name", "").lower()
                or search_lower in app.get("short_name", "").lower()
            ]

        return applications

    # Helper function to get popular applications
    async def get_popular_applications(limit: int = 10) -> list[dict[str, Any]]:
        """
        Get popular marketplace applications.

        Args:
            limit: Maximum number of applications to return

        Returns:
            List of popular applications
        """
        # Get all applications and return popular ones
        # In a real implementation, this would be based on usage statistics
        # For now, we'll return the first few marketplace apps
        applications = await vultr_client.list_applications(app_type="marketplace")
        return applications[:limit]

    # Marketplace resources
    @mcp.resource("marketplace://applications")
    async def list_applications_resource() -> list[dict[str, Any]]:
        """List all marketplace and one-click applications."""
        return await vultr_client.list_applications()

    @mcp.resource("marketplace://applications/marketplace")
    async def list_marketplace_applications_resource() -> list[dict[str, Any]]:
        """List only marketplace applications."""
        return await vultr_client.list_applications(app_type="marketplace")

    @mcp.resource("marketplace://applications/one-click")
    async def list_oneclick_applications_resource() -> list[dict[str, Any]]:
        """List only one-click applications."""
        return await vultr_client.list_applications(app_type="one-click")

    @mcp.resource("marketplace://applications/{app_id}")
    async def get_application_resource(app_id: str) -> dict[str, Any]:
        """Get information about a specific application.

        Args:
            app_id: The application ID, name, short_name, or image_id
        """
        # Get the actual identifier
        identifier = await get_application_id(app_id)

        # Find the application in the list since there's no direct get endpoint
        applications = await vultr_client.list_applications()
        for app in applications:
            if str(app.get("id")) == identifier or app.get("image_id") == identifier:
                return app

        raise ValueError(f"Application '{app_id}' not found")

    @mcp.resource("marketplace://applications/{app_id}/variables")
    async def get_application_variables_resource(app_id: str) -> dict[str, Any]:
        """Get configuration variables for a marketplace application.

        Args:
            app_id: The application name, short_name, or image_id
        """
        # Get the image_id for marketplace apps
        identifier = await get_application_id(app_id)

        # Check if this is a marketplace app
        applications = await vultr_client.list_applications(app_type="marketplace")
        marketplace_app = None
        for app in applications:
            if app.get("image_id") == identifier or str(app.get("id")) == identifier:
                marketplace_app = app
                break

        if not marketplace_app:
            raise ValueError(f"Marketplace application '{app_id}' not found")

        # Get variables using image_id
        image_id = marketplace_app.get("image_id")
        if not image_id:
            raise ValueError(
                f"No image_id found for marketplace application '{app_id}'"
            )

        return await vultr_client.get_marketplace_app_variables(image_id)

    # Marketplace tools
    @mcp.tool
    async def get_application(app_id: str) -> dict[str, Any]:
        """Get detailed information about a specific application.

        Args:
            app_id: The application ID, name, short_name, or image_id (e.g., "wordpress", "openlitespeed-wordpress")

        Returns:
            Detailed application information
        """
        # Get the actual identifier
        identifier = await get_application_id(app_id)

        # Find the application in the list since there's no direct get endpoint
        applications = await vultr_client.list_applications()
        for app in applications:
            if str(app.get("id")) == identifier or app.get("image_id") == identifier:
                return app

        raise ValueError(f"Application '{app_id}' not found")

    @mcp.tool
    async def search_applications(
        search_term: str, app_type: str | None = None, vendor: str | None = None
    ) -> list[dict[str, Any]]:
        """Search applications by name, description, or other criteria.

        Args:
            search_term: Search term to match against application names and descriptions
            app_type: Optional filter by type ('marketplace', 'one-click')
            vendor: Optional filter by vendor name

        Returns:
            List of matching applications
        """
        return await filter_applications(
            app_type=app_type, vendor=vendor, search_term=search_term
        )

    @mcp.tool
    async def get_applications_by_vendor(vendor: str) -> list[dict[str, Any]]:
        """Get all applications from a specific vendor.

        Args:
            vendor: Vendor name (e.g., "vultr", "LiteSpeed_Technologies")

        Returns:
            List of applications from the specified vendor
        """
        return await filter_applications(vendor=vendor)

    @mcp.tool
    async def get_popular_marketplace_apps(limit: int = 10) -> list[dict[str, Any]]:
        """Get popular marketplace applications.

        Args:
            limit: Maximum number of applications to return (default: 10)

        Returns:
            List of popular marketplace applications
        """
        return await get_popular_applications(limit=limit)

    @mcp.tool
    async def get_marketplace_app_variables(app_id: str) -> dict[str, Any]:
        """Get configuration variables for a marketplace application.

        Args:
            app_id: The marketplace application name, short_name, or image_id (e.g., "openlitespeed-wordpress")

        Returns:
            Application variables information including:
            - variables: List of configuration variables
            - Each variable contains: name, description, required (boolean)
        """
        # Get the image_id for marketplace apps
        identifier = await get_application_id(app_id)

        # Check if this is a marketplace app
        applications = await vultr_client.list_applications(app_type="marketplace")
        marketplace_app = None
        for app in applications:
            if app.get("image_id") == identifier or str(app.get("id")) == identifier:
                marketplace_app = app
                break

        if not marketplace_app:
            raise ValueError(f"Marketplace application '{app_id}' not found")

        # Get variables using image_id
        image_id = marketplace_app.get("image_id")
        if not image_id:
            raise ValueError(
                f"No image_id found for marketplace application '{app_id}'"
            )

        return await vultr_client.get_marketplace_app_variables(image_id)

    @mcp.tool
    async def get_application_deployment_guide(app_id: str) -> dict[str, Any]:
        """Get deployment guidance for an application.

        Args:
            app_id: The application ID, name, short_name, or image_id

        Returns:
            Deployment guidance including application details and requirements
        """
        app = await get_application(app_id)

        guide = {
            "application": app,
            "deployment_steps": [],
            "requirements": {},
            "variables": None,
        }

        # Add basic deployment steps
        if app.get("type") == "marketplace":
            guide["deployment_steps"] = [
                "1. Get the application image_id from the marketplace",
                "2. Review and configure required variables",
                "3. Create instance using the image_id and app variables",
                "4. Wait for deployment to complete",
                "5. Access application using instance IP",
            ]

            # Get variables for marketplace apps
            image_id = app.get("image_id")
            if image_id:
                try:
                    variables = await vultr_client.get_marketplace_app_variables(
                        image_id
                    )
                    guide["variables"] = variables

                    required_vars = [
                        v for v in variables.get("variables", []) if v.get("required")
                    ]
                    if required_vars:
                        guide["requirements"]["required_variables"] = [
                            f"{var['name']}: {var['description']}"
                            for var in required_vars
                        ]
                except Exception:
                    # Variables endpoint might not be available for all apps
                    guide["variables"] = {
                        "error": "Variables not available for this application"
                    }
        else:
            # One-click app
            guide["deployment_steps"] = [
                "1. Get the application ID from one-click apps",
                "2. Create instance using the app_id parameter",
                "3. Wait for deployment to complete",
                "4. Access application using instance IP",
            ]

        guide["requirements"]["minimum_resources"] = (
            "Check specific application documentation for resource requirements"
        )

        return guide

    @mcp.tool
    async def list_application_categories() -> dict[str, list[str]]:
        """List applications grouped by categories/vendors.

        Returns:
            Dictionary with vendors as keys and their applications as values
        """
        applications = await vultr_client.list_applications()

        categories = {}
        vendors = {}

        for app in applications:
            vendor = app.get("vendor", "unknown")
            app_type = app.get("type", "unknown")

            # Group by vendor
            if vendor not in vendors:
                vendors[vendor] = []
            vendors[vendor].append(
                {
                    "name": app.get("name"),
                    "short_name": app.get("short_name"),
                    "type": app_type,
                    "id": app.get("id"),
                    "image_id": app.get("image_id"),
                }
            )

            # Group by type
            if app_type not in categories:
                categories[app_type] = []
            categories[app_type].append(
                {
                    "name": app.get("name"),
                    "vendor": vendor,
                    "id": app.get("id"),
                    "image_id": app.get("image_id"),
                }
            )

        return {
            "by_vendor": vendors,
            "by_type": categories,
            "summary": {
                "total_applications": len(applications),
                "vendors": len(vendors),
                "marketplace_apps": len(
                    [a for a in applications if a.get("type") == "marketplace"]
                ),
                "oneclick_apps": len(
                    [a for a in applications if a.get("type") == "one-click"]
                ),
            },
        }

    @mcp.tool
    async def get_deployment_examples() -> dict[str, Any]:
        """Get examples of how to deploy popular marketplace applications.

        Returns:
            Dictionary with deployment examples and common use cases
        """
        examples = {
            "wordpress_deployment": {
                "description": "Deploy WordPress with OpenLiteSpeed",
                "application": "openlitespeed-wordpress",
                "steps": [
                    "1. Search for 'OpenLiteSpeed WordPress' application",
                    "2. Get application variables to see required configuration",
                    "3. Create instance with image_id and provide required variables",
                    "4. Access WordPress admin at http://your-ip/wp-admin",
                ],
                "sample_variables": {
                    "admin_user": "wp_admin",
                    "admin_password": "secure_password_here",
                    "site_title": "My WordPress Site",
                },
            },
            "common_applications": {
                "web_servers": [
                    {"name": "NGINX", "use_case": "High-performance web server"},
                    {"name": "Apache", "use_case": "Traditional web server"},
                    {
                        "name": "OpenLiteSpeed",
                        "use_case": "Fast web server with caching",
                    },
                ],
                "databases": [
                    {"name": "MySQL", "use_case": "Relational database"},
                    {"name": "PostgreSQL", "use_case": "Advanced relational database"},
                    {"name": "Redis", "use_case": "In-memory data store"},
                ],
                "cms_platforms": [
                    {"name": "WordPress", "use_case": "Content management system"},
                    {"name": "Drupal", "use_case": "Enterprise CMS"},
                    {"name": "Joomla", "use_case": "Flexible CMS"},
                ],
            },
            "deployment_tips": [
                "Always review application variables before deployment",
                "Use strong passwords for admin accounts",
                "Consider firewall rules for security",
                "Check application documentation for post-deployment configuration",
                "Monitor resource usage and scale as needed",
            ],
        }

        return examples

    return mcp
