"""
Test suite for MCP resource change notifications.

This module tests that FastMCP resource change notifications are properly
triggered when tools modify Vultr resources.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

from src.mcp_vultr.notification_manager import NotificationManager


class MockContext:
    """Mock FastMCP Context for testing notifications."""
    
    def __init__(self):
        self.notifications = []
        self.resource_list_changed_calls = 0
    
    async def send_resource_list_changed(self):
        """Mock implementation of FastMCP's send_resource_list_changed."""
        self.notifications.append("resource_list_changed")
        self.resource_list_changed_calls += 1


class TestNotificationManager:
    """Test cases for the NotificationManager."""

    @pytest.mark.asyncio
    async def test_notify_resource_change_basic(self):
        """Test basic resource change notification."""
        ctx = MockContext()
        
        await NotificationManager.notify_resource_change(
            ctx=ctx,
            operation="create_domain",
            domain="test.com"
        )
        
        assert ctx.resource_list_changed_calls == 1
        assert "resource_list_changed" in ctx.notifications

    @pytest.mark.asyncio 
    async def test_notify_dns_changes(self):
        """Test DNS-specific notification convenience method."""
        ctx = MockContext()
        
        await NotificationManager.notify_dns_changes(
            ctx=ctx,
            operation="create_record",
            domain="example.com",
            record_id="12345"
        )
        
        assert ctx.resource_list_changed_calls == 1

    @pytest.mark.asyncio
    async def test_notify_instance_changes(self):
        """Test instance-specific notification convenience method."""
        ctx = MockContext()
        
        await NotificationManager.notify_instance_changes(
            ctx=ctx,
            operation="create_instance",
            instance_id="instance-123"
        )
        
        assert ctx.resource_list_changed_calls == 1

    @pytest.mark.asyncio
    async def test_notify_storage_changes(self):
        """Test storage-specific notification convenience method."""
        ctx = MockContext()
        
        await NotificationManager.notify_storage_changes(
            ctx=ctx,
            operation="create_volume",
            volume_id="volume-456"
        )
        
        assert ctx.resource_list_changed_calls == 1

    @pytest.mark.asyncio
    async def test_notification_error_handling(self):
        """Test that notification errors don't break main operations."""
        # Create a context that throws an error
        ctx = Mock()
        ctx.send_resource_list_changed = AsyncMock(side_effect=Exception("Notification failed"))
        
        # Should not raise an exception
        await NotificationManager.notify_resource_change(
            ctx=ctx,
            operation="create_domain",
            domain="test.com"
        )
        
        # Verify the notification was attempted
        ctx.send_resource_list_changed.assert_called_once()

    def test_get_affected_resources(self):
        """Test resource URI mapping and formatting."""
        # Test DNS operation
        resources = NotificationManager.get_affected_resources(
            "create_domain",
            domain="example.com"
        )
        assert "domains://list" in resources
        
        # Test record operation with parameter substitution
        resources = NotificationManager.get_affected_resources(
            "create_record",
            domain="example.com"
        )
        assert "domains://example.com/records" in resources
        
        # Test operation with missing parameters
        resources = NotificationManager.get_affected_resources(
            "create_record"  # No domain parameter
        )
        # Should include the unformatted pattern
        assert "domains://{domain}/records" in resources

    def test_operation_resource_mapping(self):
        """Test that all expected operations are mapped to resources."""
        # Test some key operations
        assert "create_domain" in NotificationManager.OPERATION_RESOURCE_MAP
        assert "delete_domain" in NotificationManager.OPERATION_RESOURCE_MAP
        assert "create_record" in NotificationManager.OPERATION_RESOURCE_MAP
        assert "create_instance" in NotificationManager.OPERATION_RESOURCE_MAP
        assert "create_load_balancer" in NotificationManager.OPERATION_RESOURCE_MAP
        
        # Verify resource patterns for domain operations
        domain_resources = NotificationManager.OPERATION_RESOURCE_MAP["create_domain"]
        assert "domains://list" in domain_resources
        
        delete_domain_resources = NotificationManager.OPERATION_RESOURCE_MAP["delete_domain"]
        assert "domains://list" in delete_domain_resources
        assert "domains://{domain}/records" in delete_domain_resources


class TestDNSNotificationIntegration:
    """Integration tests for DNS tool notifications."""

    def test_dns_tool_signatures_updated(self):
        """Test that DNS tools have been updated with Context parameters."""
        # Import the DNS module to verify it compiles with our changes
        from src.mcp_vultr import dns
        
        # This test ensures our changes didn't break the module
        assert hasattr(dns, 'create_dns_mcp')

    @pytest.mark.asyncio
    async def test_mock_dns_operations_with_notifications(self):
        """Test mock DNS operations to verify notification flow."""
        
        # Mock Vultr client
        mock_vultr_client = Mock()
        mock_vultr_client.create_domain = AsyncMock(return_value={"status": "success"})
        mock_vultr_client.delete_domain = AsyncMock()
        mock_vultr_client.create_record = AsyncMock(return_value={"id": "record-123"})
        
        # Mock context
        ctx = MockContext()
        
        # Simulate the behavior our DNS tools should have
        async def mock_create_domain(domain: str, ip: str, ctx, dns_sec: str = "disabled"):
            result = await mock_vultr_client.create_domain(domain, ip, dns_sec)
            await NotificationManager.notify_dns_changes(
                ctx=ctx, operation="create_domain", domain=domain
            )
            return result
        
        async def mock_create_record(domain: str, record_type: str, name: str, data: str, ctx):
            result = await mock_vultr_client.create_record(domain, record_type, name, data)
            await NotificationManager.notify_dns_changes(
                ctx=ctx, operation="create_record", domain=domain
            )
            return result
        
        # Test domain creation
        await mock_create_domain("test.com", "1.2.3.4", ctx)
        assert ctx.resource_list_changed_calls == 1
        
        # Test record creation
        ctx.resource_list_changed_calls = 0  # Reset counter
        await mock_create_record("test.com", "A", "www", "1.2.3.4", ctx)
        assert ctx.resource_list_changed_calls == 1


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])