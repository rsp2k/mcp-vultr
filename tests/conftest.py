"""Configuration for pytest tests."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from mcp_vultr.server import create_mcp_server
from .mock_api_logger import logged_mock, mock_api_logger, enable_mock_api_logging


# Performance optimization: reuse event loop for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def mock_api_key():
    """Provide a mock API key for testing (session-scoped for performance)."""
    return "test-api-key-123456789"


@pytest.fixture(scope="session")
def mcp_server(mock_api_key):
    """Create a FastMCP server instance for testing (session-scoped for performance)."""
    return create_mcp_server(mock_api_key)


@pytest.fixture
def mock_vultr_client():
    """Create a mock VultrDNSServer for testing API interactions."""
    from mcp_vultr.server import VultrDNSServer

    mock_client = AsyncMock(spec=VultrDNSServer)
    
    # Add logging if enabled via environment variable or pytest option
    import os
    if os.environ.get("MOCK_API_LOGGING") == "true":
        enable_mock_api_logging(console=True)
        mock_client = logged_mock(mock_client, mock_api_logger)

    # Configure common mock responses
    mock_client.list_domains.return_value = [
        {
            "domain": "example.com",
            "date_created": "2024-01-01T00:00:00Z",
            "dns_sec": "disabled",
        },
        {
            "domain": "test.com",
            "date_created": "2024-01-02T00:00:00Z",
            "dns_sec": "enabled",
        },
    ]

    mock_client.get_domain.return_value = {
        "domain": "example.com",
        "date_created": "2024-01-01T00:00:00Z",
        "dns_sec": "disabled",
    }

    mock_client.list_records.return_value = [
        {
            "id": "record-123",
            "type": "A",
            "name": "@",
            "data": "192.168.1.100",
            "ttl": 300,
            "priority": None,
        },
        {
            "id": "record-456",
            "type": "MX",
            "name": "@",
            "data": "mail.example.com",
            "ttl": 300,
            "priority": 10,
        },
    ]

    mock_client.create_record.return_value = {
        "id": "new-record-789",
        "type": "A",
        "name": "www",
        "data": "192.168.1.100",
        "ttl": 300,
    }

    mock_client.create_domain.return_value = {
        "domain": "newdomain.com",
        "date_created": "2024-12-20T00:00:00Z",
    }

    return mock_client


@pytest.fixture(autouse=True)
def mock_env_api_key(monkeypatch, mock_api_key):
    """Automatically set the API key environment variable for all tests."""
    monkeypatch.setenv("VULTR_API_KEY", mock_api_key)


@pytest.fixture(scope="session")
def sample_domain_data():
    """Sample domain data for testing (session-scoped)."""
    return {
        "domain": "example.com",
        "date_created": "2024-01-01T00:00:00Z",
        "dns_sec": "disabled",
    }


@pytest.fixture(scope="session")
def sample_record_data():
    """Sample DNS record data for testing (session-scoped)."""
    return {
        "id": "record-123",
        "type": "A",
        "name": "www",
        "data": "192.168.1.100",
        "ttl": 300,
        "priority": None,
    }


@pytest.fixture(scope="session")
def sample_records():
    """Sample list of DNS records for testing (session-scoped)."""
    return [
        {
            "id": "record-123",
            "type": "A",
            "name": "@",
            "data": "192.168.1.100",
            "ttl": 300,
        },
        {
            "id": "record-456",
            "type": "A",
            "name": "www",
            "data": "192.168.1.100",
            "ttl": 300,
        },
        {
            "id": "record-789",
            "type": "MX",
            "name": "@",
            "data": "mail.example.com",
            "ttl": 300,
            "priority": 10,
        },
        {
            "id": "record-999",
            "type": "TXT",
            "name": "@",
            "data": "v=spf1 include:_spf.google.com ~all",
            "ttl": 300,
        },
    ]


# Performance optimization fixtures
@pytest.fixture(autouse=True)
def optimize_async_tests():
    """Automatically optimize async test execution."""
    # Set reasonable timeouts for async operations
    import asyncio
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


@pytest.fixture(scope="session", autouse=True)
def setup_test_performance():
    """Set up performance optimizations for the test session."""
    import warnings
    import logging
    
    # Reduce logging noise during tests
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Filter warnings that add overhead
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)


# Configure pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running (>10s)")
    config.addinivalue_line("markers", "fast: mark test as fast running (<5s)")
    config.addinivalue_line("markers", "mcp: mark test as MCP-specific")
    config.addinivalue_line("markers", "network: mark test as network-related")
    config.addinivalue_line("markers", "error_handling: mark test as error scenario")
    config.addinivalue_line("markers", "timeout_sensitive: mark test as sensitive to timeouts")
    config.addinivalue_line("markers", "tui: mark test as TUI application test")
    config.addinivalue_line("markers", "tui_unit: mark test as TUI unit test")
    config.addinivalue_line("markers", "tui_integration: mark test as TUI integration test")
    config.addinivalue_line("markers", "tui_snapshot: mark test as TUI snapshot test")
    config.addinivalue_line("markers", "tui_performance: mark test as TUI performance test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection for performance optimization."""
    # Auto-mark slow tests based on patterns
    for item in items:
        # Mark async tests that might be slow
        if "error" in item.name.lower() or "timeout" in item.name.lower():
            item.add_marker(pytest.mark.slow)
        
        # Mark fast unit tests
        if ("unit" in str(item.fspath) or 
            item.name.startswith("test_validate") or
            "validation" in item.name.lower()):
            item.add_marker(pytest.mark.fast)
        
        # Auto-mark TUI tests based on file patterns
        if "test_tui" in str(item.fspath):
            item.add_marker(pytest.mark.tui)
            
            # Add specific TUI markers based on test names
            if "performance" in item.name.lower() or "stress" in item.name.lower():
                item.add_marker(pytest.mark.tui_performance)
                item.add_marker(pytest.mark.slow)
            elif "snapshot" in item.name.lower() or "visual" in item.name.lower():
                item.add_marker(pytest.mark.tui_snapshot)
            elif "unit" in item.name.lower() or "widget" in item.name.lower():
                item.add_marker(pytest.mark.tui_unit)
            elif "integration" in item.name.lower() or "workflow" in item.name.lower():
                item.add_marker(pytest.mark.tui_integration)


def pytest_sessionfinish(session, exitstatus):
    """Print mock API summary at the end of the test session."""
    import os
    if os.environ.get("MOCK_API_LOGGING") == "true":
        mock_api_logger.print_summary()


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset mocks between tests for consistency."""
    # This is a placeholder for any mock reset logic needed
    # Currently not needed but could be useful for complex mock scenarios
    yield
