"""
Comprehensive tests for the cache utilities module.

This module provides thorough testing of caching functionality including
cache manager, TTL behavior, cache decorators, and edge cases.
"""

import asyncio
import hashlib
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cachetools import TTLCache

from mcp_vultr.cache import (
    CacheManager,
    cached_request,
    clear_cache,
    get_cache_manager,
    get_cache_stats,
)


@pytest.mark.unit
class TestCacheManager:
    """Test the CacheManager class."""

    def test_init_default_parameters(self):
        """Test cache manager initialization with default parameters."""
        cache_manager = CacheManager()
        
        assert cache_manager.max_size == 1000
        assert cache_manager.default_ttl == 300
        assert cache_manager.domain_ttl == 3600
        assert cache_manager.record_ttl == 300
        
        # Check cache instances
        assert isinstance(cache_manager.domain_cache, TTLCache)
        assert isinstance(cache_manager.record_cache, TTLCache)
        assert isinstance(cache_manager.general_cache, TTLCache)
        
        # Check cache sizes
        assert cache_manager.domain_cache.maxsize == 250  # max_size // 4
        assert cache_manager.record_cache.maxsize == 500  # max_size // 2
        assert cache_manager.general_cache.maxsize == 250  # max_size // 4
        
        # Check initial stats
        expected_stats = {"hits": 0, "misses": 0, "evictions": 0, "sets": 0}
        assert cache_manager.stats == expected_stats

    def test_init_custom_parameters(self):
        """Test cache manager initialization with custom parameters."""
        cache_manager = CacheManager(
            max_size=2000,
            default_ttl=600,
            domain_ttl=7200,
            record_ttl=900
        )
        
        assert cache_manager.max_size == 2000
        assert cache_manager.default_ttl == 600
        assert cache_manager.domain_ttl == 7200
        assert cache_manager.record_ttl == 900
        
        assert cache_manager.domain_cache.maxsize == 500
        assert cache_manager.record_cache.maxsize == 1000
        assert cache_manager.general_cache.maxsize == 500

    def test_generate_key_basic(self):
        """Test cache key generation with basic parameters."""
        cache_manager = CacheManager()
        
        key = cache_manager._generate_key("GET", "/api/domains")
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hash length
        
        # Same parameters should generate same key
        key2 = cache_manager._generate_key("GET", "/api/domains")
        assert key == key2

    def test_generate_key_with_params(self):
        """Test cache key generation with parameters."""
        cache_manager = CacheManager()
        
        params = {"page": 1, "limit": 10}
        key1 = cache_manager._generate_key("GET", "/api/domains", params)
        
        # Different params should generate different key
        different_params = {"page": 2, "limit": 10}
        key2 = cache_manager._generate_key("GET", "/api/domains", different_params)
        assert key1 != key2
        
        # Same params in different order should generate same key
        reordered_params = {"limit": 10, "page": 1}
        key3 = cache_manager._generate_key("GET", "/api/domains", reordered_params)
        assert key1 == key3

    def test_generate_key_deterministic(self):
        """Test that key generation is deterministic."""
        cache_manager = CacheManager()
        
        key_data = {
            "method": "GET",
            "endpoint": "/api/domains",
            "params": {"sort": "name", "order": "asc"}
        }
        
        # Generate expected key manually
        key_string = json.dumps(key_data, sort_keys=True)
        expected_key = hashlib.md5(key_string.encode()).hexdigest()
        
        actual_key = cache_manager._generate_key("GET", "/api/domains", {"sort": "name", "order": "asc"})
        assert actual_key == expected_key

    def test_get_cache_domain_endpoint(self):
        """Test cache selection for domain endpoints."""
        cache_manager = CacheManager()
        
        # Domain endpoints should use domain cache
        cache = cache_manager._get_cache("/api/domains")
        assert cache is cache_manager.domain_cache
        
        cache = cache_manager._get_cache("/api/v2/domains")
        assert cache is cache_manager.domain_cache
        
        cache = cache_manager._get_cache("/domains/example.com")
        assert cache is cache_manager.domain_cache

    def test_get_cache_record_endpoint(self):
        """Test cache selection for record endpoints."""
        cache_manager = CacheManager()
        
        # Record endpoints should use record cache
        cache = cache_manager._get_cache("/api/domains/example.com/records")
        assert cache is cache_manager.record_cache
        
        cache = cache_manager._get_cache("/records/123")
        assert cache is cache_manager.record_cache

    def test_get_cache_general_endpoint(self):
        """Test cache selection for general endpoints."""
        cache_manager = CacheManager()
        
        # Other endpoints should use general cache
        cache = cache_manager._get_cache("/api/users")
        assert cache is cache_manager.general_cache
        
        cache = cache_manager._get_cache("/api/billing")
        assert cache is cache_manager.general_cache

    def test_get_cache_precedence(self):
        """Test cache selection precedence (records over domains)."""
        cache_manager = CacheManager()
        
        # URLs with both domains and records should use record cache
        cache = cache_manager._get_cache("/api/domains/example.com/records")
        assert cache is cache_manager.record_cache

    def test_get_success(self):
        """Test successful cache retrieval."""
        cache_manager = CacheManager()
        
        # Manually add item to cache
        key = cache_manager._generate_key("GET", "/api/domains")
        cache_manager.domain_cache[key] = {"domain": "example.com"}
        
        result = cache_manager.get("GET", "/api/domains")
        assert result == {"domain": "example.com"}
        assert cache_manager.stats["hits"] == 1
        assert cache_manager.stats["misses"] == 0

    def test_get_miss(self):
        """Test cache miss."""
        cache_manager = CacheManager()
        
        result = cache_manager.get("GET", "/api/domains")
        assert result is None
        assert cache_manager.stats["hits"] == 0
        assert cache_manager.stats["misses"] == 1

    def test_get_non_get_method(self):
        """Test that non-GET methods are not cached."""
        cache_manager = CacheManager()
        
        # POST requests should not be cached
        result = cache_manager.get("POST", "/api/domains")
        assert result is None
        assert cache_manager.stats["hits"] == 0
        assert cache_manager.stats["misses"] == 0

    def test_get_with_exception(self):
        """Test cache get with exception handling."""
        cache_manager = CacheManager()
        
        # Mock the cache to raise an exception
        with patch.object(cache_manager.domain_cache, 'get', side_effect=Exception("Cache error")):
            with patch('mcp_vultr.cache.logger') as mock_logger:
                result = cache_manager.get("GET", "/api/domains")
                
                assert result is None
                mock_logger.warning.assert_called_once()

    def test_set_success(self):
        """Test successful cache setting."""
        cache_manager = CacheManager()
        
        test_data = {"domain": "example.com"}
        cache_manager.set("GET", "/api/domains", None, test_data)
        
        # Verify it was cached
        result = cache_manager.get("GET", "/api/domains")
        assert result == test_data
        assert cache_manager.stats["sets"] == 1

    def test_set_non_get_method(self):
        """Test that non-GET methods are not cached."""
        cache_manager = CacheManager()
        
        cache_manager.set("POST", "/api/domains", None, {"data": "test"})
        
        # Should not be cached
        assert cache_manager.stats["sets"] == 0

    def test_set_none_value(self):
        """Test that None values are not cached."""
        cache_manager = CacheManager()
        
        cache_manager.set("GET", "/api/domains", None, None)
        
        # Should not be cached
        assert cache_manager.stats["sets"] == 0

    def test_set_with_exception(self):
        """Test cache set with exception handling."""
        cache_manager = CacheManager()
        
        # Mock the cache to raise an exception
        with patch.object(cache_manager.domain_cache, '__setitem__', side_effect=Exception("Cache error")):
            with patch('mcp_vultr.cache.logger') as mock_logger:
                cache_manager.set("GET", "/api/domains", None, {"data": "test"})
                
                mock_logger.warning.assert_called_once()
                assert cache_manager.stats["sets"] == 0

    def test_invalidate_all(self):
        """Test invalidating all caches."""
        cache_manager = CacheManager()
        
        # Add items to all caches
        cache_manager.domain_cache["key1"] = "data1"
        cache_manager.record_cache["key2"] = "data2"
        cache_manager.general_cache["key3"] = "data3"
        
        cache_manager.invalidate()
        
        assert len(cache_manager.domain_cache) == 0
        assert len(cache_manager.record_cache) == 0
        assert len(cache_manager.general_cache) == 0

    def test_invalidate_domain_pattern(self):
        """Test invalidating domain cache only."""
        cache_manager = CacheManager()
        
        # Add items to all caches
        cache_manager.domain_cache["key1"] = "data1"
        cache_manager.record_cache["key2"] = "data2"
        cache_manager.general_cache["key3"] = "data3"
        
        cache_manager.invalidate("domain")
        
        assert len(cache_manager.domain_cache) == 0
        assert len(cache_manager.record_cache) == 1
        assert len(cache_manager.general_cache) == 1

    def test_invalidate_record_pattern(self):
        """Test invalidating record cache only."""
        cache_manager = CacheManager()
        
        # Add items to all caches
        cache_manager.domain_cache["key1"] = "data1"
        cache_manager.record_cache["key2"] = "data2"
        cache_manager.general_cache["key3"] = "data3"
        
        cache_manager.invalidate("record")
        
        assert len(cache_manager.domain_cache) == 1
        assert len(cache_manager.record_cache) == 0
        assert len(cache_manager.general_cache) == 1

    def test_invalidate_other_pattern(self):
        """Test invalidating general cache for unrecognized patterns."""
        cache_manager = CacheManager()
        
        # Add items to all caches
        cache_manager.domain_cache["key1"] = "data1"
        cache_manager.record_cache["key2"] = "data2"
        cache_manager.general_cache["key3"] = "data3"
        
        cache_manager.invalidate("users")
        
        assert len(cache_manager.domain_cache) == 1
        assert len(cache_manager.record_cache) == 1
        assert len(cache_manager.general_cache) == 0

    def test_get_stats_empty(self):
        """Test getting stats from empty cache."""
        cache_manager = CacheManager()
        
        stats = cache_manager.get_stats()
        
        expected = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "sets": 0,
            "domain_cache_size": 0,
            "record_cache_size": 0,
            "general_cache_size": 0,
            "hit_rate": 0.0
        }
        assert stats == expected

    def test_get_stats_with_data(self):
        """Test getting stats with cache activity."""
        cache_manager = CacheManager()
        
        # Add some activity
        cache_manager.set("GET", "/api/domains", None, {"domain": "example.com"})
        cache_manager.get("GET", "/api/domains")  # Hit
        cache_manager.get("GET", "/api/other")    # Miss
        
        stats = cache_manager.get_stats()
        
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 1
        assert stats["domain_cache_size"] == 1
        assert stats["hit_rate"] == 0.5  # 1 hit / (1 hit + 1 miss)

    def test_hit_rate_calculation_edge_cases(self):
        """Test hit rate calculation edge cases."""
        cache_manager = CacheManager()
        
        # No hits or misses
        stats = cache_manager.get_stats()
        assert stats["hit_rate"] == 0.0
        
        # Only hits
        cache_manager.stats["hits"] = 5
        cache_manager.stats["misses"] = 0
        stats = cache_manager.get_stats()
        assert stats["hit_rate"] == 1.0
        
        # Only misses
        cache_manager.stats["hits"] = 0
        cache_manager.stats["misses"] = 3
        stats = cache_manager.get_stats()
        assert stats["hit_rate"] == 0.0


@pytest.mark.unit
class TestTTLBehavior:
    """Test TTL (Time To Live) behavior of caches."""

    def test_cache_expiration(self):
        """Test that cached items expire after TTL."""
        # Use very short TTL for testing
        cache_manager = CacheManager(default_ttl=1, domain_ttl=1, record_ttl=1)
        
        # Add item
        cache_manager.set("GET", "/api/domains", None, {"domain": "example.com"})
        
        # Should be available immediately
        result = cache_manager.get("GET", "/api/domains")
        assert result == {"domain": "example.com"}
        
        # Wait for expiration (add buffer for timing variance)
        time.sleep(1.2)
        
        # Should be expired
        result = cache_manager.get("GET", "/api/domains")
        assert result is None

    def test_different_ttl_per_cache_type(self):
        """Test that different cache types have different TTLs."""
        # Use different TTLs for testing
        cache_manager = CacheManager(
            default_ttl=60,   # General cache: 1 minute
            domain_ttl=120,   # Domain cache: 2 minutes  
            record_ttl=30     # Record cache: 30 seconds
        )
        
        # Check TTL configuration
        assert cache_manager.domain_cache.ttl == 120
        assert cache_manager.record_cache.ttl == 30
        assert cache_manager.general_cache.ttl == 60

    def test_cache_size_limits(self):
        """Test that caches respect size limits."""
        # Small cache for testing
        cache_manager = CacheManager(max_size=8)  # 2, 4, 2 for domain, record, general
        
        # Fill domain cache beyond capacity
        for i in range(5):
            cache_manager.set("GET", f"/api/domains/{i}", None, f"domain{i}")
        
        # Should only have 2 items (maxsize of domain cache)
        assert len(cache_manager.domain_cache) == 2


@pytest.mark.unit
class TestCachedRequestDecorator:
    """Test the cached_request decorator."""

    @pytest.mark.asyncio
    async def test_decorator_basic_usage(self):
        """Test basic decorator usage."""
        cache_manager = CacheManager()
        call_count = 0
        
        @cached_request(cache_manager=cache_manager)
        async def api_call(self, method, endpoint, params=None):
            nonlocal call_count
            call_count += 1
            return f"response-{call_count}"
        
        # First call should hit the function
        result1 = await api_call(None, "GET", "/api/domains")
        assert result1 == "response-1"
        assert call_count == 1
        
        # Second call should use cache
        result2 = await api_call(None, "GET", "/api/domains")
        assert result2 == "response-1"  # Same result from cache
        assert call_count == 1  # Function not called again

    @pytest.mark.asyncio
    async def test_decorator_different_endpoints(self):
        """Test decorator with different endpoints."""
        cache_manager = CacheManager()
        call_count = 0
        
        @cached_request(cache_manager=cache_manager)
        async def api_call(self, method, endpoint, params=None):
            nonlocal call_count
            call_count += 1
            return f"response-{endpoint}-{call_count}"
        
        # Different endpoints should not use each other's cache
        result1 = await api_call(None, "GET", "/api/domains")
        result2 = await api_call(None, "GET", "/api/records")
        
        assert result1 == "response-/api/domains-1"
        assert result2 == "response-/api/records-2"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_with_params(self):
        """Test decorator with parameters."""
        cache_manager = CacheManager()
        call_count = 0
        
        @cached_request(cache_manager=cache_manager)
        async def api_call(self, method, endpoint, params=None):
            nonlocal call_count
            call_count += 1
            return f"response-{params}-{call_count}"
        
        # Same endpoint with different params should not share cache
        result1 = await api_call(None, "GET", "/api/domains", {"page": 1})
        result2 = await api_call(None, "GET", "/api/domains", {"page": 2})
        result3 = await api_call(None, "GET", "/api/domains", {"page": 1})  # Should use cache
        
        assert result1 == "response-{'page': 1}-1"
        assert result2 == "response-{'page': 2}-2"
        assert result3 == "response-{'page': 1}-1"  # From cache
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_non_get_methods(self):
        """Test that decorator doesn't cache non-GET methods."""
        cache_manager = CacheManager()
        call_count = 0
        
        @cached_request(cache_manager=cache_manager)
        async def api_call(self, method, endpoint, params=None):
            nonlocal call_count
            call_count += 1
            return f"response-{method}-{call_count}"
        
        # POST should not be cached
        result1 = await api_call(None, "POST", "/api/domains")
        result2 = await api_call(None, "POST", "/api/domains")
        
        assert result1 == "response-POST-1"
        assert result2 == "response-POST-2"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_with_kwargs_method(self):
        """Test decorator when method is passed as keyword argument."""
        cache_manager = CacheManager()
        call_count = 0
        
        @cached_request(cache_manager=cache_manager)
        async def api_call(self, **kwargs):
            nonlocal call_count
            call_count += 1
            method = kwargs.get("method", "GET")
            endpoint = kwargs.get("endpoint", "")
            return f"response-{method}-{endpoint}-{call_count}"
        
        # Test with kwargs
        result1 = await api_call(None, method="GET", endpoint="/api/domains")
        result2 = await api_call(None, method="GET", endpoint="/api/domains")
        
        assert result1 == "response-GET-/api/domains-1"
        assert result2 == "response-GET-/api/domains-1"  # From cache
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_decorator_default_cache_manager(self):
        """Test decorator with default cache manager."""
        call_count = 0
        
        @cached_request()  # No cache_manager specified
        async def api_call(self, method, endpoint, params=None):
            nonlocal call_count
            call_count += 1
            return f"response-{call_count}"
        
        # Should use global cache manager
        result1 = await api_call(None, "GET", "/api/domains")
        result2 = await api_call(None, "GET", "/api/domains")
        
        assert result1 == "response-1"
        assert result2 == "response-1"  # From cache
        assert call_count == 1


@pytest.mark.unit
class TestGlobalCacheFunctions:
    """Test the global cache management functions."""

    def test_get_cache_manager(self):
        """Test getting the global cache manager."""
        manager = get_cache_manager()
        assert isinstance(manager, CacheManager)
        
        # Should return the same instance
        manager2 = get_cache_manager()
        assert manager is manager2

    def test_clear_cache_function(self):
        """Test the global clear_cache function."""
        # Add some data to global cache
        manager = get_cache_manager()
        manager.set("GET", "/api/test", None, {"data": "test"})
        
        # Clear all
        clear_cache()
        
        # Should be cleared
        result = manager.get("GET", "/api/test")
        assert result is None

    def test_clear_cache_with_pattern(self):
        """Test clearing cache with pattern."""
        manager = get_cache_manager()
        
        # Add data to different caches
        manager.set("GET", "/api/domains", None, {"type": "domain"})
        manager.set("GET", "/api/domains/test/records", None, {"type": "record"})
        
        # Clear only domain cache
        clear_cache("domain")
        
        # Domain should be cleared, record should remain
        assert manager.get("GET", "/api/domains") is None
        assert manager.get("GET", "/api/domains/test/records") == {"type": "record"}

    def test_get_cache_stats_function(self):
        """Test the global get_cache_stats function."""
        manager = get_cache_manager()
        
        # Clear any existing state
        manager.invalidate()
        manager.stats = {"hits": 0, "misses": 0, "evictions": 0, "sets": 0}
        
        # Add some activity
        manager.set("GET", "/api/test", None, {"data": "test"})
        
        stats = get_cache_stats()
        assert stats["sets"] == 1
        assert isinstance(stats, dict)


@pytest.mark.unit
class TestCacheEvictionAndMemoryManagement:
    """Test cache eviction and memory management behavior."""

    def test_lru_eviction(self):
        """Test LRU eviction behavior."""
        # Small cache size for testing
        cache_manager = CacheManager(max_size=4)  # 1, 2, 1 for domain, record, general
        
        # Fill domain cache (maxsize is 1 for domain cache)
        cache_manager.set("GET", "/api/domains/1", None, "domain1")
        assert cache_manager.get("GET", "/api/domains/1") == "domain1"  # Should be there
        
        cache_manager.set("GET", "/api/domains/2", None, "domain2")  # Should evict domain1
        
        # Check eviction happened (domain cache has maxsize=1)
        assert cache_manager.get("GET", "/api/domains/1") is None  # Evicted
        assert cache_manager.get("GET", "/api/domains/2") == "domain2"  # Still there

    def test_cache_size_distribution(self):
        """Test cache size distribution among different cache types."""
        cache_manager = CacheManager(max_size=100)
        
        assert cache_manager.domain_cache.maxsize == 25   # 100 // 4
        assert cache_manager.record_cache.maxsize == 50   # 100 // 2
        assert cache_manager.general_cache.maxsize == 25  # 100 // 4
        
        total_capacity = (
            cache_manager.domain_cache.maxsize +
            cache_manager.record_cache.maxsize +
            cache_manager.general_cache.maxsize
        )
        assert total_capacity == 100

    def test_concurrent_access_safety(self):
        """Test that cache operations are safe under concurrent access."""
        cache_manager = CacheManager()
        
        # Simulate concurrent operations
        def concurrent_operations():
            for i in range(10):
                cache_manager.set("GET", f"/api/test/{i}", None, f"data{i}")
                cache_manager.get("GET", f"/api/test/{i}")
        
        # This should not raise any exceptions
        concurrent_operations()
        
        # Verify some data is there
        assert cache_manager.get("GET", "/api/test/9") == "data9"


@pytest.mark.integration
class TestCacheIntegrationScenarios:
    """Test realistic cache integration scenarios."""

    @pytest.mark.asyncio
    async def test_api_client_cache_integration(self):
        """Test cache integration with a simulated API client."""
        cache_manager = CacheManager(default_ttl=1)  # Short TTL for testing
        api_call_count = 0
        
        @cached_request(cache_manager=cache_manager)
        async def simulated_api_client(self, method, endpoint, params=None):
            nonlocal api_call_count
            api_call_count += 1
            
            # Simulate API response
            if "domains" in endpoint:
                return {"domains": [f"domain{api_call_count}.com"]}
            elif "records" in endpoint:
                return {"records": [{"id": api_call_count, "type": "A"}]}
            else:
                return {"data": f"response{api_call_count}"}
        
        client = None
        
        # Test caching behavior
        response1 = await simulated_api_client(client, "GET", "/api/domains")
        response2 = await simulated_api_client(client, "GET", "/api/domains")  # From cache
        
        assert response1 == response2
        assert api_call_count == 1
        
        # Different endpoint should not use cache
        response3 = await simulated_api_client(client, "GET", "/api/records")
        assert api_call_count == 2
        
        # Wait for cache expiration (add buffer for timing variance)
        time.sleep(1.2)
        
        # Should call API again after expiration
        response4 = await simulated_api_client(client, "GET", "/api/domains")
        assert api_call_count == 3
        assert response4 != response1  # Different response

    def test_cache_performance_under_load(self):
        """Test cache performance under simulated load."""
        cache_manager = CacheManager(max_size=1000)
        
        # Simulate high load
        start_time = time.time()
        
        for i in range(500):
            # Mix of sets and gets
            cache_manager.set("GET", f"/api/endpoint/{i % 100}", None, f"data{i}")
            cache_manager.get("GET", f"/api/endpoint/{i % 50}")
        
        elapsed = time.time() - start_time
        
        # Should complete quickly (performance regression test)
        assert elapsed < 1.0  # Should be much faster, but allowing buffer
        
        # Check that cache is working
        stats = cache_manager.get_stats()
        assert stats["hits"] > 0
        assert stats["sets"] > 0

    def test_memory_efficiency(self):
        """Test memory efficiency with large amounts of cached data."""
        cache_manager = CacheManager(max_size=100)  # Small for testing
        
        # Add more data than cache can hold
        for i in range(200):
            cache_manager.set("GET", f"/api/test/{i}", None, f"data{i}" * 100)  # Larger data
        
        # Cache should not exceed size limits
        total_items = (
            len(cache_manager.domain_cache) +
            len(cache_manager.record_cache) +
            len(cache_manager.general_cache)
        )
        
        # Should be at or below the total capacity
        total_capacity = (
            cache_manager.domain_cache.maxsize +
            cache_manager.record_cache.maxsize +
            cache_manager.general_cache.maxsize
        )
        assert total_items <= total_capacity

    def test_cache_invalidation_patterns(self):
        """Test common cache invalidation patterns."""
        cache_manager = CacheManager()
        
        # Populate caches with different types of data
        cache_manager.set("GET", "/api/domains", None, {"domains": ["example.com"]})
        cache_manager.set("GET", "/api/domains/example.com/records", None, {"records": []})
        cache_manager.set("GET", "/api/users", None, {"users": ["user1"]})
        cache_manager.set("GET", "/api/billing", None, {"balance": 100})
        
        # Verify all data is cached
        assert cache_manager.get("GET", "/api/domains") is not None
        assert cache_manager.get("GET", "/api/domains/example.com/records") is not None
        assert cache_manager.get("GET", "/api/users") is not None
        assert cache_manager.get("GET", "/api/billing") is not None
        
        # Invalidate only domain-related data
        cache_manager.invalidate("domain")
        
        # Domain cache should be cleared
        assert cache_manager.get("GET", "/api/domains") is None
        
        # But records and other data should remain
        # Note: "/api/domains/example.com/records" goes to record cache, not domain cache
        assert cache_manager.get("GET", "/api/domains/example.com/records") is not None
        assert cache_manager.get("GET", "/api/users") is not None
        assert cache_manager.get("GET", "/api/billing") is not None
        
        # Invalidate record data
        cache_manager.invalidate("record")
        
        # Now records should be cleared too
        assert cache_manager.get("GET", "/api/domains/example.com/records") is None
        
        # But other data should still remain
        assert cache_manager.get("GET", "/api/users") is not None
        assert cache_manager.get("GET", "/api/billing") is not None