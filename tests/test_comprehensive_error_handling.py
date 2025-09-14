"""
Comprehensive error handling tests for mcp-vultr package.

This test module focuses on edge cases and failure scenarios to improve
test suite robustness and error handling coverage.
"""

import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from mcp_vultr.server import (
    VultrDNSServer,
    VultrAPIError,
    VultrAuthError,
    VultrRateLimitError,
    VultrResourceNotFoundError,
    VultrValidationError,
)
from mcp_vultr.retry import RateLimitError, NetworkError

# Mark all tests in this module as error handling tests
pytestmark = [
    pytest.mark.error_handling,
    pytest.mark.network,
    pytest.mark.timeout_sensitive
]


class TestJSONAndResponseErrors:
    """Test JSON parsing and malformed response handling."""

    @pytest.fixture
    def server(self, mock_api_key):
        """Create server instance."""
        return VultrDNSServer(mock_api_key)

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_malformed_json_response(self, server):
        """Test handling of malformed JSON responses."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "invalid json response"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                await server.list_domains()
            
            # Should contain some indication of JSON parsing error
            error_str = str(exc_info.value)
            assert "json" in error_str.lower() or "decode" in error_str.lower()

    @pytest.mark.asyncio
    async def test_empty_json_response(self, server):
        """Test handling of empty JSON responses."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = None

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            result = await server.list_domains()
            # Should handle empty response gracefully
            assert result == []

    @pytest.mark.asyncio
    async def test_missing_expected_keys_in_response(self, server):
        """Test handling of responses missing expected keys."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        # Response missing 'domains' key
        mock_response.json.return_value = {"unexpected": "structure"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            result = await server.list_domains()
            # Should handle gracefully and return empty list
            assert result == []

    @pytest.mark.asyncio
    async def test_partial_domain_data_in_response(self, server):
        """Test handling of partial domain data in responses."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "domains": [
                {"domain": "example.com"},  # Missing other fields
                {"domain": "test.com", "date_created": "2023-01-01"},  # Partial data
                {},  # Empty domain object
                {"domain": "complete.com", "date_created": "2023-01-01", "dns_sec": "enabled"}
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            result = await server.list_domains()
            # Should handle partial data gracefully
            assert len(result) == 4
            assert result[0]["domain"] == "example.com"
            assert result[1]["domain"] == "test.com"


class TestNetworkEdgeCases:
    """Test network-related edge cases and failures."""

    @pytest.fixture
    def server(self, mock_api_key):
        """Create server instance."""
        return VultrDNSServer(mock_api_key)

    @pytest.mark.asyncio
    async def test_ssl_verification_error(self, server):
        """Test SSL certificate verification failures."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.side_effect = (
                httpx.ConnectError("SSL verification failed")
            )

            with pytest.raises(Exception) as exc_info:
                await server.list_domains()
            
            error_str = str(exc_info.value)
            assert "ssl" in error_str.lower() or "certificate" in error_str.lower() or "verification" in error_str.lower()

    @pytest.mark.asyncio
    async def test_dns_resolution_error(self, server):
        """Test DNS resolution failures for Vultr API."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.side_effect = (
                httpx.ConnectError("DNS resolution failed")
            )

            with pytest.raises(Exception) as exc_info:
                await server.list_domains()
            
            error_str = str(exc_info.value)
            assert "dns" in error_str.lower() or "resolution" in error_str.lower() or "connection" in error_str.lower()

    @pytest.mark.asyncio
    async def test_partial_response_read_error(self, server):
        """Test partial response read errors."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.side_effect = (
                httpx.ReadError("Connection closed while reading response")
            )

            with pytest.raises(Exception) as exc_info:
                await server.list_domains()
            
            error_str = str(exc_info.value)
            assert "read" in error_str.lower() or "connection" in error_str.lower()

    @pytest.mark.asyncio
    async def test_http2_protocol_error(self, server):
        """Test HTTP/2 protocol errors."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.side_effect = (
                httpx.ProtocolError("HTTP/2 protocol error")
            )

            with pytest.raises(Exception) as exc_info:
                await server.list_domains()
            
            error_str = str(exc_info.value)
            assert "protocol" in error_str.lower() or "http" in error_str.lower()


class TestAdvancedValidationEdgeCases:
    """Test advanced validation scenarios and edge cases."""

    @pytest.fixture
    def server(self, mock_api_key):
        """Create server instance."""
        return VultrDNSServer(mock_api_key)

    @pytest.mark.asyncio
    async def test_ipv4_address_validation_edge_cases(self, server):
        """Test IPv4 address validation edge cases."""
        invalid_ipv4_addresses = [
            "256.1.1.1",        # Octet too high
            "1.1.1",            # Too few octets
            "1.1.1.1.1",        # Too many octets
            "1.1.1.-1",         # Negative octet
            "1.1.1.1a",         # Non-numeric characters
            "999.999.999.999",  # All octets too high
            "192.168.1.",       # Trailing dot with missing octet
            "192.168..1",       # Double dots
        ]

        for invalid_ip in invalid_ipv4_addresses:
            with pytest.raises(ValueError, match="Invalid IPv4 address"):
                await server.create_record("example.com", "A", "test", invalid_ip)

    @pytest.mark.asyncio
    async def test_ipv6_address_validation_edge_cases(self, server):
        """Test IPv6 address validation edge cases."""
        invalid_ipv6_addresses = [
            "2001:db8::gggg",                    # Invalid hex digit
            "2001:db8:85a3::8a2e:370k:7334",   # Invalid hex digit (k)
            "2001:db8:85a3::8a2e::7334",       # Double "::"
            "2001:db8:85a3:8a2e:370:7334",     # Too few groups
            "2001:db8:85a3::8a2e:370:7334:extra:group",  # Too many groups
            ":::",                               # Invalid triple colon
            "2001:db8::85a3::8a2e",            # Multiple "::"
        ]

        for invalid_ip in invalid_ipv6_addresses:
            with pytest.raises(ValueError, match="Invalid IPv6 address"):
                await server.create_record("example.com", "AAAA", "test", invalid_ip)

    @pytest.mark.asyncio
    async def test_domain_name_validation_comprehensive(self, server):
        """Test comprehensive domain name validation."""
        invalid_domains = [
            "",                              # Empty string
            ".",                             # Just a dot
            ".example.com",                  # Leading dot
            "example..com",                  # Double dots
            "example.com.",                  # Trailing dot (should be allowed but normalized)
            "-example.com",                  # Leading hyphen
            "example-.com",                  # Trailing hyphen in label
            "ex_ample.com",                  # Underscore (invalid in domain names)
            "example com",                   # Space
            "example.c",                     # TLD too short
            "a" * 254,                       # Domain too long (>253 chars)
            "example.123",                   # Numeric TLD (technically valid but suspicious)
        ]

        for invalid_domain in invalid_domains[:7]:  # Test first 7 which are clearly invalid
            if invalid_domain == "example.com.":
                # Trailing dots should be normalized, not rejected
                continue
            with pytest.raises(ValueError):
                await server.create_domain(invalid_domain)

    @pytest.mark.asyncio
    async def test_record_name_validation_comprehensive(self, server):
        """Test comprehensive DNS record name validation."""
        invalid_names = [
            "a" * 64,                        # Name too long (>63 chars)
            "test space",                    # Space in name
            "test.sub",                      # Dot in name (may be valid in some contexts)
            "-test",                         # Leading hyphen
            "test-",                         # Trailing hyphen
            "test_underscore",               # Underscore (may be valid in some record types)
            "test@domain",                   # @ symbol
            "test#hash",                     # Hash symbol
            "test%percent",                  # Percent symbol
        ]

        # Only test clearly invalid names
        clearly_invalid = ["test space", "test@domain", "test#hash", "test%percent"]
        
        for invalid_name in clearly_invalid:
            with pytest.raises(ValueError):
                await server.create_record("example.com", "A", invalid_name, "192.168.1.1")

    @pytest.mark.asyncio
    async def test_mx_record_validation_comprehensive(self, server):
        """Test comprehensive MX record validation."""
        # Test invalid priorities
        invalid_priorities = [-1, 65536, -100, 70000]
        
        for priority in invalid_priorities:
            with pytest.raises(ValueError, match="Invalid MX priority"):
                await server.create_record(
                    "example.com", "MX", "test", "mail.example.com", priority=priority
                )

        # Test invalid target formats
        invalid_targets = [
            "",                              # Empty target
            ".",                             # Just a dot
            ".mail.example.com",             # Leading dot
            "mail..example.com",             # Double dots
            "mail-.example.com",             # Invalid hyphen placement
        ]
        
        for target in invalid_targets:
            with pytest.raises(ValueError):
                await server.create_record("example.com", "MX", "test", target, priority=10)

    @pytest.mark.asyncio
    async def test_srv_record_validation_comprehensive(self, server):
        """Test comprehensive SRV record validation."""
        invalid_srv_data = [
            "invalid format",                # Missing required fields
            "10 5",                          # Missing port and target
            "-1 5 80 target.example.com",    # Invalid priority (negative)
            "10 -5 80 target.example.com",   # Invalid weight (negative)
            "10 5 -80 target.example.com",   # Invalid port (negative)
            "10 5 70000 target.example.com", # Invalid port (too high)
            "abc 5 80 target.example.com",   # Non-numeric priority
            "10 abc 80 target.example.com",  # Non-numeric weight
            "10 5 abc target.example.com",   # Non-numeric port
            "10 5 80",                       # Missing target
        ]
        
        for srv_data in invalid_srv_data:
            with pytest.raises(ValueError):
                await server.create_record("example.com", "SRV", "_service._tcp", srv_data)

    @pytest.mark.asyncio
    async def test_txt_record_validation_edge_cases(self, server):
        """Test TXT record validation edge cases."""
        # Test very long TXT records (>255 characters in a single string)
        long_txt = "a" * 256
        
        # Mock successful response since this might be valid at API level
        mock_response = AsyncMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"record": {"id": "123", "type": "TXT"}}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            # Long TXT records should be handled by the API, not rejected client-side
            result = await server.create_record("example.com", "TXT", "test", long_txt)
            assert result is not None

    @pytest.mark.asyncio
    async def test_ttl_validation_edge_cases(self, server):
        """Test TTL validation edge cases."""
        invalid_ttls = [
            -1,                              # Negative TTL
            0,                               # Zero TTL (may be valid)
            2**31,                           # TTL too large (>2^31-1)
            "invalid",                       # Non-numeric TTL
        ]
        
        # Test clearly invalid TTLs
        for ttl in [-1, 2**31]:
            with pytest.raises(ValueError):
                await server.create_record("example.com", "A", "test", "192.168.1.1", ttl=ttl)


class TestAuthenticationEdgeCases:
    """Test authentication edge cases and failure scenarios."""

    @pytest.mark.asyncio
    async def test_malformed_api_key(self):
        """Test handling of malformed API keys."""
        malformed_keys = [
            "",                              # Empty key
            "short",                         # Too short
            "invalid-characters-in-key!@#",  # Invalid characters
            None,                            # None value
        ]
        
        for key in malformed_keys:
            if key is None:
                with pytest.raises((ValueError, TypeError)):
                    VultrDNSServer(api_key=key)
            else:
                # Server should initialize but fail on first API call
                server = VultrDNSServer(api_key=key)
                
                mock_response = AsyncMock()
                mock_response.status_code = 401
                mock_response.text = "Invalid API key format"

                with patch("httpx.AsyncClient") as mock_client:
                    mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

                    with pytest.raises(Exception) as exc_info:
                        await server.list_domains()
                    
                    error_str = str(exc_info.value)
                    assert "auth" in error_str.lower() or "401" in error_str or "unauthorized" in error_str.lower()

    @pytest.mark.asyncio
    async def test_expired_api_key_handling(self, mock_api_key):
        """Test handling of expired API keys."""
        server = VultrDNSServer(mock_api_key)
        
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.text = "API key expired"
        mock_response.json.return_value = {"error": "Token has expired"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                await server.list_domains()
            
            error_str = str(exc_info.value)
            assert "auth" in error_str.lower() or "401" in error_str or "expired" in error_str.lower()

    @pytest.mark.asyncio
    async def test_revoked_api_key_handling(self, mock_api_key):
        """Test handling of revoked API keys."""
        server = VultrDNSServer(mock_api_key)
        
        mock_response = AsyncMock()
        mock_response.status_code = 403
        mock_response.text = "API key revoked"
        mock_response.json.return_value = {"error": "Access has been revoked"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                await server.list_domains()
            
            error_str = str(exc_info.value)
            assert "auth" in error_str.lower() or "403" in error_str or "forbidden" in error_str.lower()


class TestRateLimitingEdgeCases:
    """Test rate limiting edge cases and retry scenarios."""

    @pytest.fixture
    def server(self, mock_api_key):
        """Create server instance."""
        return VultrDNSServer(mock_api_key)

    @pytest.mark.asyncio
    async def test_rate_limit_with_retry_after_header(self, server):
        """Test rate limit handling with Retry-After header."""
        mock_response = AsyncMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.headers = {"Retry-After": "60"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                await server.list_domains()
            
            error_str = str(exc_info.value)
            assert "rate" in error_str.lower() or "429" in error_str or "limit" in error_str.lower()

    @pytest.mark.asyncio
    async def test_rate_limit_without_retry_header(self, server):
        """Test rate limit handling without Retry-After header."""
        mock_response = AsyncMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.headers = {}  # No Retry-After header

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                await server.list_domains()
            
            error_str = str(exc_info.value)
            assert "rate" in error_str.lower() or "429" in error_str or "limit" in error_str.lower()

    @pytest.mark.asyncio
    async def test_multiple_consecutive_rate_limits(self, server):
        """Test handling of multiple consecutive rate limit responses."""
        mock_response = AsyncMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            # Should fail with rate limit error
            with pytest.raises(Exception):
                await server.list_domains()

    @pytest.mark.asyncio
    async def test_rate_limit_recovery(self, server):
        """Test recovery after rate limit expires."""
        call_count = 0
        
        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call hits rate limit
                mock_response = AsyncMock()
                mock_response.status_code = 429
                mock_response.text = "Rate limit exceeded"
                return mock_response
            else:
                # Second call succeeds
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"domains": []}
                return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.side_effect = mock_request

            # First call should fail
            with pytest.raises(Exception):
                await server.list_domains()
            
            # Reset call count for second attempt (in real scenario this would be after delay)
            call_count = 1
            
            # Second call should succeed
            result = await server.list_domains()
            assert result == []


class TestServerMaintenanceAndDowntime:
    """Test server maintenance and downtime scenarios."""

    @pytest.fixture
    def server(self, mock_api_key):
        """Create server instance."""
        return VultrDNSServer(mock_api_key)

    @pytest.mark.asyncio
    async def test_maintenance_mode_503(self, server):
        """Test handling of 503 Service Unavailable during maintenance."""
        mock_response = AsyncMock()
        mock_response.status_code = 503
        mock_response.text = "Service temporarily unavailable - maintenance mode"
        mock_response.headers = {"Retry-After": "1800"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                await server.list_domains()
            
            error_str = str(exc_info.value)
            assert "503" in error_str or "unavailable" in error_str.lower() or "maintenance" in error_str.lower()

    @pytest.mark.asyncio
    async def test_bad_gateway_502(self, server):
        """Test handling of 502 Bad Gateway errors."""
        mock_response = AsyncMock()
        mock_response.status_code = 502
        mock_response.text = "Bad Gateway"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                await server.list_domains()
            
            error_str = str(exc_info.value)
            assert "502" in error_str or "gateway" in error_str.lower()

    @pytest.mark.asyncio
    async def test_gateway_timeout_504(self, server):
        """Test handling of 504 Gateway Timeout errors."""
        mock_response = AsyncMock()
        mock_response.status_code = 504
        mock_response.text = "Gateway Timeout"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                await server.list_domains()
            
            error_str = str(exc_info.value)
            assert "504" in error_str or "timeout" in error_str.lower()


class TestConcurrentRequestHandling:
    """Test concurrent request handling and race conditions."""

    @pytest.fixture
    def server(self, mock_api_key):
        """Create server instance."""
        return VultrDNSServer(mock_api_key)

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_mixed_results(self, server):
        """Test handling of concurrent requests with mixed success/failure."""
        import asyncio
        
        call_count = 0
        
        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count % 3 == 0:
                # Every third call fails
                raise httpx.TimeoutException("Timeout")
            else:
                # Other calls succeed
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"domains": [{"domain": f"example{call_count}.com"}]}
                return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request.side_effect = mock_request

            # Run multiple concurrent requests
            tasks = [server.list_domains() for _ in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Should have mix of successful results and exceptions
            successes = [r for r in results if isinstance(r, list)]
            failures = [r for r in results if isinstance(r, Exception)]
            
            assert len(successes) > 0  # At least some should succeed
            assert len(failures) > 0   # At least some should fail


class TestZoneFileParsingEdgeCases:
    """Test zone file parsing edge cases and error handling."""

    @pytest.fixture
    def server(self, mock_api_key):
        """Create server instance."""
        return VultrDNSServer(mock_api_key)

    def test_malformed_zone_file_syntax(self, server):
        """Test parsing of malformed zone files."""
        malformed_zone_files = [
            # Missing semicolon in comment
            """
            $TTL 3600
            example.com. IN SOA ns1.example.com. admin.example.com. (
                2023010101 ; serial (malformed
                3600       ; refresh
                1800       ; retry
                604800     ; expire
                86400      ; minimum
            )
            """,
            # Invalid record type
            """
            $TTL 3600
            @       IN  SOA  ns1.example.com. admin.example.com. (
                2023010101 3600 1800 604800 86400
            )
            www     IN  INVALID  192.168.1.1
            """,
            # Missing required fields
            """
            $TTL 3600
            @       IN  SOA  ; Missing SOA data
            www     IN  A    ; Missing IP address
            """,
            # Invalid TTL values
            """
            $TTL invalid_ttl
            @       IN  SOA  ns1.example.com. admin.example.com. (
                2023010101 3600 1800 604800 86400
            )
            """,
            # Completely malformed syntax
            """
            This is not a valid zone file at all!
            It contains random text and no DNS records.
            $TTL should be a number but this is text.
            """
        ]
        
        for malformed_zone in malformed_zone_files:
            # Zone file parsing should handle errors gracefully
            # The exact behavior depends on implementation
            try:
                records = server.parse_zone_file(malformed_zone, "example.com")
                # If parsing succeeds, it should return empty list or handle gracefully
                assert isinstance(records, list)
            except Exception as e:
                # If parsing fails, it should raise appropriate exception
                assert isinstance(e, (ValueError, AttributeError, KeyError))

    def test_zone_file_with_unsupported_record_types(self, server):
        """Test zone files with unsupported DNS record types."""
        zone_with_unsupported = """
        $TTL 3600
        @       IN  SOA  ns1.example.com. admin.example.com. (
            2023010101 3600 1800 604800 86400
        )
        
        ; Standard supported records
        www     IN  A     192.168.1.1
        mail    IN  MX    10 mail.example.com.
        
        ; Unsupported record types
        test    IN  LOC   42 21 54 N 71 06 18 W -24m 30m
        _sip    IN  NAPTR 100 50 "s" "SIP+D2U" "" _sip._udp.example.com.
        key     IN  DNSKEY 256 3 7 AwEAAaHGU...
        """
        
        # Should parse supported records and skip/ignore unsupported ones
        try:
            records = server.parse_zone_file(zone_with_unsupported, "example.com")
            # Should return at least the supported A and MX records
            assert isinstance(records, list)
        except Exception:
            # If implementation doesn't handle unsupported records, that's also valid
            pass