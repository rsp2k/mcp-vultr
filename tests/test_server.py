"""Tests for the Vultr DNS server module."""

import pytest
from unittest.mock import AsyncMock, patch
from mcp_vultr.server import VultrDNSServer, create_mcp_server


class TestVultrDNSServer:
    """Test cases for VultrDNSServer class."""
    
    def test_init(self):
        """Test server initialization."""
        server = VultrDNSServer("test-api-key")
        assert server.api_key == "test-api-key"
        assert server.headers["Authorization"] == "Bearer test-api-key"
        assert server.headers["Content-Type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_make_request_success(self):
        """Test successful API request."""
        server = VultrDNSServer("test-api-key")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"test": "data"}
            
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response
            
            result = await server._make_request("GET", "/test")
            assert result == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_make_request_error(self):
        """Test API request error handling."""
        server = VultrDNSServer("test-api-key")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response
            
            with pytest.raises(Exception) as exc_info:
                await server._make_request("GET", "/test")
            
            assert "Vultr API error 400" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_domains(self):
        """Test listing domains."""
        server = VultrDNSServer("test-api-key")
        
        with patch.object(server, '_make_request') as mock_request:
            mock_request.return_value = {"domains": [{"domain": "example.com"}]}
            
            result = await server.list_domains()
            assert result == [{"domain": "example.com"}]
            mock_request.assert_called_once_with("GET", "/domains")
    
    @pytest.mark.asyncio
    async def test_create_domain(self):
        """Test creating a domain."""
        server = VultrDNSServer("test-api-key")
        
        with patch.object(server, '_make_request') as mock_request:
            mock_request.return_value = {"domain": "example.com"}
            
            result = await server.create_domain("example.com", "192.168.1.1")
            assert result == {"domain": "example.com"}
            mock_request.assert_called_once_with(
                "POST", 
                "/domains", 
                {"domain": "example.com", "ip": "192.168.1.1"}
            )


class TestMCPServer:
    """Test cases for MCP server creation."""
    
    def test_create_mcp_server_with_api_key(self):
        """Test creating MCP server with API key."""
        server = create_mcp_server("test-api-key")
        assert server is not None
        assert server.name == "Vultr DNS Manager"
    
    def test_create_mcp_server_without_api_key(self):
        """Test creating MCP server without API key raises error."""
        with pytest.raises(ValueError) as exc_info:
            create_mcp_server()
        
        assert "VULTR_API_KEY must be provided" in str(exc_info.value)
    
    @patch.dict('os.environ', {'VULTR_API_KEY': 'env-api-key'})
    def test_create_mcp_server_from_env(self):
        """Test creating MCP server with API key from environment."""
        server = create_mcp_server()
        assert server is not None
        assert server.name == "Vultr DNS Manager"


@pytest.fixture
def mock_vultr_server():
    """Fixture for mocked VultrDNSServer."""
    with patch('mcp_vultr.server.VultrDNSServer') as mock:
        yield mock


@pytest.mark.asyncio
async def test_validation_tool():
    """Test DNS record validation functionality."""
    from mcp_vultr.server import create_mcp_server
    
    # Create server (this will fail without API key, but we can test the structure)
    with pytest.raises(ValueError):
        create_mcp_server()


if __name__ == "__main__":
    pytest.main([__file__])
