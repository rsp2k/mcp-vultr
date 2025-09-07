"""
Vultr Operating Systems FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr operating systems.
"""

from typing import Any

from fastmcp import FastMCP


def create_os_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr operating system management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with OS management tools
    """
    mcp = FastMCP(name="vultr-os")

    @mcp.tool()
    async def list_operating_systems() -> list[dict[str, Any]]:
        """
        List all available operating systems.

        Returns:
            List of available operating systems
        """
        return await vultr_client.list_operating_systems()

    @mcp.tool()
    async def get_operating_system(os_id: str) -> dict[str, Any]:
        """
        Get details of a specific operating system.

        Args:
            os_id: The operating system ID

        Returns:
            Operating system details
        """
        return await vultr_client.get_operating_system(os_id)

    @mcp.tool()
    async def list_linux_os() -> list[dict[str, Any]]:
        """
        List Linux operating systems.

        Returns:
            List of Linux operating systems
        """
        all_os = await vultr_client.list_operating_systems()
        # Filter for Linux distributions
        linux_keywords = [
            "ubuntu",
            "debian",
            "centos",
            "fedora",
            "arch",
            "rocky",
            "alma",
            "opensuse",
        ]
        linux_os = []

        for os_item in all_os:
            name = os_item.get("name", "").lower()
            if any(keyword in name for keyword in linux_keywords):
                linux_os.append(os_item)

        return linux_os

    @mcp.tool()
    async def list_windows_os() -> list[dict[str, Any]]:
        """
        List Windows operating systems.

        Returns:
            List of Windows operating systems
        """
        all_os = await vultr_client.list_operating_systems()
        # Filter for Windows
        windows_os = [
            os_item
            for os_item in all_os
            if "windows" in os_item.get("name", "").lower()
        ]
        return windows_os

    @mcp.tool()
    async def search_os_by_name(name: str) -> list[dict[str, Any]]:
        """
        Search operating systems by name.

        Args:
            name: OS name to search for (partial match)

        Returns:
            List of matching operating systems
        """
        all_os = await vultr_client.list_operating_systems()
        matching_os = []

        for os_item in all_os:
            if name.lower() in os_item.get("name", "").lower():
                matching_os.append(os_item)

        return matching_os

    @mcp.tool()
    async def get_os_by_name(name: str) -> dict[str, Any]:
        """
        Get operating system by exact name match.

        Args:
            name: Exact OS name to find

        Returns:
            Operating system details
        """
        all_os = await vultr_client.list_operating_systems()

        for os_item in all_os:
            if os_item.get("name", "").lower() == name.lower():
                return os_item

        raise ValueError(f"Operating system '{name}' not found")

    @mcp.tool()
    async def list_application_images() -> list[dict[str, Any]]:
        """
        List application images (one-click apps).

        Returns:
            List of application images
        """
        all_os = await vultr_client.list_operating_systems()
        # Filter for application images (typically have "Application" in family)
        app_images = [
            os_item
            for os_item in all_os
            if os_item.get("family", "").lower() == "application"
        ]
        return app_images

    @mcp.tool()
    async def list_os_by_family(family: str) -> list[dict[str, Any]]:
        """
        List operating systems by family.

        Args:
            family: OS family (e.g., 'ubuntu', 'centos', 'windows', 'application')

        Returns:
            List of operating systems in the specified family
        """
        all_os = await vultr_client.list_operating_systems()
        family_os = [
            os_item
            for os_item in all_os
            if os_item.get("family", "").lower() == family.lower()
        ]
        return family_os

    return mcp
