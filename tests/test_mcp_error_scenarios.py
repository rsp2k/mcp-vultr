"""
Comprehensive MCP server error handling tests.

This module tests error scenarios specific to the MCP (Model Context Protocol)
server implementation, focusing on tool failures and error propagation.
"""

import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from mcp import types
from mcp_vultr.server import create_mcp_server, VultrDNSServer
from mcp_vultr.server import (
    VultrAPIError,
    VultrAuthError,
    VultrRateLimitError,
    VultrResourceNotFoundError,
    VultrValidationError,
)


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


class TestMCPToolErrorHandling:
    """Test error handling in MCP tools."""

    @pytest.mark.asyncio
    async def test_list_domains_tool_with_api_error(self, mock_api_key):
        """Test list_domains_tool with API errors."""
        mock_vultr_client = AsyncMock()
        mock_vultr_client.list_domains.side_effect = VultrAPIError(500, "Internal Server Error")
        
        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_vultr_client):
            server = create_mcp_server(mock_api_key)
            result = await call_mcp_tool(server, "list_dns_domains")

            # Error should be in the content text (not necessarily isError=True)
            assert "Error" in str(result.content) or "error" in str(result.content)
            assert "Internal Server Error" in str(result.content)

    @pytest.mark.asyncio
    async def test_create_domain_tool_with_validation_error(self, mock_api_key):
        """Test create_domain_tool with validation errors."""
        mock_vultr_client = AsyncMock()
        mock_vultr_client.create_domain.side_effect = VultrValidationError(400, "Invalid domain name")
        
        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_vultr_client):
            server = create_mcp_server(mock_api_key)
            result = await call_mcp_tool(server, "create_dns_domain", {"domain": "invalid..domain.com"})

            # Error should be in the content text
            assert "Error" in str(result.content) or "error" in str(result.content)
            assert "validation" in str(result.content).lower()

    @pytest.mark.asyncio
    async def test_validate_record_tool_with_invalid_input(self, mock_api_key):
        """Test validate_dns_record_tool with invalid input."""
        server = create_mcp_server(mock_api_key)
        result = await call_mcp_tool(server, "validate_dns_record", {
            "record_type": "INVALID_TYPE",
            "name": "www",
            "data": "192.168.1.1"
        })

        # Validation tool returns structured response, not isError=True
        content_str = str(result.content)
        assert "'valid': False" in content_str
        assert "Invalid record type" in content_str


class TestMCPServerInitializationErrors:
    """Test MCP server initialization error scenarios."""

    def test_create_mcp_server_without_api_key(self):
        """Test creating MCP server without API key."""
        with pytest.raises((ValueError, TypeError)):
            create_mcp_server(api_key=None)

    def test_create_mcp_server_with_empty_api_key(self):
        """Test creating MCP server with empty API key."""
        with pytest.raises((ValueError, TypeError)):
            create_mcp_server(api_key="")

    def test_create_mcp_server_with_invalid_api_key_format(self):
        """Test creating MCP server with invalid API key format."""
        # Very short key that's obviously invalid
        with pytest.raises(ValueError):
            create_mcp_server(api_key="abc")


class TestMCPToolArgumentValidation:
    """Test MCP tool argument validation."""

    @pytest.mark.asyncio
    async def test_create_domain_tool_missing_domain_argument(self, mock_api_key):
        """Test create_domain_tool with missing domain argument."""
        server = create_mcp_server(mock_api_key)
        result = await call_mcp_tool(server, "create_dns_domain", {})  # Missing required 'domain' argument

        # Should fail with domain missing error
        content_str = str(result.content)
        assert "Error" in content_str
        assert "domain" in content_str.lower() and ("required" in content_str.lower() or "missing" in content_str.lower())

    @pytest.mark.asyncio
    async def test_validate_record_tool_with_none_values(self, mock_api_key):
        """Test validate_record_tool with None values."""
        server = create_mcp_server(mock_api_key)
        result = await call_mcp_tool(server, "validate_dns_record", {
            "record_type": None,
            "name": None,
            "data": None
        })

        # Should handle None values appropriately
        content_str = str(result.content)
        assert "Error" in content_str or "'valid': False" in content_str


class TestMCPErrorPropagation:
    """Test error propagation through MCP layer."""

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(self, mock_api_key):
        """Test handling of unexpected exceptions."""
        mock_vultr_client = AsyncMock()
        mock_vultr_client.list_domains.side_effect = RuntimeError("Unexpected error")
        
        with patch("mcp_vultr.server.VultrDNSServer", return_value=mock_vultr_client):
            server = create_mcp_server(mock_api_key)
            result = await call_mcp_tool(server, "list_dns_domains")

            # Should handle unexpected errors
            content_str = str(result.content)
            assert "Error" in content_str or "error" in content_str.lower()