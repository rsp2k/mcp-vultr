"""
Vultr Object Storage (S3) FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr Object Storage 
(S3-compatible) instances, including storage management, access keys, and cluster information.
"""

from typing import Optional, List, Dict, Any
from fastmcp import FastMCP


def create_object_storage_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr Object Storage management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with Object Storage management tools
    """
    mcp = FastMCP(name="vultr-object-storage")
    
    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
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
    async def list_object_storage_resource() -> List[Dict[str, Any]]:
        """List all Object Storage instances in your Vultr account."""
        return await vultr_client.list_object_storage()
    
    @mcp.resource("object-storage://{object_storage_id}")
    async def get_object_storage_resource(object_storage_id: str) -> Dict[str, Any]:
        """Get information about a specific Object Storage instance.
        
        Args:
            object_storage_id: The Object Storage ID or label
        """
        actual_id = await get_object_storage_id(object_storage_id)
        return await vultr_client.get_object_storage(actual_id)
    
    @mcp.resource("object-storage://clusters")
    async def list_clusters_resource() -> List[Dict[str, Any]]:
        """List all Object Storage clusters."""
        return await vultr_client.list_object_storage_clusters()
    
    @mcp.resource("object-storage://clusters/{cluster_id}/tiers")
    async def list_cluster_tiers_resource(cluster_id: str) -> List[Dict[str, Any]]:
        """List available tiers for a specific Object Storage cluster.
        
        Args:
            cluster_id: The cluster ID
        """
        return await vultr_client.list_object_storage_cluster_tiers(int(cluster_id))
    
    # Object Storage management tools
    @mcp.tool()
    async def list() -> List[Dict[str, Any]]:
        """List all Object Storage instances in your Vultr account.
        
        Returns:
            List of Object Storage instances with details including:
            - id: Object Storage ID
            - label: User-defined label
            - region: Region where the storage is located
            - cluster_id: Cluster ID
            - status: Instance status (active, pending, etc.)
            - s3_hostname: S3-compatible hostname
            - s3_access_key: S3 access key
            - s3_secret_key: S3 secret key (sensitive)
            - date_created: Creation date
        """
        return await vultr_client.list_object_storage()
    
    @mcp.tool()
    async def get(object_storage_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific Object Storage instance.
        
        Args:
            object_storage_id: The Object Storage ID or label (e.g., "my-storage", "backup-bucket", or UUID)
            
        Returns:
            Detailed Object Storage information including access credentials
        """
        actual_id = await get_object_storage_id(object_storage_id)
        return await vultr_client.get_object_storage(actual_id)
    
    @mcp.tool()
    async def create(
        cluster_id: int,
        label: str
    ) -> Dict[str, Any]:
        """Create a new Object Storage instance.
        
        Args:
            cluster_id: The cluster ID where the Object Storage will be created (use list_clusters to see options)
            label: A descriptive label for the Object Storage instance
            
        Returns:
            Created Object Storage information including access credentials
        """
        return await vultr_client.create_object_storage(
            cluster_id=cluster_id,
            label=label
        )
    
    @mcp.tool()
    async def update(
        object_storage_id: str,
        label: str
    ) -> Dict[str, str]:
        """Update an Object Storage instance's label.
        
        Args:
            object_storage_id: The Object Storage ID or label (e.g., "my-storage", "backup-bucket", or UUID)
            label: New label for the Object Storage instance
            
        Returns:
            Status message confirming update
        """
        actual_id = await get_object_storage_id(object_storage_id)
        await vultr_client.update_object_storage(actual_id, label)
        return {"status": "success", "message": f"Object Storage {object_storage_id} updated successfully"}
    
    @mcp.tool()
    async def delete(object_storage_id: str) -> Dict[str, str]:
        """Delete an Object Storage instance.
        
        Args:
            object_storage_id: The Object Storage ID or label (e.g., "my-storage", "backup-bucket", or UUID)
            
        Returns:
            Status message confirming deletion
        """
        actual_id = await get_object_storage_id(object_storage_id)
        await vultr_client.delete_object_storage(actual_id)
        return {"status": "success", "message": f"Object Storage {object_storage_id} deleted successfully"}
    
    @mcp.tool()
    async def regenerate_keys(object_storage_id: str) -> Dict[str, Any]:
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
    async def list_clusters() -> List[Dict[str, Any]]:
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
    async def list_cluster_tiers(cluster_id: int) -> List[Dict[str, Any]]:
        """List all available tiers for a specific Object Storage cluster.
        
        Args:
            cluster_id: The cluster ID (use list_clusters to see available clusters)
            
        Returns:
            List of available tiers for the cluster with pricing and limits
        """
        return await vultr_client.list_object_storage_cluster_tiers(cluster_id)
    
    # Helper tools for Object Storage management
    @mcp.tool()
    async def get_s3_config(object_storage_id: str) -> Dict[str, Any]:
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
        actual_id = await get_object_storage_id(object_storage_id)
        storage = await vultr_client.get_object_storage(actual_id)
        
        return {
            "endpoint": f"https://{storage.get('s3_hostname', '')}",
            "access_key": storage.get("s3_access_key", ""),
            "secret_key": storage.get("s3_secret_key", ""),
            "region": storage.get("region", ""),
            "hostname": storage.get("s3_hostname", ""),
            "bucket_examples": {
                "aws_cli": f"aws s3 ls --endpoint-url=https://{storage.get('s3_hostname', '')}",
                "boto3_config": {
                    "endpoint_url": f"https://{storage.get('s3_hostname', '')}",
                    "aws_access_key_id": storage.get("s3_access_key", ""),
                    "aws_secret_access_key": storage.get("s3_secret_key", ""),
                    "region_name": storage.get("region", "")
                }
            }
        }
    
    @mcp.tool()
    async def find_by_region(region: str) -> List[Dict[str, Any]]:
        """Find all Object Storage instances in a specific region.
        
        Args:
            region: Region code (e.g., "ewr", "lax", "fra")
            
        Returns:
            List of Object Storage instances in the specified region
        """
        all_storages = await vultr_client.list_object_storage()
        return [storage for storage in all_storages if storage.get("region") == region]
    
    @mcp.tool()
    async def get_storage_summary() -> Dict[str, Any]:
        """Get a summary of all Object Storage instances.
        
        Returns:
            Summary information including:
            - total_instances: Total number of Object Storage instances
            - regions: List of regions with storage counts
            - status_breakdown: Count by status
            - cluster_usage: Count by cluster
        """
        storages = await vultr_client.list_object_storage()
        
        summary = {
            "total_instances": len(storages),
            "regions": {},
            "status_breakdown": {},
            "cluster_usage": {}
        }
        
        for storage in storages:
            region = storage.get("region", "unknown")
            status = storage.get("status", "unknown")
            cluster_id = storage.get("cluster_id", "unknown")
            
            summary["regions"][region] = summary["regions"].get(region, 0) + 1
            summary["status_breakdown"][status] = summary["status_breakdown"].get(status, 0) + 1
            summary["cluster_usage"][str(cluster_id)] = summary["cluster_usage"].get(str(cluster_id), 0) + 1
        
        return summary
    
    @mcp.tool()
    async def validate_s3_access(object_storage_id: str) -> Dict[str, Any]:
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
        actual_id = await get_object_storage_id(object_storage_id)
        storage = await vultr_client.get_object_storage(actual_id)
        
        has_hostname = bool(storage.get("s3_hostname"))
        has_access_key = bool(storage.get("s3_access_key"))
        has_secret_key = bool(storage.get("s3_secret_key"))
        is_active = storage.get("status") == "active"
        
        suggestions = []
        if not is_active:
            suggestions.append("Object Storage is not in 'active' status - wait for provisioning to complete")
        if not has_access_key or not has_secret_key:
            suggestions.append("Missing access keys - try regenerating keys")
        if not has_hostname:
            suggestions.append("Missing S3 hostname - check Object Storage configuration")
        
        return {
            "valid": has_hostname and has_access_key and has_secret_key and is_active,
            "endpoint": f"https://{storage.get('s3_hostname', '')}" if has_hostname else None,
            "has_credentials": has_access_key and has_secret_key,
            "status": storage.get("status"),
            "suggestions": suggestions,
            "details": {
                "has_hostname": has_hostname,
                "has_access_key": has_access_key,
                "has_secret_key": has_secret_key,
                "is_active": is_active
            }
        }
    
    return mcp