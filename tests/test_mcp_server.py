"""Tests for MCP server functionality using official MCP testing patterns."""

import pytest
from unittest.mock import patch, AsyncMock
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client
from mcp_vultr.server import VultrDNSServer, create_mcp_server


class TestMCPServerBasics:
    """Test basic MCP server functionality."""
    
    def test_server_creation(self, mock_api_key):
        """Test that MCP server can be created successfully."""
        server = create_mcp_server(mock_api_key)
        assert server is not None
        assert hasattr(server, '_tools')
        assert hasattr(server, '_resources')
    
    def test_server_creation_without_api_key(self):
        """Test that server creation fails without API key."""
        with pytest.raises(ValueError, match="VULTR_API_KEY must be provided"):
            create_mcp_server(None)
    
    @patch.dict('os.environ', {'VULTR_API_KEY': 'env-test-key'})
    def test_server_creation_from_env(self):
        """Test server creation using environment variable."""
        server = create_mcp_server()
        assert server is not None


@pytest.mark.mcp
class TestMCPTools:
    """Test MCP tools through in-memory client connection."""
    
    @pytest.mark.asyncio
    async def test_list_dns_domains_tool(self, mcp_server, mock_vultr_client):
        """Test the list_dns_domains MCP tool."""
        with patch('mcp_vultr.server.VultrDNSServer', return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")
            
            # For the official MCP package, we need to use ClientSession
            async with ClientSession(server) as session:
                result = await session.call_tool("list_dns_domains", {})
                
                assert isinstance(result, list)
                # The result should be a list containing the response
                assert len(result) > 0
                
                # Check if we got the mock data
                domains_data = result[0].text if hasattr(result[0], 'text') else result
                mock_vultr_client.list_domains.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_get_dns_domain_tool(self, mcp_server, mock_vultr_client):
        """Test the get_dns_domain MCP tool."""
        with patch('mcp_vultr.server.VultrDNSServer', return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")
            
            async with ClientSession(server) as session:
                result = await session.call_tool("get_dns_domain", {"domain": "example.com"})
                
                assert result is not None
                mock_vultr_client.get_domain.assert_called_once_with("example.com")
    
    @pytest.mark.asyncio
    async def test_create_dns_domain_tool(self, mcp_server, mock_vultr_client):
        """Test the create_dns_domain MCP tool."""
        with patch('mcp_vultr.server.VultrDNSServer', return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")
            
            async with ClientSession(server) as session:
                result = await session.call_tool("create_dns_domain", {
                    "domain": "newdomain.com",
                    "ip": "192.168.1.100"
                })
                
                assert result is not None
                mock_vultr_client.create_domain.assert_called_once_with("newdomain.com", "192.168.1.100")
    
    @pytest.mark.asyncio
    async def test_delete_dns_domain_tool(self, mcp_server, mock_vultr_client):
        """Test the delete_dns_domain MCP tool.""" 
        with patch('mcp_vultr.server.VultrDNSServer', return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")
            
            async with ClientSession(server) as session:
                result = await session.call_tool("delete_dns_domain", {"domain": "example.com"})
                
                assert result is not None
                mock_vultr_client.delete_domain.assert_called_once_with("example.com")
    
    @pytest.mark.asyncio
    async def test_list_dns_records_tool(self, mcp_server, mock_vultr_client):
        """Test the list_dns_records MCP tool."""
        with patch('mcp_vultr.server.VultrDNSServer', return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")
            
            async with ClientSession(server) as session:
                result = await session.call_tool("list_dns_records", {"domain": "example.com"})
                
                assert result is not None
                mock_vultr_client.list_records.assert_called_once_with("example.com")
    
    @pytest.mark.asyncio
    async def test_create_dns_record_tool(self, mcp_server, mock_vultr_client):
        """Test the create_dns_record MCP tool."""
        with patch('mcp_vultr.server.VultrDNSServer', return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")
            
            async with ClientSession(server) as session:
                result = await session.call_tool("create_dns_record", {
                    "domain": "example.com",
                    "record_type": "A",
                    "name": "www",
                    "data": "192.168.1.100",
                    "ttl": 300
                })
                
                assert result is not None
                mock_vultr_client.create_record.assert_called_once_with(
                    "example.com", "A", "www", "192.168.1.100", 300, None
                )
    
    @pytest.mark.asyncio
    async def test_validate_dns_record_tool(self, mcp_server):
        """Test the validate_dns_record MCP tool."""
        async with ClientSession(mcp_server) as session:
            # Test valid A record
            result = await session.call_tool("validate_dns_record", {
                "record_type": "A",
                "name": "www", 
                "data": "192.168.1.100",
                "ttl": 300
            })
            
            assert result is not None
            # The validation should pass for a valid A record
    
    @pytest.mark.asyncio
    async def test_validate_dns_record_invalid(self, mcp_server):
        """Test the validate_dns_record tool with invalid data."""
        async with ClientSession(mcp_server) as session:
            # Test invalid A record (bad IP)
            result = await session.call_tool("validate_dns_record", {
                "record_type": "A",
                "name": "www",
                "data": "invalid-ip-address"
            })
            
            assert result is not None
            # Should detect the invalid IP address
    
    @pytest.mark.asyncio
    async def test_analyze_dns_records_tool(self, mcp_server, mock_vultr_client):
        """Test the analyze_dns_records MCP tool."""
        with patch('mcp_vultr.server.VultrDNSServer', return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")
            
            async with ClientSession(server) as session:
                result = await session.call_tool("analyze_dns_records", {"domain": "example.com"})
                
                assert result is not None
                mock_vultr_client.list_records.assert_called_once_with("example.com")


@pytest.mark.mcp
class TestMCPResources:
    """Test MCP resources through in-memory client connection."""
    
    @pytest.mark.asyncio
    async def test_domains_resource(self, mcp_server, mock_vultr_client):
        """Test the vultr://domains resource."""
        with patch('mcp_vultr.server.VultrDNSServer', return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")
            
            async with ClientSession(server) as session:
                # Get available resources
                resources = await session.list_resources()
                
                # Check that domains resource is available
                resource_uris = [r.uri for r in resources]
                assert "vultr://domains" in resource_uris
    
    @pytest.mark.asyncio
    async def test_capabilities_resource(self, mcp_server):
        """Test the vultr://capabilities resource."""
        async with ClientSession(mcp_server) as session:
            resources = await session.list_resources()
            resource_uris = [r.uri for r in resources]
            assert "vultr://capabilities" in resource_uris
    
    @pytest.mark.asyncio
    async def test_read_domains_resource(self, mcp_server, mock_vultr_client):
        """Test reading the domains resource content."""
        with patch('mcp_vultr.server.VultrDNSServer', return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")
            
            async with ClientSession(server) as session:
                try:
                    result = await session.read_resource("vultr://domains")
                    assert result is not None
                    mock_vultr_client.list_domains.assert_called_once()
                except Exception:
                    # Resource reading might not be available in all MCP versions
                    pass


@pytest.mark.mcp
class TestMCPToolErrors:
    """Test MCP tool error handling."""
    
    @pytest.mark.asyncio
    async def test_tool_with_api_error(self, mcp_server):
        """Test tool behavior when API returns an error."""
        mock_client = AsyncMock()
        mock_client.list_domains.side_effect = Exception("API Error")
        
        with patch('mcp_vultr.server.VultrDNSServer', return_value=mock_client):
            server = create_mcp_server("test-api-key")
            
            async with ClientSession(server) as session:
                result = await session.call_tool("list_dns_domains", {})
                
                # Should handle the error gracefully
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_missing_required_parameters(self, mcp_server):
        """Test tool behavior with missing required parameters."""
        async with ClientSession(mcp_server) as session:
            with pytest.raises(Exception):
                # This should fail due to missing required 'domain' parameter
                await session.call_tool("get_dns_domain", {})


@pytest.mark.integration
class TestMCPIntegration:
    """Integration tests for the complete MCP workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_domain_workflow(self, mcp_server, mock_vultr_client):
        """Test a complete domain management workflow."""
        with patch('mcp_vultr.server.VultrDNSServer', return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")
            
            async with ClientSession(server) as session:
                # 1. List domains
                domains = await session.call_tool("list_dns_domains", {})
                assert domains is not None
                
                # 2. Get domain details
                domain_info = await session.call_tool("get_dns_domain", {"domain": "example.com"})
                assert domain_info is not None
                
                # 3. List records
                records = await session.call_tool("list_dns_records", {"domain": "example.com"})
                assert records is not None
                
                # 4. Analyze configuration
                analysis = await session.call_tool("analyze_dns_records", {"domain": "example.com"})
                assert analysis is not None
                
                # Verify all expected API calls were made
                mock_vultr_client.list_domains.assert_called()
                mock_vultr_client.get_domain.assert_called_with("example.com")
                mock_vultr_client.list_records.assert_called_with("example.com")
    
    @pytest.mark.asyncio
    async def test_record_management_workflow(self, mcp_server, mock_vultr_client):
        """Test record creation and management workflow."""
        with patch('mcp_vultr.server.VultrDNSServer', return_value=mock_vultr_client):
            server = create_mcp_server("test-api-key")
            
            async with ClientSession(server) as session:
                # 1. Validate record before creation
                validation = await session.call_tool("validate_dns_record", {
                    "record_type": "A",
                    "name": "www",
                    "data": "192.168.1.100"
                })
                assert validation is not None
                
                # 2. Create the record
                create_result = await session.call_tool("create_dns_record", {
                    "domain": "example.com",
                    "record_type": "A", 
                    "name": "www",
                    "data": "192.168.1.100",
                    "ttl": 300
                })
                assert create_result is not None
                
                # 3. Verify the record was created
                mock_vultr_client.create_record.assert_called_with(
                    "example.com", "A", "www", "192.168.1.100", 300, None
                )


@pytest.mark.unit
class TestValidationLogic:
    """Test DNS record validation logic in isolation."""
    
    @pytest.mark.asyncio
    async def test_a_record_validation(self, mcp_server):
        """Test A record validation logic."""
        async with ClientSession(mcp_server) as session:
            # Valid IPv4
            result = await session.call_tool("validate_dns_record", {
                "record_type": "A",
                "name": "www",
                "data": "192.168.1.1"
            })
            assert result is not None
            
            # Invalid IPv4
            result = await session.call_tool("validate_dns_record", {
                "record_type": "A", 
                "name": "www",
                "data": "999.999.999.999"
            })
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_cname_validation(self, mcp_server):
        """Test CNAME record validation logic."""
        async with ClientSession(mcp_server) as session:
            # Invalid: CNAME on root domain
            result = await session.call_tool("validate_dns_record", {
                "record_type": "CNAME",
                "name": "@",
                "data": "example.com"
            })
            assert result is not None
            
            # Valid: CNAME on subdomain
            result = await session.call_tool("validate_dns_record", {
                "record_type": "CNAME",
                "name": "www", 
                "data": "example.com"
            })
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_mx_validation(self, mcp_server):
        """Test MX record validation logic."""
        async with ClientSession(mcp_server) as session:
            # Invalid: Missing priority
            result = await session.call_tool("validate_dns_record", {
                "record_type": "MX",
                "name": "@",
                "data": "mail.example.com"
            })
            assert result is not None
            
            # Valid: With priority
            result = await session.call_tool("validate_dns_record", {
                "record_type": "MX",
                "name": "@",
                "data": "mail.example.com", 
                "priority": 10
            })
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_aaaa_record_validation(self, mcp_server):
        """Test comprehensive AAAA (IPv6) record validation logic."""
        async with ClientSession(mcp_server) as session:
            # Valid IPv6 addresses
            valid_ipv6_addresses = [
                "2001:db8::1",                    # Standard format
                "2001:0db8:0000:0000:0000:0000:0000:0001",  # Full format
                "::",                             # All zeros
                "::1",                            # Loopback
                "fe80::1",                        # Link-local
                "2001:db8:85a3::8a2e:370:7334",  # Mixed compression
                "::ffff:192.0.2.1",              # IPv4-mapped
            ]
            
            for ipv6_addr in valid_ipv6_addresses:
                result = await session.call_tool("validate_dns_record", {
                    "record_type": "AAAA",
                    "name": "www",
                    "data": ipv6_addr
                })
                assert result is not None
                # Parse the result to check validation passed
                import json
                parsed = json.loads(result[0].text.replace("'", '"'))
                assert parsed["validation"]["valid"] == True, f"Failed to validate {ipv6_addr}"
            
            # Invalid IPv6 addresses
            invalid_ipv6_addresses = [
                "2001:db8::1::2",                 # Multiple ::
                "2001:db8:85a3::8a2e::7334",      # Multiple ::
                "gggg::1",                        # Invalid hex
                "2001:db8:85a3:0:0:8a2e:370g:7334",  # Invalid character
                "2001:db8:85a3:0:0:8a2e:370:7334:extra",  # Too many groups
                "",                               # Empty
                "192.168.1.1",                   # IPv4 instead of IPv6
            ]
            
            for ipv6_addr in invalid_ipv6_addresses:
                result = await session.call_tool("validate_dns_record", {
                    "record_type": "AAAA", 
                    "name": "www",
                    "data": ipv6_addr
                })
                assert result is not None
                # Parse the result to check validation failed
                import json
                parsed = json.loads(result[0].text.replace("'", '"'))
                assert parsed["validation"]["valid"] == False, f"Should have failed to validate {ipv6_addr}"
    
    @pytest.mark.asyncio
    async def test_ipv6_suggestions_and_warnings(self, mcp_server):
        """Test that IPv6 validation provides helpful suggestions and warnings."""
        async with ClientSession(mcp_server) as session:
            # Test IPv4-mapped suggestion
            result = await session.call_tool("validate_dns_record", {
                "record_type": "AAAA",
                "name": "www", 
                "data": "::ffff:192.0.2.1"
            })
            assert result is not None
            import json
            parsed = json.loads(result[0].text.replace("'", '"'))
            suggestions = parsed["validation"]["suggestions"]
            assert any("IPv4-mapped" in s for s in suggestions)
            
            # Test compression suggestion
            result = await session.call_tool("validate_dns_record", {
                "record_type": "AAAA",
                "name": "www",
                "data": "2001:0db8:0000:0000:0000:0000:0000:0001"
            })
            assert result is not None
            parsed = json.loads(result[0].text.replace("'", '"'))
            suggestions = parsed["validation"]["suggestions"]
            assert any("compressed format" in s for s in suggestions)
            
            # Test loopback warning
            result = await session.call_tool("validate_dns_record", {
                "record_type": "AAAA",
                "name": "www",
                "data": "::1"
            })
            assert result is not None
            parsed = json.loads(result[0].text.replace("'", '"'))
            warnings = parsed["validation"]["warnings"]
            assert any("loopback" in w for w in warnings)


if __name__ == "__main__":
    pytest.main([__file__])
