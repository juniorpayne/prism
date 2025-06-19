#!/usr/bin/env python3
"""
Retry logic with exponential backoff for email sending.
"""

import asyncio
import logging
import random
from functools import wraps
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of attempts
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add randomness to delays
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def with_retry(retry_config: RetryConfig):
    """
    Decorator for adding retry logic to async functions.

    Args:
        retry_config: Configuration for retry behavior

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(retry_config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt == retry_config.max_attempts - 1:
                        raise

                    # Calculate delay
                    delay = min(
                        retry_config.initial_delay * (retry_config.exponential_base**attempt),
                        retry_config.max_delay,
                    )

                    # Add jitter
                    if retry_config.jitter:
                        delay *= 0.5 + random.random()

                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. " f"Retrying in {delay:.2f} seconds..."
                    )

                    await asyncio.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


class RetryableEmailError(Exception):
    """Exception that indicates an email error that should be retried."""

    pass


class PermanentEmailError(Exception):
    """Exception that indicates an email error that should not be retried."""

    pass
