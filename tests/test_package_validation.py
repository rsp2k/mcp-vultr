"""Test runner and validation tests."""

import os
import sys
from pathlib import Path

import pytest

# Add the src directory to the path so we can import the package
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def test_package_imports():
    """Test that all main package imports work correctly."""
    # Test main package imports
    from mcp_vultr import VultrDNSClient, VultrDNSServer, create_mcp_server

    assert VultrDNSClient is not None
    assert VultrDNSServer is not None
    assert create_mcp_server is not None

    # Test individual module imports
    from mcp_vultr._version import __version__
    from mcp_vultr.cli_main import cli
    from mcp_vultr.client import VultrDNSClient as ClientClass
    from mcp_vultr.server import VultrDNSServer as ServerClass

    assert ServerClass is not None
    assert ClientClass is not None
    assert cli is not None
    assert __version__ is not None


def test_version_consistency():
    """Test that version is consistent across files."""
    from mcp_vultr._version import __version__

    # Read version from pyproject.toml
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        # Extract version from pyproject.toml
        for line in content.split("\n"):
            if line.strip().startswith("version = "):
                pyproject_version = line.split('"')[1]
                assert __version__ == pyproject_version, (
                    f"Version mismatch: __version__={__version__}, pyproject.toml={pyproject_version}"
                )
                break


def test_fastmcp_available():
    """Test that FastMCP is available for testing."""
    try:
        from fastmcp import Client, FastMCP

        assert FastMCP is not None
        assert Client is not None
    except ImportError:
        pytest.skip("FastMCP not available - install with: pip install fastmcp")


def test_mcp_server_creation():
    """Test that MCP server can be created without errors."""
    from mcp_vultr.server import create_mcp_server

    # This should work with any API key for creation (won't make API calls)
    server = create_mcp_server("test-api-key-for-testing")
    assert server is not None

    # Check that server has expected attributes (for low-level MCP server)
    assert hasattr(server, "list_tools") or hasattr(server, "_tools")
    assert hasattr(server, "list_resources") or hasattr(server, "_resources")


def test_cli_entry_points():
    """Test that CLI entry points are properly configured."""
    from mcp_vultr.cli_main import cli, server

    assert callable(cli)
    assert callable(server)


def test_test_markers():
    """Test that pytest markers are properly configured."""
    # This will fail if markers aren't properly configured in conftest.py
    import pytest

    # These should not raise warnings about unknown markers
    @pytest.mark.unit
    def dummy_unit_test():
        pass

    @pytest.mark.integration
    def dummy_integration_test():
        pass

    @pytest.mark.mcp
    def dummy_mcp_test():
        pass

    @pytest.mark.slow
    def dummy_slow_test():
        pass


def test_mock_fixtures_available(mock_api_key, mock_vultr_client, sample_domain_data):
    """Test that mock fixtures are available and working."""
    assert mock_api_key is not None
    assert mock_vultr_client is not None
    assert sample_domain_data is not None

    # Test that mock_vultr_client has expected methods
    assert hasattr(mock_vultr_client, "list_domains")
    assert hasattr(mock_vultr_client, "create_domain")
    assert hasattr(mock_vultr_client, "list_records")


@pytest.mark.asyncio
async def test_async_test_setup():
    """Test that async testing is properly configured."""
    # This test verifies that pytest-asyncio is working
    import asyncio

    async def dummy_async_function():
        await asyncio.sleep(0.01)
        return "async_result"

    result = await dummy_async_function()
    assert result == "async_result"


def test_environment_setup():
    """Test that test environment is properly set up."""
    # Check that we're not accidentally using real API keys in tests
    api_key = os.getenv("VULTR_API_KEY")
    if api_key:
        # If an API key is set, it should be a test key or we should be in a test environment
        assert "test" in api_key.lower() or api_key.startswith("test-"), (
            "Real API key detected in test environment - this could lead to accidental API calls"
        )


def test_package_structure():
    """Test that package structure is correct."""
    package_root = Path(__file__).parent.parent / "src" / "mcp_vultr"

    # Check that all expected files exist
    expected_files = [
        "__init__.py",
        "_version.py",
        "server.py",
        "client.py",
        "cli_main.py",
        "py.typed",
    ]
    
    # Check that CLI directory exists
    cli_dir = package_root / "cli"
    assert cli_dir.exists(), "CLI directory should exist"
    
    expected_cli_files = [
        "__init__.py",
        "dns.py",
        "billing.py",
        "compute.py",
        "utils.py",
    ]

    for file_name in expected_files:
        file_path = package_root / file_name
        assert file_path.exists(), f"Expected file {file_name} not found"
    
    for file_name in expected_cli_files:
        file_path = cli_dir / file_name
        assert file_path.exists(), f"Expected CLI file {file_name} not found"


if __name__ == "__main__":
    # Run this test file specifically
    pytest.main([__file__, "-v"])
