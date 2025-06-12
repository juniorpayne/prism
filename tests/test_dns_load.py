#!/usr/bin/env python3
"""
Load testing script for PowerDNS under stress conditions (SCRUM-51)
Simulates real-world load patterns and edge cases.
"""

import asyncio
import json
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import aiohttp
import pytest
from prometheus_client import Counter, Gauge, Histogram, start_http_server

from server.dns_manager import PowerDNSClient, create_dns_client


@dataclass
class LoadPattern:
    """Defines a load pattern for testing."""
    name: str
    duration_seconds: int
    requests_per_second: int
    operation_mix: Dict[str, float]  # operation -> probability
    burst_factor: float = 1.0
    ramp_up_seconds: int = 0


class DNSLoadTester:
    """Load testing harness for DNS operations."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.dns_client = None
        self.active_hosts: List[str] = []
        self.zone = config["powerdns"]["default_zone"]
        
        # Metrics
        self.request_counter = Counter(
            'dns_load_test_requests_total',
            'Total DNS requests',
            ['operation', 'status']
        )
        self.latency_histogram = Histogram(
            'dns_load_test_latency_seconds',
            'Request latency',
            ['operation'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
        )
        self.active_connections = Gauge(
            'dns_load_test_active_connections',
            'Number of active connections'
        )
        self.error_rate = Counter(
            'dns_load_test_errors_total',
            'Total errors',
            ['operation', 'error_type']
        )
    
    async def setup(self):
        """Setup load test environment."""
        self.dns_client = create_dns_client(self.config)
        await self.dns_client.__aenter__()
        
        # Ensure zone exists
        if not await self.dns_client.zone_exists(self.zone):
            await self.dns_client.create_zone(self.zone)
        
        # Pre-populate some records
        print("Pre-populating test records...")
        for i in range(100):
            hostname = f"load-test-seed-{i}"
            ip = f"10.200.{i // 256}.{i % 256}"
            try:
                await self.dns_client.create_a_record(hostname, ip)
                self.active_hosts.append(hostname)
            except Exception as e:
                print(f"Failed to create seed record: {e}")
    
    async def teardown(self):
        """Cleanup load test environment."""
        if self.dns_client:
            await self.dns_client.__aexit__(None, None, None)
    
    async def run_load_pattern(self, pattern: LoadPattern) -> Dict:
        """Execute a specific load pattern."""
        print(f"\n🔥 Running load pattern: {pattern.name}")
        print(f"   Duration: {pattern.duration_seconds}s")
        print(f"   Target RPS: {pattern.requests_per_second}")
        print(f"   Operation mix: {pattern.operation_mix}")
        
        results = {
            "pattern": pattern.name,
            "start_time": datetime.now().isoformat(),
            "operations": {op: {"success": 0, "failure": 0, "latencies": []} 
                          for op in pattern.operation_mix},
            "errors": {},
        }
        
        # Calculate request interval
        base_interval = 1.0 / pattern.requests_per_second
        
        # Start workers
        start_time = time.time()
        tasks = []
        request_count = 0
        
        while time.time() - start_time < pattern.duration_seconds:
            # Calculate current load factor (for ramp-up)
            elapsed = time.time() - start_time
            if elapsed < pattern.ramp_up_seconds:
                load_factor = elapsed / pattern.ramp_up_seconds
            else:
                load_factor = 1.0
            
            # Apply burst factor randomly
            if random.random() < 0.1:  # 10% chance of burst
                interval = base_interval / pattern.burst_factor
            else:
                interval = base_interval
            
            # Adjust for load factor
            interval = interval / load_factor if load_factor > 0 else interval
            
            # Select operation
            operation = self._select_operation(pattern.operation_mix)
            
            # Launch request
            task = asyncio.create_task(self._execute_operation(operation, results))
            tasks.append(task)
            request_count += 1
            
            # Wait for next request
            await asyncio.sleep(interval)
            
            # Clean up completed tasks periodically
            if len(tasks) > 1000:
                done_tasks = [t for t in tasks if t.done()]
                for t in done_tasks:
                    tasks.remove(t)
        
        # Wait for remaining tasks
        print(f"Waiting for {len(tasks)} remaining requests...")
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate final stats
        duration = time.time() - start_time
        results["duration_seconds"] = duration
        results["total_requests"] = request_count
        results["actual_rps"] = request_count / duration
        results["end_time"] = datetime.now().isoformat()
        
        self._print_results(results)
        return results
    
    def _select_operation(self, operation_mix: Dict[str, float]) -> str:
        """Select operation based on probability distribution."""
        rand = random.random()
        cumulative = 0.0
        
        for operation, probability in operation_mix.items():
            cumulative += probability
            if rand <= cumulative:
                return operation
        
        return list(operation_mix.keys())[-1]
    
    async def _execute_operation(self, operation: str, results: Dict):
        """Execute a single operation and record results."""
        self.active_connections.inc()
        start_time = time.perf_counter()
        
        try:
            if operation == "create":
                await self._create_operation()
            elif operation == "read":
                await self._read_operation()
            elif operation == "update":
                await self._update_operation()
            elif operation == "delete":
                await self._delete_operation()
            elif operation == "batch_create":
                await self._batch_create_operation()
            elif operation == "invalid":
                await self._invalid_operation()
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            # Success
            latency = time.perf_counter() - start_time
            results["operations"][operation]["success"] += 1
            results["operations"][operation]["latencies"].append(latency)
            self.request_counter.labels(operation=operation, status="success").inc()
            self.latency_histogram.labels(operation=operation).observe(latency)
            
        except Exception as e:
            # Failure
            results["operations"][operation]["failure"] += 1
            self.request_counter.labels(operation=operation, status="failure").inc()
            
            error_type = type(e).__name__
            if error_type not in results["errors"]:
                results["errors"][error_type] = 0
            results["errors"][error_type] += 1
            self.error_rate.labels(operation=operation, error_type=error_type).inc()
        
        finally:
            self.active_connections.dec()
    
    async def _create_operation(self):
        """Create a new DNS record."""
        hostname = f"load-test-{random.randint(0, 999999)}-{int(time.time())}"
        ip = f"10.201.{random.randint(0, 255)}.{random.randint(0, 255)}"
        
        await self.dns_client.create_a_record(hostname, ip)
        self.active_hosts.append(hostname)
        
        # Limit active hosts
        if len(self.active_hosts) > 10000:
            self.active_hosts = self.active_hosts[-5000:]
    
    async def _read_operation(self):
        """Read an existing DNS record."""
        if not self.active_hosts:
            raise ValueError("No active hosts to read")
        
        hostname = random.choice(self.active_hosts)
        record = await self.dns_client.get_record(hostname, "A")
        
        if not record:
            raise ValueError(f"Record not found: {hostname}")
    
    async def _update_operation(self):
        """Update an existing DNS record."""
        if not self.active_hosts:
            raise ValueError("No active hosts to update")
        
        hostname = random.choice(self.active_hosts)
        new_ip = f"10.202.{random.randint(0, 255)}.{random.randint(0, 255)}"
        
        await self.dns_client.update_record(hostname, new_ip, "A")
    
    async def _delete_operation(self):
        """Delete a DNS record."""
        if len(self.active_hosts) < 100:  # Keep minimum hosts
            raise ValueError("Too few hosts to delete")
        
        hostname = self.active_hosts.pop(random.randint(0, len(self.active_hosts) - 1))
        await self.dns_client.delete_record(hostname, "A")
    
    async def _batch_create_operation(self):
        """Create multiple records in batch."""
        batch_size = random.randint(5, 20)
        tasks = []
        
        for i in range(batch_size):
            hostname = f"load-batch-{random.randint(0, 999999)}-{i}"
            ip = f"10.203.{random.randint(0, 255)}.{random.randint(0, 255)}"
            tasks.append(self.dns_client.create_a_record(hostname, ip))
        
        await asyncio.gather(*tasks)
    
    async def _invalid_operation(self):
        """Attempt invalid operations to test error handling."""
        operation_type = random.choice([
            "invalid_hostname",
            "invalid_ip",
            "duplicate_create",
            "delete_nonexistent",
            "invalid_zone"
        ])
        
        if operation_type == "invalid_hostname":
            await self.dns_client.create_a_record("host with spaces!", "192.168.1.1")
        elif operation_type == "invalid_ip":
            await self.dns_client.create_a_record("valid-host", "999.999.999.999")
        elif operation_type == "duplicate_create":
            if self.active_hosts:
                hostname = random.choice(self.active_hosts)
                await self.dns_client.create_a_record(hostname, "192.168.1.1")
        elif operation_type == "delete_nonexistent":
            await self.dns_client.delete_record("nonexistent-host-12345", "A")
        elif operation_type == "invalid_zone":
            await self.dns_client.create_a_record(
                "test-host", "192.168.1.1", zone="invalid.zone."
            )
    
    def _print_results(self, results: Dict):
        """Print load test results."""
        print(f"\n📊 Results for {results['pattern']}:")
        print(f"   Duration: {results['duration_seconds']:.2f}s")
        print(f"   Total requests: {results['total_requests']}")
        print(f"   Actual RPS: {results['actual_rps']:.2f}")
        
        print("\n   Operations:")
        for op, data in results["operations"].items():
            total = data["success"] + data["failure"]
            if total > 0:
                success_rate = data["success"] / total * 100
                if data["latencies"]:
                    avg_latency = sum(data["latencies"]) / len(data["latencies"])
                    print(f"     {op}: {total} requests, {success_rate:.1f}% success, "
                          f"{avg_latency*1000:.2f}ms avg latency")
                else:
                    print(f"     {op}: {total} requests, {success_rate:.1f}% success")
        
        if results["errors"]:
            print("\n   Errors:")
            for error_type, count in results["errors"].items():
                print(f"     {error_type}: {count}")
    
    async def run_stress_test(self, duration_seconds: int = 300):
        """Run comprehensive stress test with multiple patterns."""
        patterns = [
            # Steady load
            LoadPattern(
                name="Steady Load",
                duration_seconds=60,
                requests_per_second=100,
                operation_mix={
                    "create": 0.2,
                    "read": 0.6,
                    "update": 0.15,
                    "delete": 0.05,
                }
            ),
            
            # High write load
            LoadPattern(
                name="Write Heavy",
                duration_seconds=60,
                requests_per_second=50,
                operation_mix={
                    "create": 0.6,
                    "read": 0.2,
                    "update": 0.15,
                    "delete": 0.05,
                }
            ),
            
            # Burst traffic
            LoadPattern(
                name="Burst Traffic",
                duration_seconds=60,
                requests_per_second=200,
                operation_mix={
                    "create": 0.1,
                    "read": 0.8,
                    "update": 0.08,
                    "delete": 0.02,
                },
                burst_factor=5.0
            ),
            
            # Mixed with errors
            LoadPattern(
                name="Chaos Testing",
                duration_seconds=60,
                requests_per_second=50,
                operation_mix={
                    "create": 0.2,
                    "read": 0.4,
                    "update": 0.1,
                    "delete": 0.05,
                    "batch_create": 0.1,
                    "invalid": 0.15,
                }
            ),
            
            # Ramp up test
            LoadPattern(
                name="Ramp Up",
                duration_seconds=120,
                requests_per_second=500,
                operation_mix={
                    "create": 0.1,
                    "read": 0.85,
                    "update": 0.04,
                    "delete": 0.01,
                },
                ramp_up_seconds=60
            ),
        ]
        
        all_results = []
        
        # Run patterns sequentially
        for pattern in patterns:
            if duration_seconds > 0 and len(all_results) * 60 >= duration_seconds:
                break
            
            results = await self.run_load_pattern(pattern)
            all_results.append(results)
            
            # Cool down between patterns
            print("\n⏸️  Cooling down for 10 seconds...")
            await asyncio.sleep(10)
        
        # Generate summary report
        self._generate_summary_report(all_results)
        
        return all_results
    
    def _generate_summary_report(self, all_results: List[Dict]):
        """Generate summary report of all load tests."""
        print("\n" + "="*60)
        print("📈 LOAD TEST SUMMARY REPORT")
        print("="*60)
        
        total_requests = sum(r["total_requests"] for r in all_results)
        total_duration = sum(r["duration_seconds"] for r in all_results)
        
        print(f"\nTotal requests: {total_requests}")
        print(f"Total duration: {total_duration:.2f}s")
        print(f"Average RPS: {total_requests/total_duration:.2f}")
        
        # Aggregate operation stats
        op_stats = {}
        for result in all_results:
            for op, data in result["operations"].items():
                if op not in op_stats:
                    op_stats[op] = {"success": 0, "failure": 0, "latencies": []}
                op_stats[op]["success"] += data["success"]
                op_stats[op]["failure"] += data["failure"]
                op_stats[op]["latencies"].extend(data["latencies"])
        
        print("\nOperation Summary:")
        for op, stats in op_stats.items():
            total = stats["success"] + stats["failure"]
            if total > 0:
                success_rate = stats["success"] / total * 100
                if stats["latencies"]:
                    avg_latency = sum(stats["latencies"]) / len(stats["latencies"])
                    p95_latency = sorted(stats["latencies"])[int(len(stats["latencies"]) * 0.95)]
                    print(f"  {op}:")
                    print(f"    Total: {total}")
                    print(f"    Success rate: {success_rate:.2f}%")
                    print(f"    Avg latency: {avg_latency*1000:.2f}ms")
                    print(f"    P95 latency: {p95_latency*1000:.2f}ms")
        
        # Error summary
        all_errors = {}
        for result in all_results:
            for error_type, count in result.get("errors", {}).items():
                all_errors[error_type] = all_errors.get(error_type, 0) + count
        
        if all_errors:
            print("\nError Summary:")
            for error_type, count in sorted(all_errors.items(), key=lambda x: x[1], reverse=True):
                print(f"  {error_type}: {count}")
        
        # Save report to file
        report_file = f"load_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump({
                "summary": {
                    "total_requests": total_requests,
                    "total_duration": total_duration,
                    "average_rps": total_requests/total_duration,
                    "operation_stats": op_stats,
                    "error_summary": all_errors,
                },
                "detailed_results": all_results,
            }, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_file}")


@pytest.mark.load
@pytest.mark.asyncio
class TestDNSLoadTesting:
    """Load testing suite for DNS operations."""
    
    @pytest.fixture
    def load_config(self):
        """Configuration for load tests."""
        import os
        return {
            "powerdns": {
                "enabled": True,
                "api_url": os.getenv("POWERDNS_API_URL", "http://localhost:8053/api/v1"),
                "api_key": os.getenv("POWERDNS_API_KEY", "test-api-key"),
                "default_zone": "load.test.local.",
                "default_ttl": 60,
                "timeout": 30,
                "retry_attempts": 3,
            }
        }
    
    async def test_basic_load_pattern(self, load_config):
        """Test basic load pattern execution."""
        tester = DNSLoadTester(load_config)
        await tester.setup()
        
        try:
            pattern = LoadPattern(
                name="Basic Test",
                duration_seconds=10,
                requests_per_second=10,
                operation_mix={
                    "create": 0.3,
                    "read": 0.6,
                    "update": 0.1,
                }
            )
            
            results = await tester.run_load_pattern(pattern)
            
            # Verify results
            assert results["total_requests"] > 0
            assert results["actual_rps"] > 0
            assert results["operations"]["read"]["success"] > 0
            
        finally:
            await tester.teardown()
    
    @pytest.mark.skipif(
        not os.getenv("RUN_STRESS_TESTS"),
        reason="Stress tests disabled by default"
    )
    async def test_full_stress_test(self, load_config):
        """Run full stress test suite."""
        # Start metrics server
        start_http_server(8888)
        
        tester = DNSLoadTester(load_config)
        await tester.setup()
        
        try:
            results = await tester.run_stress_test(duration_seconds=300)
            
            # Basic validation
            assert len(results) > 0
            total_requests = sum(r["total_requests"] for r in results)
            assert total_requests > 0
            
        finally:
            await tester.teardown()


if __name__ == "__main__":
    """Run load tests directly."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="DNS Load Testing")
    parser.add_argument("--api-url", default="http://localhost:8053/api/v1")
    parser.add_argument("--api-key", default="test-api-key")
    parser.add_argument("--zone", default="load.test.local.")
    parser.add_argument("--duration", type=int, default=300, help="Test duration in seconds")
    parser.add_argument("--metrics-port", type=int, default=8888, help="Prometheus metrics port")
    
    args = parser.parse_args()
    
    config = {
        "powerdns": {
            "enabled": True,
            "api_url": args.api_url,
            "api_key": args.api_key,
            "default_zone": args.zone,
            "default_ttl": 60,
            "timeout": 30,
            "retry_attempts": 3,
        }
    }
    
    async def run_load_test():
        # Start metrics server
        start_http_server(args.metrics_port)
        print(f"📊 Prometheus metrics available at http://localhost:{args.metrics_port}/metrics")
        
        tester = DNSLoadTester(config)
        await tester.setup()
        
        try:
            await tester.run_stress_test(duration_seconds=args.duration)
        finally:
            await tester.teardown()
    
    asyncio.run(run_load_test())