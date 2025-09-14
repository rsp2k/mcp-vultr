"""
Comprehensive CLI error handling tests.

This module tests error scenarios specific to the command-line interface,
focusing on argument validation, user input handling, and error reporting.
"""

import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner

from mcp_vultr.cli_main import cli
from mcp_vultr.server import (
    VultrAPIError,
    VultrAuthError,
    VultrRateLimitError,
    VultrResourceNotFoundError,
    VultrValidationError,
)


class TestCLIAuthenticationErrors:
    """Test CLI authentication error scenarios."""

    def test_cli_missing_api_key_environment_variable(self):
        """Test CLI behavior when VULTR_API_KEY environment variable is missing."""
        runner = CliRunner()
        
        # Test with no API key in environment
        with patch.dict('os.environ', {}, clear=True):
            result = runner.invoke(cli, ['domains', 'list'])
            
            assert result.exit_code != 0
            assert "api key" in result.output.lower() or "environment" in result.output.lower()

    def test_cli_empty_api_key_environment_variable(self):
        """Test CLI behavior with empty VULTR_API_KEY environment variable."""
        runner = CliRunner()
        
        with patch.dict('os.environ', {'VULTR_API_KEY': ''}):
            result = runner.invoke(cli, ['domains', 'list'])
            
            assert result.exit_code != 0
            assert "api key" in result.output.lower() or "empty" in result.output.lower()

    def test_cli_invalid_api_key_format(self):
        """Test CLI behavior with invalid API key format."""
        runner = CliRunner()
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'invalid-key-format'}):
            with patch('mcp_vultr.client.VultrDNSClient') as mock_client:
                mock_client.side_effect = ValueError("Invalid API key format")
                
                result = runner.invoke(cli, ['domains', 'list'])
                
                assert result.exit_code != 0
                assert "invalid" in result.output.lower() or "format" in result.output.lower()


class TestDomainCommandErrors:
    """Test domain command error scenarios."""

    @pytest.fixture
    def mock_client(self):
        """Mock client for testing."""
        with patch('mcp_vultr.client.VultrDNSClient') as mock:
            yield mock.return_value

    def test_domains_list_network_error(self, mock_client):
        """Test domains list with network error."""
        runner = CliRunner()
        
        mock_client.list_domains.side_effect = VultrAPIError(500, "Network error")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['domains', 'list'])
            
            assert result.exit_code != 0
            assert "error" in result.output.lower()

    def test_domains_list_auth_error(self, mock_client):
        """Test domains list with authentication error."""
        runner = CliRunner()
        
        mock_client.list_domains.side_effect = VultrAuthError(401, "Invalid API key")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['domains', 'list'])
            
            assert result.exit_code != 0
            assert "auth" in result.output.lower() or "401" in result.output

    def test_domains_get_not_found_error(self, mock_client):
        """Test domains get with domain not found."""
        runner = CliRunner()
        
        mock_client.get_domain.side_effect = VultrResourceNotFoundError(404, "Domain not found")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['domains', 'get', 'nonexistent.com'])
            
            assert result.exit_code != 0
            assert "not found" in result.output.lower()

    def test_domains_create_validation_error(self, mock_client):
        """Test domains create with validation error."""
        runner = CliRunner()
        
        mock_client.create_domain.side_effect = VultrValidationError(400, "Invalid domain name")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['domains', 'create', 'invalid..domain.com'])
            
            assert result.exit_code != 0
            assert "invalid" in result.output.lower() or "validation" in result.output.lower()

    def test_domains_create_duplicate_error(self, mock_client):
        """Test domains create with duplicate domain error."""
        runner = CliRunner()
        
        mock_client.create_domain.side_effect = VultrValidationError(400, "Domain already exists")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['domains', 'create', 'existing.com'])
            
            assert result.exit_code != 0
            assert "exists" in result.output.lower() or "duplicate" in result.output.lower()

    def test_domains_delete_permission_error(self, mock_client):
        """Test domains delete with permission error."""
        runner = CliRunner()
        
        mock_client.delete_domain.side_effect = VultrAuthError(403, "Insufficient permissions")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['domains', 'delete', 'protected.com'])
            
            assert result.exit_code != 0
            assert "permission" in result.output.lower() or "403" in result.output

    def test_domains_delete_missing_confirmation(self):
        """Test domains delete without confirmation flag."""
        runner = CliRunner()
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['domains', 'delete', 'example.com'])
            
            # Should prompt for confirmation or fail without --yes flag
            assert result.exit_code != 0 or "confirm" in result.output.lower()


class TestRecordCommandErrors:
    """Test record command error scenarios."""

    @pytest.fixture
    def mock_client(self):
        """Mock client for testing."""
        with patch('mcp_vultr.client.VultrDNSClient') as mock:
            yield mock.return_value

    def test_records_list_rate_limit_error(self, mock_client):
        """Test records list with rate limit error."""
        runner = CliRunner()
        
        mock_client.list_records.side_effect = VultrRateLimitError(429, "Rate limit exceeded")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['records', 'list', 'example.com'])
            
            assert result.exit_code != 0
            assert "rate limit" in result.output.lower() or "429" in result.output

    def test_records_create_invalid_record_type(self, mock_client):
        """Test records create with invalid record type."""
        runner = CliRunner()
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, [
                'records', 'create', 'example.com', 'INVALID', 'test', '192.168.1.1'
            ])
            
            # Should fail validation before making API call
            assert result.exit_code != 0
            assert "invalid" in result.output.lower() or "type" in result.output.lower()

    def test_records_create_invalid_ip_address(self, mock_client):
        """Test records create with invalid IP address."""
        runner = CliRunner()
        
        mock_client.create_record.side_effect = VultrValidationError(400, "Invalid IP address")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, [
                'records', 'create', 'example.com', 'A', 'test', '999.999.999.999'
            ])
            
            assert result.exit_code != 0
            assert "ip" in result.output.lower() or "invalid" in result.output.lower()

    def test_records_create_missing_required_arguments(self):
        """Test records create with missing required arguments."""
        runner = CliRunner()
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            # Missing data argument
            result = runner.invoke(cli, [
                'records', 'create', 'example.com', 'A', 'test'
            ])
            
            assert result.exit_code != 0
            assert "usage" in result.output.lower() or "missing" in result.output.lower()

    def test_records_update_record_not_found(self, mock_client):
        """Test records update with record not found."""
        runner = CliRunner()
        
        mock_client.update_record.side_effect = VultrResourceNotFoundError(404, "Record not found")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, [
                'records', 'update', 'example.com', 'invalid_id', '--name', 'test', '--data', '192.168.1.1'
            ])
            
            assert result.exit_code != 0
            assert "not found" in result.output.lower()

    def test_records_delete_missing_record_id(self):
        """Test records delete with missing record ID."""
        runner = CliRunner()
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, [
                'records', 'delete', 'example.com'
            ])
            
            assert result.exit_code != 0
            assert "usage" in result.output.lower() or "missing" in result.output.lower()

    def test_records_update_no_changes_specified(self):
        """Test records update with no changes specified."""
        runner = CliRunner()
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, [
                'records', 'update', 'example.com', 'record_id'
            ])
            
            # Should require at least one change parameter
            assert result.exit_code != 0
            assert "change" in result.output.lower() or "specify" in result.output.lower()


class TestSetupCommandErrors:
    """Test setup command error scenarios."""

    @pytest.fixture
    def mock_client(self):
        """Mock client for testing."""
        with patch('mcp_vultr.client.VultrDNSClient') as mock:
            yield mock.return_value

    def test_setup_website_invalid_ip_format(self, mock_client):
        """Test setup website with invalid IP address format."""
        runner = CliRunner()
        
        mock_client.setup_basic_website.side_effect = VultrValidationError(400, "Invalid IP address")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, [
                'setup', 'website', 'example.com', 'not.an.ip.address'
            ])
            
            assert result.exit_code != 0
            assert "ip" in result.output.lower() or "invalid" in result.output.lower()

    def test_setup_website_partial_failures(self, mock_client):
        """Test setup website with partial record creation failures."""
        runner = CliRunner()
        
        # Mock partial success response
        mock_client.setup_basic_website.return_value = {
            "created": {"@": "record_1"},
            "failed": {
                "www": "Duplicate record exists",
                "*": "Rate limit exceeded"
            }
        }
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, [
                'setup', 'website', 'example.com', '192.168.1.1'
            ])
            
            # Should report both successes and failures
            assert "created" in result.output.lower()
            assert "failed" in result.output.lower() or "error" in result.output.lower()

    def test_setup_email_invalid_mx_server(self, mock_client):
        """Test setup email with invalid MX server format."""
        runner = CliRunner()
        
        mock_client.setup_email_dns.side_effect = VultrValidationError(400, "Invalid MX server")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, [
                'setup', 'email', 'example.com', 'invalid..mx.server'
            ])
            
            assert result.exit_code != 0
            assert "mx" in result.output.lower() or "invalid" in result.output.lower()

    def test_setup_email_all_records_failed(self, mock_client):
        """Test setup email when all record creations fail."""
        runner = CliRunner()
        
        mock_client.setup_email_dns.return_value = {
            "created": {},
            "failed": {
                "MX": "Permission denied",
                "TXT": "Permission denied"
            }
        }
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, [
                'setup', 'email', 'example.com', 'mail.example.com'
            ])
            
            assert result.exit_code != 0
            assert "failed" in result.output.lower() or "error" in result.output.lower()


class TestAnalyzeCommandErrors:
    """Test analyze command error scenarios."""

    @pytest.fixture
    def mock_client(self):
        """Mock client for testing."""
        with patch('mcp_vultr.client.VultrDNSClient') as mock:
            yield mock.return_value

    def test_analyze_domain_not_found(self, mock_client):
        """Test analyze with domain not found."""
        runner = CliRunner()
        
        mock_client.analyze_dns_config.side_effect = VultrResourceNotFoundError(404, "Domain not found")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['analyze', 'nonexistent.com'])
            
            assert result.exit_code != 0
            assert "not found" in result.output.lower()

    def test_analyze_empty_domain(self, mock_client):
        """Test analyze with domain that has no records."""
        runner = CliRunner()
        
        mock_client.analyze_dns_config.return_value = {
            "total_records": 0,
            "record_types": {},
            "issues": ["No DNS records found for this domain"],
            "score": 0,
            "recommendations": ["Add basic A records to make domain accessible"]
        }
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['analyze', 'empty.com'])
            
            # Should report the analysis even for empty domain
            assert result.exit_code == 0
            assert "no records" in result.output.lower() or "empty" in result.output.lower()

    def test_analyze_api_error(self, mock_client):
        """Test analyze with API error."""
        runner = CliRunner()
        
        mock_client.analyze_dns_config.side_effect = VultrAPIError(500, "Internal server error")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['analyze', 'example.com'])
            
            assert result.exit_code != 0
            assert "error" in result.output.lower()


class TestServerCommandErrors:
    """Test server command error scenarios."""

    def test_server_command_missing_api_key(self):
        """Test server command without API key."""
        runner = CliRunner()
        
        with patch.dict('os.environ', {}, clear=True):
            result = runner.invoke(cli, ['server'])
            
            assert result.exit_code != 0
            assert "api key" in result.output.lower()

    def test_server_command_startup_error(self):
        """Test server command with startup error."""
        runner = CliRunner()
        
        with patch('mcp_vultr.server.create_mcp_server') as mock_create:
            mock_create.side_effect = ValueError("Failed to initialize server")
            
            with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
                result = runner.invoke(cli, ['server'])
                
                assert result.exit_code != 0
                assert "error" in result.output.lower() or "failed" in result.output.lower()


class TestCLIArgumentValidation:
    """Test CLI argument validation errors."""

    def test_invalid_command(self):
        """Test invalid CLI command."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['invalid_command'])
        
        assert result.exit_code != 0
        assert "usage" in result.output.lower() or "no such command" in result.output.lower()

    def test_invalid_subcommand(self):
        """Test invalid CLI subcommand."""
        runner = CliRunner()
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['domains', 'invalid_subcommand'])
            
            assert result.exit_code != 0
            assert "usage" in result.output.lower() or "no such command" in result.output.lower()

    def test_missing_required_domain_argument(self):
        """Test commands missing required domain argument."""
        runner = CliRunner()
        
        commands_requiring_domain = [
            ['records', 'list'],
            ['records', 'create', 'A', 'test', '192.168.1.1'],
            ['domains', 'get'],
            ['analyze']
        ]
        
        for command in commands_requiring_domain:
            with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
                result = runner.invoke(cli, command)
                
                assert result.exit_code != 0
                assert "usage" in result.output.lower() or "missing" in result.output.lower()

    def test_invalid_record_type_argument(self):
        """Test records create with invalid record type."""
        runner = CliRunner()
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, [
                'records', 'create', 'example.com', 'INVALIDTYPE', 'test', '192.168.1.1'
            ])
            
            assert result.exit_code != 0
            assert "invalid" in result.output.lower() or "type" in result.output.lower()

    def test_help_command_functionality(self):
        """Test that help commands work correctly."""
        runner = CliRunner()
        
        help_commands = [
            ['--help'],
            ['domains', '--help'],
            ['records', '--help'],
            ['setup', '--help'],
            ['analyze', '--help']
        ]
        
        for command in help_commands:
            result = runner.invoke(cli, command)
            
            assert result.exit_code == 0
            assert "usage" in result.output.lower() or "help" in result.output.lower()


class TestCLIOutputFormatting:
    """Test CLI output formatting in error scenarios."""

    @pytest.fixture
    def mock_client(self):
        """Mock client for testing."""
        with patch('mcp_vultr.client.VultrDNSClient') as mock:
            yield mock.return_value

    def test_json_output_format_with_error(self, mock_client):
        """Test JSON output format during error scenarios."""
        runner = CliRunner()
        
        mock_client.list_domains.side_effect = VultrAPIError(500, "Server error")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['domains', 'list', '--format', 'json'])
            
            assert result.exit_code != 0
            # Error output might still be in JSON format or regular text
            assert "error" in result.output.lower()

    def test_table_output_format_with_empty_results(self, mock_client):
        """Test table output format with empty results."""
        runner = CliRunner()
        
        mock_client.list_domains.return_value = []
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['domains', 'list', '--format', 'table'])
            
            assert result.exit_code == 0
            assert "no domains" in result.output.lower() or len(result.output.strip()) == 0

    def test_verbose_output_with_errors(self, mock_client):
        """Test verbose output during error scenarios."""
        runner = CliRunner()
        
        mock_client.get_domain.side_effect = VultrResourceNotFoundError(404, "Domain not found")
        
        with patch.dict('os.environ', {'VULTR_API_KEY': 'test-key'}):
            result = runner.invoke(cli, ['domains', 'get', 'nonexistent.com', '--verbose'])
            
            assert result.exit_code != 0
            # Verbose mode should include more details about the error
            assert "not found" in result.output.lower()
            # Verbose output might include more technical details