#!/usr/bin/env python3
"""
DNS Health Monitor for PowerDNS
Provides Prometheus metrics for DNS query performance and availability
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Optional

import dns.asyncresolver
import dns.exception
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Prometheus metrics
dns_queries_total = Counter(
    "dns_monitor_queries_total",
    "Total number of DNS queries performed",
    ["domain", "record_type", "status"],
)

dns_query_duration_seconds = Histogram(
    "dns_monitor_query_duration_seconds",
    "DNS query response time in seconds",
    ["domain", "record_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

dns_query_success = Gauge(
    "dns_monitor_query_success",
    "DNS query success status (1=success, 0=failure)",
    ["domain", "record_type"],
)

dns_records_found = Gauge(
    "dns_monitor_records_found", "Number of DNS records found for domain", ["domain", "record_type"]
)

dns_monitor_up = Gauge("dns_monitor_up", "DNS monitor is running")


class DNSMonitor:
    """Monitor DNS server health and performance."""

    def __init__(self):
        self.dns_server = os.getenv("DNS_SERVER", "powerdns")
        self.dns_port = int(os.getenv("DNS_PORT", "53"))
        self.test_domains = os.getenv("TEST_DOMAINS", "test.managed.prism.local").split(",")
        self.check_interval = int(os.getenv("CHECK_INTERVAL", "30"))
        self.record_types = ["A", "AAAA", "MX", "TXT", "NS", "SOA"]

        # Configure DNS resolver
        self.resolver = dns.asyncresolver.Resolver()
        self.resolver.nameservers = [self.dns_server]
        self.resolver.port = self.dns_port
        self.resolver.timeout = 5.0
        self.resolver.lifetime = 5.0

        logger.info(f"DNS Monitor initialized - Server: {self.dns_server}:{self.dns_port}")
        logger.info(f"Test domains: {self.test_domains}")

    async def query_dns(self, domain: str, record_type: str) -> Optional[Dict]:
        """
        Perform DNS query and collect metrics.

        Returns:
            Dict with query results or None if failed
        """
        start_time = time.time()

        try:
            # Perform DNS query
            answers = await self.resolver.resolve(domain, record_type)

            # Calculate duration
            duration = time.time() - start_time

            # Update metrics
            dns_queries_total.labels(domain=domain, record_type=record_type, status="success").inc()
            dns_query_duration_seconds.labels(domain=domain, record_type=record_type).observe(
                duration
            )
            dns_query_success.labels(domain=domain, record_type=record_type).set(1)
            dns_records_found.labels(domain=domain, record_type=record_type).set(len(answers))

            # Log results
            logger.debug(
                f"DNS query successful: {domain}/{record_type} - {len(answers)} records in {duration:.3f}s"
            )

            return {
                "domain": domain,
                "record_type": record_type,
                "status": "success",
                "records": len(answers),
                "duration": duration,
                "answers": [str(rdata) for rdata in answers],
            }

        except dns.exception.NXDOMAIN:
            # Domain doesn't exist
            duration = time.time() - start_time
            dns_queries_total.labels(
                domain=domain, record_type=record_type, status="nxdomain"
            ).inc()
            dns_query_duration_seconds.labels(domain=domain, record_type=record_type).observe(
                duration
            )
            dns_query_success.labels(domain=domain, record_type=record_type).set(0)
            dns_records_found.labels(domain=domain, record_type=record_type).set(0)

            logger.debug(f"DNS query NXDOMAIN: {domain}/{record_type}")
            return None

        except dns.exception.Timeout:
            # Query timeout
            duration = time.time() - start_time
            dns_queries_total.labels(domain=domain, record_type=record_type, status="timeout").inc()
            dns_query_success.labels(domain=domain, record_type=record_type).set(0)

            logger.warning(f"DNS query timeout: {domain}/{record_type} after {duration:.3f}s")
            return None

        except Exception as e:
            # Other errors
            duration = time.time() - start_time
            dns_queries_total.labels(domain=domain, record_type=record_type, status="error").inc()
            dns_query_success.labels(domain=domain, record_type=record_type).set(0)

            logger.error(f"DNS query error: {domain}/{record_type} - {e}")
            return None

    async def check_domain(self, domain: str) -> List[Dict]:
        """Check all record types for a domain."""
        results = []

        for record_type in self.record_types:
            try:
                result = await self.query_dns(domain, record_type)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error checking {domain}/{record_type}: {e}")

        return results

    async def monitor_loop(self):
        """Main monitoring loop."""
        logger.info("Starting DNS monitoring loop")
        dns_monitor_up.set(1)

        while True:
            try:
                # Check all test domains
                for domain in self.test_domains:
                    await self.check_domain(domain.strip())

                # Wait for next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                dns_monitor_up.set(0)
                await asyncio.sleep(self.check_interval)
                dns_monitor_up.set(1)


async def main():
    """Main entry point."""
    # Start Prometheus metrics server
    prometheus_port = int(os.getenv("PROMETHEUS_PORT", "9121"))
    start_http_server(prometheus_port)
    logger.info(f"Prometheus metrics server started on port {prometheus_port}")

    # Create and run monitor
    monitor = DNSMonitor()
    await monitor.monitor_loop()


if __name__ == "__main__":
    asyncio.run(main())
