"""
Vultr Object Storage (S3) FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr Object Storage
(S3-compatible) instances, including storage management, access keys, and cluster information.
"""

from typing import Any

from fastmcp import FastMCP

from .object_storage_analyzer import ObjectStorageAnalyzer
from .server import VultrResourceNotFoundError


def create_object_storage_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr Object Storage management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with Object Storage management tools
    """
    mcp = FastMCP(name="vultr-object-storage")
    storage_analyzer = ObjectStorageAnalyzer(vultr_client)

    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        import re

        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return bool(re.match(uuid_pattern, s, re.IGNORECASE))

    # Helper function to get Object Storage ID from label or UUID
    async def get_object_storage_id(identifier: str) -> str:
        """
        Get the Object Storage ID from a label or UUID.

        Args:
            identifier: Object Storage label or UUID

        Returns:
            The Object Storage ID (UUID)

        Raises:
            ValueError: If the Object Storage is not found
        """
        # If it looks like a UUID, return it as-is
        if is_uuid_format(identifier):
            return identifier

        # Otherwise, search for it by label
        storages = await vultr_client.list_object_storage()
        for storage in storages:
            if storage.get("label") == identifier:
                return storage["id"]

        raise ValueError(f"Object Storage '{identifier}' not found (searched by label)")

    # Object Storage resources
    @mcp.resource("object-storage://list")
    async def list_object_storage_resource() -> list[dict[str, Any]]:
        """List all Object Storage instances in your Vultr account."""
        try:
            return await vultr_client.list_object_storage()
        except Exception:
            # If the API returns an error when no object storage exists, return empty list
            return []

    @mcp.resource("object-storage://{object_storage_id}")
    async def get_object_storage_resource(object_storage_id: str) -> dict[str, Any]:
        """Get information about a specific Object Storage instance.

        Args:
            object_storage_id: The Object Storage ID or label
        """
        actual_id = await get_object_storage_id(object_storage_id)
        return await vultr_client.get_object_storage(actual_id)

    @mcp.resource("object-storage://clusters")
    async def list_clusters_resource() -> list[dict[str, Any]]:
        """List all Object Storage clusters."""
        return await vultr_client.list_object_storage_clusters()

    @mcp.resource("object-storage://clusters/{cluster_id}/tiers")
    async def list_cluster_tiers_resource(cluster_id: str) -> list[dict[str, Any]]:
        """List available tiers for a specific Object Storage cluster.

        Args:
            cluster_id: The cluster ID
        """
        return await vultr_client.list_object_storage_cluster_tiers(int(cluster_id))

    # Object Storage management tools
    @mcp.tool()
    async def get(object_storage_id: str) -> dict[str, Any]:
        """Get detailed information about a specific Object Storage instance.

        Args:
            object_storage_id: The Object Storage ID or label (e.g., "my-storage", "backup-bucket", or UUID)

        Returns:
            Detailed Object Storage information including access credentials
        """
        actual_id = await get_object_storage_id(object_storage_id)
        return await vultr_client.get_object_storage(actual_id)

    @mcp.tool()
    async def create(cluster_id: int, label: str) -> dict[str, Any]:
        """Create a new Object Storage instance.

        Args:
            cluster_id: The cluster ID where the Object Storage will be created (use list_clusters to see options)
            label: A descriptive label for the Object Storage instance

        Returns:
            Created Object Storage information including access credentials
        """
        return await vultr_client.create_object_storage(
            cluster_id=cluster_id, label=label
        )

    @mcp.tool()
    async def update(object_storage_id: str, label: str) -> dict[str, str]:
        """Update an Object Storage instance's label.

        Args:
            object_storage_id: The Object Storage ID or label (e.g., "my-storage", "backup-bucket", or UUID)
            label: New label for the Object Storage instance

        Returns:
            Status message confirming update
        """
        actual_id = await get_object_storage_id(object_storage_id)
        await vultr_client.update_object_storage(actual_id, label)
        return {
            "status": "success",
            "message": f"Object Storage {object_storage_id} updated successfully",
        }

    @mcp.tool()
    async def delete(object_storage_id: str) -> dict[str, str]:
        """Delete an Object Storage instance.

        Args:
            object_storage_id: The Object Storage ID or label (e.g., "my-storage", "backup-bucket", or UUID)

        Returns:
            Status message confirming deletion
        """
        actual_id = await get_object_storage_id(object_storage_id)
        try:
            await vultr_client.delete_object_storage(actual_id)
        except VultrResourceNotFoundError:
            storages = await vultr_client.list_object_storage()
            if storages:
                storage_list = ", ".join(
                    f"{s.get('label', 'unnamed')} ({s.get('id')})" for s in storages
                )
                raise ValueError(
                    f"Object Storage '{object_storage_id}' not found. "
                    f"Available: {storage_list}."
                ) from None
            else:
                raise ValueError(
                    f"Object Storage '{object_storage_id}' not found. "
                    f"No Object Storage instances exist in this account."
                ) from None
        return {
            "status": "success",
            "message": f"Object Storage {object_storage_id} deleted successfully",
        }

    @mcp.tool()
    async def regenerate_keys(object_storage_id: str) -> dict[str, Any]:
        """Regenerate the S3 access keys for an Object Storage instance.

        Args:
            object_storage_id: The Object Storage ID or label (e.g., "my-storage", "backup-bucket", or UUID)

        Returns:
            Object Storage information with new access keys
        """
        actual_id = await get_object_storage_id(object_storage_id)
        return await vultr_client.regenerate_object_storage_keys(actual_id)

    # Cluster and tier information tools
    @mcp.tool()
    async def list_clusters() -> list[dict[str, Any]]:
        """List all available Object Storage clusters.

        Returns:
            List of Object Storage clusters with details including:
            - id: Cluster ID
            - region: Region code
            - hostname: S3-compatible hostname for the cluster
            - deploy: Deployment status
        """
        return await vultr_client.list_object_storage_clusters()

    @mcp.tool()
    async def list_cluster_tiers(cluster_id: int) -> list[dict[str, Any]]:
        """List all available tiers for a specific Object Storage cluster.

        Args:
            cluster_id: The cluster ID (use list_clusters to see available clusters)

        Returns:
            List of available tiers for the cluster with pricing and limits
        """
        return await vultr_client.list_object_storage_cluster_tiers(cluster_id)

    # Helper tools for Object Storage management
    @mcp.tool()
    async def get_s3_config(object_storage_id: str) -> dict[str, Any]:
        """Get S3-compatible configuration details for an Object Storage instance.

        Args:
            object_storage_id: The Object Storage ID or label (e.g., "my-storage", "backup-bucket", or UUID)

        Returns:
            S3 configuration details including:
            - endpoint: S3-compatible endpoint URL
            - access_key: S3 access key
            - secret_key: S3 secret key
            - region: Storage region
            - bucket_examples: Example bucket operations
        """
        return await storage_analyzer.get_s3_config(object_storage_id)

    @mcp.tool()
    async def find_by_region(region: str) -> list[dict[str, Any]]:
        """Find all Object Storage instances in a specific region.

        Args:
            region: Region code (e.g., "ewr", "lax", "fra")

        Returns:
            List of Object Storage instances in the specified region
        """
        return await storage_analyzer.find_by_region(region)

    @mcp.tool()
    async def get_storage_summary() -> dict[str, Any]:
        """Get a summary of all Object Storage instances.

        Returns:
            Summary information including:
            - total_instances: Total number of Object Storage instances
            - regions: List of regions with storage counts
            - status_breakdown: Count by status
            - cluster_usage: Count by cluster
        """
        return await storage_analyzer.get_storage_summary()

    @mcp.tool()
    async def validate_s3_access(object_storage_id: str) -> dict[str, Any]:
        """Validate that an Object Storage instance has valid S3 credentials.

        Args:
            object_storage_id: The Object Storage ID or label (e.g., "my-storage", "backup-bucket", or UUID)

        Returns:
            Validation results including:
            - valid: Whether the configuration appears valid
            - endpoint: S3 endpoint URL
            - has_credentials: Whether access keys are present
            - suggestions: Any configuration suggestions
        """
        return await storage_analyzer.validate_s3_access(object_storage_id)

    return mcp
