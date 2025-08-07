"""
Vultr Container Registry FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr container registries.
"""

from typing import List, Dict, Any, Optional
from fastmcp import FastMCP


def create_container_registry_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr container registry management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with container registry management tools
    """
    mcp = FastMCP(name="vultr-container-registry")
    
    # Helper function to check if string is UUID format
    def is_uuid_format(value: str) -> bool:
        """Check if a string looks like a UUID."""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))
    
    # Helper function to get registry ID from name or ID
    async def get_registry_id(identifier: str) -> str:
        """
        Get the registry ID from name or existing ID.
        
        Args:
            identifier: Registry name or ID
            
        Returns:
            The registry ID
            
        Raises:
            ValueError: If the registry is not found
        """
        # If it looks like a UUID, return as-is
        if is_uuid_format(identifier):
            return identifier
        
        # Search by name
        registries = await vultr_client.list_container_registries()
        for registry in registries:
            if registry.get("name") == identifier:
                return registry["id"]
        
        raise ValueError(f"Container registry '{identifier}' not found")
    
    # Container Registry resources
    @mcp.resource("container-registry://list")
    async def list_registries_resource() -> List[Dict[str, Any]]:
        """List all container registries."""
        return await vultr_client.list_container_registries()
    
    @mcp.resource("container-registry://{registry_identifier}")
    async def get_registry_resource(registry_identifier: str) -> Dict[str, Any]:
        """Get details of a specific container registry.
        
        Args:
            registry_identifier: The registry name or ID
        """
        registry_id = await get_registry_id(registry_identifier)
        return await vultr_client.get_container_registry(registry_id)
    
    @mcp.resource("container-registry://plans")
    async def list_plans_resource() -> List[Dict[str, Any]]:
        """List all available container registry plans."""
        return await vultr_client.list_registry_plans()
    
    # Container Registry tools
    @mcp.tool
    async def list() -> List[Dict[str, Any]]:
        """List all container registries in your account.
        
        Returns:
            List of container registry objects with details including:
            - id: Registry ID
            - name: Registry name
            - urn: Universal Resource Name
            - storage: Storage details
            - date_created: Creation date
            - public: Whether registry is public
            - root_user: Root user details
        """
        return await vultr_client.list_container_registries()
    
    @mcp.tool
    async def get(registry_identifier: str) -> Dict[str, Any]:
        """Get detailed information about a specific container registry.
        
        Smart identifier resolution: Use registry name or ID.
        
        Args:
            registry_identifier: Registry name or ID to retrieve
            
        Returns:
            Detailed registry information including storage, plan, and configuration
        """
        registry_id = await get_registry_id(registry_identifier)
        return await vultr_client.get_container_registry(registry_id)
    
    @mcp.tool
    async def create(
        name: str,
        plan: str,
        region: str
    ) -> Dict[str, Any]:
        """Create a new container registry subscription.
        
        Args:
            name: Name for the container registry
            plan: Registry plan ("start_up", "business", "premium", etc.)
            region: Region code for the registry (e.g., "ewr", "lax", "fra")
            
        Returns:
            Created registry information including ID, URN, and configuration
        """
        return await vultr_client.create_container_registry(name, plan, region)
    
    @mcp.tool
    async def update(registry_identifier: str, plan: str) -> Dict[str, str]:
        """Update container registry plan.
        
        Smart identifier resolution: Use registry name or ID.
        
        Args:
            registry_identifier: Registry name or ID to update
            plan: New registry plan ("start_up", "business", "premium", etc.)
            
        Returns:
            Success confirmation
        """
        registry_id = await get_registry_id(registry_identifier)
        await vultr_client.update_container_registry(registry_id, plan)
        return {
            "success": True,
            "message": f"Registry plan updated to {plan}",
            "registry_id": registry_id
        }
    
    @mcp.tool
    async def delete(registry_identifier: str) -> Dict[str, str]:
        """Delete a container registry subscription.
        
        Smart identifier resolution: Use registry name or ID.
        
        Args:
            registry_identifier: Registry name or ID to delete
            
        Returns:
            Success confirmation
        """
        registry_id = await get_registry_id(registry_identifier)
        await vultr_client.delete_container_registry(registry_id)
        return {
            "success": True,
            "message": f"Registry deleted successfully",
            "registry_id": registry_id
        }
    
    @mcp.tool
    async def list_plans() -> List[Dict[str, Any]]:
        """List all available container registry plans.
        
        Returns:
            List of available plans with pricing and feature details
        """
        return await vultr_client.list_registry_plans()
    
    @mcp.tool
    async def generate_docker_credentials(
        registry_identifier: str,
        expiry_seconds: Optional[int] = None,
        read_write: bool = True
    ) -> Dict[str, Any]:
        """Generate Docker credentials for container registry access.
        
        Smart identifier resolution: Use registry name or ID.
        
        Args:
            registry_identifier: Registry name or ID
            expiry_seconds: Expiration time in seconds (optional, default: no expiry)
            read_write: Whether to grant read-write access (default: True, False for read-only)
            
        Returns:
            Docker credentials including username, password, and registry URL
        """
        registry_id = await get_registry_id(registry_identifier)
        return await vultr_client.generate_docker_credentials(
            registry_id, expiry_seconds, read_write
        )
    
    @mcp.tool
    async def generate_kubernetes_credentials(
        registry_identifier: str,
        expiry_seconds: Optional[int] = None,
        read_write: bool = True,
        base64_encode: bool = True
    ) -> Dict[str, Any]:
        """Generate Kubernetes credentials for container registry access.
        
        Smart identifier resolution: Use registry name or ID.
        
        Args:
            registry_identifier: Registry name or ID
            expiry_seconds: Expiration time in seconds (optional, default: no expiry)
            read_write: Whether to grant read-write access (default: True, False for read-only)
            base64_encode: Whether to base64 encode the credentials (default: True)
            
        Returns:
            Kubernetes secret YAML configuration for registry access
        """
        registry_id = await get_registry_id(registry_identifier)
        return await vultr_client.generate_kubernetes_credentials(
            registry_id, expiry_seconds, read_write, base64_encode
        )
    
    @mcp.tool
    async def get_docker_login_command(
        registry_identifier: str,
        expiry_seconds: Optional[int] = None,
        read_write: bool = True
    ) -> Dict[str, str]:
        """Generate Docker login command for easy CLI access.
        
        Smart identifier resolution: Use registry name or ID.
        
        Args:
            registry_identifier: Registry name or ID
            expiry_seconds: Expiration time in seconds (optional, default: no expiry)
            read_write: Whether to grant read-write access (default: True, False for read-only)
            
        Returns:
            Docker login command and credentials information
        """
        registry_id = await get_registry_id(registry_identifier)
        creds = await vultr_client.generate_docker_credentials(
            registry_id, expiry_seconds, read_write
        )
        
        # Extract registry URL and credentials
        registry_url = creds.get("docker_credentials", {}).get("registry", "")
        username = creds.get("docker_credentials", {}).get("username", "")
        password = creds.get("docker_credentials", {}).get("password", "")
        
        login_command = f"docker login {registry_url} -u {username} -p {password}"
        
        return {
            "login_command": login_command,
            "registry_url": registry_url,
            "username": username,
            "expires_in_seconds": expiry_seconds,
            "access_type": "read-write" if read_write else "read-only"
        }
    
    @mcp.tool
    async def get_registry_info(registry_identifier: str) -> Dict[str, Any]:
        """Get comprehensive registry information including usage and configuration.
        
        Smart identifier resolution: Use registry name or ID.
        
        Args:
            registry_identifier: Registry name or ID
            
        Returns:
            Complete registry information with usage statistics and endpoints
        """
        registry_id = await get_registry_id(registry_identifier)
        registry_info = await vultr_client.get_container_registry(registry_id)
        
        # Enhance with additional helpful information
        enhanced_info = {
            **registry_info,
            "docker_push_example": f"docker tag my-image:latest {registry_info.get('urn', '')}/my-image:latest && docker push {registry_info.get('urn', '')}/my-image:latest",
            "docker_pull_example": f"docker pull {registry_info.get('urn', '')}/my-image:latest",
            "management_url": f"https://my.vultr.com/container-registry/{registry_id}",
        }
        
        return enhanced_info

    return mcp