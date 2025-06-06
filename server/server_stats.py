#!/usr/bin/env python3
"""
Server Statistics and Monitoring for Prism DNS Server (SCRUM-14)
Tracks connection, message, and performance statistics.
"""

import json
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ServerStats:
    """
    Thread-safe server statistics tracking.

    Tracks connections, messages, errors, and performance metrics
    for monitoring and debugging purposes.
    """

    def __init__(self, max_performance_samples: int = 1000):
        """
        Initialize server statistics.

        Args:
            max_performance_samples: Maximum number of performance samples to keep
        """
        self._lock = threading.RLock()
        self.max_performance_samples = max_performance_samples

        # Connection statistics
        self._total_connections = 0
        self._active_connections = 0
        self._connection_history = deque(maxlen=1000)
        self._connections_by_ip = defaultdict(int)

        # Message statistics
        self._messages_received = 0
        self._messages_sent = 0
        self._messages_by_type = defaultdict(int)

        # Error statistics
        self._total_errors = 0
        self._errors_by_type = defaultdict(int)
        self._recent_errors = deque(maxlen=100)

        # Performance statistics
        self._processing_times = deque(maxlen=max_performance_samples)
        self._total_processing_time = 0.0

        # Server lifecycle
        self._start_time = time.time()
        self._last_reset_time = time.time()

        logger.debug("ServerStats initialized")

    def connection_opened(self, client_ip: str) -> None:
        """
        Record a new connection opening.

        Args:
            client_ip: IP address of connecting client
        """
        with self._lock:
            self._total_connections += 1
            self._active_connections += 1
            self._connections_by_ip[client_ip] += 1

            # Record connection event
            self._connection_history.append(
                {"timestamp": time.time(), "event": "opened", "ip": client_ip}
            )

        logger.debug(f"Connection opened from {client_ip}, active: {self._active_connections}")

    def connection_closed(self, client_ip: str) -> None:
        """
        Record a connection closing.

        Args:
            client_ip: IP address of disconnecting client
        """
        with self._lock:
            self._active_connections = max(0, self._active_connections - 1)

            # Record connection event
            self._connection_history.append(
                {"timestamp": time.time(), "event": "closed", "ip": client_ip}
            )

        logger.debug(f"Connection closed from {client_ip}, active: {self._active_connections}")

    def message_received(self, message_type: str) -> None:
        """
        Record a message being received.

        Args:
            message_type: Type of message received
        """
        with self._lock:
            self._messages_received += 1
            self._messages_by_type[f"received_{message_type}"] += 1

        logger.debug(f"Message received: {message_type}")

    def message_sent(self, message_type: str) -> None:
        """
        Record a message being sent.

        Args:
            message_type: Type of message sent
        """
        with self._lock:
            self._messages_sent += 1
            self._messages_by_type[f"sent_{message_type}"] += 1

        logger.debug(f"Message sent: {message_type}")

    def error_occurred(self, error_type: str, error_message: Optional[str] = None) -> None:
        """
        Record an error occurrence.

        Args:
            error_type: Type/category of error
            error_message: Optional detailed error message
        """
        with self._lock:
            self._total_errors += 1
            self._errors_by_type[error_type] += 1

            # Record detailed error info
            error_record = {"timestamp": time.time(), "type": error_type, "message": error_message}
            self._recent_errors.append(error_record)

        logger.warning(f"Error occurred: {error_type} - {error_message}")

    def message_processed(self, processing_time: float) -> None:
        """
        Record message processing time.

        Args:
            processing_time: Time taken to process message in seconds
        """
        with self._lock:
            self._processing_times.append(processing_time)
            self._total_processing_time += processing_time

    def get_total_connections(self) -> int:
        """Get total number of connections since start."""
        with self._lock:
            return self._total_connections

    def get_active_connections(self) -> int:
        """Get current number of active connections."""
        with self._lock:
            return self._active_connections

    def get_messages_received(self) -> int:
        """Get total number of messages received."""
        with self._lock:
            return self._messages_received

    def get_messages_sent(self) -> int:
        """Get total number of messages sent."""
        with self._lock:
            return self._messages_sent

    def get_total_errors(self) -> int:
        """Get total number of errors."""
        with self._lock:
            return self._total_errors

    def get_error_counts(self) -> Dict[str, int]:
        """Get error counts by type."""
        with self._lock:
            return dict(self._errors_by_type)

    def get_performance_metrics(self) -> Dict[str, float]:
        """
        Get performance metrics.

        Returns:
            Dictionary with performance statistics
        """
        with self._lock:
            if not self._processing_times:
                return {
                    "avg_processing_time": 0.0,
                    "min_processing_time": 0.0,
                    "max_processing_time": 0.0,
                    "total_processing_time": 0.0,
                    "sample_count": 0,
                }

            processing_times = list(self._processing_times)

            return {
                "avg_processing_time": sum(processing_times) / len(processing_times),
                "min_processing_time": min(processing_times),
                "max_processing_time": max(processing_times),
                "total_processing_time": self._total_processing_time,
                "sample_count": len(processing_times),
            }

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get detailed connection statistics.

        Returns:
            Dictionary with connection statistics
        """
        with self._lock:
            return {
                "total_connections": self._total_connections,
                "active_connections": self._active_connections,
                "connections_by_ip": dict(self._connections_by_ip),
                "connection_history_size": len(self._connection_history),
            }

    def get_message_stats(self) -> Dict[str, Any]:
        """
        Get detailed message statistics.

        Returns:
            Dictionary with message statistics
        """
        with self._lock:
            return {
                "messages_received": self._messages_received,
                "messages_sent": self._messages_sent,
                "messages_by_type": dict(self._messages_by_type),
            }

    def get_error_stats(self) -> Dict[str, Any]:
        """
        Get detailed error statistics.

        Returns:
            Dictionary with error statistics
        """
        with self._lock:
            recent_errors = list(self._recent_errors)

            return {
                "total_errors": self._total_errors,
                "errors_by_type": dict(self._errors_by_type),
                "recent_errors_count": len(recent_errors),
                "recent_errors": recent_errors[-10:],  # Last 10 errors
            }

    def get_uptime(self) -> float:
        """Get server uptime in seconds."""
        return time.time() - self._start_time

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive server statistics.

        Returns:
            Dictionary with all statistics
        """
        with self._lock:
            stats = {
                "timestamp": time.time(),
                "uptime_seconds": self.get_uptime(),
                "connections": self.get_connection_stats(),
                "messages": self.get_message_stats(),
                "errors": self.get_error_stats(),
                "performance": self.get_performance_metrics(),
            }

            return stats

    def reset(self) -> None:
        """Reset all statistics."""
        with self._lock:
            self._total_connections = 0
            self._active_connections = 0
            self._connection_history.clear()
            self._connections_by_ip.clear()

            self._messages_received = 0
            self._messages_sent = 0
            self._messages_by_type.clear()

            self._total_errors = 0
            self._errors_by_type.clear()
            self._recent_errors.clear()

            self._processing_times.clear()
            self._total_processing_time = 0.0

            self._last_reset_time = time.time()

        logger.info("Server statistics reset")

    def to_json(self) -> str:
        """
        Export statistics as JSON string.

        Returns:
            JSON representation of statistics
        """
        stats = self.get_comprehensive_stats()
        return json.dumps(stats, indent=2, default=str)

    def get_connection_rate(self, window_seconds: int = 60) -> float:
        """
        Get connection rate over time window.

        Args:
            window_seconds: Time window in seconds

        Returns:
            Connections per second in the window
        """
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - window_seconds

            # Count connections in window
            connections_in_window = sum(
                1
                for event in self._connection_history
                if event["timestamp"] >= cutoff_time and event["event"] == "opened"
            )

            return connections_in_window / window_seconds

    def get_top_client_ips(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get top client IPs by connection count.

        Args:
            limit: Maximum number of IPs to return

        Returns:
            List of (ip, connection_count) tuples
        """
        with self._lock:
            sorted_ips = sorted(self._connections_by_ip.items(), key=lambda x: x[1], reverse=True)

            return sorted_ips[:limit]

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get server health status based on statistics.

        Returns:
            Dictionary with health status indicators
        """
        with self._lock:
            perf_metrics = self.get_performance_metrics()
            error_rate = self._total_errors / max(1, self._messages_received + self._messages_sent)

            # Determine health status
            status = "healthy"
            issues = []

            # Check error rate
            if error_rate > 0.1:  # >10% error rate
                status = "degraded"
                issues.append(f"High error rate: {error_rate:.2%}")

            # Check processing time
            avg_processing_time = perf_metrics.get("avg_processing_time", 0)
            if avg_processing_time > 0.1:  # >100ms average
                status = "degraded"
                issues.append(f"Slow processing: {avg_processing_time:.3f}s avg")

            # Check active connections vs capacity
            if self._active_connections > 500:  # Arbitrary threshold
                status = "warning"
                issues.append(f"High connection count: {self._active_connections}")

            return {
                "status": status,
                "uptime_seconds": self.get_uptime(),
                "active_connections": self._active_connections,
                "error_rate": error_rate,
                "avg_processing_time": avg_processing_time,
                "issues": issues,
            }


class StatsCollector:
    """Collects and aggregates statistics from multiple sources."""

    def __init__(self):
        """Initialize stats collector."""
        self.server_stats = ServerStats()
        self.custom_metrics = {}
        self._lock = threading.Lock()

        logger.debug("StatsCollector initialized")

    def add_custom_metric(self, name: str, value: Any) -> None:
        """
        Add a custom metric.

        Args:
            name: Metric name
            value: Metric value
        """
        with self._lock:
            self.custom_metrics[name] = {"value": value, "timestamp": time.time()}

    def get_all_stats(self) -> Dict[str, Any]:
        """
        Get all statistics including custom metrics.

        Returns:
            Comprehensive statistics dictionary
        """
        with self._lock:
            stats = self.server_stats.get_comprehensive_stats()
            stats["custom_metrics"] = dict(self.custom_metrics)

            return stats


def create_stats_collector() -> StatsCollector:
    """
    Create a statistics collector instance.

    Returns:
        Configured StatsCollector instance
    """
    return StatsCollector()
