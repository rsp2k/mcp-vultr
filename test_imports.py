#!/usr/bin/env python3
"""Test imports to identify any import issues."""

def test_retry_imports():
    """Test retry module imports."""
    try:
        from mcp_vultr.retry import (
            NetworkError,
            RateLimitError,
            RetryableError,
            create_retry_decorator,
            retry_api_call,
            retry_async,
            retry_network,
            retry_rate_limit,
        )
        print("✓ Retry imports successful")
        return True
    except Exception as e:
        print(f"✗ Retry import failed: {e}")
        return False

def test_cache_imports():
    """Test cache module imports."""
    try:
        from mcp_vultr.cache import (
            CacheManager,
            cached_request,
            clear_cache,
            get_cache_manager,
            get_cache_stats,
        )
        print("✓ Cache imports successful")
        return True
    except Exception as e:
        print(f"✗ Cache import failed: {e}")
        return False

def test_logging_imports():
    """Test logging module imports."""
    try:
        from mcp_vultr.logging import get_logger
        logger = get_logger(__name__)
        print("✓ Logging imports successful")
        return True
    except Exception as e:
        print(f"✗ Logging import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality to ensure modules work."""
    try:
        # Test retry
        from mcp_vultr.retry import RetryableError
        error = RetryableError("test")
        assert str(error) == "test"
        
        # Test cache
        from mcp_vultr.cache import CacheManager
        cache = CacheManager()
        assert cache.max_size == 1000
        
        print("✓ Basic functionality tests passed")
        return True
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing imports and basic functionality...")
    
    all_passed = True
    all_passed &= test_retry_imports()
    all_passed &= test_cache_imports()
    all_passed &= test_logging_imports()
    all_passed &= test_basic_functionality()
    
    if all_passed:
        print("\n✓ All import tests passed!")
    else:
        print("\n✗ Some import tests failed!")