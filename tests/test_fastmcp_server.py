"""Tests for the FastMCP server module."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import FastMCP

from mcp_vultr.dns import create_dns_mcp
from mcp_vultr.fastmcp_server import create_vultr_mcp_server, run_server
from mcp_vultr.server import VultrAPIError, VultrAuthError, VultrRateLimitError


@pytest.mark.unit
class TestFastMCPServer:
    """Test FastMCP server creation and configuration."""

    def test_create_server_with_api_key(self):
        """Test creating server with provided API key."""
        with patch("mcp_vultr.fastmcp_server.VultrDNSServer") as mock_vultr:
            with patch("mcp_vultr.fastmcp_server.FastMCP") as mock_fastmcp_class:
                # Create a mock server instance
                mock_server = MagicMock()
                mock_server.name = "mcp-vultr"
                mock_fastmcp_class.return_value = mock_server
                
                # Mock all create_*_mcp functions to avoid import errors
                module_patches = []
                for module in ["dns", "instances", "ssh_keys", "backups", "firewall",
                             "snapshots", "regions", "reserved_ips", "container_registry",
                             "block_storage", "vpcs", "iso", "os", "plans", "startup_scripts",
                             "billing", "bare_metal", "cdn", "kubernetes", "load_balancer",
                             "managed_databases", "marketplace", "object_storage",
                             "serverless_inference", "storage_gateways", "subaccount", "users"]:
                    p = patch(f"mcp_vultr.fastmcp_server.create_{module}_mcp", return_value=MagicMock())
                    module_patches.append(p)
                    p.__enter__()
                
                try:
                    # Create server
                    server = create_vultr_mcp_server("test-api-key")
                    
                    # Verify server created
                    assert server == mock_server
                    
                    # Verify FastMCP initialized with correct name
                    mock_fastmcp_class.assert_called_once_with(name="mcp-vultr")
                    
                    # Verify Vultr client initialized with API key
                    mock_vultr.assert_called_once_with("test-api-key")
                    
                    # Verify mount was called for expected modules
                    assert mock_server.mount.call_count >= 2  # At least DNS and instances
                    
                finally:
                    for p in module_patches:
                        p.__exit__(None, None, None)

    def test_create_server_from_env_var(self):
        """Test creating server with API key from environment variable."""
        with patch.dict(os.environ, {"VULTR_API_KEY": "env-api-key"}):
            with patch("mcp_vultr.fastmcp_server.VultrDNSServer") as mock_vultr:
                with patch("mcp_vultr.fastmcp_server.FastMCP") as mock_fastmcp_class:
                    mock_server = MagicMock()
                    mock_fastmcp_class.return_value = mock_server
                    
                    # Mock all create_*_mcp functions
                    module_patches = []
                    for module in ["dns", "instances", "ssh_keys", "backups", "firewall",
                                 "snapshots", "regions", "reserved_ips", "container_registry",
                                 "block_storage", "vpcs", "iso", "os", "plans", "startup_scripts",
                                 "billing", "bare_metal", "cdn", "kubernetes", "load_balancer",
                                 "managed_databases", "marketplace", "object_storage",
                                 "serverless_inference", "storage_gateways", "subaccount", "users"]:
                        p = patch(f"mcp_vultr.fastmcp_server.create_{module}_mcp", return_value=MagicMock())
                        module_patches.append(p)
                        p.__enter__()
                    
                    try:
                        # Create server without explicit API key
                        server = create_vultr_mcp_server()
                        
                        # Verify server created
                        assert server == mock_server
                        
                        # Verify Vultr client initialized with env API key
                        mock_vultr.assert_called_once_with("env-api-key")
                    finally:
                        for p in module_patches:
                            p.__exit__(None, None, None)

    def test_create_server_no_api_key_raises_error(self):
        """Test that creating server without API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                create_vultr_mcp_server()
            
            assert "VULTR_API_KEY must be provided" in str(exc_info.value)

    @patch("mcp_vultr.fastmcp_server.create_vultr_mcp_server")
    def test_run_server_with_api_key(self, mock_create):
        """Test run_server function with API key."""
        mock_mcp = MagicMock()
        mock_create.return_value = mock_mcp
        
        run_server("test-api-key")
        
        mock_create.assert_called_once_with("test-api-key")
        mock_mcp.run.assert_called_once()

    @patch("mcp_vultr.fastmcp_server.create_vultr_mcp_server")
    def test_run_server_without_api_key(self, mock_create):
        """Test run_server function without API key."""
        mock_mcp = MagicMock()
        mock_create.return_value = mock_mcp
        
        run_server()
        
        mock_create.assert_called_once_with(None)
        mock_mcp.run.assert_called_once()

    def test_all_modules_mounted(self):
        """Test that all expected modules are mounted to the server."""
        expected_modules = [
            "dns", "instances", "ssh_keys", "backups", "firewall",
            "snapshots", "regions", "reserved_ips", "container_registry",
            "block_storage", "vpcs", "iso", "os", "plans", "startup_scripts",
            "billing", "bare_metal", "cdn", "kubernetes", "load_balancer",
            "managed_databases", "marketplace", "object_storage",
            "serverless_inference", "storage_gateways", "subaccount", "users"
        ]
        
        with patch("mcp_vultr.fastmcp_server.VultrDNSServer"):
            with patch("mcp_vultr.fastmcp_server.FastMCP") as mock_fastmcp_class:
                mock_server = MagicMock()
                mock_fastmcp_class.return_value = mock_server
                
                # Patch all create_*_mcp functions
                patches = {}
                for module in expected_modules:
                    patch_name = f"mcp_vultr.fastmcp_server.create_{module}_mcp"
                    patches[module] = patch(patch_name, return_value=MagicMock())
                    patches[module].__enter__()
                
                try:
                    server = create_vultr_mcp_server("test-api-key")
                    
                    # Verify server created
                    assert server == mock_server
                    
                    # Verify mount was called for each module
                    assert mock_server.mount.call_count == len(expected_modules)
                    
                    # Verify each module was mounted with correct prefix
                    mount_calls = mock_server.mount.call_args_list
                    mounted_prefixes = [call[0][0] for call in mount_calls]
                    for module in expected_modules:
                        assert module in mounted_prefixes
                        
                finally:
                    # Clean up patches
                    for p in patches.values():
                        p.__exit__(None, None, None)

    def test_server_name_is_correct(self):
        """Test that the server name is set correctly."""
        with patch("mcp_vultr.fastmcp_server.VultrDNSServer"):
            with patch("mcp_vultr.fastmcp_server.FastMCP") as mock_fastmcp_class:
                mock_server = MagicMock()
                mock_server.name = "mcp-vultr"
                mock_fastmcp_class.return_value = mock_server
                
                # Mock all modules to avoid import errors
                module_patches = []
                for module in ["dns", "instances", "ssh_keys", "backups", "firewall",
                             "snapshots", "regions", "reserved_ips", "container_registry",
                             "block_storage", "vpcs", "iso", "os", "plans", "startup_scripts",
                             "billing", "bare_metal", "cdn", "kubernetes", "load_balancer",
                             "managed_databases", "marketplace", "object_storage",
                             "serverless_inference", "storage_gateways", "subaccount", "users"]:
                    p = patch(f"mcp_vultr.fastmcp_server.create_{module}_mcp", return_value=MagicMock())
                    module_patches.append(p)
                    p.__enter__()
                
                try:
                    server = create_vultr_mcp_server("test-api-key")
                    
                    # Verify FastMCP was called with correct name
                    mock_fastmcp_class.assert_called_once_with(name="mcp-vultr")
                    assert server.name == "mcp-vultr"
                finally:
                    for p in module_patches:
                        p.__exit__(None, None, None)


@pytest.mark.mcp
class TestFastMCPDNSTools:
    """Test critical FastMCP DNS tools that were missing comprehensive coverage."""

    @pytest.fixture
    def mock_vultr_client(self):
        """Create a mock VultrDNSServer client."""
        client = AsyncMock()
        client.get_record = AsyncMock()
        client.update_record = AsyncMock()
        client.delete_record = AsyncMock()
        return client

    @pytest.fixture
    async def dns_mcp_server(self, mock_vultr_client):
        """Create a DNS FastMCP server with mocked client."""
        return create_dns_mcp(mock_vultr_client)

    @pytest.fixture 
    async def dns_tools(self, dns_mcp_server):
        """Get DNS tools from the FastMCP server."""
        return await dns_mcp_server.get_tools()

    @pytest.mark.asyncio
    async def test_get_record_tool_success(self, dns_tools, mock_vultr_client):
        """Test get_record tool with successful response."""
        # Mock successful response
        expected_record = {
            "id": "record-123",
            "type": "A",
            "name": "www",
            "data": "192.168.1.100",
            "ttl": 300,
            "priority": None
        }
        mock_vultr_client.get_record.return_value = expected_record

        # Call the tool function directly
        get_record_tool = dns_tools["get_record"]
        result = await get_record_tool.fn(
            domain="example.com",
            record_id="record-123"
        )

        # Verify the result
        assert result == expected_record
        mock_vultr_client.get_record.assert_called_once_with("example.com", "record-123")

    @pytest.mark.asyncio
    async def test_get_record_tool_with_api_error(self, dns_tools, mock_vultr_client):
        """Test get_record tool when API returns an error."""
        # Mock API error
        mock_vultr_client.get_record.side_effect = VultrAPIError(404, "Record not found")

        # Call the tool and expect it to propagate the error
        with pytest.raises(VultrAPIError) as exc_info:
            get_record_tool = dns_tools["get_record"]
            await get_record_tool.fn(
                domain="example.com",
                record_id="non-existent-record"
            )

        assert "Record not found" in str(exc_info.value)
        assert exc_info.value.status_code == 404
        mock_vultr_client.get_record.assert_called_once_with("example.com", "non-existent-record")

    @pytest.mark.asyncio
    async def test_get_record_tool_with_auth_error(self, dns_tools, mock_vultr_client):
        """Test get_record tool when authentication fails."""
        # Mock authentication error
        mock_vultr_client.get_record.side_effect = VultrAuthError(401, "Invalid API key")

        # Call the tool and expect it to propagate the error
        with pytest.raises(VultrAuthError) as exc_info:
            get_record_tool = dns_tools["get_record"]
            await get_record_tool.fn(
                domain="example.com",
                record_id="record-123"
            )

        assert "Invalid API key" in str(exc_info.value)
        assert exc_info.value.status_code == 401
        mock_vultr_client.get_record.assert_called_once_with("example.com", "record-123")

    @pytest.mark.asyncio
    async def test_update_record_tool_success_all_fields(self, dns_tools, mock_vultr_client):
        """Test update_record tool with all fields updated successfully."""
        # Mock successful response
        expected_record = {
            "id": "record-123",
            "type": "A",
            "name": "api",
            "data": "192.168.2.200",
            "ttl": 600,
            "priority": None
        }
        mock_vultr_client.update_record.return_value = expected_record

        # Call the tool with all parameters
        update_record_tool = dns_tools["update_record"]
        result = await update_record_tool.fn(
            domain="example.com",
            record_id="record-123",
            name="api",
            data="192.168.2.200",
            ttl=600,
            priority=None
        )

        # Verify the result
        assert result == expected_record
        mock_vultr_client.update_record.assert_called_once_with(
            "example.com", "record-123", "api", "192.168.2.200", 600, None
        )

    @pytest.mark.asyncio
    async def test_update_record_tool_partial_update(self, dns_tools, mock_vultr_client):
        """Test update_record tool with only some fields updated."""
        # Mock successful response
        expected_record = {
            "id": "record-123",
            "type": "A",
            "name": "www",
            "data": "192.168.3.300", 
            "ttl": 300,
            "priority": None
        }
        mock_vultr_client.update_record.return_value = expected_record

        # Call the tool with only data parameter
        update_record_tool = dns_tools["update_record"]
        result = await update_record_tool.fn(
            domain="example.com",
            record_id="record-123",
            data="192.168.3.300"
        )

        # Verify the result
        assert result == expected_record
        mock_vultr_client.update_record.assert_called_once_with(
            "example.com", "record-123", None, "192.168.3.300", None, None
        )

    @pytest.mark.asyncio
    async def test_update_record_tool_mx_record_with_priority(self, dns_tools, mock_vultr_client):
        """Test update_record tool for MX record with priority."""
        # Mock successful response
        expected_record = {
            "id": "record-456",
            "type": "MX",
            "name": "@",
            "data": "mail.example.com",
            "ttl": 3600,
            "priority": 5
        }
        mock_vultr_client.update_record.return_value = expected_record

        # Call the tool with priority for MX record
        update_record_tool = dns_tools["update_record"]
        result = await update_record_tool.fn(
            domain="example.com",
            record_id="record-456",
            data="mail.example.com",
            ttl=3600,
            priority=5
        )

        # Verify the result
        assert result == expected_record
        mock_vultr_client.update_record.assert_called_once_with(
            "example.com", "record-456", None, "mail.example.com", 3600, 5
        )

    @pytest.mark.asyncio
    async def test_update_record_tool_with_rate_limit_error(self, dns_tools, mock_vultr_client):
        """Test update_record tool when rate limit is exceeded."""
        # Mock rate limit error
        mock_vultr_client.update_record.side_effect = VultrRateLimitError(429, "Rate limit exceeded")

        # Call the tool and expect it to propagate the error
        with pytest.raises(VultrRateLimitError) as exc_info:
            update_record_tool = dns_tools["update_record"]
            await update_record_tool.fn(
                domain="example.com",
                record_id="record-123",
                data="192.168.1.100"
            )

        assert "Rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.status_code == 429
        mock_vultr_client.update_record.assert_called_once_with(
            "example.com", "record-123", None, "192.168.1.100", None, None
        )

    @pytest.mark.asyncio
    async def test_update_record_tool_record_not_found(self, dns_tools, mock_vultr_client):
        """Test update_record tool when record doesn't exist."""
        # Mock record not found error
        mock_vultr_client.update_record.side_effect = VultrAPIError(404, "Record not found")

        # Call the tool and expect it to propagate the error
        with pytest.raises(VultrAPIError) as exc_info:
            update_record_tool = dns_tools["update_record"]
            await update_record_tool.fn(
                domain="example.com",
                record_id="non-existent-record",
                data="192.168.1.100"
            )

        assert "Record not found" in str(exc_info.value)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_record_tool_success(self, dns_tools, mock_vultr_client):
        """Test delete_record tool with successful deletion."""
        # Mock successful deletion (delete_record returns None)
        mock_vultr_client.delete_record.return_value = None

        # Call the tool
        delete_record_tool = dns_tools["delete_record"]
        result = await delete_record_tool.fn(
            domain="example.com",
            record_id="record-123"
        )

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert "record-123" in result["message"]
        assert "deleted successfully" in result["message"]
        
        mock_vultr_client.delete_record.assert_called_once_with("example.com", "record-123")

    @pytest.mark.asyncio
    async def test_delete_record_tool_with_api_error(self, dns_tools, mock_vultr_client):
        """Test delete_record tool when API returns an error."""
        # Mock API error
        mock_vultr_client.delete_record.side_effect = VultrAPIError(404, "Record not found")

        # Call the tool and expect it to propagate the error
        with pytest.raises(VultrAPIError) as exc_info:
            delete_record_tool = dns_tools["delete_record"]
            await delete_record_tool.fn(
                domain="example.com",
                record_id="non-existent-record"
            )

        assert "Record not found" in str(exc_info.value)
        assert exc_info.value.status_code == 404
        mock_vultr_client.delete_record.assert_called_once_with("example.com", "non-existent-record")

    @pytest.mark.asyncio
    async def test_delete_record_tool_with_permission_error(self, dns_tools, mock_vultr_client):
        """Test delete_record tool when user lacks permission."""
        # Mock permission error
        mock_vultr_client.delete_record.side_effect = VultrAPIError(403, "Forbidden")

        # Call the tool and expect it to propagate the error
        with pytest.raises(VultrAPIError) as exc_info:
            delete_record_tool = dns_tools["delete_record"]
            await delete_record_tool.fn(
                domain="example.com",
                record_id="record-123"
            )

        assert "Forbidden" in str(exc_info.value)
        assert exc_info.value.status_code == 403
        mock_vultr_client.delete_record.assert_called_once_with("example.com", "record-123")

    @pytest.mark.asyncio
    async def test_delete_record_tool_with_network_error(self, dns_mcp_server, mock_vultr_client):
        """Test delete_record tool when network error occurs."""
        # Mock network error (non-Vultr exception)
        mock_vultr_client.delete_record.side_effect = Exception("Network timeout")

        # Call the tool and expect it to propagate the error
        with pytest.raises(Exception) as exc_info:
            await dns_mcp_server.tools["delete_record"](
                domain="example.com",
                record_id="record-123"
            )

        assert "Network timeout" in str(exc_info.value)
        mock_vultr_client.delete_record.assert_called_once_with("example.com", "record-123")


@pytest.mark.integration
class TestFastMCPDNSToolsIntegration:
    """Integration tests for FastMCP DNS tools workflow."""

    @pytest.fixture
    def mock_vultr_client(self):
        """Create a mock VultrDNSServer client for integration tests."""
        client = AsyncMock()
        client.get_record = AsyncMock()
        client.update_record = AsyncMock() 
        client.delete_record = AsyncMock()
        client.list_records = AsyncMock()
        return client

    @pytest.fixture
    def dns_mcp_server(self, mock_vultr_client):
        """Create a DNS FastMCP server with mocked client."""
        return create_dns_mcp(mock_vultr_client)

    @pytest.mark.asyncio
    async def test_record_lifecycle_workflow(self, dns_mcp_server, mock_vultr_client):
        """Test complete record lifecycle: create -> get -> update -> delete."""
        domain = "test-lifecycle.com"
        record_id = "lifecycle-record-123"

        # Step 1: Get initial record
        initial_record = {
            "id": record_id,
            "type": "A",
            "name": "www",
            "data": "192.168.1.100",
            "ttl": 300,
            "priority": None
        }
        mock_vultr_client.get_record.return_value = initial_record

        get_result = await dns_mcp_server.tools["get_record"](
            domain=domain,
            record_id=record_id
        )

        assert get_result == initial_record
        assert get_result["data"] == "192.168.1.100"

        # Step 2: Update the record's IP address and TTL
        updated_record = {
            "id": record_id,
            "type": "A", 
            "name": "www",
            "data": "192.168.2.200",
            "ttl": 600,
            "priority": None
        }
        mock_vultr_client.update_record.return_value = updated_record

        update_result = await dns_mcp_server.tools["update_record"](
            domain=domain,
            record_id=record_id,
            data="192.168.2.200",
            ttl=600
        )

        assert update_result == updated_record
        assert update_result["data"] == "192.168.2.200"
        assert update_result["ttl"] == 600

        # Step 3: Verify the update by getting the record again
        mock_vultr_client.get_record.return_value = updated_record

        verify_result = await dns_mcp_server.tools["get_record"](
            domain=domain,
            record_id=record_id
        )

        assert verify_result == updated_record
        assert verify_result["data"] == "192.168.2.200"

        # Step 4: Delete the record
        mock_vultr_client.delete_record.return_value = None

        delete_result = await dns_mcp_server.tools["delete_record"](
            domain=domain,
            record_id=record_id
        )

        assert delete_result["status"] == "success"
        assert record_id in delete_result["message"]

        # Verify all client methods were called correctly
        assert mock_vultr_client.get_record.call_count == 2
        mock_vultr_client.update_record.assert_called_once_with(
            domain, record_id, None, "192.168.2.200", 600, None
        )
        mock_vultr_client.delete_record.assert_called_once_with(domain, record_id)

    @pytest.mark.asyncio
    async def test_error_propagation_consistency(self, dns_mcp_server, mock_vultr_client):
        """Test that all three tools consistently propagate errors."""
        domain = "error-test.com"
        record_id = "error-record-123"

        # Test VultrAPIError propagation for all tools
        api_error = VultrAPIError(500, "Server error")

        # Test get_record error propagation
        mock_vultr_client.get_record.side_effect = api_error
        with pytest.raises(VultrAPIError) as exc_info:
            get_record_tool = dns_tools["get_record"]
            await get_record_tool.fn(domain=domain, record_id=record_id)
        assert exc_info.value.status_code == 500

        # Test update_record error propagation
        mock_vultr_client.update_record.side_effect = api_error
        with pytest.raises(VultrAPIError) as exc_info:
            update_record_tool = dns_tools["update_record"]
            await update_record_tool.fn(
                domain=domain, record_id=record_id, data="192.168.1.1"
            )
        assert exc_info.value.status_code == 500

        # Test delete_record error propagation
        mock_vultr_client.delete_record.side_effect = api_error
        with pytest.raises(VultrAPIError) as exc_info:
            delete_record_tool = dns_tools["delete_record"]
            await delete_record_tool.fn(domain=domain, record_id=record_id)
        assert exc_info.value.status_code == 500

        # Test VultrAuthError propagation for all tools
        auth_error = VultrAuthError(401, "Unauthorized")

        # Reset side effects and test auth errors
        mock_vultr_client.get_record.side_effect = auth_error
        mock_vultr_client.update_record.side_effect = auth_error
        mock_vultr_client.delete_record.side_effect = auth_error

        for tool_name in ["get_record", "update_record", "delete_record"]:
            with pytest.raises(VultrAuthError) as exc_info:
                tool = dns_tools[tool_name]
                if tool_name == "get_record":
                    await tool.fn(domain=domain, record_id=record_id)
                elif tool_name == "update_record":
                    await tool.fn(
                        domain=domain, record_id=record_id, data="192.168.1.1"
                    )
                else:  # delete_record
                    await tool.fn(domain=domain, record_id=record_id)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_mx_record_update_with_priority_handling(self, dns_tools, mock_vultr_client):
        """Test updating MX records with proper priority handling."""
        domain = "mx-test.com"
        record_id = "mx-record-456"

        # Initial MX record
        initial_mx = {
            "id": record_id,
            "type": "MX",
            "name": "@",
            "data": "mail1.example.com",
            "ttl": 3600,
            "priority": 10
        }
        mock_vultr_client.get_record.return_value = initial_mx

        # Get initial record
        get_record_tool = dns_tools["get_record"]
        get_result = await get_record_tool.fn(
            domain=domain,
            record_id=record_id
        )
        assert get_result["priority"] == 10

        # Update MX record with higher priority (lower number)
        updated_mx = {
            "id": record_id,
            "type": "MX",
            "name": "@", 
            "data": "mail2.example.com",
            "ttl": 3600,
            "priority": 5
        }
        mock_vultr_client.update_record.return_value = updated_mx

        update_record_tool = dns_tools["update_record"]
        update_result = await update_record_tool.fn(
            domain=domain,
            record_id=record_id,
            data="mail2.example.com",
            priority=5
        )

        assert update_result["data"] == "mail2.example.com"
        assert update_result["priority"] == 5

        # Verify the update call included priority
        mock_vultr_client.update_record.assert_called_once_with(
            domain, record_id, None, "mail2.example.com", None, 5
        )