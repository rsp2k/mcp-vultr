"""
Comprehensive error handling tests for the VultrDNSClient.

This module tests error scenarios specific to the high-level DNS client,
focusing on validation, error recovery, and edge cases.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from mcp_vultr.client import VultrDNSClient
from mcp_vultr.server import (
    VultrAPIError,
    VultrAuthError,
    VultrRateLimitError,
    VultrResourceNotFoundError,
    VultrValidationError,
)


class TestClientInitializationErrors:
    """Test client initialization error scenarios."""

    def test_client_init_without_api_key(self):
        """Test client initialization without API key."""
        with pytest.raises((ValueError, TypeError)):
            VultrDNSClient(api_key=None)

    def test_client_init_with_empty_api_key(self):
        """Test client initialization with empty API key."""
        with pytest.raises((ValueError, TypeError)):
            VultrDNSClient(api_key="")

    def test_client_init_with_whitespace_api_key(self):
        """Test client initialization with whitespace-only API key."""
        with pytest.raises((ValueError, TypeError)):
            VultrDNSClient(api_key="   ")


class TestDomainOperationErrors:
    """Test domain operation error scenarios."""

    @pytest.fixture
    def client(self, mock_api_key):
        """Create client instance."""
        return VultrDNSClient(api_key=mock_api_key)

    @pytest.mark.asyncio
    async def test_list_domains_with_network_error(self, client):
        """Test list_domains with network errors."""
        with patch.object(client.server, 'list_domains') as mock_list:
            mock_list.side_effect = httpx.ConnectError("Network unreachable")

            with pytest.raises(Exception) as exc_info:
                await client.list_domains()
            
            error_str = str(exc_info.value)
            assert "network" in error_str.lower() or "connect" in error_str.lower()

    @pytest.mark.asyncio
    async def test_get_domain_with_invalid_format(self, client):
        """Test get_domain with invalid domain format."""
        with patch.object(client.server, 'get_domain') as mock_get:
            mock_get.side_effect = VultrValidationError(400, "Invalid domain format")

            with pytest.raises(VultrValidationError):
                await client.get_domain("invalid..domain.com")

    @pytest.mark.asyncio
    async def test_create_domain_duplicate_error(self, client):
        """Test create_domain with duplicate domain error."""
        with patch.object(client.server, 'create_domain') as mock_create:
            mock_create.side_effect = VultrValidationError(400, "Domain already exists")

            with pytest.raises(VultrValidationError):
                await client.create_domain("existing.com")

    @pytest.mark.asyncio
    async def test_delete_domain_not_found_error(self, client):
        """Test delete_domain with domain not found."""
        with patch.object(client.server, 'delete_domain') as mock_delete:
            mock_delete.side_effect = VultrResourceNotFoundError(404, "Domain not found")

            with pytest.raises(VultrResourceNotFoundError):
                await client.delete_domain("nonexistent.com")

    @pytest.mark.asyncio
    async def test_delete_domain_permission_error(self, client):
        """Test delete_domain with insufficient permissions."""
        with patch.object(client.server, 'delete_domain') as mock_delete:
            mock_delete.side_effect = VultrAuthError(403, "Insufficient permissions")

            with pytest.raises(VultrAuthError):
                await client.delete_domain("protected.com")


class TestRecordOperationErrors:
    """Test DNS record operation error scenarios."""

    @pytest.fixture
    def client(self, mock_api_key):
        """Create client instance."""
        return VultrDNSClient(api_key=mock_api_key)

    @pytest.mark.asyncio
    async def test_list_records_rate_limit_error(self, client):
        """Test list_records with rate limit error."""
        with patch.object(client.server, 'list_records') as mock_list:
            mock_list.side_effect = VultrRateLimitError(429, "Rate limit exceeded")

            with pytest.raises(VultrRateLimitError):
                await client.list_records("example.com")

    @pytest.mark.asyncio
    async def test_create_record_validation_errors(self, client):
        """Test create_record with various validation errors."""
        validation_errors = [
            ("Invalid IPv4 address", "A", "www", "999.999.999.999"),
            ("Invalid IPv6 address", "AAAA", "www", "invalid::ipv6"),
            ("Invalid record type", "INVALID", "www", "192.168.1.1"),
            ("Invalid MX priority", "MX", "mail", "mail.example.com", {"priority": -1}),
            ("Invalid TTL", "A", "www", "192.168.1.1", {"ttl": -300}),
        ]

        for error_msg, record_type, name, data, *extra_kwargs in validation_errors:
            kwargs = extra_kwargs[0] if extra_kwargs else {}
            
            with patch.object(client.server, 'create_record') as mock_create:
                mock_create.side_effect = VultrValidationError(400, error_msg)

                with pytest.raises(VultrValidationError):
                    await client.create_record("example.com", record_type, name, data, **kwargs)

    @pytest.mark.asyncio
    async def test_update_record_not_found_error(self, client):
        """Test update_record with record not found."""
        with patch.object(client.server, 'update_record') as mock_update:
            mock_update.side_effect = VultrResourceNotFoundError(404, "Record not found")

            with pytest.raises(VultrResourceNotFoundError):
                await client.update_record("example.com", "nonexistent_id", name="www", data="192.168.1.1")

    @pytest.mark.asyncio
    async def test_delete_record_permission_error(self, client):
        """Test delete_record with insufficient permissions."""
        with patch.object(client.server, 'delete_record') as mock_delete:
            mock_delete.side_effect = VultrAuthError(403, "Cannot delete system records")

            with pytest.raises(VultrAuthError):
                await client.delete_record("example.com", "system_record_id")

    @pytest.mark.asyncio
    async def test_get_record_with_malformed_response(self, client):
        """Test get_record with malformed API response."""
        with patch.object(client.server, 'get_record') as mock_get:
            # Return malformed record data
            mock_get.return_value = {"incomplete": "data"}

            result = await client.get_record("example.com", "record_id")
            # Should handle gracefully
            assert result is not None
            assert "incomplete" in result


class TestAnalysisAndValidationErrors:
    """Test DNS analysis and validation error scenarios."""

    @pytest.fixture
    def client(self, mock_api_key):
        """Create client instance."""
        return VultrDNSClient(api_key=mock_api_key)

    @pytest.mark.asyncio
    async def test_validate_record_comprehensive_errors(self, client):
        """Test comprehensive record validation errors."""
        invalid_records = [
            # Invalid A records
            ("A", "www", "999.999.999.999", "Invalid IPv4 address"),
            ("A", "www", "not.an.ip", "Invalid IPv4 address"),
            ("A", "", "192.168.1.1", "Empty record name"),
            
            # Invalid AAAA records
            ("AAAA", "www", "invalid::ipv6::address", "Invalid IPv6 address"),
            ("AAAA", "www", "2001:db8::gggg", "Invalid IPv6 address"),
            
            # Invalid CNAME records
            ("CNAME", "www", "", "Empty CNAME target"),
            ("CNAME", "www", "invalid..target.com", "Invalid CNAME target"),
            
            # Invalid MX records
            ("MX", "mail", "10", "Invalid MX record format"),
            ("MX", "mail", "invalid priority mail.example.com", "Invalid MX priority"),
            
            # Invalid SRV records
            ("SRV", "_service._tcp", "invalid format", "Invalid SRV record format"),
            ("SRV", "_service._tcp", "-1 5 80 target.com", "Invalid SRV priority"),
            ("SRV", "_service._tcp", "10 -5 80 target.com", "Invalid SRV weight"),
            ("SRV", "_service._tcp", "10 5 70000 target.com", "Invalid SRV port"),
        ]

        for record_type, name, data, expected_error in invalid_records:
            result = await client.validate_record(record_type, name, data)
            
            assert not result["valid"]
            assert expected_error.lower() in result["error"].lower()

    @pytest.mark.asyncio
    async def test_get_domain_summary_with_api_errors(self, client):
        """Test get_domain_summary with various API errors."""
        # Test with domain info error
        with patch.object(client.server, 'get_domain') as mock_get_domain:
            with patch.object(client.server, 'list_records') as mock_list_records:
                mock_get_domain.side_effect = VultrResourceNotFoundError(404, "Domain not found")
                mock_list_records.return_value = []

                result = await client.get_domain_summary("nonexistent.com")
                
                assert result is not None
                assert "error" in result
                assert "not found" in result["error"].lower()

        # Test with records listing error
        with patch.object(client.server, 'get_domain') as mock_get_domain:
            with patch.object(client.server, 'list_records') as mock_list_records:
                mock_get_domain.return_value = {"domain": "example.com", "date_created": "2023-01-01"}
                mock_list_records.side_effect = VultrAPIError(500, "Server error")

                result = await client.get_domain_summary("example.com")
                
                assert result is not None
                assert "error" in result
                assert "server error" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_analyze_dns_config_with_empty_domain(self, client):
        """Test analyze_dns_config with domain that has no records."""
        with patch.object(client.server, 'list_records') as mock_list:
            mock_list.return_value = []

            result = await client.analyze_dns_config("empty.com")
            
            assert result is not None
            assert result["total_records"] == 0
            assert len(result["issues"]) > 0  # Should flag missing essential records
            assert any("no records" in issue.lower() or "missing" in issue.lower() 
                      for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_analyze_dns_config_with_malformed_records(self, client):
        """Test analyze_dns_config with malformed record data."""
        malformed_records = [
            {"id": "1"},  # Missing required fields
            {"id": "2", "type": "A"},  # Missing name and data
            {"id": "3", "type": "INVALID", "name": "test", "data": "invalid"},
            {"id": "4", "type": "A", "name": "www", "data": "999.999.999.999"},  # Invalid IP
        ]

        with patch.object(client.server, 'list_records') as mock_list:
            mock_list.return_value = malformed_records

            result = await client.analyze_dns_config("example.com")
            
            assert result is not None
            assert result["total_records"] == len(malformed_records)
            assert len(result["issues"]) > 0  # Should identify malformed records


class TestSetupOperationErrors:
    """Test DNS setup operation error scenarios."""

    @pytest.fixture
    def client(self, mock_api_key):
        """Create client instance."""
        return VultrDNSClient(api_key=mock_api_key)

    @pytest.mark.asyncio
    async def test_setup_basic_website_partial_failures(self, client):
        """Test setup_basic_website with partial record creation failures."""
        call_count = 0
        
        def mock_create_record(domain, record_type, name, data, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 2:  # Second call fails (www record)
                raise VultrValidationError(400, "Duplicate record exists")
            elif call_count == 3:  # Third call fails (wildcard record)
                raise VultrRateLimitError(429, "Rate limit exceeded")
            
            return {"id": f"record_{call_count}", "type": record_type, "name": name}

        with patch.object(client.server, 'create_record', side_effect=mock_create_record):
            result = await client.setup_basic_website("example.com", "192.168.1.1")
            
            assert result is not None
            assert "created" in result
            assert "failed" in result
            assert len(result["created"]) > 0  # At least root A record should succeed
            assert len(result["failed"]) > 0   # Some records should fail

    @pytest.mark.asyncio
    async def test_setup_basic_website_all_failures(self, client):
        """Test setup_basic_website when all record creations fail."""
        with patch.object(client.server, 'create_record') as mock_create:
            mock_create.side_effect = VultrAuthError(403, "Insufficient permissions")

            result = await client.setup_basic_website("example.com", "192.168.1.1")
            
            assert result is not None
            assert len(result["created"]) == 0
            assert len(result["failed"]) > 0
            assert all("permissions" in error.lower() for error in result["failed"].values())

    @pytest.mark.asyncio
    async def test_setup_email_invalid_mx_server(self, client):
        """Test setup_email_dns with invalid MX server format."""
        result = await client.setup_email_dns("example.com", "invalid..mx.server")
        
        assert result is not None
        assert len(result["created"]) == 0
        assert len(result["failed"]) > 0
        assert any("invalid" in error.lower() for error in result["failed"].values())

    @pytest.mark.asyncio
    async def test_setup_email_mx_record_creation_failure(self, client):
        """Test setup_email_dns with MX record creation failure."""
        with patch.object(client.server, 'create_record') as mock_create:
            mock_create.side_effect = VultrValidationError(400, "MX record limit exceeded")

            result = await client.setup_email_dns("example.com", "mail.example.com")
            
            assert result is not None
            assert len(result["created"]) == 0
            assert len(result["failed"]) > 0
            assert "limit" in list(result["failed"].values())[0].lower()


class TestZoneFileOperationErrors:
    """Test zone file operation error scenarios."""

    @pytest.fixture
    def client(self, mock_api_key):
        """Create client instance."""
        return VultrDNSClient(api_key=mock_api_key)

    @pytest.mark.asyncio
    async def test_export_zone_file_with_api_error(self, client):
        """Test export_zone_file with API error."""
        with patch.object(client.server, 'list_records') as mock_list:
            mock_list.side_effect = VultrAPIError(500, "Internal server error")

            with pytest.raises(VultrAPIError):
                await client.export_zone_file("example.com")

    @pytest.mark.asyncio
    async def test_export_zone_file_empty_domain(self, client):
        """Test export_zone_file with domain that has no records."""
        with patch.object(client.server, 'list_records') as mock_list:
            mock_list.return_value = []

            result = await client.export_zone_file("empty.com")
            
            assert result is not None
            assert "empty.com" in result
            assert "$TTL" in result  # Should have basic zone structure

    @pytest.mark.asyncio
    async def test_import_zone_file_parse_errors(self, client):
        """Test import_zone_file with various parsing errors."""
        malformed_zone_files = [
            "",  # Empty zone file
            "Not a zone file at all",  # Invalid content
            "$TTL invalid\n@ IN SOA invalid syntax",  # Syntax errors
            "$TTL 3600\n@ IN SOA missing.fields",  # Missing required fields
        ]

        for malformed_zone in malformed_zone_files:
            with pytest.raises(Exception):  # Should raise parsing error
                await client.import_zone_file("example.com", malformed_zone)

    @pytest.mark.asyncio
    async def test_import_zone_file_record_creation_failures(self, client):
        """Test import_zone_file with record creation failures."""
        valid_zone = """
$TTL 3600
@       IN  SOA  ns1.example.com. admin.example.com. (
    2023010101 3600 1800 604800 86400
)
www     IN  A    192.168.1.1
mail    IN  MX   10 mail.example.com.
"""

        call_count = 0
        
        def mock_create_record(domain, record_type, name, data, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 2:  # Second record fails
                raise VultrValidationError(400, "Duplicate record")
            
            return {"id": f"record_{call_count}", "type": record_type}

        with patch.object(client.server, 'create_record', side_effect=mock_create_record):
            result = await client.import_zone_file("example.com", valid_zone)
            
            assert result is not None
            assert "created" in result
            assert "failed" in result
            assert len(result["created"]) > 0  # At least one should succeed
            assert len(result["failed"]) > 0   # At least one should fail


class TestClientErrorRecovery:
    """Test client error recovery and resilience."""

    @pytest.fixture
    def client(self, mock_api_key):
        """Create client instance."""
        return VultrDNSClient(api_key=mock_api_key)

    @pytest.mark.asyncio
    async def test_client_continues_after_temporary_error(self, client):
        """Test that client continues to work after temporary errors."""
        call_count = 0
        
        def mock_list_domains():
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call fails
                raise VultrRateLimitError(429, "Rate limit exceeded")
            else:
                # Second call succeeds
                return [{"domain": "example.com", "date_created": "2023-01-01"}]

        with patch.object(client.server, 'list_domains', side_effect=mock_list_domains):
            # First call should fail
            with pytest.raises(VultrRateLimitError):
                await client.list_domains()
            
            # Second call should succeed
            result = await client.list_domains()
            assert len(result) == 1
            assert result[0]["domain"] == "example.com"

    @pytest.mark.asyncio
    async def test_client_handles_mixed_operation_results(self, client):
        """Test client handling of mixed success/failure in batch operations."""
        # Test scenario where some operations in a batch succeed and others fail
        
        call_count = 0
        
        def mock_create_record(domain, record_type, name, data, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count % 2 == 0:  # Even calls fail
                raise VultrValidationError(400, f"Failed to create {name} record")
            else:  # Odd calls succeed
                return {"id": f"record_{call_count}", "type": record_type, "name": name}

        with patch.object(client.server, 'create_record', side_effect=mock_create_record):
            result = await client.setup_basic_website("example.com", "192.168.1.1")
            
            # Should have both successes and failures
            assert len(result["created"]) > 0
            assert len(result["failed"]) > 0