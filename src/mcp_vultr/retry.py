"""
Retry utilities for robust API interactions.

This module provides retry decorators and utilities for handling
transient failures in API calls with exponential backoff.
"""

import asyncio
import logging
import random
from collections.abc import Callable
from typing import Any

from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .vultr_logging import get_logger

logger = get_logger(__name__)


def create_retry_decorator(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 60.0,
    multiplier: float = 2.0,
    jitter: bool = True,
    exception_types: tuple = None,
):
    """
    Create a retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        multiplier: Multiplier for exponential backoff
        jitter: Whether to add random jitter to wait times
        exception_types: Tuple of exception types to retry on

    Returns:
        Configured retry decorator
    """
    if exception_types is None:
        exception_types = (Exception,)

    wait_strategy = wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait)

    if jitter:
        # Add random jitter to reduce thundering herd
        original_wait = wait_strategy

        def jittered_wait(retry_state):
            base_wait = original_wait(retry_state)
            jitter_range = base_wait * 0.1  # 10% jitter
            return base_wait + random.uniform(-jitter_range, jitter_range)

        wait_strategy = jittered_wait

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_strategy,
        retry=retry_if_exception_type(exception_types),
        before_sleep=before_sleep_log(logger, log_level=logging.WARNING),
        after=after_log(logger, log_level=logging.INFO),
    )


# Exception classes for retry logic
class RetryableError(Exception):
    """Base class for retryable errors."""

    pass


class RateLimitError(RetryableError):
    """Error for rate limit exceeded scenarios."""

    pass


class NetworkError(RetryableError):
    """Error for network-related issues."""

    pass


# Common retry decorators for different scenarios

# API calls (retry ONLY on rate limits, timeouts, network errors - NOT validation errors)
retry_api_call = create_retry_decorator(
    max_attempts=3,
    min_wait=1.0,
    max_wait=30.0,
    multiplier=2.0,
    jitter=True,
    exception_types=(RateLimitError, NetworkError),
)

# Rate limit retries (more aggressive, longer waits)
retry_rate_limit = create_retry_decorator(
    max_attempts=5,
    min_wait=5.0,
    max_wait=120.0,
    multiplier=2.0,
    jitter=True,
    exception_types=(RateLimitError,),
)

# Network retries (quick retries for network issues)
retry_network = create_retry_decorator(
    max_attempts=3,
    min_wait=0.5,
    max_wait=10.0,
    multiplier=1.5,
    jitter=True,
    exception_types=(NetworkError,),
)


async def retry_async(
    func: Callable,
    *args,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    **kwargs,
) -> Any:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Positional arguments for the function
        max_attempts: Maximum number of attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for exponential backoff
        jitter: Whether to add random jitter
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function call

    Raises:
        Last exception if all attempts fail
    """
    last_exception = None

    # Ensure at least one attempt is made
    attempts_to_make = max(1, max_attempts)
    for attempt in range(1, attempts_to_make + 1):
        try:
            result = await func(*args, **kwargs)
            if attempt > 1:
                logger.info(
                    "Function succeeded after retry",
                    function=func.__name__,
                    attempt=attempt,
                    max_attempts=attempts_to_make,
                )
            return result

        except Exception as e:
            last_exception = e

            if attempt == attempts_to_make:
                logger.error(
                    "Function failed after all retry attempts",
                    function=func.__name__,
                    attempt=attempt,
                    max_attempts=attempts_to_make,
                    error=str(e),
                )
                break

            # Calculate delay with exponential backoff
            delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)

            # Add jitter if enabled
            if jitter:
                jitter_range = delay * 0.1
                delay += random.uniform(-jitter_range, jitter_range)

            logger.warning(
                "Function failed, retrying",
                function=func.__name__,
                attempt=attempt,
                max_attempts=attempts_to_make,
                delay=delay,
                error=str(e),
            )

            await asyncio.sleep(delay)

    raise last_exception
