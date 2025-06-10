#!/usr/bin/env python3
"""
Production Monitoring and Metrics Collection (SCRUM-38)
Prometheus metrics for Prism DNS server monitoring.
"""

import logging
import time
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram, Summary, generate_latest

logger = logging.getLogger(__name__)

# Request metrics
http_requests_total = Counter(
    "prism_http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "prism_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

# TCP connection metrics
tcp_connections_total = Counter(
    "prism_tcp_connections_total",
    "Total TCP connections",
    ["status"],  # 'accepted', 'rejected', 'failed'
)

tcp_active_connections = Gauge("prism_tcp_active_connections", "Number of active TCP connections")

tcp_connection_duration_seconds = Histogram(
    "prism_tcp_connection_duration_seconds", "TCP connection duration in seconds"
)

# Host metrics
registered_hosts_total = Gauge("prism_registered_hosts_total", "Total number of registered hosts")

online_hosts_total = Gauge("prism_online_hosts_total", "Total number of online hosts")

offline_hosts_total = Gauge("prism_offline_hosts_total", "Total number of offline hosts")

# Message processing metrics
messages_processed_total = Counter(
    "prism_messages_processed_total",
    "Total messages processed",
    ["message_type", "status"],  # 'registration', 'heartbeat', 'update' / 'success', 'error'
)

message_processing_duration_seconds = Histogram(
    "prism_message_processing_duration_seconds",
    "Message processing duration in seconds",
    ["message_type"],
)

# Database metrics
database_queries_total = Counter(
    "prism_database_queries_total",
    "Total database queries",
    ["operation", "status"],  # 'select', 'insert', 'update', 'delete' / 'success', 'error'
)

database_query_duration_seconds = Histogram(
    "prism_database_query_duration_seconds", "Database query duration in seconds", ["operation"]
)

database_connection_pool_size = Gauge(
    "prism_database_connection_pool_size", "Current size of database connection pool"
)

database_connection_pool_used = Gauge(
    "prism_database_connection_pool_used", "Number of database connections currently in use"
)

# Error metrics
errors_total = Counter(
    "prism_errors_total",
    "Total errors",
    [
        "error_type",
        "component",
    ],  # 'validation', 'database', 'network' / 'tcp_server', 'api', 'heartbeat'
)

# Heartbeat monitoring metrics
heartbeat_check_duration_seconds = Histogram(
    "prism_heartbeat_check_duration_seconds", "Heartbeat check duration in seconds"
)

heartbeat_timeouts_total = Counter("prism_heartbeat_timeouts_total", "Total heartbeat timeouts")

# System metrics
server_uptime_seconds = Gauge("prism_server_uptime_seconds", "Server uptime in seconds")

server_start_time = Gauge("prism_server_start_time", "Unix timestamp of server start time")

# Business metrics
dns_queries_total = Counter(
    "prism_dns_queries_total", "Total DNS queries", ["query_type", "status"]
)

host_registrations_total = Counter(
    "prism_host_registrations_total", "Total host registrations", ["status"]  # 'success', 'failed'
)

host_updates_total = Counter(
    "prism_host_updates_total", "Total host updates", ["status"]  # 'success', 'failed'
)


class MetricsCollector:
    """Centralized metrics collection and management."""

    def __init__(self):
        """Initialize metrics collector."""
        self._start_time = time.time()
        server_start_time.set(self._start_time)
        logger.info("Metrics collector initialized")

    def update_server_metrics(self):
        """Update server-level metrics."""
        uptime = time.time() - self._start_time
        server_uptime_seconds.set(uptime)

    def record_http_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics."""
        http_requests_total.labels(method=method, endpoint=endpoint, status=str(status)).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

    def record_tcp_connection(self, status: str):
        """Record TCP connection event."""
        tcp_connections_total.labels(status=status).inc()

    def update_tcp_connections(self, count: int):
        """Update active TCP connections gauge."""
        tcp_active_connections.set(count)

    def record_tcp_connection_duration(self, duration: float):
        """Record TCP connection duration."""
        tcp_connection_duration_seconds.observe(duration)

    def update_host_metrics(self, total: int, online: int, offline: int):
        """Update host-related metrics."""
        registered_hosts_total.set(total)
        online_hosts_total.set(online)
        offline_hosts_total.set(offline)

    def record_message(self, message_type: str, status: str, duration: float):
        """Record message processing metrics."""
        messages_processed_total.labels(message_type=message_type, status=status).inc()
        message_processing_duration_seconds.labels(message_type=message_type).observe(duration)

    def record_database_query(self, operation: str, status: str, duration: float):
        """Record database query metrics."""
        database_queries_total.labels(operation=operation, status=status).inc()
        database_query_duration_seconds.labels(operation=operation).observe(duration)

    def update_database_pool_metrics(self, pool_size: int, pool_used: int):
        """Update database connection pool metrics."""
        database_connection_pool_size.set(pool_size)
        database_connection_pool_used.set(pool_used)

    def record_error(self, error_type: str, component: str):
        """Record error occurrence."""
        errors_total.labels(error_type=error_type, component=component).inc()

    def record_heartbeat_check(self, duration: float, timeouts: int = 0):
        """Record heartbeat check metrics."""
        heartbeat_check_duration_seconds.observe(duration)
        if timeouts > 0:
            heartbeat_timeouts_total.inc(timeouts)

    def record_dns_query(self, query_type: str, status: str):
        """Record DNS query metrics."""
        dns_queries_total.labels(query_type=query_type, status=status).inc()

    def record_host_registration(self, status: str):
        """Record host registration event."""
        host_registrations_total.labels(status=status).inc()

    def record_host_update(self, status: str):
        """Record host update event."""
        host_updates_total.labels(status=status).inc()

    def get_metrics(self) -> bytes:
        """Get all metrics in Prometheus format."""
        self.update_server_metrics()
        return generate_latest()


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics_collector():
    """Reset the metrics collector (for testing)."""
    global _metrics_collector
    _metrics_collector = None
