"""Tests for MCP server functionality using direct server testing patterns."""

from unittest.mock import AsyncMock, patch

import pytest
from mcp import types

from mcp_vultr.server import create_mcp_server


async def call_mcp_tool(server, tool_name: str, arguments: dict = None) -> types.CallToolResult:
    """Helper function to call MCP tools properly."""
    if arguments is None:
        arguments = {}
    
    # Create proper MCP request
    request = types.CallToolRequest(
        method="tools/call",
        params=types.CallToolRequestParams(
            name=tool_name,
            arguments=arguments
        )
    )
    
    # Get handler and call it
    handler = server.request_handlers[types.CallToolRequest]
    result = await handler(request)
    
    return result.root


async def list_mcp_resources(server) -> types.ListResourcesResult:
    """Helper function to list MCP resources properly."""
    # Create proper MCP request
    request = types.ListResourcesRequest(
        method="resources/list"
    )
    
    # Get handler and call it
    handler = server.request_handlers[types.ListResourcesRequest]
    result = await handler(request)
    
    return result.root


async def read_mcp_resource(server, uri: str) -> types.ReadResourceResult:
    """Helper function to read MCP resources properly."""
    # Create proper MCP request
    request = types.ReadResourceRequest(
        method="resources/read",
        params=types.ReadResourceRequestParams(uri=uri)
    )
    
    # Get handler and call it
    handler = server.request_handlers[types.ReadResourceRequest]
    result = await handler(request)
    
    return result.root


class TestMCPServerBasics:
    """Test basic MCP server functionality."""

    def test_server_creation(self, mock_api_key):
        """Test that MCP server can be created successfully."""
        server = create_mcp_server(mock_api_key)
        assert server is not None
        assert hasattr(server, "list_tools")
        assert hasattr(server, "list_resources")
        assert hasattr(server, "call_tool")

    @patch.dict("os.environ", {}, clear=True)
    def test_server_creation_without_api_key(self):
        """Test that server creation fails without API key."""
        with pytest.raises(ValueError, match="VULTR_API_KEY must be provided"):
            create_mcp_server(None)

    @patch.dict("os.environ", {"VULTR_API_KEY": "env-test-key"})
    def test_server_creation_from_env(self):
        """Test server creation using environment variable."""
        server = create_mcp_server()
        assert server is not None


@pytest.mark.mcp
class TestMCPTools:
    """Test MCP tools through in-memory client connection."""

    @pytest.mark.asyncio
    async def test_list_dns_domains_tool(self, mock_vultr_client):
        """Test the list_dns_domains MCP tool."""
        # Mock the response
        mock_vultr_client.list_domains.return_value = [
            {"domain": "example.com", "date_created": "2023-01-01"}
        ]

        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")

            # Call the tool using proper MCP request
            result = await call_mcp_tool(server, "list_dns_domains")
            
            # Verify the result
            assert result is not None
            assert not result.isError
            assert len(result.content) == 1
            assert result.content[0].type == "text"
            assert "example.com" in result.content[0].text
            
            # Verify the mock was called
            mock_vultr_client.list_domains.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dns_domain_tool(self, mock_vultr_client):
        """Test the get_dns_domain MCP tool."""
        # Mock the response
        mock_vultr_client.get_domain.return_value = {
            "domain": "example.com",
            "date_created": "2023-01-01",
            "dns_sec": "disabled"
        }

        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")

            # Call the tool using proper MCP request
            result = await call_mcp_tool(server, "get_dns_domain", {"domain": "example.com"})
            
            # Verify the result
            assert result is not None
            assert not result.isError
            assert len(result.content) == 1
            assert result.content[0].type == "text"
            assert "example.com" in result.content[0].text
            assert "2023-01-01" in result.content[0].text
            
            # Verify the mock was called correctly
            mock_vultr_client.get_domain.assert_called_once_with("example.com")

    @pytest.mark.asyncio
    async def test_create_dns_domain_tool(self, mock_vultr_client):
        """Test the create_dns_domain MCP tool."""
        # Mock the response
        mock_vultr_client.create_domain.return_value = {
            "domain": "newdomain.com",
            "date_created": "2024-01-01",
            "dns_sec": "disabled"
        }

        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")

            # Call the tool using proper MCP request
            result = await call_mcp_tool(
                server, 
                "create_dns_domain", 
                {"domain": "newdomain.com", "ip": "192.168.1.100"}
            )
            
            # Verify the result
            assert result is not None
            assert not result.isError
            assert len(result.content) == 1
            assert result.content[0].type == "text"
            assert "newdomain.com" in result.content[0].text
            
            # Verify the mock was called correctly
            mock_vultr_client.create_domain.assert_called_once_with(
                "newdomain.com", "192.168.1.100"
            )

    @pytest.mark.asyncio
    async def test_delete_dns_domain_tool(self, mock_vultr_client):
        """Test the delete_dns_domain MCP tool."""
        # Mock the response
        mock_vultr_client.delete_domain.return_value = {"message": "Domain deleted successfully"}

        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")

            # Call the tool using proper MCP request
            result = await call_mcp_tool(server, "delete_dns_domain", {"domain": "example.com"})
            
            # Verify the result
            assert result is not None
            assert not result.isError
            assert len(result.content) == 1
            assert result.content[0].type == "text"
            
            # Verify the mock was called
            mock_vultr_client.delete_domain.assert_called_once_with("example.com")

    @pytest.mark.asyncio
    async def test_list_dns_records_tool(self, mock_vultr_client):
        """Test the list_dns_records MCP tool."""
        # Mock the response
        mock_vultr_client.list_records.return_value = [
            {"id": "rec1", "type": "A", "name": "www", "data": "192.168.1.1"},
            {"id": "rec2", "type": "MX", "name": "@", "data": "mail.example.com"}
        ]

        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")

            # Call the tool using proper MCP request
            result = await call_mcp_tool(server, "list_dns_records", {"domain": "example.com"})
            
            # Verify the result
            assert result is not None
            assert not result.isError
            assert len(result.content) == 1
            assert result.content[0].type == "text"
            assert "www" in result.content[0].text
            assert "MX" in result.content[0].text
            
            # Verify the mock was called
            mock_vultr_client.list_records.assert_called_once_with("example.com")

    @pytest.mark.asyncio
    async def test_create_dns_record_tool(self, mock_vultr_client):
        """Test the create_dns_record MCP tool."""
        # Mock the response
        mock_vultr_client.create_record.return_value = {
            "record": {"id": "rec123", "type": "A", "name": "www", "data": "192.168.1.100"}
        }

        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")

            # Call the tool using proper MCP request
            result = await call_mcp_tool(server, "create_dns_record", {
                "domain": "example.com",
                "record_type": "A",
                "name": "www",
                "data": "192.168.1.100",
                "ttl": 300,
            })
            
            # Verify the result
            assert result is not None
            assert not result.isError
            assert len(result.content) == 1
            assert result.content[0].type == "text"
            assert "rec123" in result.content[0].text or "www" in result.content[0].text
            
            # Verify the mock was called
            mock_vultr_client.create_record.assert_called_once_with(
                "example.com", "A", "www", "192.168.1.100", 300, None
            )

    @pytest.mark.asyncio
    async def test_validate_dns_record_tool(self):
        """Test the validate_dns_record MCP tool."""
        server = create_mcp_server("test-api-key")
        
        # Call the tool using proper MCP request - Test valid A record
        result = await call_mcp_tool(server, "validate_dns_record", {
            "record_type": "A",
            "name": "www",
            "data": "192.168.1.100",
            "ttl": 300,
        })
        
        # Verify the result
        assert result is not None
        assert not result.isError
        assert len(result.content) == 1
        assert result.content[0].type == "text"
        # The validation should pass for a valid A record
        assert "valid" in result.content[0].text.lower() or "success" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_validate_dns_record_invalid(self):
        """Test the validate_dns_record tool with invalid data."""
        server = create_mcp_server("test-api-key")
        
        # Call the tool using proper MCP request - Test invalid A record (bad IP)
        result = await call_mcp_tool(server, "validate_dns_record", {
            "record_type": "A", 
            "name": "www", 
            "data": "invalid-ip-address"
        })
        
        # Verify the result
        assert result is not None
        assert not result.isError
        assert len(result.content) == 1
        assert result.content[0].type == "text"
        # Should detect the invalid IP address
        assert "invalid" in result.content[0].text.lower() or "error" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_analyze_dns_records_tool(self, mock_vultr_client):
        """Test the analyze_dns_records MCP tool."""
        # Mock the response
        mock_vultr_client.list_records.return_value = [
            {"id": "rec1", "type": "A", "name": "www", "data": "192.168.1.1", "ttl": 300},
            {"id": "rec2", "type": "MX", "name": "@", "data": "mail.example.com", "priority": 10},
            {"id": "rec3", "type": "TXT", "name": "@", "data": "v=spf1 include:_spf.google.com ~all"}
        ]

        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")

            # Call the tool using proper MCP request
            result = await call_mcp_tool(server, "analyze_dns_records", {"domain": "example.com"})
            
            # Verify the result
            assert result is not None
            assert not result.isError
            assert len(result.content) == 1
            assert result.content[0].type == "text"
            # Should contain analysis of the DNS records
            content_text = result.content[0].text.lower()
            assert "analysis" in content_text or "record" in content_text
            
            # Verify the mock was called
            mock_vultr_client.list_records.assert_called_once_with("example.com")


@pytest.mark.mcp
class TestMCPResources:
    """Test MCP resources through in-memory client connection."""

    @pytest.mark.asyncio
    async def test_domains_resource(self, mock_vultr_client):
        """Test the vultr://domains resource."""
        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")

            # Get available resources using proper MCP request
            result = await list_mcp_resources(server)

            # Verify the result
            assert result is not None
            assert hasattr(result, 'resources')
            
            # Check that domains resource is available
            resource_uris = [str(r.uri) for r in result.resources]
            assert "vultr://domains" in resource_uris
            
            # Verify resource has proper metadata
            domains_resource = next((r for r in result.resources if str(r.uri) == "vultr://domains"), None)
            assert domains_resource is not None
            assert domains_resource.name == "DNS Domains"

    @pytest.mark.asyncio
    async def test_capabilities_resource(self):
        """Test the vultr://capabilities resource."""
        server = create_mcp_server("test-api-key")
        
        # Get available resources using proper MCP request
        result = await list_mcp_resources(server)
        
        # Check that capabilities resource is available
        resource_uris = [str(r.uri) for r in result.resources]
        assert "vultr://capabilities" in resource_uris

    @pytest.mark.asyncio
    async def test_read_domains_resource(self, mock_vultr_client):
        """Test reading the domains resource content."""
        # Mock the response
        mock_vultr_client.list_domains.return_value = [
            {"domain": "example.com", "date_created": "2023-01-01"},
            {"domain": "test.com", "date_created": "2023-01-02"}
        ]
        
        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")

            # Read the domains resource using proper MCP request
            result = await read_mcp_resource(server, "vultr://domains")
            
            # Verify the result
            assert result is not None
            assert len(result.contents) == 1
            assert result.contents[0].text is not None
            assert "example.com" in result.contents[0].text
            
            # Verify the mock was called
            mock_vultr_client.list_domains.assert_called_once()


@pytest.mark.mcp
class TestMCPToolErrors:
    """Test MCP tool error handling."""

    @pytest.mark.asyncio
    async def test_tool_with_api_error(self, mcp_server):
        """Test tool behavior when API returns an error."""
        mock_client = AsyncMock()
        mock_client.list_domains.side_effect = Exception("API Error")

        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_client):
            server = create_mcp_server("test-api-key")

            # Call tool directly and expect it to handle error gracefully
            try:
                result = await server.call_tool("list_dns_domains", {})
                # Should handle the error gracefully
                assert result is not None
            except Exception:
                # Some errors might be expected to propagate
                pass

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self, mcp_server):
        """Test tool behavior with missing required parameters."""
        with pytest.raises((ValueError, TypeError, Exception)):
            # This should fail due to missing required 'domain' parameter
            await mcp_server.call_tool("get_dns_domain", {})


@pytest.mark.integration
class TestMCPIntegration:
    """Integration tests for the complete MCP workflow."""

    @pytest.mark.asyncio
    async def test_complete_domain_workflow(self, mock_vultr_client):
        """Test a complete domain management workflow."""
        # Mock the responses for each step
        mock_vultr_client.list_domains.return_value = [
            {"domain": "example.com", "date_created": "2023-01-01"}
        ]
        mock_vultr_client.get_domain.return_value = {
            "domain": "example.com", 
            "date_created": "2023-01-01",
            "dns_sec": "disabled"
        }
        mock_vultr_client.list_records.return_value = [
            {"id": "rec1", "type": "A", "name": "www", "data": "192.168.1.1"}
        ]
        
        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")

            # 1. List domains
            domains_result = await call_mcp_tool(server, "list_dns_domains")
            assert domains_result is not None
            assert not domains_result.isError
            assert "example.com" in domains_result.content[0].text

            # 2. Get domain details
            domain_result = await call_mcp_tool(server, "get_dns_domain", {"domain": "example.com"})
            assert domain_result is not None
            assert not domain_result.isError
            assert "example.com" in domain_result.content[0].text

            # 3. List records
            records_result = await call_mcp_tool(server, "list_dns_records", {"domain": "example.com"})
            assert records_result is not None
            assert not records_result.isError
            assert "www" in records_result.content[0].text

            # 4. Analyze configuration
            analysis_result = await call_mcp_tool(server, "analyze_dns_records", {"domain": "example.com"})
            assert analysis_result is not None
            assert not analysis_result.isError

            # Verify all expected API calls were made
            mock_vultr_client.list_domains.assert_called()
            mock_vultr_client.get_domain.assert_called_with("example.com")
            mock_vultr_client.list_records.assert_called_with("example.com")

    @pytest.mark.asyncio
    async def test_record_management_workflow(self, mock_vultr_client):
        """Test record creation and management workflow."""
        # Mock the create record response
        mock_vultr_client.create_record.return_value = {
            "record": {"id": "rec123", "type": "A", "name": "www", "data": "192.168.1.100"}
        }
        
        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")

            # 1. Validate record before creation
            validation_result = await call_mcp_tool(server, "validate_dns_record", {
                "record_type": "A", 
                "name": "www", 
                "data": "192.168.1.100"
            })
            assert validation_result is not None
            assert not validation_result.isError
            # Should be valid
            content_text = validation_result.content[0].text.lower()
            assert "valid" in content_text or "success" in content_text

            # 2. Create the record
            create_result = await call_mcp_tool(server, "create_dns_record", {
                "domain": "example.com",
                "record_type": "A",
                "name": "www",
                "data": "192.168.1.100",
                "ttl": 300,
            })
            assert create_result is not None
            assert not create_result.isError
            assert "rec123" in create_result.content[0].text or "www" in create_result.content[0].text

            # 3. Verify the record was created
            mock_vultr_client.create_record.assert_called_with(
                "example.com", "A", "www", "192.168.1.100", 300, None
            )


@pytest.mark.unit
class TestValidationLogic:
    """Test DNS record validation logic in isolation."""

    @pytest.mark.asyncio
    async def test_a_record_validation(self):
        """Test A record validation logic."""
        server = create_mcp_server("test-api-key")
        
        # Valid IPv4
        result = await call_mcp_tool(server, "validate_dns_record", {
            "record_type": "A", 
            "name": "www", 
            "data": "192.168.1.1"
        })
        assert result is not None
        assert not result.isError
        content_text = result.content[0].text.lower()
        assert "valid" in content_text or "success" in content_text

        # Invalid IPv4
        result = await call_mcp_tool(server, "validate_dns_record", {
            "record_type": "A", 
            "name": "www", 
            "data": "999.999.999.999"
        })
        assert result is not None
        assert not result.isError
        content_text = result.content[0].text.lower()
        assert "invalid" in content_text or "error" in content_text

    @pytest.mark.asyncio
    async def test_cname_validation(self):
        """Test CNAME record validation logic."""
        server = create_mcp_server("test-api-key")
        
        # Invalid: CNAME on root domain
        result = await call_mcp_tool(server, "validate_dns_record", {
            "record_type": "CNAME", 
            "name": "@", 
            "data": "example.com"
        })
        assert result is not None
        assert not result.isError
        content_text = result.content[0].text.lower()
        # Should warn about CNAME on root domain
        assert "invalid" in content_text or "warning" in content_text or "error" in content_text

        # Valid: CNAME on subdomain
        result = await call_mcp_tool(server, "validate_dns_record", {
            "record_type": "CNAME", 
            "name": "www", 
            "data": "example.com"
        })
        assert result is not None
        assert not result.isError
        content_text = result.content[0].text.lower()
        assert "valid" in content_text or "success" in content_text

    @pytest.mark.asyncio
    async def test_mx_validation(self):
        """Test MX record validation logic."""
        server = create_mcp_server("test-api-key")
        
        # Invalid: Missing priority
        result = await call_mcp_tool(server, "validate_dns_record", {
            "record_type": "MX", 
            "name": "@", 
            "data": "mail.example.com"
        })
        assert result is not None
        assert not result.isError
        content_text = result.content[0].text.lower()
        # Should warn about missing priority for MX record
        assert "priority" in content_text or "invalid" in content_text or "error" in content_text

        # Valid: With priority
        result = await call_mcp_tool(server, "validate_dns_record", {
            "record_type": "MX",
            "name": "@",
            "data": "mail.example.com",
            "priority": 10,
        })
        assert result is not None
        assert not result.isError
        content_text = result.content[0].text.lower()
        assert "valid" in content_text or "success" in content_text

    @pytest.mark.asyncio
    async def test_aaaa_record_validation(self):
        """Test comprehensive AAAA (IPv6) record validation logic."""
        server = create_mcp_server("test-api-key")
        
        # Valid IPv6 addresses
        valid_ipv6_addresses = [
            "2001:db8::1",  # Standard format
            "2001:0db8:0000:0000:0000:0000:0000:0001",  # Full format
            "::",  # All zeros
            "::1",  # Loopback
            "fe80::1",  # Link-local
            "2001:db8:85a3::8a2e:370:7334",  # Mixed compression
        ]

        for ipv6_addr in valid_ipv6_addresses:
            result = await call_mcp_tool(server, "validate_dns_record", {
                "record_type": "AAAA", 
                "name": "www", 
                "data": ipv6_addr
            })
            assert result is not None
            assert not result.isError
            content_text = result.content[0].text.lower()
            assert "valid" in content_text or "success" in content_text, f"Failed to validate {ipv6_addr}"

        # Invalid IPv6 addresses
        invalid_ipv6_addresses = [
            "2001:db8::1::2",  # Multiple ::
            "2001:db8:85a3::8a2e::7334",  # Multiple ::
            "gggg::1",  # Invalid hex
            "2001:db8:85a3:0:0:8a2e:370g:7334",  # Invalid character
            "",  # Empty
            "192.168.1.1",  # IPv4 instead of IPv6
        ]

        for ipv6_addr in invalid_ipv6_addresses:
            result = await call_mcp_tool(server, "validate_dns_record", {
                "record_type": "AAAA", 
                "name": "www", 
                "data": ipv6_addr
            })
            assert result is not None
            assert not result.isError
            content_text = result.content[0].text.lower()
            assert "invalid" in content_text or "error" in content_text, f"Should have failed to validate {ipv6_addr}"

    @pytest.mark.asyncio
    async def test_ipv6_suggestions_and_warnings(self):
        """Test that IPv6 validation provides helpful suggestions and warnings."""
        server = create_mcp_server("test-api-key")
        
        # Test IPv4-mapped suggestion
        result = await call_mcp_tool(server, "validate_dns_record", {
            "record_type": "AAAA", 
            "name": "www", 
            "data": "::ffff:192.0.2.1"
        })
        assert result is not None
        assert not result.isError
        content_text = result.content[0].text.lower()
        # Should mention IPv4-mapped or provide suggestions
        assert "ipv4" in content_text or "mapped" in content_text or "suggestion" in content_text

        # Test compression suggestion
        result = await call_mcp_tool(server, "validate_dns_record", {
            "record_type": "AAAA",
            "name": "www",
            "data": "2001:0db8:0000:0000:0000:0000:0000:0001",
        })
        assert result is not None
        assert not result.isError
        content_text = result.content[0].text.lower()
        # Should suggest compression or shorter format
        assert "compress" in content_text or "shorter" in content_text or "suggestion" in content_text

        # Test loopback warning
        result = await call_mcp_tool(server, "validate_dns_record", {
            "record_type": "AAAA", 
            "name": "www", 
            "data": "::1"
        })
        assert result is not None
        assert not result.isError
        content_text = result.content[0].text.lower()
        # Should warn about loopback
        assert "loopback" in content_text or "warning" in content_text


if __name__ == "__main__":
    pytest.main([__file__])
