"""
Vultr SSH Keys FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr SSH keys.
"""

from typing import Optional, List, Dict, Any
from fastmcp import FastMCP


def create_ssh_keys_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr SSH keys management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with SSH key management tools
    """
    mcp = FastMCP(name="vultr-ssh-keys")
    
    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        if len(s) == 36 and s.count('-') == 4:
            return True
        return False
    
    # Helper function to get SSH key ID from name
    async def get_ssh_key_id(identifier: str) -> str:
        """
        Get the SSH key ID from a name or UUID.
        
        Args:
            identifier: SSH key name or UUID
            
        Returns:
            The SSH key ID (UUID)
            
        Raises:
            ValueError: If the SSH key is not found
        """
        # If it looks like a UUID, return it as-is
        if is_uuid_format(identifier):
            return identifier
            
        # Otherwise, search for it by name
        ssh_keys = await vultr_client.list_ssh_keys()
        for key in ssh_keys:
            if key.get("name") == identifier:
                return key["id"]
        
        raise ValueError(f"SSH key '{identifier}' not found")
    
    # SSH Key resources
    @mcp.resource("ssh-keys://list")
    async def list_ssh_keys_resource() -> List[Dict[str, Any]]:
        """List all SSH keys in your Vultr account."""
        return await vultr_client.list_ssh_keys()
    
    @mcp.resource("ssh-keys://{ssh_key_id}")
    async def get_ssh_key_resource(ssh_key_id: str) -> Dict[str, Any]:
        """Get information about a specific SSH key.
        
        Args:
            ssh_key_id: The SSH key ID or name
        """
        actual_id = await get_ssh_key_id(ssh_key_id)
        return await vultr_client.get_ssh_key(actual_id)
    
    # SSH Key tools
    @mcp.tool
    async def list() -> List[Dict[str, Any]]:
        """List all SSH keys in your Vultr account.
        
        Returns:
            List of SSH key objects with details including:
            - id: SSH key ID
            - name: SSH key name
            - ssh_key: The public SSH key
            - date_created: Creation date
        """
        return await vultr_client.list_ssh_keys()
    
    @mcp.tool
    async def get(ssh_key_id: str) -> Dict[str, Any]:
        """Get information about a specific SSH key.
        
        Args:
            ssh_key_id: The SSH key ID or name (e.g., "my-laptop-key" or UUID)
            
        Returns:
            SSH key information including:
            - id: SSH key ID
            - name: SSH key name
            - ssh_key: The public SSH key
            - date_created: Creation date
        """
        actual_id = await get_ssh_key_id(ssh_key_id)
        return await vultr_client.get_ssh_key(actual_id)
    
    @mcp.tool
    async def create(name: str, ssh_key: str) -> Dict[str, Any]:
        """Create a new SSH key.
        
        Args:
            name: Name for the SSH key
            ssh_key: The SSH public key (e.g., "ssh-rsa AAAAB3NzaC1yc2...")
            
        Returns:
            Created SSH key information including:
            - id: SSH key ID
            - name: SSH key name
            - ssh_key: The public SSH key
            - date_created: Creation date
        """
        return await vultr_client.create_ssh_key(name, ssh_key)
    
    @mcp.tool
    async def update(ssh_key_id: str, name: Optional[str] = None, ssh_key: Optional[str] = None) -> Dict[str, Any]:
        """Update an existing SSH key.
        
        Args:
            ssh_key_id: The SSH key ID or name (e.g., "my-laptop-key" or UUID)
            name: New name for the SSH key (optional)
            ssh_key: New SSH public key (optional)
            
        Returns:
            Updated SSH key information
        """
        actual_id = await get_ssh_key_id(ssh_key_id)
        return await vultr_client.update_ssh_key(actual_id, name, ssh_key)
    
    @mcp.tool
    async def delete(ssh_key_id: str) -> Dict[str, str]:
        """Delete an SSH key.
        
        Args:
            ssh_key_id: The SSH key ID or name (e.g., "my-laptop-key" or UUID)
            
        Returns:
            Status message confirming deletion
        """
        actual_id = await get_ssh_key_id(ssh_key_id)
        await vultr_client.delete_ssh_key(actual_id)
        return {"status": "success", "message": f"SSH key {ssh_key_id} deleted successfully"}
    
    return mcp