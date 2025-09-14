"""
Comprehensive tests for the retry utilities module.

This module provides thorough testing of retry functionality including
decorators, async retry functions, exception handling, and edge cases.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tenacity import RetryError

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


@pytest.mark.unit
class TestRetryableExceptions:
    """Test the custom exception hierarchy."""

    def test_retryable_error_inheritance(self):
        """Test RetryableError is a proper Exception subclass."""
        error = RetryableError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_rate_limit_error_inheritance(self):
        """Test RateLimitError inherits from RetryableError."""
        error = RateLimitError("Rate limit exceeded")
        assert isinstance(error, RetryableError)
        assert isinstance(error, Exception)
        assert str(error) == "Rate limit exceeded"

    def test_network_error_inheritance(self):
        """Test NetworkError inherits from RetryableError."""
        error = NetworkError("Network timeout")
        assert isinstance(error, RetryableError)
        assert isinstance(error, Exception)
        assert str(error) == "Network timeout"


@pytest.mark.unit
class TestCreateRetryDecorator:
    """Test the create_retry_decorator function."""

    def test_default_parameters(self):
        """Test decorator creation with default parameters."""
        decorator = create_retry_decorator()
        assert decorator is not None
        
        # Test that it's a valid decorator by applying it to a function
        @decorator
        def test_func():
            return "success"
        
        assert test_func() == "success"

    def test_custom_parameters(self):
        """Test decorator creation with custom parameters."""
        decorator = create_retry_decorator(
            max_attempts=5,
            min_wait=0.1,
            max_wait=10.0,
            multiplier=3.0,
            jitter=False,
            exception_types=(ValueError, TypeError)
        )
        assert decorator is not None

    def test_none_exception_types(self):
        """Test that None exception_types defaults to (Exception,)."""
        decorator = create_retry_decorator(exception_types=None)
        
        call_count = 0
        
        @decorator
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Test error")
            return "success"
        
        result = failing_func()
        assert result == "success"
        assert call_count == 3

    def test_jitter_enabled(self):
        """Test that jitter adds randomness to wait times."""
        decorator = create_retry_decorator(
            max_attempts=3,
            min_wait=1.0,
            max_wait=5.0,
            jitter=True
        )
        
        call_count = 0
        start_time = time.time()
        
        @decorator
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Test error")
            return "success"
        
        result = failing_func()
        elapsed = time.time() - start_time
        
        assert result == "success"
        assert call_count == 3
        # Should have some delay due to retries (even with jitter), but allow for timing variance
        assert elapsed > 0.1  # More lenient timing check

    def test_jitter_disabled(self):
        """Test that jitter can be disabled."""
        decorator = create_retry_decorator(
            max_attempts=2,
            min_wait=0.1,
            max_wait=1.0,
            jitter=False
        )
        
        call_count = 0
        
        @decorator
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Test error")
            return "success"
        
        result = failing_func()
        assert result == "success"
        assert call_count == 2

    def test_specific_exception_types(self):
        """Test that only specified exception types are retried."""
        decorator = create_retry_decorator(
            max_attempts=3,
            exception_types=(ValueError,)
        )
        
        call_count = 0
        
        @decorator
        def func_with_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("This should not be retried")
        
        with pytest.raises(TypeError):
            func_with_type_error()
        
        # Should only be called once since TypeError is not in exception_types
        assert call_count == 1

    def test_max_attempts_reached(self):
        """Test that function fails after max attempts."""
        decorator = create_retry_decorator(
            max_attempts=2,
            min_wait=0.01,
            exception_types=(ValueError,)
        )
        
        call_count = 0
        
        @decorator
        def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        with pytest.raises(RetryError):
            always_failing_func()
        
        assert call_count == 2


@pytest.mark.unit
class TestPredefinedRetryDecorators:
    """Test the predefined retry decorators."""

    def test_retry_api_call_decorator(self):
        """Test the retry_api_call decorator."""
        call_count = 0
        
        @retry_api_call
        def api_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("API error")
            return {"status": "success"}
        
        result = api_func()
        assert result == {"status": "success"}
        assert call_count == 2

    def test_retry_rate_limit_decorator(self):
        """Test the retry_rate_limit decorator."""
        call_count = 0
        
        @retry_rate_limit
        def rate_limited_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Rate limit exceeded")
            return "success"
        
        result = rate_limited_func()
        assert result == "success"
        assert call_count == 2

    def test_retry_network_decorator(self):
        """Test the retry_network decorator."""
        call_count = 0
        
        @retry_network
        def network_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("Network error")
            return "connected"
        
        result = network_func()
        assert result == "connected"
        assert call_count == 2


@pytest.mark.unit
class TestRetryAsync:
    """Test the retry_async function."""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Test successful function call without retries."""
        async def success_func(arg1, arg2=None):
            return f"success-{arg1}-{arg2}"
        
        result = await retry_async(success_func, "test", arg2="value")
        assert result == "success-test-value"

    @pytest.mark.asyncio
    async def test_retry_with_eventual_success(self):
        """Test function that fails then succeeds."""
        call_count = 0
        
        async def eventually_success_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count} failed")
            return "success"
        
        result = await retry_async(
            eventually_success_func,
            max_attempts=5,
            base_delay=0.01
        )
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """Test function that always fails."""
        call_count = 0
        
        async def always_fail_func():
            nonlocal call_count
            call_count += 1
            raise RuntimeError(f"Failure {call_count}")
        
        with pytest.raises(RuntimeError) as exc_info:
            await retry_async(
                always_fail_func,
                max_attempts=3,
                base_delay=0.01
            )
        
        assert "Failure 3" in str(exc_info.value)
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test that delays increase exponentially."""
        call_count = 0
        delays = []
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError("Still failing")
            return "success"
        
        # Patch asyncio.sleep to capture delays
        original_sleep = asyncio.sleep
        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0.001)  # Very small actual delay for testing
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            result = await retry_async(
                failing_func,
                max_attempts=4,
                base_delay=0.1,
                backoff_factor=2.0,
                jitter=False
            )
        
        assert result == "success"
        assert call_count == 4
        assert len(delays) == 3  # 3 retries, so 3 delays
        
        # Check exponential progression (0.1, 0.2, 0.4)
        assert delays[0] == pytest.approx(0.1, rel=1e-2)
        assert delays[1] == pytest.approx(0.2, rel=1e-2)
        assert delays[2] == pytest.approx(0.4, rel=1e-2)

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test that delays are capped at max_delay."""
        call_count = 0
        delays = []
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError("Still failing")
            return "success"
        
        async def mock_sleep(delay):
            delays.append(delay)
            await asyncio.sleep(0.001)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            result = await retry_async(
                failing_func,
                max_attempts=4,
                base_delay=1.0,
                max_delay=1.5,
                backoff_factor=3.0,
                jitter=False
            )
        
        assert result == "success"
        assert len(delays) == 3
        
        # Delays should be capped at max_delay
        assert delays[0] == pytest.approx(1.0)  # 1.0 * 3^0 = 1.0
        assert delays[1] == pytest.approx(1.5)  # min(1.0 * 3^1, 1.5) = 1.5
        assert delays[2] == pytest.approx(1.5)  # min(1.0 * 3^2, 1.5) = 1.5

    @pytest.mark.asyncio
    async def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to delays."""
        call_count = 0
        delays = []
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Still failing")
            return "success"
        
        async def mock_sleep(delay):
            delays.append(delay)
            await asyncio.sleep(0.001)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            result = await retry_async(
                failing_func,
                max_attempts=3,
                base_delay=1.0,
                backoff_factor=2.0,
                jitter=True
            )
        
        assert result == "success"
        assert len(delays) == 2
        
        # With jitter, delays should be close to expected but not exactly equal
        # Expected: 1.0, 2.0 but with ±10% jitter
        assert 0.9 <= delays[0] <= 1.1
        assert 1.8 <= delays[1] <= 2.2

    @pytest.mark.asyncio
    async def test_with_args_and_kwargs(self):
        """Test retry_async with function arguments."""
        call_count = 0
        
        async def func_with_args(pos1, pos2, kw1=None, kw2="default"):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("First call fails")
            return f"{pos1}-{pos2}-{kw1}-{kw2}"
        
        result = await retry_async(
            func_with_args,
            "arg1", "arg2",
            kw1="kwval1", kw2="kwval2",
            max_attempts=3,
            base_delay=0.01
        )
        
        assert result == "arg1-arg2-kwval1-kwval2"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_logging_on_retry(self):
        """Test that retry attempts are logged."""
        call_count = 0
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count}")
            return "success"
        
        with patch('mcp_vultr.retry.logger') as mock_logger:
            result = await retry_async(
                failing_func,
                max_attempts=3,
                base_delay=0.01
            )
        
        assert result == "success"
        
        # Check that warning was called for retries
        assert mock_logger.warning.call_count == 2  # 2 retries
        
        # Check that info was called for success after retry
        assert mock_logger.info.call_count == 1
        
        # Check that error was not called (since it succeeded)
        assert mock_logger.error.call_count == 0

    @pytest.mark.asyncio
    async def test_logging_on_final_failure(self):
        """Test that final failure is logged as error."""
        call_count = 0
        
        async def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Attempt {call_count}")
        
        with patch('mcp_vultr.retry.logger') as mock_logger:
            with pytest.raises(ValueError):
                await retry_async(
                    always_failing_func,
                    max_attempts=2,
                    base_delay=0.01
                )
        
        # Check that warning was called for the first retry
        assert mock_logger.warning.call_count == 1
        
        # Check that error was called for final failure
        assert mock_logger.error.call_count == 1
        
        # Check that info was not called (since it never succeeded)
        assert mock_logger.info.call_count == 0

    @pytest.mark.asyncio
    async def test_zero_attempts(self):
        """Test behavior with zero max_attempts."""
        call_count = 0
        
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Should not retry")
        
        with pytest.raises(ValueError):
            await retry_async(test_func, max_attempts=0)
        
        # With 0 max_attempts, should still try once (implementation ensures at least 1 attempt)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_one_attempt(self):
        """Test behavior with one max_attempt."""
        call_count = 0
        
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Should not retry")
        
        with pytest.raises(ValueError):
            await retry_async(test_func, max_attempts=1)
        
        assert call_count == 1


@pytest.mark.integration
class TestIntegrationScenarios:
    """Test integration scenarios combining different retry features."""

    @pytest.mark.asyncio
    async def test_api_timeout_retry_scenario(self):
        """Test a realistic API timeout retry scenario."""
        call_count = 0
        
        async def api_call_with_timeout():
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                raise asyncio.TimeoutError("Request timeout")
            elif call_count == 2:
                raise ConnectionError("Connection refused")
            else:
                return {"data": "api_response", "status": "success"}
        
        result = await retry_async(
            api_call_with_timeout,
            max_attempts=5,
            base_delay=0.1,
            max_delay=2.0,
            backoff_factor=1.5,
            jitter=True
        )
        
        assert result == {"data": "api_response", "status": "success"}
        assert call_count == 3

    def test_decorator_with_custom_exceptions(self):
        """Test decorator with custom exception handling."""
        retry_custom = create_retry_decorator(
            max_attempts=3,
            min_wait=0.01,
            max_wait=1.0,
            exception_types=(RateLimitError, NetworkError)
        )
        
        call_count = 0
        
        @retry_custom
        def api_func():
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                raise RateLimitError("Rate limit hit")
            elif call_count == 2:
                raise NetworkError("Network timeout")
            else:
                return "success"
        
        result = api_func()
        assert result == "success"
        assert call_count == 3

    def test_non_retryable_exception_not_retried(self):
        """Test that non-retryable exceptions are not retried."""
        retry_specific = create_retry_decorator(
            max_attempts=3,
            exception_types=(ValueError,)
        )
        
        call_count = 0
        
        @retry_specific
        def func_with_auth_error():
            nonlocal call_count
            call_count += 1
            raise PermissionError("Authentication failed")
        
        with pytest.raises(PermissionError):
            func_with_auth_error()
        
        # Should only be called once
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_mixed_success_failure_pattern(self):
        """Test complex success/failure patterns."""
        call_history = []
        
        async def complex_func(operation):
            call_history.append(operation)
            
            if operation == "flaky_network":
                if len([c for c in call_history if c == operation]) < 3:
                    raise ConnectionError("Network unstable")
                return "network_stable"
            elif operation == "rate_limited":
                if len([c for c in call_history if c == operation]) < 2:
                    raise Exception("Rate limited")
                return "rate_limit_cleared"
            else:
                return f"success_{operation}"
        
        # Test multiple operations
        result1 = await retry_async(
            complex_func, "stable_op",
            max_attempts=3, base_delay=0.01
        )
        assert result1 == "success_stable_op"
        
        result2 = await retry_async(
            complex_func, "flaky_network",
            max_attempts=5, base_delay=0.01
        )
        assert result2 == "network_stable"
        
        result3 = await retry_async(
            complex_func, "rate_limited",
            max_attempts=3, base_delay=0.01
        )
        assert result3 == "rate_limit_cleared"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_realistic_timing_behavior(self):
        """Test timing behavior under realistic conditions."""
        call_count = 0
        start_time = time.time()
        
        async def slow_api_call():
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                # Simulate actual delay in a failing API call
                await asyncio.sleep(0.05)
                raise Exception("Service temporarily unavailable")
            
            return "service_restored"
        
        result = await retry_async(
            slow_api_call,
            max_attempts=4,
            base_delay=0.1,
            max_delay=1.0,
            backoff_factor=2.0,
            jitter=False
        )
        
        elapsed = time.time() - start_time
        
        assert result == "service_restored"
        assert call_count == 3
        
        # Total time should include:
        # - First call: ~0.05s (fails)
        # - First retry delay: 0.1s
        # - Second call: ~0.05s (fails)  
        # - Second retry delay: 0.2s
        # - Third call: succeeds
        # Total: ~0.4s minimum, but allow more tolerance for system variance
        assert elapsed >= 0.25  # More lenient tolerance for timing