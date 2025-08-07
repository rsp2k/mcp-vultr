"""
Vultr Load Balancer FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr Load Balancers.
"""

from typing import List, Dict, Any, Optional
from fastmcp import FastMCP


def create_load_balancer_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr Load Balancer management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with load balancer management tools
    """
    mcp = FastMCP(name="vultr-load-balancer")
    
    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        if len(s) == 36 and s.count('-') == 4:
            return True
        return False
    
    # Helper function to get load balancer ID from label or UUID
    async def get_load_balancer_id(identifier: str) -> str:
        """
        Get the load balancer ID from a label or UUID.
        
        Args:
            identifier: Load balancer label or UUID
            
        Returns:
            The load balancer ID (UUID)
            
        Raises:
            ValueError: If the load balancer is not found
        """
        # If it looks like a UUID, return it as-is
        if is_uuid_format(identifier):
            return identifier
            
        # Otherwise, search for it by label
        load_balancers = await vultr_client.list_load_balancers()
        for lb in load_balancers:
            if lb.get("label") == identifier:
                return lb["id"]
        
        raise ValueError(f"Load balancer '{identifier}' not found (searched by label)")
    
    # Load Balancer resources
    @mcp.resource("load_balancers://list")
    async def list_load_balancers_resource() -> List[Dict[str, Any]]:
        """List all load balancers in your Vultr account."""
        return await vultr_client.list_load_balancers()
    
    @mcp.resource("load_balancers://{load_balancer_id}")
    async def get_load_balancer_resource(load_balancer_id: str) -> Dict[str, Any]:
        """Get information about a specific load balancer.
        
        Args:
            load_balancer_id: The load balancer ID or label
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.get_load_balancer(actual_id)
    
    # Load Balancer tools
    @mcp.tool
    async def list() -> List[Dict[str, Any]]:
        """List all load balancers in your Vultr account.
        
        Returns:
            List of load balancer objects with details including:
            - id: Load balancer ID
            - label: Load balancer label
            - region: Region code
            - status: Load balancer status (active, pending, etc.)
            - ipv4: IPv4 address
            - ipv6: IPv6 address
            - date_created: Creation date
            - generic_info: Configuration details
            - health_check: Health check configuration
            - has_ssl: Whether SSL is configured
            - nodes: Number of backend nodes
            - forward_rules: Forwarding rules
            - firewall_rules: Firewall rules
            - instances: Attached instances
        """
        return await vultr_client.list_load_balancers()
    
    @mcp.tool
    async def get(load_balancer_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific load balancer.
        
        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            
        Returns:
            Detailed load balancer information
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.get_load_balancer(actual_id)
    
    @mcp.tool
    async def create(
        region: str,
        balancing_algorithm: str = "roundrobin",
        ssl_redirect: bool = False,
        http2: bool = False,
        http3: bool = False,
        proxy_protocol: bool = False,
        timeout: int = 600,
        label: Optional[str] = None,
        nodes: int = 1,
        health_check: Optional[Dict[str, Any]] = None,
        forwarding_rules: Optional[List[Dict[str, Any]]] = None,
        ssl: Optional[Dict[str, str]] = None,
        firewall_rules: Optional[List[Dict[str, Any]]] = None,
        auto_ssl: Optional[Dict[str, str]] = None,
        global_regions: Optional[List[str]] = None,
        vpc: Optional[str] = None,
        private_network: Optional[str] = None,
        sticky_session: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a new load balancer.
        
        Args:
            region: Region code (e.g., 'ewr', 'lax')
            balancing_algorithm: Algorithm to use ('roundrobin' or 'leastconn')
            ssl_redirect: Redirect HTTP traffic to HTTPS
            http2: Enable HTTP/2 support
            http3: Enable HTTP/3 support
            proxy_protocol: Enable proxy protocol
            timeout: Connection timeout in seconds
            label: Label for the load balancer
            nodes: Number of backend nodes
            health_check: Health check configuration dict with keys:
                - protocol: 'http', 'https', 'tcp'
                - port: Port number
                - path: Path for HTTP checks
                - check_interval: Check interval in seconds
                - response_timeout: Response timeout in seconds
                - unhealthy_threshold: Failures before marking unhealthy
                - healthy_threshold: Successes before marking healthy
            forwarding_rules: List of forwarding rule dicts with keys:
                - frontend_protocol: 'http', 'https', 'tcp'
                - frontend_port: Frontend port number
                - backend_protocol: 'http', 'https', 'tcp'
                - backend_port: Backend port number
            ssl: SSL configuration dict with keys:
                - private_key: Private key content
                - certificate: Certificate content
                - chain: Certificate chain content
            firewall_rules: List of firewall rule dicts with keys:
                - port: Port number
                - source: Source IP or CIDR
                - ip_type: 'v4' or 'v6'
            auto_ssl: Auto SSL configuration dict with keys:
                - domain_zone: Domain zone
                - domain_sub: Subdomain
            global_regions: List of global region codes
            vpc: VPC ID to attach to
            private_network: Private network ID (legacy)
            sticky_session: Sticky session configuration with cookie_name
            
        Returns:
            Created load balancer information
        """
        return await vultr_client.create_load_balancer(
            region=region,
            balancing_algorithm=balancing_algorithm,
            ssl_redirect=ssl_redirect,
            http2=http2,
            http3=http3,
            proxy_protocol=proxy_protocol,
            timeout=timeout,
            label=label,
            nodes=nodes,
            health_check=health_check,
            forwarding_rules=forwarding_rules,
            ssl=ssl,
            firewall_rules=firewall_rules,
            auto_ssl=auto_ssl,
            global_regions=global_regions,
            vpc=vpc,
            private_network=private_network,
            sticky_session=sticky_session
        )
    
    @mcp.tool
    async def update(
        load_balancer_id: str,
        ssl: Optional[Dict[str, str]] = None,
        sticky_session: Optional[Dict[str, str]] = None,
        forwarding_rules: Optional[List[Dict[str, Any]]] = None,
        health_check: Optional[Dict[str, Any]] = None,
        proxy_protocol: Optional[bool] = None,
        timeout: Optional[int] = None,
        ssl_redirect: Optional[bool] = None,
        http2: Optional[bool] = None,
        http3: Optional[bool] = None,
        nodes: Optional[int] = None,
        balancing_algorithm: Optional[str] = None,
        instances: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Update an existing load balancer.
        
        Args:
            load_balancer_id: The load balancer ID or label
            ssl: SSL configuration dict
            sticky_session: Sticky session configuration
            forwarding_rules: Updated forwarding rules
            health_check: Updated health check configuration
            proxy_protocol: Enable/disable proxy protocol
            timeout: Connection timeout in seconds
            ssl_redirect: Enable/disable SSL redirect
            http2: Enable/disable HTTP/2
            http3: Enable/disable HTTP/3
            nodes: Number of backend nodes
            balancing_algorithm: Balancing algorithm
            instances: List of instance IDs to attach
            
        Returns:
            Updated load balancer information
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.update_load_balancer(
            load_balancer_id=actual_id,
            ssl=ssl,
            sticky_session=sticky_session,
            forwarding_rules=forwarding_rules,
            health_check=health_check,
            proxy_protocol=proxy_protocol,
            timeout=timeout,
            ssl_redirect=ssl_redirect,
            http2=http2,
            http3=http3,
            nodes=nodes,
            balancing_algorithm=balancing_algorithm,
            instances=instances
        )
    
    @mcp.tool
    async def delete(load_balancer_id: str) -> Dict[str, str]:
        """Delete a load balancer.
        
        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            
        Returns:
            Status message confirming deletion
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        await vultr_client.delete_load_balancer(actual_id)
        return {"status": "success", "message": f"Load balancer {load_balancer_id} deleted successfully"}
    
    # SSL Management
    @mcp.tool
    async def delete_ssl(load_balancer_id: str) -> Dict[str, str]:
        """Delete SSL certificate from a load balancer.
        
        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            
        Returns:
            Status message confirming SSL deletion
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        await vultr_client.delete_load_balancer_ssl(actual_id)
        return {"status": "success", "message": f"SSL certificate deleted from load balancer {load_balancer_id}"}
    
    @mcp.tool
    async def disable_auto_ssl(load_balancer_id: str) -> Dict[str, str]:
        """Disable Auto SSL for a load balancer.
        
        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            
        Returns:
            Status message confirming Auto SSL disabled
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        await vultr_client.disable_load_balancer_auto_ssl(actual_id)
        return {"status": "success", "message": f"Auto SSL disabled for load balancer {load_balancer_id}"}
    
    # Forwarding Rules Management
    @mcp.resource("load_balancers://{load_balancer_id}/forwarding_rules")
    async def list_forwarding_rules_resource(load_balancer_id: str) -> List[Dict[str, Any]]:
        """List forwarding rules for a load balancer.
        
        Args:
            load_balancer_id: The load balancer ID or label
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.list_load_balancer_forwarding_rules(actual_id)
    
    @mcp.tool
    async def list_forwarding_rules(load_balancer_id: str) -> List[Dict[str, Any]]:
        """List forwarding rules for a load balancer.
        
        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            
        Returns:
            List of forwarding rules
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.list_load_balancer_forwarding_rules(actual_id)
    
    @mcp.tool
    async def create_forwarding_rule(
        load_balancer_id: str,
        frontend_protocol: str,
        frontend_port: int,
        backend_protocol: str,
        backend_port: int
    ) -> Dict[str, Any]:
        """Create a forwarding rule for a load balancer.
        
        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            frontend_protocol: Frontend protocol ('http', 'https', 'tcp')
            frontend_port: Frontend port number
            backend_protocol: Backend protocol ('http', 'https', 'tcp')
            backend_port: Backend port number
            
        Returns:
            Created forwarding rule information
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.create_load_balancer_forwarding_rule(
            load_balancer_id=actual_id,
            frontend_protocol=frontend_protocol,
            frontend_port=frontend_port,
            backend_protocol=backend_protocol,
            backend_port=backend_port
        )
    
    @mcp.tool
    async def get_forwarding_rule(load_balancer_id: str, forwarding_rule_id: str) -> Dict[str, Any]:
        """Get details of a specific forwarding rule.
        
        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            forwarding_rule_id: The forwarding rule ID
            
        Returns:
            Forwarding rule details
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.get_load_balancer_forwarding_rule(actual_id, forwarding_rule_id)
    
    @mcp.tool
    async def delete_forwarding_rule(load_balancer_id: str, forwarding_rule_id: str) -> Dict[str, str]:
        """Delete a forwarding rule from a load balancer.
        
        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            forwarding_rule_id: The forwarding rule ID
            
        Returns:
            Status message confirming deletion
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        await vultr_client.delete_load_balancer_forwarding_rule(actual_id, forwarding_rule_id)
        return {"status": "success", "message": f"Forwarding rule {forwarding_rule_id} deleted successfully"}
    
    # Firewall Rules Management
    @mcp.resource("load_balancers://{load_balancer_id}/firewall_rules")
    async def list_firewall_rules_resource(load_balancer_id: str) -> List[Dict[str, Any]]:
        """List firewall rules for a load balancer.
        
        Args:
            load_balancer_id: The load balancer ID or label
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.list_load_balancer_firewall_rules(actual_id)
    
    @mcp.tool
    async def list_firewall_rules(load_balancer_id: str) -> List[Dict[str, Any]]:
        """List firewall rules for a load balancer.
        
        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            
        Returns:
            List of firewall rules
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.list_load_balancer_firewall_rules(actual_id)
    
    @mcp.tool
    async def get_firewall_rule(load_balancer_id: str, firewall_rule_id: str) -> Dict[str, Any]:
        """Get details of a specific firewall rule.
        
        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            firewall_rule_id: The firewall rule ID
            
        Returns:
            Firewall rule details
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        return await vultr_client.get_load_balancer_firewall_rule(actual_id, firewall_rule_id)
    
    # Helper tools for load balancer configuration
    @mcp.tool
    async def configure_basic_web_lb(
        region: str,
        label: str,
        backend_instances: List[str],
        enable_ssl: bool = True,
        ssl_redirect: bool = True,
        domain_zone: Optional[str] = None,
        domain_sub: Optional[str] = None
    ) -> Dict[str, Any]:
        """Configure a basic web load balancer with standard HTTP/HTTPS rules.
        
        Args:
            region: Region code (e.g., 'ewr', 'lax')
            label: Label for the load balancer
            backend_instances: List of instance IDs to attach
            enable_ssl: Enable SSL/Auto SSL
            ssl_redirect: Redirect HTTP to HTTPS
            domain_zone: Domain zone for Auto SSL
            domain_sub: Subdomain for Auto SSL
            
        Returns:
            Created and configured load balancer information
        """
        # Basic forwarding rules for web traffic
        forwarding_rules = [
            {
                "frontend_protocol": "http",
                "frontend_port": 80,
                "backend_protocol": "http",
                "backend_port": 80
            }
        ]
        
        if enable_ssl:
            forwarding_rules.append({
                "frontend_protocol": "https",
                "frontend_port": 443,
                "backend_protocol": "http",
                "backend_port": 80
            })
        
        # Basic health check configuration
        health_check = {
            "protocol": "http",
            "port": 80,
            "path": "/",
            "check_interval": 15,
            "response_timeout": 5,
            "unhealthy_threshold": 3,
            "healthy_threshold": 2
        }
        
        # Basic firewall rules (allow HTTP/HTTPS from anywhere)
        firewall_rules = [
            {
                "port": 80,
                "source": "0.0.0.0/0",
                "ip_type": "v4"
            }
        ]
        
        if enable_ssl:
            firewall_rules.append({
                "port": 443,
                "source": "0.0.0.0/0",
                "ip_type": "v4"
            })
        
        # Auto SSL configuration if domain provided
        auto_ssl = None
        if enable_ssl and domain_zone:
            auto_ssl = {
                "domain_zone": domain_zone,
                "domain_sub": domain_sub or "www"
            }
        
        # Create load balancer
        load_balancer = await vultr_client.create_load_balancer(
            region=region,
            label=label,
            balancing_algorithm="roundrobin",
            ssl_redirect=ssl_redirect,
            forwarding_rules=forwarding_rules,
            health_check=health_check,
            firewall_rules=firewall_rules,
            auto_ssl=auto_ssl,
            instances=backend_instances
        )
        
        return {
            "load_balancer": load_balancer,
            "configuration": "basic_web",
            "message": f"Basic web load balancer '{label}' configured successfully"
        }
    
    @mcp.tool
    async def get_health_status(load_balancer_id: str) -> Dict[str, Any]:
        """Get health status and monitoring information for a load balancer.
        
        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            
        Returns:
            Health status and configuration information
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        lb_details = await vultr_client.get_load_balancer(actual_id)
        
        # Extract health-related information
        health_info = {
            "id": lb_details.get("id"),
            "label": lb_details.get("label"),
            "status": lb_details.get("status"),
            "health_check": lb_details.get("health_check", {}),
            "instances": lb_details.get("instances", []),
            "forwarding_rules": lb_details.get("forward_rules", []),
            "has_ssl": lb_details.get("has_ssl", False),
            "ipv4": lb_details.get("ipv4"),
            "ipv6": lb_details.get("ipv6"),
            "region": lb_details.get("region")
        }
        
        return health_info
    
    @mcp.tool
    async def get_configuration_summary(load_balancer_id: str) -> Dict[str, Any]:
        """Get a comprehensive configuration summary for a load balancer.
        
        Args:
            load_balancer_id: The load balancer ID or label (e.g., "web-lb", "api-load-balancer", or UUID)
            
        Returns:
            Detailed configuration summary
        """
        actual_id = await get_load_balancer_id(load_balancer_id)
        lb_details = await vultr_client.get_load_balancer(actual_id)
        
        generic_info = lb_details.get("generic_info", {})
        
        summary = {
            "basic_info": {
                "id": lb_details.get("id"),
                "label": lb_details.get("label"),
                "status": lb_details.get("status"),
                "region": lb_details.get("region"),
                "date_created": lb_details.get("date_created")
            },
            "network": {
                "ipv4": lb_details.get("ipv4"),
                "ipv6": lb_details.get("ipv6"),
                "vpc": generic_info.get("vpc"),
                "private_network": generic_info.get("private_network")
            },
            "configuration": {
                "balancing_algorithm": generic_info.get("balancing_algorithm"),
                "ssl_redirect": generic_info.get("ssl_redirect"),
                "proxy_protocol": generic_info.get("proxy_protocol"),
                "timeout": generic_info.get("timeout"),
                "sticky_sessions": generic_info.get("sticky_sessions")
            },
            "ssl": {
                "has_ssl": lb_details.get("has_ssl", False)
            },
            "health_check": lb_details.get("health_check", {}),
            "forwarding_rules": lb_details.get("forward_rules", []),
            "firewall_rules": lb_details.get("firewall_rules", []),
            "backend": {
                "nodes": lb_details.get("nodes"),
                "instances": lb_details.get("instances", [])
            }
        }
        
        return summary
    
    return mcp