"""
Vultr ISO FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr ISO images.
"""

from typing import Any

from fastmcp import FastMCP


def create_iso_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr ISO management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with ISO management tools
    """
    mcp = FastMCP(name="vultr-iso")

    @mcp.tool()
    async def list_isos() -> list[dict[str, Any]]:
        """
        List all available ISO images.

        Returns:
            List of available ISO images
        """
        return await vultr_client.list_isos()

    @mcp.tool()
    async def get_iso(iso_id: str) -> dict[str, Any]:
        """
        Get details of a specific ISO image.

        Args:
            iso_id: The ISO ID

        Returns:
            ISO image details
        """
        return await vultr_client.get_iso(iso_id)

    @mcp.tool()
    async def create_iso(url: str) -> dict[str, Any]:
        """
        Create a new ISO image from URL.

        Args:
            url: The URL to create the ISO from

        Returns:
            Created ISO details
        """
        return await vultr_client.create_iso(url)

    @mcp.tool()
    async def delete_iso(iso_id: str) -> str:
        """
        Delete an ISO image.

        Args:
            iso_id: The ISO ID to delete

        Returns:
            Success message
        """
        await vultr_client.delete_iso(iso_id)
        return f"Successfully deleted ISO {iso_id}"

    @mcp.tool()
    async def list_public_isos() -> list[dict[str, Any]]:
        """
        List public ISO images (filtered from all ISOs).

        Returns:
            List of public ISO images
        """
        all_isos = await vultr_client.list_isos()
        # Filter to show only public ISOs (those without a filename, indicating they're Vultr-provided)
        public_isos = [iso for iso in all_isos if not iso.get("filename")]
        return public_isos

    @mcp.tool()
    async def list_custom_isos() -> list[dict[str, Any]]:
        """
        List custom ISO images (user-uploaded).

        Returns:
            List of custom ISO images
        """
        all_isos = await vultr_client.list_isos()
        # Filter to show only custom ISOs (those with a filename, indicating they're user-uploaded)
        custom_isos = [iso for iso in all_isos if iso.get("filename")]
        return custom_isos

    @mcp.tool()
    async def get_iso_by_name(name: str) -> dict[str, Any]:
        """
        Get ISO by name or filename.

        Args:
            name: ISO name or filename to search for

        Returns:
            ISO details if found
        """
        all_isos = await vultr_client.list_isos()

        for iso in all_isos:
            if (
                iso.get("name", "").lower() == name.lower()
                or iso.get("filename", "").lower() == name.lower()
            ):
                return iso

        raise ValueError(f"ISO with name '{name}' not found")

    return mcp
