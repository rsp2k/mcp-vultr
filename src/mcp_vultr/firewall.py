"""
Vultr Firewall FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr firewall groups and rules.
"""

from typing import Optional, List, Dict, Any
from fastmcp import FastMCP


def create_firewall_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr firewall management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with firewall management tools
    """
    mcp = FastMCP(name="vultr-firewall")
    
    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        if len(s) == 36 and s.count('-') == 4:
            return True
        return False
    
    # Helper function to get firewall group ID from description
    async def get_firewall_group_id(identifier: str) -> str:
        """
        Get the firewall group ID from a description or UUID.
        
        Args:
            identifier: Firewall group description or UUID
            
        Returns:
            The firewall group ID (UUID)
            
        Raises:
            ValueError: If the firewall group is not found
        """
        # If it looks like a UUID, return it as-is
        if is_uuid_format(identifier):
            return identifier
            
        # Otherwise, search for it by description
        groups = await vultr_client.list_firewall_groups()
        for group in groups:
            if group.get("description") == identifier:
                return group["id"]
        
        raise ValueError(f"Firewall group '{identifier}' not found")
    
    # Firewall Group resources
    @mcp.resource("firewall://groups")
    async def list_groups_resource() -> List[Dict[str, Any]]:
        """List all firewall groups in your Vultr account."""
        return await vultr_client.list_firewall_groups()
    
    @mcp.resource("firewall://groups/{firewall_group_id}")
    async def get_group_resource(firewall_group_id: str) -> Dict[str, Any]:
        """Get information about a specific firewall group.
        
        Args:
            firewall_group_id: The firewall group ID or description
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        return await vultr_client.get_firewall_group(actual_id)
    
    @mcp.resource("firewall://groups/{firewall_group_id}/rules")
    async def list_rules_resource(firewall_group_id: str) -> List[Dict[str, Any]]:
        """List all rules in a firewall group.
        
        Args:
            firewall_group_id: The firewall group ID or description
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        return await vultr_client.list_firewall_rules(actual_id)
    
    @mcp.resource("firewall://groups/{firewall_group_id}/rules/{firewall_rule_id}")
    async def get_rule_resource(firewall_group_id: str, firewall_rule_id: str) -> Dict[str, Any]:
        """Get information about a specific firewall rule.
        
        Args:
            firewall_group_id: The firewall group ID or description
            firewall_rule_id: The firewall rule ID
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        return await vultr_client.get_firewall_rule(actual_id, firewall_rule_id)
    
    # Firewall Group tools
    @mcp.tool
    async def list_groups() -> List[Dict[str, Any]]:
        """List all firewall groups in your Vultr account.
        
        Returns:
            List of firewall group objects with details including:
            - id: Firewall group ID
            - description: Group description
            - date_created: Creation date
            - date_modified: Last modification date
            - instance_count: Number of instances using this group
            - rule_count: Number of rules in this group
            - max_rule_count: Maximum allowed rules
        """
        return await vultr_client.list_firewall_groups()
    
    @mcp.tool
    async def get_group(firewall_group_id: str) -> Dict[str, Any]:
        """Get information about a specific firewall group.
        
        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)
            
        Returns:
            Firewall group information
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        return await vultr_client.get_firewall_group(actual_id)
    
    @mcp.tool
    async def create_group(description: str) -> Dict[str, Any]:
        """Create a new firewall group.
        
        Args:
            description: Description for the firewall group
            
        Returns:
            Created firewall group information
        """
        return await vultr_client.create_firewall_group(description)
    
    @mcp.tool
    async def update_group(firewall_group_id: str, description: str) -> Dict[str, str]:
        """Update a firewall group description.
        
        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)
            description: New description for the firewall group
            
        Returns:
            Status message confirming update
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        await vultr_client.update_firewall_group(actual_id, description)
        return {"status": "success", "message": f"Firewall group {firewall_group_id} updated successfully"}
    
    @mcp.tool
    async def delete_group(firewall_group_id: str) -> Dict[str, str]:
        """Delete a firewall group.
        
        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)
            
        Returns:
            Status message confirming deletion
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        await vultr_client.delete_firewall_group(actual_id)
        return {"status": "success", "message": f"Firewall group {firewall_group_id} deleted successfully"}
    
    # Firewall Rule tools
    @mcp.tool
    async def list_rules(firewall_group_id: str) -> List[Dict[str, Any]]:
        """List all rules in a firewall group.
        
        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)
            
        Returns:
            List of firewall rules with details
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        return await vultr_client.list_firewall_rules(actual_id)
    
    @mcp.tool
    async def get_rule(firewall_group_id: str, firewall_rule_id: str) -> Dict[str, Any]:
        """Get information about a specific firewall rule.
        
        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)
            firewall_rule_id: The firewall rule ID
            
        Returns:
            Firewall rule information
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        return await vultr_client.get_firewall_rule(actual_id, firewall_rule_id)
    
    @mcp.tool
    async def create_rule(
        firewall_group_id: str,
        ip_type: str,
        protocol: str,
        subnet: str,
        subnet_size: int,
        port: Optional[str] = None,
        source: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new firewall rule.
        
        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)
            ip_type: IP type (v4 or v6)
            protocol: Protocol (tcp, udp, icmp, gre)
            subnet: IP subnet (use "0.0.0.0" for any IPv4, "::" for any IPv6)
            subnet_size: Subnet size (0-32 for IPv4, 0-128 for IPv6)
            port: Port or port range (e.g., "80" or "8000:8999") - required for tcp/udp
            source: Source type (e.g., "cloudflare") - optional
            notes: Notes for the rule - optional
            
        Returns:
            Created firewall rule information
            
        Examples:
            # Allow HTTP from anywhere
            create_rule(group_id, "v4", "tcp", "0.0.0.0", 0, port="80")
            
            # Allow SSH from specific subnet
            create_rule(group_id, "v4", "tcp", "192.168.1.0", 24, port="22", notes="Office network")
            
            # Allow ping from anywhere
            create_rule(group_id, "v4", "icmp", "0.0.0.0", 0)
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        return await vultr_client.create_firewall_rule(
            actual_id, ip_type, protocol, subnet, subnet_size, port, source, notes
        )
    
    @mcp.tool
    async def delete_rule(firewall_group_id: str, firewall_rule_id: str) -> Dict[str, str]:
        """Delete a firewall rule.
        
        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)
            firewall_rule_id: The firewall rule ID to delete
            
        Returns:
            Status message confirming deletion
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        await vultr_client.delete_firewall_rule(actual_id, firewall_rule_id)
        return {"status": "success", "message": f"Firewall rule {firewall_rule_id} deleted successfully"}
    
    @mcp.tool
    async def setup_web_server_rules(firewall_group_id: str, allow_ssh_from: str = "0.0.0.0/0") -> List[Dict[str, Any]]:
        """Set up common firewall rules for a web server.
        
        Args:
            firewall_group_id: The firewall group ID or description (e.g., "web-servers" or UUID)
            allow_ssh_from: IP subnet to allow SSH from (default: anywhere)
            
        Returns:
            List of created firewall rules
            
        Creates rules for:
        - HTTP (port 80) from anywhere
        - HTTPS (port 443) from anywhere
        - SSH (port 22) from specified subnet
        - ICMP (ping) from anywhere
        """
        actual_id = await get_firewall_group_id(firewall_group_id)
        rules = []
        
        # Parse SSH subnet
        ssh_parts = allow_ssh_from.split('/')
        ssh_subnet = ssh_parts[0]
        ssh_size = int(ssh_parts[1]) if len(ssh_parts) > 1 else 0
        
        # HTTP
        rules.append(await vultr_client.create_firewall_rule(
            actual_id, "v4", "tcp", "0.0.0.0", 0, port="80", notes="HTTP"
        ))
        
        # HTTPS
        rules.append(await vultr_client.create_firewall_rule(
            actual_id, "v4", "tcp", "0.0.0.0", 0, port="443", notes="HTTPS"
        ))
        
        # SSH
        rules.append(await vultr_client.create_firewall_rule(
            actual_id, "v4", "tcp", ssh_subnet, ssh_size, port="22", notes="SSH"
        ))
        
        # ICMP (ping)
        rules.append(await vultr_client.create_firewall_rule(
            actual_id, "v4", "icmp", "0.0.0.0", 0, notes="ICMP/Ping"
        ))
        
        return rules
    
    return mcp