"""Tests for the VultrDNSClient module."""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_vultr.client import VultrDNSClient


@pytest.mark.unit
class TestVultrDNSClient:
    """Test the VultrDNSClient class."""

    def test_client_initialization(self, mock_api_key):
        """Test client initialization."""
        client = VultrDNSClient(mock_api_key)
        assert client.server is not None
        assert client.server.api_key == mock_api_key

    @pytest.mark.asyncio
    async def test_domains_method(self, mock_api_key, mock_vultr_client):
        """Test the domains() method."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.domains()

            assert result is not None
            mock_vultr_client.list_domains.assert_called_once()

    @pytest.mark.asyncio
    async def test_domain_method(self, mock_api_key, mock_vultr_client):
        """Test the domain() method."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.domain("example.com")

            assert result is not None
            mock_vultr_client.get_domain.assert_called_once_with("example.com")

    @pytest.mark.asyncio
    async def test_add_domain_method(self, mock_api_key, mock_vultr_client):
        """Test the add_domain() method."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.add_domain("newdomain.com", "192.168.1.100")

            assert result is not None
            mock_vultr_client.create_domain.assert_called_once_with(
                "newdomain.com", "192.168.1.100"
            )

    @pytest.mark.asyncio
    async def test_remove_domain_success(self, mock_api_key, mock_vultr_client):
        """Test successful domain removal."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.remove_domain("example.com")

            assert result is True
            mock_vultr_client.delete_domain.assert_called_once_with("example.com")

    @pytest.mark.asyncio
    async def test_remove_domain_failure(self, mock_api_key):
        """Test domain removal failure."""
        mock_client = AsyncMock()
        mock_client.delete_domain.side_effect = Exception("API Error")

        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.remove_domain("example.com")

            assert result is False

    @pytest.mark.asyncio
    async def test_records_method(self, mock_api_key, mock_vultr_client):
        """Test the records() method."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.records("example.com")

            assert result is not None
            mock_vultr_client.list_records.assert_called_once_with("example.com")

    @pytest.mark.asyncio
    async def test_add_record_method(self, mock_api_key, mock_vultr_client):
        """Test the add_record() method."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.add_record(
                "example.com", "A", "www", "192.168.1.100", 300
            )

            assert result is not None
            mock_vultr_client.create_record.assert_called_once_with(
                "example.com", "A", "www", "192.168.1.100", 300, None
            )

    @pytest.mark.asyncio
    async def test_update_record_method(self, mock_api_key, mock_vultr_client):
        """Test the update_record() method."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.update_record(
                "example.com", "record-123", "A", "www", "192.168.1.200", 600
            )

            assert result is not None
            mock_vultr_client.update_record.assert_called_once_with(
                "example.com", "record-123", "A", "www", "192.168.1.200", 600, None
            )

    @pytest.mark.asyncio
    async def test_remove_record_success(self, mock_api_key, mock_vultr_client):
        """Test successful record removal."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.remove_record("example.com", "record-123")

            assert result is True
            mock_vultr_client.delete_record.assert_called_once_with(
                "example.com", "record-123"
            )

    @pytest.mark.asyncio
    async def test_remove_record_failure(self, mock_api_key):
        """Test record removal failure."""
        mock_client = AsyncMock()
        mock_client.delete_record.side_effect = Exception("API Error")

        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.remove_record("example.com", "record-123")

            assert result is False

    @pytest.mark.asyncio
    async def test_record_method(self, mock_api_key, mock_vultr_client):
        """Test the record() method - covers line 70."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.record("example.com", "record-123")

            assert result is not None
            mock_vultr_client.get_record.assert_called_once_with("example.com", "record-123")


@pytest.mark.unit
class TestConvenienceMethods:
    """Test convenience methods for common record types."""

    @pytest.mark.asyncio
    async def test_add_a_record(self, mock_api_key, mock_vultr_client):
        """Test add_a_record convenience method."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.add_a_record(
                "example.com", "www", "192.168.1.100", 300
            )

            assert result is not None
            mock_vultr_client.create_record.assert_called_once_with(
                "example.com", "A", "www", "192.168.1.100", 300, None
            )

    @pytest.mark.asyncio
    async def test_add_aaaa_record(self, mock_api_key, mock_vultr_client):
        """Test add_aaaa_record convenience method."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.add_aaaa_record(
                "example.com", "www", "2001:db8::1", 300
            )

            assert result is not None
            mock_vultr_client.create_record.assert_called_once_with(
                "example.com", "AAAA", "www", "2001:db8::1", 300, None
            )

    @pytest.mark.asyncio
    async def test_add_cname_record(self, mock_api_key, mock_vultr_client):
        """Test add_cname_record convenience method."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.add_cname_record(
                "example.com", "www", "example.com", 300
            )

            assert result is not None
            mock_vultr_client.create_record.assert_called_once_with(
                "example.com", "CNAME", "www", "example.com", 300, None
            )

    @pytest.mark.asyncio
    async def test_add_mx_record(self, mock_api_key, mock_vultr_client):
        """Test add_mx_record convenience method."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.add_mx_record(
                "example.com", "@", "mail.example.com", 10, 300
            )

            assert result is not None
            mock_vultr_client.create_record.assert_called_once_with(
                "example.com", "MX", "@", "mail.example.com", 300, 10
            )

    @pytest.mark.asyncio
    async def test_add_txt_record(self, mock_api_key, mock_vultr_client):
        """Test add_txt_record convenience method."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.add_txt_record(
                "example.com", "@", "v=spf1 include:_spf.google.com ~all", 300
            )

            assert result is not None
            mock_vultr_client.create_record.assert_called_once_with(
                "example.com",
                "TXT",
                "@",
                "v=spf1 include:_spf.google.com ~all",
                300,
                None,
            )


@pytest.mark.unit
class TestUtilityMethods:
    """Test utility methods."""

    @pytest.mark.asyncio
    async def test_find_records_by_type(self, mock_api_key, sample_records):
        """Test find_records_by_type method."""
        mock_client = AsyncMock()
        mock_client.list_records.return_value = sample_records

        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.find_records_by_type("example.com", "A")

            assert len(result) == 2  # Should find 2 A records
            assert all(r["type"] == "A" for r in result)

    @pytest.mark.asyncio
    async def test_find_records_by_name(self, mock_api_key, sample_records):
        """Test find_records_by_name method."""
        mock_client = AsyncMock()
        mock_client.list_records.return_value = sample_records

        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.find_records_by_name("example.com", "@")

            assert len(result) == 3  # Should find 3 @ records
            assert all(r["name"] == "@" for r in result)

    @pytest.mark.asyncio
    async def test_get_domain_summary(self, mock_api_key, sample_records):
        """Test get_domain_summary method."""
        mock_client = AsyncMock()
        mock_client.get_domain.return_value = {
            "domain": "example.com",
            "date_created": "2024-01-01",
        }
        mock_client.list_records.return_value = sample_records

        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.get_domain_summary("example.com")

            assert result["domain"] == "example.com"
            assert result["total_records"] == 4
            assert "A" in result["record_types"]
            assert "MX" in result["record_types"]
            assert result["configuration"]["has_root_record"] is True
            assert result["configuration"]["has_www_subdomain"] is True
            assert result["configuration"]["has_email_setup"] is True

    @pytest.mark.asyncio
    async def test_get_domain_summary_error(self, mock_api_key):
        """Test get_domain_summary error handling."""
        mock_client = AsyncMock()
        mock_client.get_domain.side_effect = Exception("API Error")

        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.get_domain_summary("example.com")

            assert "error" in result
            assert result["domain"] == "example.com"


@pytest.mark.integration
class TestSetupMethods:
    """Test setup utility methods."""

    @pytest.mark.asyncio
    async def test_setup_basic_website_success(self, mock_api_key, mock_vultr_client):
        """Test successful website setup."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.setup_basic_website(
                "example.com", "192.168.1.100", True, 300
            )

            assert result["domain"] == "example.com"
            assert len(result["created_records"]) == 2  # Root and www
            assert len(result["errors"]) == 0

            # Should create 2 A records
            assert mock_vultr_client.create_record.call_count == 2

    @pytest.mark.asyncio
    async def test_setup_basic_website_no_www(self, mock_api_key, mock_vultr_client):
        """Test website setup without www subdomain."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.setup_basic_website(
                "example.com", "192.168.1.100", False, 300
            )

            assert result["domain"] == "example.com"
            assert len(result["created_records"]) == 1  # Only root

            # Should create 1 A record
            assert mock_vultr_client.create_record.call_count == 1

    @pytest.mark.asyncio
    async def test_setup_basic_website_with_errors(self, mock_api_key):
        """Test website setup with API errors."""
        mock_client = AsyncMock()
        mock_client.create_record.side_effect = Exception("API Error")

        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.setup_basic_website(
                "example.com", "192.168.1.100", True, 300
            )

            assert result["domain"] == "example.com"
            assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_setup_basic_website_with_error_responses(self, mock_api_key):
        """Test website setup with error responses from create_record - covers lines 253, 261."""
        mock_client = AsyncMock()
        # Mock create_record to return error responses instead of raising exceptions
        mock_client.create_record.return_value = {"error": "API error message"}

        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.setup_basic_website(
                "example.com", "192.168.1.100", True, 300
            )

            assert result["domain"] == "example.com"
            assert len(result["errors"]) == 2  # Both root and www should have errors
            assert "Root A record: API error message" in result["errors"]
            assert "WWW A record: API error message" in result["errors"]
            assert len(result["created_records"]) == 0

    @pytest.mark.asyncio
    async def test_setup_email_success(self, mock_api_key, mock_vultr_client):
        """Test successful email setup."""
        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_vultr_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.setup_email(
                "example.com", "mail.example.com", 10, 300
            )

            assert result["domain"] == "example.com"
            assert len(result["created_records"]) == 1
            assert len(result["errors"]) == 0

            # Should create 1 MX record
            mock_vultr_client.create_record.assert_called_once_with(
                "example.com", "MX", "@", "mail.example.com", 300, 10
            )

    @pytest.mark.asyncio
    async def test_setup_email_with_error(self, mock_api_key):
        """Test email setup with API error."""
        mock_client = AsyncMock()
        mock_client.create_record.side_effect = Exception("API Error")

        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.setup_email(
                "example.com", "mail.example.com", 10, 300
            )

            assert result["domain"] == "example.com"
            assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_setup_email_with_error_response(self, mock_api_key):
        """Test email setup with error response from create_record - covers line 297."""
        mock_client = AsyncMock()
        # Mock create_record to return error response instead of raising exception
        mock_client.create_record.return_value = {"error": "MX record creation failed"}

        with patch("mcp_vultr.client.VultrDNSServer", return_value=mock_client):
            client = VultrDNSClient(mock_api_key)
            result = await client.setup_email(
                "example.com", "mail.example.com", 10, 300
            )

            assert result["domain"] == "example.com"
            assert len(result["errors"]) == 1
            assert "MX record: MX record creation failed" in result["errors"]
            assert len(result["created_records"]) == 0


if __name__ == "__main__":
    pytest.main([__file__])
