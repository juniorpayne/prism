#!/usr/bin/env python3
"""
Unit tests for circuit breaker pattern.
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from server.auth.email_providers.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker with test configuration."""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            expected_exception=ValueError,
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_initial_state(self, circuit_breaker):
        """Test circuit breaker starts in closed state."""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.last_failure_time is None

    @pytest.mark.asyncio
    async def test_successful_calls_keep_circuit_closed(self, circuit_breaker):
        """Test successful calls keep circuit closed."""

        async def success_func():
            return "success"

        # Multiple successful calls
        for _ in range(5):
            result = await circuit_breaker.call(success_func)
            assert result == "success"

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_failures_increment_counter(self, circuit_breaker):
        """Test failures increment the failure counter."""

        async def failing_func():
            raise ValueError("Expected failure")

        # First two failures
        for i in range(2):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 2

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self, circuit_breaker):
        """Test circuit opens after failure threshold is reached."""

        async def failing_func():
            raise ValueError("Expected failure")

        # Reach failure threshold
        for i in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == 3
        assert circuit_breaker.last_failure_time is not None

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self, circuit_breaker):
        """Test open circuit rejects calls immediately."""

        async def failing_func():
            raise ValueError("Expected failure")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        # Now circuit is open, calls should be rejected
        async def success_func():
            return "success"

        with pytest.raises(Exception) as exc_info:
            await circuit_breaker.call(success_func)

        assert "Circuit breaker is OPEN" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, circuit_breaker):
        """Test circuit transitions to half-open after recovery timeout."""

        async def failing_func():
            raise ValueError("Expected failure")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.OPEN

        # Mock time to simulate recovery timeout
        future_time = datetime.now() + timedelta(seconds=61)
        with patch("server.auth.email_providers.circuit_breaker.datetime") as mock_datetime:
            mock_datetime.now.return_value = future_time

            # Should transition to half-open on next call attempt
            async def success_func():
                return "success"

            # First call should succeed and close the circuit
            result = await circuit_breaker.call(success_func)
            assert result == "success"
            assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self, circuit_breaker):
        """Test successful call in half-open state closes circuit."""

        # First, open the circuit
        async def failing_func():
            raise ValueError("Expected failure")

        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        # Simulate recovery timeout
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.failure_count = 0

        # Successful call should close circuit
        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self, circuit_breaker):
        """Test failure in half-open state reopens circuit."""
        # Set to half-open state
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.last_failure_time = datetime.now()

        async def failing_func():
            raise ValueError("Expected failure")

        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_only_expected_exceptions_trigger_circuit(self, circuit_breaker):
        """Test only expected exceptions affect circuit state."""

        # Circuit breaker expects ValueError
        async def unexpected_error():
            raise TypeError("Unexpected error type")

        # This should not affect circuit state
        with pytest.raises(TypeError):
            await circuit_breaker.call(unexpected_error)

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, circuit_breaker):
        """Test successful call resets failure count."""

        async def failing_func():
            raise ValueError("Expected failure")

        # Two failures
        for _ in range(2):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.failure_count == 2

        # Successful call
        async def success_func():
            return "success"

        await circuit_breaker.call(success_func)

        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_concurrent_calls_handle_state_correctly(self, circuit_breaker):
        """Test concurrent calls handle circuit state correctly."""
        call_results = []

        async def sometimes_failing_func(fail: bool):
            if fail:
                raise ValueError("Expected failure")
            return "success"

        # Open the circuit first
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(sometimes_failing_func, True)

        assert circuit_breaker.state == CircuitState.OPEN

        # Try concurrent calls while circuit is open
        async def try_call():
            try:
                result = await circuit_breaker.call(sometimes_failing_func, False)
                call_results.append(("success", result))
            except Exception as e:
                call_results.append(("error", str(e)))

        # Run multiple concurrent calls
        await asyncio.gather(*[try_call() for _ in range(5)], return_exceptions=True)

        # All calls should have been rejected
        assert all(result[0] == "error" for result in call_results)
        assert all("Circuit breaker is OPEN" in result[1] for result in call_results)

    def test_should_attempt_reset_logic(self, circuit_breaker):
        """Test the logic for determining when to attempt reset."""
        # Initially should not attempt reset
        assert circuit_breaker._should_attempt_reset() is False

        # Open the circuit
        circuit_breaker.state = CircuitState.OPEN
        circuit_breaker.last_failure_time = datetime.now()

        # Should not attempt reset immediately
        assert circuit_breaker._should_attempt_reset() is False

        # Should attempt reset after recovery timeout
        circuit_breaker.last_failure_time = datetime.now() - timedelta(seconds=61)
        assert circuit_breaker._should_attempt_reset() is True

    def test_on_success_behavior(self, circuit_breaker):
        """Test _on_success method behavior in different states."""
        # In CLOSED state
        circuit_breaker.failure_count = 2
        circuit_breaker._on_success()
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == CircuitState.CLOSED

        # In HALF_OPEN state
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker._on_success()
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    def test_on_failure_behavior(self, circuit_breaker):
        """Test _on_failure method behavior."""
        # First failure
        circuit_breaker._on_failure()
        assert circuit_breaker.failure_count == 1
        assert circuit_breaker.state == CircuitState.CLOSED

        # Reach threshold
        circuit_breaker.failure_count = 2
        circuit_breaker._on_failure()
        assert circuit_breaker.failure_count == 3
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.last_failure_time is not None

        # In HALF_OPEN state
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker._on_failure()
        assert circuit_breaker.state == CircuitState.OPEN
