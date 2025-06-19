#!/usr/bin/env python3
"""
Unit tests for SMTP retry logic.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from server.auth.email_providers.retry import RetryConfig, with_retry


class TestRetryLogic:
    """Test retry decorator and configuration."""

    @pytest.mark.asyncio
    async def test_retry_config_defaults(self):
        """Test default retry configuration."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Test successful call doesn't retry."""
        config = RetryConfig(max_attempts=3)
        call_count = 0

        @with_retry(config)
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await test_func()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test function retries on failure."""
        config = RetryConfig(
            max_attempts=3,
            initial_delay=0.1,
            jitter=False,  # Disable jitter for predictable timing
        )
        call_count = 0

        @with_retry(config)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        # Mock sleep to speed up test
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await test_func()

        assert result == "success"
        assert call_count == 3
        # Should sleep twice (before 2nd and 3rd attempts)
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_max_attempts_exceeded(self):
        """Test retry gives up after max attempts."""
        config = RetryConfig(max_attempts=3, initial_delay=0.1, jitter=False)
        call_count = 0

        @with_retry(config)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Permanent failure")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception) as exc_info:
                await test_func()

        assert str(exc_info.value) == "Permanent failure"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        config = RetryConfig(
            max_attempts=4,
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=False,
        )

        sleep_times = []

        @with_retry(config)
        async def test_func():
            raise Exception("Always fails")

        # Capture sleep times
        async def mock_sleep(delay):
            sleep_times.append(delay)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with pytest.raises(Exception):
                await test_func()

        # Expected delays: 1.0, 2.0, 4.0
        assert len(sleep_times) == 3
        assert sleep_times[0] == 1.0
        assert sleep_times[1] == 2.0
        assert sleep_times[2] == 4.0

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test delays are capped at max_delay."""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=10.0,
            max_delay=20.0,
            exponential_base=2.0,
            jitter=False,
        )

        sleep_times = []

        @with_retry(config)
        async def test_func():
            raise Exception("Always fails")

        async def mock_sleep(delay):
            sleep_times.append(delay)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with pytest.raises(Exception):
                await test_func()

        # All delays should be capped at 20.0
        assert all(delay <= 20.0 for delay in sleep_times)
        # Later delays should hit the cap
        assert sleep_times[-1] == 20.0

    @pytest.mark.asyncio
    async def test_jitter_adds_randomness(self):
        """Test jitter adds randomness to delays."""
        config = RetryConfig(
            max_attempts=3,
            initial_delay=1.0,
            jitter=True,
        )

        sleep_times = []

        @with_retry(config)
        async def test_func():
            raise Exception("Always fails")

        async def mock_sleep(delay):
            sleep_times.append(delay)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with pytest.raises(Exception):
                await test_func()

        # With jitter, delays should vary
        # Base delay is 1.0, with jitter it should be between 0.5 and 1.5
        assert 0.5 <= sleep_times[0] <= 1.5
        # Second delay base is 2.0, with jitter between 1.0 and 3.0
        assert 1.0 <= sleep_times[1] <= 3.0

    @pytest.mark.asyncio
    async def test_retry_preserves_function_signature(self):
        """Test retry decorator preserves function signature."""
        config = RetryConfig()

        @with_retry(config)
        async def test_func(a: int, b: str = "default") -> str:
            """Test function docstring."""
            return f"{a}-{b}"

        # Function name and docstring preserved
        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring."

        # Function works with arguments
        result = await test_func(42, b="custom")
        assert result == "42-custom"

    @pytest.mark.asyncio
    async def test_retry_with_specific_exceptions(self):
        """Test retry only on specific exceptions."""
        config = RetryConfig(max_attempts=3, initial_delay=0.1)
        call_count = 0

        # Create custom retry decorator that only retries on ValueError
        def with_retry_for_valueerror(retry_config: RetryConfig):
            def decorator(func):
                async def wrapper(*args, **kwargs):
                    last_exception = None
                    for attempt in range(retry_config.max_attempts):
                        try:
                            return await func(*args, **kwargs)
                        except ValueError as e:
                            last_exception = e
                            if attempt == retry_config.max_attempts - 1:
                                raise
                            await asyncio.sleep(0.01)  # Short sleep for test
                        except Exception:
                            # Don't retry other exceptions
                            raise
                    raise last_exception

                return wrapper

            return decorator

        @with_retry_for_valueerror(config)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retry this")
            elif call_count == 2:
                raise TypeError("Don't retry this")
            return "success"

        # Should not retry TypeError
        with pytest.raises(TypeError):
            await test_func()

        # Should have tried twice (once for ValueError, once for TypeError)
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_concurrent_retries(self):
        """Test multiple functions with retry running concurrently."""
        config = RetryConfig(max_attempts=2, initial_delay=0.1, jitter=False)

        call_counts = {"func1": 0, "func2": 0}

        @with_retry(config)
        async def func1():
            call_counts["func1"] += 1
            if call_counts["func1"] < 2:
                raise Exception("Fail once")
            return "func1_success"

        @with_retry(config)
        async def func2():
            call_counts["func2"] += 1
            if call_counts["func2"] < 2:
                raise Exception("Fail once")
            return "func2_success"

        # Run both functions concurrently
        with patch("asyncio.sleep", new_callable=AsyncMock):
            results = await asyncio.gather(func1(), func2())

        assert results == ["func1_success", "func2_success"]
        assert call_counts["func1"] == 2
        assert call_counts["func2"] == 2
