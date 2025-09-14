"""
Caching utilities for API responses.

This module provides caching functionality to reduce API calls
and improve performance for frequently accessed data.
"""

import hashlib
import json
from functools import wraps
from typing import Any

from cachetools import TTLCache

from .vultr_logging import get_logger

logger = get_logger(__name__)


class CacheManager:
    """
    Cache manager for API responses with TTL and LRU eviction.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 300,  # 5 minutes
        domain_ttl: int = 3600,  # 1 hour for domains
        record_ttl: int = 300,  # 5 minutes for records
    ):
        """
        Initialize cache manager.

        Args:
            max_size: Maximum number of items in cache
            default_ttl: Default TTL in seconds
            domain_ttl: TTL for domain queries
            record_ttl: TTL for record queries
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.domain_ttl = domain_ttl
        self.record_ttl = record_ttl

        # Create separate caches for different data types
        self.domain_cache = TTLCache(maxsize=max_size // 4, ttl=domain_ttl)
        self.record_cache = TTLCache(maxsize=max_size // 2, ttl=record_ttl)
        self.general_cache = TTLCache(maxsize=max_size // 4, ttl=default_ttl)

        # Track cache statistics
        self.stats = {"hits": 0, "misses": 0, "evictions": 0, "sets": 0}

    def _generate_key(self, method: str, endpoint: str, params: dict = None) -> str:
        """
        Generate a cache key from method, endpoint and parameters.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Hash-based cache key
        """
        key_data = {"method": method, "endpoint": endpoint, "params": params or {}}

        # Create a stable hash of the key data
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _get_cache(self, endpoint: str) -> TTLCache:
        """
        Get the appropriate cache for an endpoint.

        Args:
            endpoint: API endpoint

        Returns:
            Appropriate cache instance
        """
        if "/domains" in endpoint and "/records" not in endpoint:
            return self.domain_cache
        elif "/records" in endpoint:
            return self.record_cache
        else:
            return self.general_cache

    def get(self, method: str, endpoint: str, params: dict = None) -> Any | None:
        """
        Get cached response.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Cached response or None if not found
        """
        # Only cache GET requests
        if method.upper() != "GET":
            return None

        key = self._generate_key(method, endpoint, params)
        cache = self._get_cache(endpoint)

        try:
            result = cache.get(key)
            if result is not None:
                self.stats["hits"] += 1
                logger.debug(
                    "Cache hit",
                    endpoint=endpoint,
                    key=key[:8],
                    cache_type=type(cache).__name__,
                )
                return result
            else:
                self.stats["misses"] += 1
                return None
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None

    def set(
        self, method: str, endpoint: str, params: dict = None, value: Any = None
    ) -> None:
        """
        Cache a response.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            value: Response to cache
        """
        # Only cache GET requests
        if method.upper() != "GET" or value is None:
            return

        key = self._generate_key(method, endpoint, params)
        cache = self._get_cache(endpoint)

        try:
            cache[key] = value
            self.stats["sets"] += 1
            logger.debug(
                "Cache set",
                endpoint=endpoint,
                key=key[:8],
                cache_type=type(cache).__name__,
            )
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))

    def invalidate(self, pattern: str = None) -> None:
        """
        Invalidate cache entries matching pattern.

        Args:
            pattern: Pattern to match (endpoint substring)
        """
        if pattern is None:
            # Clear all caches
            self.domain_cache.clear()
            self.record_cache.clear()
            self.general_cache.clear()
            logger.info("All caches cleared")
        else:
            # Clear specific entries (simplified - would need more sophisticated matching)
            if "domain" in pattern.lower():
                self.domain_cache.clear()
                logger.info("Domain cache cleared", pattern=pattern)
            elif "record" in pattern.lower():
                self.record_cache.clear()
                logger.info("Record cache cleared", pattern=pattern)
            else:
                self.general_cache.clear()
                logger.info("General cache cleared", pattern=pattern)

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            **self.stats,
            "domain_cache_size": len(self.domain_cache),
            "record_cache_size": len(self.record_cache),
            "general_cache_size": len(self.general_cache),
            "hit_rate": self.stats["hits"]
            / max(1, self.stats["hits"] + self.stats["misses"]),
        }


# Global cache instance
_cache_manager = CacheManager()


def cached_request(
    cache_manager: CacheManager = None,
    ttl: int = None,  # noqa: ARG001
    cache_key_func: callable = None,  # noqa: ARG001
):
    """
    Decorator for caching API requests.

    Args:
        cache_manager: Cache manager instance
        ttl: Custom TTL for this request
        cache_key_func: Custom function to generate cache key

    Returns:
        Decorated function
    """
    if cache_manager is None:
        cache_manager = _cache_manager

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract method and endpoint from args/kwargs
            # This assumes the decorated function has method and endpoint parameters
            method = kwargs.get("method") or (args[1] if len(args) > 1 else "GET")
            endpoint = kwargs.get("endpoint") or (args[2] if len(args) > 2 else "")
            params = kwargs.get("params")

            # Check cache first
            cached_result = cache_manager.get(method, endpoint, params)
            if cached_result is not None:
                return cached_result

            # Call original function
            result = await func(*args, **kwargs)

            # Cache the result
            cache_manager.set(method, endpoint, params, result)

            return result

        return wrapper

    return decorator


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    return _cache_manager


def clear_cache(pattern: str = None) -> None:
    """Clear cache entries matching pattern."""
    _cache_manager.invalidate(pattern)


def get_cache_stats() -> dict[str, Any]:
    """Get cache statistics."""
    return _cache_manager.get_stats()
