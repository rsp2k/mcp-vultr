"""Configuration for pytest tests."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from mcp_vultr.server import create_mcp_server


@pytest.fixture
def mock_api_key():
    """Provide a mock API key for testing."""
    return "test-api-key-123456789"


@pytest.fixture
def mcp_server(mock_api_key):
    """Create a FastMCP server instance for testing."""
    return create_mcp_server(mock_api_key)


@pytest.fixture
def mock_vultr_client():
    """Create a mock VultrDNSServer for testing API interactions."""
    from mcp_vultr.server import VultrDNSServer
    
    mock_client = AsyncMock(spec=VultrDNSServer)
    
    # Configure common mock responses
    mock_client.list_domains.return_value = [
        {
            "domain": "example.com",
            "date_created": "2024-01-01T00:00:00Z",
            "dns_sec": "disabled"
        },
        {
            "domain": "test.com", 
            "date_created": "2024-01-02T00:00:00Z",
            "dns_sec": "enabled"
        }
    ]
    
    mock_client.get_domain.return_value = {
        "domain": "example.com",
        "date_created": "2024-01-01T00:00:00Z",
        "dns_sec": "disabled"
    }
    
    mock_client.list_records.return_value = [
        {
            "id": "record-123",
            "type": "A",
            "name": "@",
            "data": "192.168.1.100",
            "ttl": 300,
            "priority": None
        },
        {
            "id": "record-456",
            "type": "MX",
            "name": "@",
            "data": "mail.example.com",
            "ttl": 300,
            "priority": 10
        }
    ]
    
    mock_client.create_record.return_value = {
        "id": "new-record-789",
        "type": "A",
        "name": "www",
        "data": "192.168.1.100",
        "ttl": 300
    }
    
    mock_client.create_domain.return_value = {
        "domain": "newdomain.com",
        "date_created": "2024-12-20T00:00:00Z"
    }
    
    return mock_client


@pytest.fixture(autouse=True)
def mock_env_api_key(monkeypatch, mock_api_key):
    """Automatically set the API key environment variable for all tests."""
    monkeypatch.setenv("VULTR_API_KEY", mock_api_key)


@pytest.fixture
def sample_domain_data():
    """Sample domain data for testing."""
    return {
        "domain": "example.com",
        "date_created": "2024-01-01T00:00:00Z",
        "dns_sec": "disabled"
    }


@pytest.fixture
def sample_record_data():
    """Sample DNS record data for testing."""
    return {
        "id": "record-123",
        "type": "A", 
        "name": "www",
        "data": "192.168.1.100",
        "ttl": 300,
        "priority": None
    }


@pytest.fixture
def sample_records():
    """Sample list of DNS records for testing."""
    return [
        {
            "id": "record-123",
            "type": "A",
            "name": "@",
            "data": "192.168.1.100",
            "ttl": 300
        },
        {
            "id": "record-456", 
            "type": "A",
            "name": "www",
            "data": "192.168.1.100",
            "ttl": 300
        },
        {
            "id": "record-789",
            "type": "MX",
            "name": "@", 
            "data": "mail.example.com",
            "ttl": 300,
            "priority": 10
        },
        {
            "id": "record-999",
            "type": "TXT",
            "name": "@",
            "data": "v=spf1 include:_spf.google.com ~all",
            "ttl": 300
        }
    ]


# Configure pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "mcp: mark test as MCP-specific"
    )
