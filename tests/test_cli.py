"""Tests for the CLI module."""

from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from mcp_vultr.cli_main import cli


@pytest.fixture
def cli_runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_client_for_cli():
    """Create a mock VultrDNSClient for CLI tests."""
    mock_client = AsyncMock()

    # Configure mock responses
    mock_client.domains.return_value = [
        {"domain": "example.com", "date_created": "2024-01-01"},
        {"domain": "test.com", "date_created": "2024-01-02"},
    ]

    mock_client.get_domain_summary.return_value = {
        "domain": "example.com",
        "total_records": 5,
        "record_types": {"A": 2, "MX": 1, "TXT": 2},
        "configuration": {
            "has_root_record": True,
            "has_www_subdomain": True,
            "has_email_setup": True,
        },
    }

    mock_client.records.return_value = [
        {"id": "rec1", "type": "A", "name": "@", "data": "192.168.1.100", "ttl": 300},
        {"id": "rec2", "type": "A", "name": "www", "data": "192.168.1.100", "ttl": 300},
    ]

    mock_client.add_domain.return_value = {"domain": "newdomain.com"}
    mock_client.add_record.return_value = {
        "id": "new-rec",
        "type": "A",
        "name": "www",
        "data": "192.168.1.100",
    }
    mock_client.remove_record.return_value = True

    mock_client.setup_basic_website.return_value = {
        "domain": "example.com",
        "created_records": ["A record for root domain", "A record for www subdomain"],
        "errors": [],
    }

    mock_client.setup_email.return_value = {
        "domain": "example.com",
        "created_records": ["MX record for mail.example.com"],
        "errors": [],
    }

    return mock_client


@pytest.mark.unit
class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_help(self, cli_runner):
        """Test CLI help output."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Vultr DNS MCP" in result.output

    def test_cli_version(self, cli_runner):
        """Test CLI version output."""
        result = cli_runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_cli_without_api_key(self, cli_runner):
        """Test CLI behavior without API key."""
        with patch.dict("os.environ", {}, clear=True):
            result = cli_runner.invoke(cli, ["domains", "list"])
            assert result.exit_code == 1
            assert "VULTR_API_KEY is required" in result.output


@pytest.mark.unit
class TestServerCommand:
    """Test the server command."""

    def test_server_command_without_api_key(self, cli_runner):
        """Test server command without API key."""
        with patch.dict("os.environ", {}, clear=True):
            result = cli_runner.invoke(cli, ["server"])
            assert result.exit_code == 1
            assert "VULTR_API_KEY is required" in result.output

    @pytest.mark.xfail(reason="FastMCP server has import issues that need fixing")
    @patch("mcp_vultr.fastmcp_server.run_server")
    def test_server_command_with_api_key(self, mock_run_server, cli_runner):
        """Test server command with API key."""
        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            # Mock run_server to return immediately without doing anything
            mock_run_server.return_value = None

            result = cli_runner.invoke(cli, ["server"])
            # Should exit normally after calling run_server
            assert result.exit_code == 0
            assert "Starting Vultr DNS MCP Server" in result.output
            mock_run_server.assert_called_once_with("test-key")

    @patch("mcp_vultr.fastmcp_server.run_server")
    def test_server_command_with_error(self, mock_run_server, cli_runner):
        """Test server command with error."""
        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            mock_run_server.side_effect = Exception("Server error")

            result = cli_runner.invoke(cli, ["server"])
            assert result.exit_code == 1
            assert "Error starting server:" in result.output


@pytest.mark.unit
class TestDomainsCommands:
    """Test domain management commands."""

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_list_domains(self, mock_client_class, cli_runner, mock_client_for_cli):
        """Test domains list command."""
        mock_client_class.return_value = mock_client_for_cli

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(cli, ["domains", "list"])

            assert result.exit_code == 0
            assert "example.com" in result.output
            assert "test.com" in result.output
            mock_client_for_cli.domains.assert_called_once()

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_list_domains_empty(self, mock_client_class, cli_runner):
        """Test domains list command with no domains."""
        mock_client = AsyncMock()
        mock_client.domains.return_value = []
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(cli, ["domains", "list"])

            assert result.exit_code == 0
            assert "No domains found" in result.output

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_domain_info(self, mock_client_class, cli_runner, mock_client_for_cli):
        """Test domains info command."""
        mock_client_class.return_value = mock_client_for_cli

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(cli, ["domains", "info", "example.com"])

            assert result.exit_code == 0
            assert "example.com" in result.output
            assert "Total Records: 5" in result.output
            mock_client_for_cli.get_domain_summary.assert_called_once_with(
                "example.com"
            )

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_domain_info_error(self, mock_client_class, cli_runner):
        """Test domains info command with error."""
        mock_client = AsyncMock()
        mock_client.get_domain_summary.return_value = {"error": "Domain not found"}
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(cli, ["domains", "info", "nonexistent.com"])

            assert result.exit_code == 1
            assert "Domain not found" in result.output

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_create_domain(self, mock_client_class, cli_runner, mock_client_for_cli):
        """Test domains create command."""
        mock_client_class.return_value = mock_client_for_cli

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(
                cli, ["domains", "create", "newdomain.com", "192.168.1.100"]
            )

            assert result.exit_code == 0
            assert "Created domain newdomain.com" in result.output
            mock_client_for_cli.add_domain.assert_called_once_with(
                "newdomain.com", "192.168.1.100"
            )

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_create_domain_error(self, mock_client_class, cli_runner):
        """Test domains create command with error."""
        mock_client = AsyncMock()
        mock_client.add_domain.return_value = {"error": "Domain already exists"}
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(
                cli, ["domains", "create", "existing.com", "192.168.1.100"]
            )

            assert result.exit_code == 1
            assert "Domain already exists" in result.output


@pytest.mark.unit
class TestRecordsCommands:
    """Test DNS records commands."""

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_list_records(self, mock_client_class, cli_runner, mock_client_for_cli):
        """Test records list command."""
        mock_client_class.return_value = mock_client_for_cli

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(cli, ["records", "list", "example.com"])

            assert result.exit_code == 0
            assert "example.com" in result.output
            assert "192.168.1.100" in result.output  # Check for record data instead
            mock_client_for_cli.records.assert_called_once_with("example.com")

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_list_records_filtered(
        self, mock_client_class, cli_runner, mock_client_for_cli
    ):
        """Test records list command with type filter."""
        mock_client_class.return_value = mock_client_for_cli

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(
                cli, ["records", "list", "example.com", "--type", "A"]
            )

            assert result.exit_code == 0
            mock_client_for_cli.find_records_by_type.assert_called_once_with(
                "example.com", "A"
            )

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_list_records_empty(self, mock_client_class, cli_runner):
        """Test records list command with no records."""
        mock_client = AsyncMock()
        mock_client.records.return_value = []
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(cli, ["records", "list", "example.com"])

            assert result.exit_code == 0
            assert "No records found" in result.output

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_add_record(self, mock_client_class, cli_runner, mock_client_for_cli):
        """Test records add command."""
        mock_client_class.return_value = mock_client_for_cli

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(
                cli, ["records", "add", "example.com", "A", "www", "192.168.1.100"]
            )

            assert result.exit_code == 0
            assert "Created A record" in result.output
            mock_client_for_cli.add_record.assert_called_once_with(
                "example.com", "A", "www", "192.168.1.100", None, None
            )

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_add_record_with_ttl_and_priority(
        self, mock_client_class, cli_runner, mock_client_for_cli
    ):
        """Test records add command with TTL and priority."""
        mock_client_class.return_value = mock_client_for_cli

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(
                cli,
                [
                    "records",
                    "add",
                    "example.com",
                    "MX",
                    "@",
                    "mail.example.com",
                    "--ttl",
                    "600",
                    "--priority",
                    "10",
                ],
            )

            assert result.exit_code == 0
            mock_client_for_cli.add_record.assert_called_once_with(
                "example.com", "MX", "@", "mail.example.com", 600, 10
            )

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_add_record_error(self, mock_client_class, cli_runner):
        """Test records add command with error."""
        mock_client = AsyncMock()
        mock_client.add_record.return_value = {"error": "Invalid record"}
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(
                cli, ["records", "add", "example.com", "A", "www", "invalid-ip"]
            )

            assert result.exit_code == 1
            assert "Invalid record" in result.output

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_delete_record(self, mock_client_class, cli_runner, mock_client_for_cli):
        """Test records delete command."""
        mock_client_class.return_value = mock_client_for_cli

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(
                cli, ["records", "delete", "example.com", "record-123"], input="y\n"
            )  # Confirm deletion

            assert result.exit_code == 0
            assert "Deleted record record-123" in result.output
            mock_client_for_cli.remove_record.assert_called_once_with(
                "example.com", "record-123"
            )

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_delete_record_failure(self, mock_client_class, cli_runner):
        """Test records delete command failure."""
        mock_client = AsyncMock()
        mock_client.remove_record.return_value = False
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(
                cli, ["records", "delete", "example.com", "record-123"], input="y\n"
            )

            assert result.exit_code == 1
            assert "Failed to delete" in result.output


@pytest.mark.unit
class TestSetupCommands:
    """Test setup utility commands."""

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_setup_website(self, mock_client_class, cli_runner, mock_client_for_cli):
        """Test setup-website command."""
        mock_client_class.return_value = mock_client_for_cli

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(
                cli, ["setup-website", "example.com", "192.168.1.100"]
            )

            assert result.exit_code == 0
            assert "Setting up website" in result.output
            assert "Website setup complete" in result.output
            mock_client_for_cli.setup_basic_website.assert_called_once_with(
                "example.com", "192.168.1.100", include_www=True, ttl=None
            )

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_setup_website_no_www(
        self, mock_client_class, cli_runner, mock_client_for_cli
    ):
        """Test setup-website command without www."""
        mock_client_class.return_value = mock_client_for_cli

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(
                cli, ["setup-website", "example.com", "192.168.1.100", "--no-www"]
            )

            assert result.exit_code == 0
            mock_client_for_cli.setup_basic_website.assert_called_once_with(
                "example.com", "192.168.1.100", include_www=False, ttl=None
            )

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_setup_website_with_ttl(
        self, mock_client_class, cli_runner, mock_client_for_cli
    ):
        """Test setup-website command with custom TTL."""
        mock_client_class.return_value = mock_client_for_cli

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(
                cli, ["setup-website", "example.com", "192.168.1.100", "--ttl", "600"]
            )

            assert result.exit_code == 0
            mock_client_for_cli.setup_basic_website.assert_called_once_with(
                "example.com", "192.168.1.100", include_www=True, ttl=600
            )

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_setup_website_with_errors(self, mock_client_class, cli_runner):
        """Test setup-website command with errors."""
        mock_client = AsyncMock()
        mock_client.setup_basic_website.return_value = {
            "domain": "example.com",
            "created_records": ["A record for root domain"],
            "errors": ["Failed to create www record"],
        }
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(
                cli, ["setup-website", "example.com", "192.168.1.100"]
            )

            assert result.exit_code == 0
            assert "Setup completed with some errors" in result.output

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_setup_email(self, mock_client_class, cli_runner, mock_client_for_cli):
        """Test setup-email command."""
        mock_client_class.return_value = mock_client_for_cli

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(
                cli, ["setup-email", "example.com", "mail.example.com"]
            )

            assert result.exit_code == 0
            assert "Setting up email" in result.output
            assert "Email setup complete" in result.output
            mock_client_for_cli.setup_email.assert_called_once_with(
                "example.com", "mail.example.com", priority=10, ttl=None
            )

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_setup_email_custom_priority(
        self, mock_client_class, cli_runner, mock_client_for_cli
    ):
        """Test setup-email command with custom priority."""
        mock_client_class.return_value = mock_client_for_cli

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(
                cli,
                ["setup-email", "example.com", "mail.example.com", "--priority", "5"],
            )

            assert result.exit_code == 0
            mock_client_for_cli.setup_email.assert_called_once_with(
                "example.com", "mail.example.com", priority=5, ttl=None
            )


@pytest.mark.unit
class TestCLIErrorHandling:
    """Test CLI error handling."""

    @patch("mcp_vultr.cli.dns.VultrDNSClient")
    def test_api_exception_handling(self, mock_client_class, cli_runner):
        """Test CLI handling of API exceptions."""
        mock_client = AsyncMock()
        mock_client.domains.side_effect = Exception("Network error")
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(cli, ["domains", "list"])

            assert result.exit_code == 1
            assert "Network error" in result.output

    def test_missing_arguments(self, cli_runner):
        """Test CLI behavior with missing arguments."""
        with patch.dict("os.environ", {"VULTR_API_KEY": "test-key"}):
            result = cli_runner.invoke(cli, ["domains", "info"])

            assert result.exit_code == 2  # Click argument error

    def test_invalid_command(self, cli_runner):
        """Test CLI behavior with invalid command."""
        result = cli_runner.invoke(cli, ["invalid-command"])
        assert result.exit_code == 2


if __name__ == "__main__":
    pytest.main([__file__])
