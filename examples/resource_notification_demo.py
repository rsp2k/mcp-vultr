#!/usr/bin/env python3
"""
Demonstration of MCP Resource Change Notifications.

This script demonstrates how the Vultr MCP server now sends resource change
notifications to clients when tools modify resources.

Usage:
    python examples/resource_notification_demo.py
"""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

# Simulate the MCP notification flow
class MockMCPClient:
    """Mock MCP client that subscribes to resource changes."""
    
    def __init__(self, name: str):
        self.name = name
        self.subscribed_resources: List[str] = []
        self.received_notifications: List[Dict[str, Any]] = []
    
    def subscribe_to_resource(self, resource_uri: str):
        """Subscribe to resource change notifications."""
        self.subscribed_resources.append(resource_uri)
        print(f"📡 {self.name} subscribed to: {resource_uri}")
    
    def receive_notification(self, notification_type: str, resource_uri: str):
        """Receive a resource change notification."""
        self.received_notifications.append({
            "type": notification_type,
            "resource": resource_uri,
            "timestamp": asyncio.get_event_loop().time()
        })
        print(f"🔔 {self.name} received notification: {notification_type} for {resource_uri}")


class MockFastMCPContext:
    """Mock FastMCP Context that sends notifications to subscribed clients."""
    
    def __init__(self, clients: List[MockMCPClient]):
        self.clients = clients
        self.notification_count = 0
    
    async def send_resource_list_changed(self):
        """Send resource list changed notification to all subscribed clients."""
        self.notification_count += 1
        
        # In a real FastMCP setup, this would send MCP protocol messages
        # Here we simulate the notification delivery
        for client in self.clients:
            # Notify all subscribed clients about resource changes
            for resource_uri in client.subscribed_resources:
                client.receive_notification("resources/list_changed", resource_uri)
        
        print(f"⚡ FastMCP sent resource_list_changed notification (#{self.notification_count})")


class MockVultrClient:
    """Mock Vultr API client for demonstration."""
    
    def __init__(self):
        self.domains: List[Dict[str, Any]] = []
        self.records: Dict[str, List[Dict[str, Any]]] = {}
    
    async def create_domain(self, domain: str, ip: str, dns_sec: str = "disabled"):
        """Mock domain creation."""
        domain_data = {
            "domain": domain,
            "ip": ip,
            "dns_sec": dns_sec,
            "date_created": "2024-01-01",
        }
        self.domains.append(domain_data)
        self.records[domain] = []
        print(f"🌐 Created domain: {domain} -> {ip}")
        return domain_data
    
    async def create_record(self, domain: str, record_type: str, name: str, data: str, ttl: int = 300, priority: int = None):
        """Mock DNS record creation."""
        record_data = {
            "id": f"record-{len(self.records.get(domain, []))}",
            "type": record_type,
            "name": name,
            "data": data,
            "ttl": ttl,
            "priority": priority
        }
        
        if domain not in self.records:
            self.records[domain] = []
        
        self.records[domain].append(record_data)
        print(f"📝 Created {record_type} record: {name}.{domain} -> {data}")
        return record_data
    
    async def delete_domain(self, domain: str):
        """Mock domain deletion."""
        self.domains = [d for d in self.domains if d["domain"] != domain]
        if domain in self.records:
            del self.records[domain]
        print(f"🗑️ Deleted domain: {domain}")


# Import our notification manager
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.mcp_vultr.notification_manager import NotificationManager


async def demonstrate_dns_operations_with_notifications():
    """Demonstrate DNS operations with resource change notifications."""
    
    print("🚀 Starting Resource Change Notification Demonstration")
    print("=" * 60)
    
    # Set up mock clients
    claude_desktop = MockMCPClient("Claude Desktop")
    api_client = MockMCPClient("API Client")
    
    # Clients subscribe to different resources
    claude_desktop.subscribe_to_resource("domains://list")
    claude_desktop.subscribe_to_resource("domains://example.com/records")
    
    api_client.subscribe_to_resource("domains://list")
    
    # Set up mock context and Vultr client
    ctx = MockFastMCPContext([claude_desktop, api_client])
    vultr_client = MockVultrClient()
    
    print("\\n🔧 Mock DNS Tools with Notifications")
    print("-" * 40)
    
    # Mock DNS tools that use our notification system
    async def create_domain_with_notifications(domain: str, ip: str, dns_sec: str = "disabled"):
        """Mock create_domain tool with notifications."""
        result = await vultr_client.create_domain(domain, ip, dns_sec)
        await NotificationManager.notify_dns_changes(
            ctx=ctx, operation="create_domain", domain=domain, debug_enabled=True
        )
        return result
    
    async def create_record_with_notifications(domain: str, record_type: str, name: str, data: str):
        """Mock create_record tool with notifications."""
        result = await vultr_client.create_record(domain, record_type, name, data)
        await NotificationManager.notify_dns_changes(
            ctx=ctx, operation="create_record", domain=domain, debug_enabled=True
        )
        return result
    
    async def delete_domain_with_notifications(domain: str):
        """Mock delete_domain tool with notifications."""
        await vultr_client.delete_domain(domain)
        await NotificationManager.notify_dns_changes(
            ctx=ctx, operation="delete_domain", domain=domain, debug_enabled=True
        )
        return {"status": "success", "message": f"Domain {domain} deleted"}
    
    print("\\n📋 Executing DNS Operations")
    print("-" * 40)
    
    # Simulate user operations
    print("\\n1️⃣ User creates a domain:")
    await create_domain_with_notifications("example.com", "1.2.3.4")
    
    print("\\n2️⃣ User adds DNS records:")
    await create_record_with_notifications("example.com", "A", "www", "1.2.3.4")
    await create_record_with_notifications("example.com", "MX", "@", "mail.example.com")
    
    print("\\n3️⃣ User creates another domain:")
    await create_domain_with_notifications("test.org", "5.6.7.8")
    
    print("\\n4️⃣ User deletes a domain:")
    await delete_domain_with_notifications("test.org")
    
    print("\\n📊 Notification Summary")
    print("-" * 40)
    print(f"Total FastMCP notifications sent: {ctx.notification_count}")
    
    print("\\n📱 Claude Desktop received:")
    for i, notification in enumerate(claude_desktop.received_notifications, 1):
        print(f"  {i}. {notification['type']} for {notification['resource']}")
    
    print("\\n🖥️ API Client received:")
    for i, notification in enumerate(api_client.received_notifications, 1):
        print(f"  {i}. {notification['type']} for {notification['resource']}")
    
    print("\\n✨ Benefits of Resource Change Notifications:")
    print("-" * 50)
    print("• Claude Desktop UI updates automatically when domains/records change")
    print("• API clients stay synchronized with server state")
    print("• No need for manual refresh or polling")
    print("• Real-time collaboration between multiple MCP clients")
    print("• Better user experience with immediate feedback")
    
    print("\\n🎯 Implementation Impact:")
    print("-" * 50)
    print("• DNS module now has Context parameters on all modify operations")
    print("• NotificationManager provides systematic notification patterns")
    print("• FastMCP handles the MCP protocol details automatically")
    print("• Pattern can be systematically applied to all 16+ modules")


async def demonstrate_notification_architecture():
    """Show the overall notification architecture."""
    
    print("\\n🏗️ MCP Resource Change Notification Architecture")
    print("=" * 60)
    
    print("""
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Claude Code   │    │   API Client    │    │  Other Client   │
│     (MCP)       │    │     (MCP)       │    │     (MCP)       │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ resources/subscribe  │                      │
          └──────────────────────┼──────────────────────┘
                                 │
          ┌─────────────────────────────────────────┐
          │            FastMCP Server               │
          │  ┌─────────────────────────────────┐    │
          │  │       Vultr MCP Tools           │    │
          │  │  • create_domain(ctx: Context)  │    │
          │  │  • create_record(ctx: Context)  │    │
          │  │  • delete_domain(ctx: Context)  │    │
          │  │  • ...                          │    │
          │  └─────────────────────────────────┘    │
          │              │                          │
          │              ▼                          │
          │  ┌─────────────────────────────────┐    │
          │  │    NotificationManager          │    │
          │  │  • notify_dns_changes()         │    │
          │  │  • notify_instance_changes()    │    │
          │  │  • OPERATION_RESOURCE_MAP       │    │
          │  └─────────────────────────────────┘    │
          │              │                          │
          │              ▼                          │
          │  ┌─────────────────────────────────┐    │
          │  │   ctx.send_resource_list_changed│    │
          │  └─────────────────────────────────┘    │
          └─────────────────────────────────────────┘
                                 │
          ┌─────────────────────────────────────────┐
          │     MCP Protocol Notifications          │
          │  notifications/resources/list_changed   │
          └─────────────────────────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   UI Updates    │    │   Cache Refresh │    │  State Sync     │
│   Automatically │    │   Automatically │    │  Automatically  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
""")
    
    print("Key Components:")
    print("• Tools accept Context parameter for notification capability")
    print("• NotificationManager maps operations to affected resources")
    print("• FastMCP sends MCP protocol notifications to subscribed clients")
    print("• Clients receive real-time updates and refresh their views")


def show_implementation_rollout_plan():
    """Show the systematic rollout plan for all modules."""
    
    print("\\n📋 Systematic Implementation Rollout Plan")
    print("=" * 60)
    
    modules_priority = [
        ("dns.py", "✅ COMPLETED", "High - Most commonly used"),
        ("instances.py", "⏳ Next", "High - Core compute resources"),
        ("ssh_keys.py", "⏳ Next", "High - Used with instances"),
        ("firewall.py", "⏳ Next", "High - Security-related"),
        ("load_balancer.py", "⏳ Next", "Medium - Infrastructure"),
        ("kubernetes.py", "⏳ Next", "Medium - Container orchestration"),
        ("block_storage.py", "⏳ Next", "Medium - Storage resources"),
        ("container_registry.py", "⏳ Next", "Medium - Container images"),
        ("object_storage.py", "⏳ Next", "Medium - Object storage"),
        ("managed_databases.py", "⏳ Next", "Medium - Database services"),
        ("vpcs.py", "⏳ Next", "Medium - Networking"),
        ("reserved_ips.py", "⏳ Next", "Medium - IP management"),
        ("users.py", "⏳ Next", "Low - Admin functions"),
        ("subaccount.py", "⏳ Next", "Low - Account management"),
        ("snapshots.py", "⏳ Next", "Low - Backup operations"),
        ("backups.py", "⏳ Next", "Low - Backup operations"),
    ]
    
    print("\\nModule Implementation Priority:")
    for module, status, priority in modules_priority:
        print(f"  {status} {module:<25} - {priority}")
    
    print("\\n🔧 Implementation Pattern for Each Module:")
    print("""
1. Add imports:
   from fastmcp import Context
   from .notification_manager import NotificationManager

2. Update tool signatures:
   @mcp.tool
   async def create_resource(param1: str, ctx: Context, param2: str = "default"):

3. Add notifications after operations:
   result = await vultr_client.create_resource(...)
   await NotificationManager.notify_resource_change(
       ctx=ctx, operation="create_resource", resource_id=result["id"]
   )
   return result

4. Test with mock context to verify notifications
""")
    
    print("\\n📈 Expected Benefits After Full Rollout:")
    print("• All 16 modules support real-time resource notifications")
    print("• Claude Desktop provides seamless user experience")
    print("• API clients stay synchronized automatically")
    print("• Consistent notification patterns across all resources")
    print("• Better developer experience with reactive UI updates")


async def main():
    """Main demonstration function."""
    await demonstrate_dns_operations_with_notifications()
    await demonstrate_notification_architecture()
    show_implementation_rollout_plan()
    
    print("\\n🎉 Demonstration Complete!")
    print("\\n💡 Next Steps:")
    print("1. Systematically apply this pattern to other modules")
    print("2. Test with real Claude Desktop client")
    print("3. Monitor notification performance and optimize if needed")
    print("4. Document the pattern for other contributors")


if __name__ == "__main__":
    asyncio.run(main())