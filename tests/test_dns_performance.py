#!/usr/bin/env python3
"""
Performance benchmarking suite for PowerDNS operations (SCRUM-51)
Tests throughput, latency, and scalability of DNS operations.
"""

import asyncio
import json
import statistics
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import aiohttp
import dns.resolver
import matplotlib.pyplot as plt
import numpy as np
import pytest
from prometheus_client import CollectorRegistry, Histogram, Summary, write_to_textfile

from server.dns_manager import PowerDNSClient, create_dns_client


@dataclass
class BenchmarkResult:
    """Container for benchmark results."""
    operation: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    duration_seconds: float
    latencies: List[float]
    throughput: float
    mean_latency: float
    median_latency: float
    p95_latency: float
    p99_latency: float
    min_latency: float
    max_latency: float


class DNSBenchmarkSuite:
    """Performance benchmarking suite for DNS operations."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.dns_client = None
        self.results: List[BenchmarkResult] = []
        
        # Prometheus metrics
        self.registry = CollectorRegistry()
        self.latency_histogram = Histogram(
            'dns_benchmark_latency_seconds',
            'DNS operation latency',
            ['operation'],
            registry=self.registry,
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
        )
        self.throughput_summary = Summary(
            'dns_benchmark_throughput_ops',
            'DNS operation throughput',
            ['operation'],
            registry=self.registry
        )
    
    async def setup(self):
        """Setup benchmark environment."""
        self.dns_client = create_dns_client(self.config)
        await self.dns_client.__aenter__()
        
        # Ensure test zone exists
        zone = self.config["powerdns"]["default_zone"]
        if not await self.dns_client.zone_exists(zone):
            await self.dns_client.create_zone(zone)
    
    async def teardown(self):
        """Cleanup benchmark environment."""
        if self.dns_client:
            await self.dns_client.__aexit__(None, None, None)
    
    async def benchmark_create_records(
        self,
        num_records: int,
        concurrency: int = 10
    ) -> BenchmarkResult:
        """Benchmark record creation performance."""
        print(f"\n📊 Benchmarking CREATE operations ({num_records} records)...")
        
        semaphore = asyncio.Semaphore(concurrency)
        latencies = []
        failures = 0
        
        async def create_record(index: int) -> float:
            """Create a single record and measure latency."""
            async with semaphore:
                hostname = f"bench-create-{index}-{int(time.time())}"
                ip = f"10.100.{index // 256}.{index % 256}"
                
                start = time.perf_counter()
                try:
                    await self.dns_client.create_a_record(hostname, ip)
                    latency = time.perf_counter() - start
                    return latency
                except Exception as e:
                    print(f"Failed to create record {index}: {e}")
                    nonlocal failures
                    failures += 1
                    return -1
        
        # Run benchmark
        start_time = time.time()
        tasks = [create_record(i) for i in range(num_records)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # Filter out failures
        latencies = [r for r in results if r > 0]
        successful = len(latencies)
        
        # Calculate metrics
        result = self._calculate_metrics(
            "create_records",
            num_records,
            successful,
            failures,
            duration,
            latencies
        )
        
        self.results.append(result)
        self._print_result(result)
        
        return result
    
    async def benchmark_read_records(
        self,
        num_reads: int,
        num_existing: int = 100,
        concurrency: int = 50
    ) -> BenchmarkResult:
        """Benchmark record read performance."""
        print(f"\n📊 Benchmarking READ operations ({num_reads} reads)...")
        
        # Create records to read
        print(f"  Creating {num_existing} test records...")
        hostnames = []
        for i in range(num_existing):
            hostname = f"bench-read-{i}-{int(time.time())}"
            ip = f"10.101.{i // 256}.{i % 256}"
            await self.dns_client.create_a_record(hostname, ip)
            hostnames.append(hostname)
        
        # Benchmark reads
        semaphore = asyncio.Semaphore(concurrency)
        latencies = []
        failures = 0
        
        async def read_record(index: int) -> float:
            """Read a random record and measure latency."""
            async with semaphore:
                hostname = hostnames[index % len(hostnames)]
                
                start = time.perf_counter()
                try:
                    record = await self.dns_client.get_record(hostname, "A")
                    if record:
                        latency = time.perf_counter() - start
                        return latency
                    else:
                        nonlocal failures
                        failures += 1
                        return -1
                except Exception:
                    nonlocal failures
                    failures += 1
                    return -1
        
        # Run benchmark
        start_time = time.time()
        tasks = [read_record(i) for i in range(num_reads)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # Filter out failures
        latencies = [r for r in results if r > 0]
        successful = len(latencies)
        
        # Calculate metrics
        result = self._calculate_metrics(
            "read_records",
            num_reads,
            successful,
            failures,
            duration,
            latencies
        )
        
        self.results.append(result)
        self._print_result(result)
        
        return result
    
    async def benchmark_update_records(
        self,
        num_updates: int,
        concurrency: int = 20
    ) -> BenchmarkResult:
        """Benchmark record update performance."""
        print(f"\n📊 Benchmarking UPDATE operations ({num_updates} updates)...")
        
        # Create records to update
        print(f"  Creating test records...")
        hostnames = []
        for i in range(min(num_updates, 100)):
            hostname = f"bench-update-{i}-{int(time.time())}"
            ip = f"10.102.{i // 256}.{i % 256}"
            await self.dns_client.create_a_record(hostname, ip)
            hostnames.append(hostname)
        
        # Benchmark updates
        semaphore = asyncio.Semaphore(concurrency)
        latencies = []
        failures = 0
        
        async def update_record(index: int) -> float:
            """Update a record and measure latency."""
            async with semaphore:
                hostname = hostnames[index % len(hostnames)]
                new_ip = f"10.103.{index // 256}.{index % 256}"
                
                start = time.perf_counter()
                try:
                    await self.dns_client.update_record(hostname, new_ip, "A")
                    latency = time.perf_counter() - start
                    return latency
                except Exception:
                    nonlocal failures
                    failures += 1
                    return -1
        
        # Run benchmark
        start_time = time.time()
        tasks = [update_record(i) for i in range(num_updates)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # Filter out failures
        latencies = [r for r in results if r > 0]
        successful = len(latencies)
        
        # Calculate metrics
        result = self._calculate_metrics(
            "update_records",
            num_updates,
            successful,
            failures,
            duration,
            latencies
        )
        
        self.results.append(result)
        self._print_result(result)
        
        return result
    
    async def benchmark_delete_records(
        self,
        num_deletes: int,
        concurrency: int = 20
    ) -> BenchmarkResult:
        """Benchmark record deletion performance."""
        print(f"\n📊 Benchmarking DELETE operations ({num_deletes} deletes)...")
        
        # Create records to delete
        print(f"  Creating {num_deletes} test records...")
        hostnames = []
        for i in range(num_deletes):
            hostname = f"bench-delete-{i}-{int(time.time())}"
            ip = f"10.104.{i // 256}.{i % 256}"
            await self.dns_client.create_a_record(hostname, ip)
            hostnames.append(hostname)
        
        # Benchmark deletes
        semaphore = asyncio.Semaphore(concurrency)
        latencies = []
        failures = 0
        
        async def delete_record(index: int) -> float:
            """Delete a record and measure latency."""
            async with semaphore:
                hostname = hostnames[index]
                
                start = time.perf_counter()
                try:
                    await self.dns_client.delete_record(hostname, "A")
                    latency = time.perf_counter() - start
                    return latency
                except Exception:
                    nonlocal failures
                    failures += 1
                    return -1
        
        # Run benchmark
        start_time = time.time()
        tasks = [delete_record(i) for i in range(num_deletes)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # Filter out failures
        latencies = [r for r in results if r > 0]
        successful = len(latencies)
        
        # Calculate metrics
        result = self._calculate_metrics(
            "delete_records",
            num_deletes,
            successful,
            failures,
            duration,
            latencies
        )
        
        self.results.append(result)
        self._print_result(result)
        
        return result
    
    async def benchmark_dns_resolution(
        self,
        num_queries: int,
        concurrency: int = 100
    ) -> BenchmarkResult:
        """Benchmark DNS resolution performance."""
        print(f"\n📊 Benchmarking DNS RESOLUTION ({num_queries} queries)...")
        
        # Create test records
        print("  Creating test records...")
        hostnames = []
        zone = self.config["powerdns"]["default_zone"]
        for i in range(50):
            hostname = f"bench-resolve-{i}-{int(time.time())}"
            ip = f"10.105.{i // 256}.{i % 256}"
            await self.dns_client.create_a_record(hostname, ip)
            hostnames.append(f"{hostname}.{zone}")
        
        # Configure resolver
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [self.config.get("powerdns_host", "localhost")]
        resolver.port = self.config.get("powerdns_port", 5353)
        resolver.timeout = 2.0
        resolver.lifetime = 5.0
        
        # Benchmark resolution
        semaphore = asyncio.Semaphore(concurrency)
        latencies = []
        failures = 0
        
        async def resolve_hostname(index: int) -> float:
            """Resolve a hostname and measure latency."""
            async with semaphore:
                hostname = hostnames[index % len(hostnames)]
                
                start = time.perf_counter()
                try:
                    # Run DNS resolution in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        resolver.resolve,
                        hostname,
                        "A"
                    )
                    latency = time.perf_counter() - start
                    return latency
                except Exception:
                    nonlocal failures
                    failures += 1
                    return -1
        
        # Run benchmark
        start_time = time.time()
        tasks = [resolve_hostname(i) for i in range(num_queries)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # Filter out failures
        latencies = [r for r in results if r > 0]
        successful = len(latencies)
        
        # Calculate metrics
        result = self._calculate_metrics(
            "dns_resolution",
            num_queries,
            successful,
            failures,
            duration,
            latencies
        )
        
        self.results.append(result)
        self._print_result(result)
        
        return result
    
    async def benchmark_concurrent_operations(
        self,
        duration_seconds: int = 60
    ) -> Dict[str, BenchmarkResult]:
        """Benchmark mixed concurrent operations."""
        print(f"\n📊 Benchmarking CONCURRENT operations ({duration_seconds}s)...")
        
        # Counters
        counters = {
            "create": {"success": 0, "failure": 0, "latencies": []},
            "read": {"success": 0, "failure": 0, "latencies": []},
            "update": {"success": 0, "failure": 0, "latencies": []},
            "delete": {"success": 0, "failure": 0, "latencies": []},
        }
        
        # Pre-create some records
        existing_hosts = []
        for i in range(100):
            hostname = f"bench-concurrent-{i}-{int(time.time())}"
            ip = f"10.106.{i // 256}.{i % 256}"
            await self.dns_client.create_a_record(hostname, ip)
            existing_hosts.append(hostname)
        
        # Define operation tasks
        async def create_op():
            index = counters["create"]["success"] + counters["create"]["failure"]
            hostname = f"bench-concurrent-new-{index}-{int(time.time())}"
            ip = f"10.107.{index // 256}.{index % 256}"
            
            start = time.perf_counter()
            try:
                await self.dns_client.create_a_record(hostname, ip)
                latency = time.perf_counter() - start
                counters["create"]["success"] += 1
                counters["create"]["latencies"].append(latency)
                existing_hosts.append(hostname)
            except Exception:
                counters["create"]["failure"] += 1
        
        async def read_op():
            if not existing_hosts:
                return
            
            index = counters["read"]["success"] + counters["read"]["failure"]
            hostname = existing_hosts[index % len(existing_hosts)]
            
            start = time.perf_counter()
            try:
                record = await self.dns_client.get_record(hostname, "A")
                if record:
                    latency = time.perf_counter() - start
                    counters["read"]["success"] += 1
                    counters["read"]["latencies"].append(latency)
                else:
                    counters["read"]["failure"] += 1
            except Exception:
                counters["read"]["failure"] += 1
        
        async def update_op():
            if not existing_hosts:
                return
            
            index = counters["update"]["success"] + counters["update"]["failure"]
            hostname = existing_hosts[index % len(existing_hosts)]
            new_ip = f"10.108.{index // 256}.{index % 256}"
            
            start = time.perf_counter()
            try:
                await self.dns_client.update_record(hostname, new_ip, "A")
                latency = time.perf_counter() - start
                counters["update"]["success"] += 1
                counters["update"]["latencies"].append(latency)
            except Exception:
                counters["update"]["failure"] += 1
        
        async def delete_op():
            if len(existing_hosts) < 50:  # Keep some records
                return
            
            hostname = existing_hosts.pop()
            
            start = time.perf_counter()
            try:
                await self.dns_client.delete_record(hostname, "A")
                latency = time.perf_counter() - start
                counters["delete"]["success"] += 1
                counters["delete"]["latencies"].append(latency)
            except Exception:
                counters["delete"]["failure"] += 1
                existing_hosts.append(hostname)  # Put it back
        
        # Run concurrent operations
        start_time = time.time()
        operations = [create_op, read_op, update_op, delete_op]
        
        async def run_random_operations():
            while time.time() - start_time < duration_seconds:
                # Pick random operation with weights
                weights = [0.25, 0.50, 0.20, 0.05]  # More reads, fewer deletes
                operation = np.random.choice(operations, p=weights)
                await operation()
                await asyncio.sleep(0.001)  # Small delay
        
        # Run multiple workers
        workers = 10
        await asyncio.gather(*[run_random_operations() for _ in range(workers)])
        
        # Calculate results
        duration = time.time() - start_time
        results = {}
        
        for op_type, data in counters.items():
            if data["latencies"]:
                result = self._calculate_metrics(
                    f"concurrent_{op_type}",
                    data["success"] + data["failure"],
                    data["success"],
                    data["failure"],
                    duration,
                    data["latencies"]
                )
                results[op_type] = result
                self.results.append(result)
                self._print_result(result)
        
        return results
    
    def _calculate_metrics(
        self,
        operation: str,
        total_requests: int,
        successful_requests: int,
        failed_requests: int,
        duration_seconds: float,
        latencies: List[float]
    ) -> BenchmarkResult:
        """Calculate performance metrics from raw data."""
        if not latencies:
            return BenchmarkResult(
                operation=operation,
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                duration_seconds=duration_seconds,
                latencies=[],
                throughput=0,
                mean_latency=0,
                median_latency=0,
                p95_latency=0,
                p99_latency=0,
                min_latency=0,
                max_latency=0
            )
        
        # Update Prometheus metrics
        for latency in latencies:
            self.latency_histogram.labels(operation=operation).observe(latency)
        
        throughput = successful_requests / duration_seconds if duration_seconds > 0 else 0
        self.throughput_summary.labels(operation=operation).observe(throughput)
        
        # Calculate percentiles
        sorted_latencies = sorted(latencies)
        
        return BenchmarkResult(
            operation=operation,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            duration_seconds=duration_seconds,
            latencies=latencies,
            throughput=throughput,
            mean_latency=statistics.mean(latencies),
            median_latency=statistics.median(latencies),
            p95_latency=np.percentile(sorted_latencies, 95),
            p99_latency=np.percentile(sorted_latencies, 99),
            min_latency=min(latencies),
            max_latency=max(latencies)
        )
    
    def _print_result(self, result: BenchmarkResult):
        """Print benchmark result."""
        print(f"\n  Results for {result.operation}:")
        print(f"    Total requests: {result.total_requests}")
        print(f"    Successful: {result.successful_requests}")
        print(f"    Failed: {result.failed_requests}")
        print(f"    Duration: {result.duration_seconds:.2f}s")
        print(f"    Throughput: {result.throughput:.2f} ops/sec")
        print(f"    Latency (ms):")
        print(f"      Mean: {result.mean_latency*1000:.2f}")
        print(f"      Median: {result.median_latency*1000:.2f}")
        print(f"      P95: {result.p95_latency*1000:.2f}")
        print(f"      P99: {result.p99_latency*1000:.2f}")
        print(f"      Min: {result.min_latency*1000:.2f}")
        print(f"      Max: {result.max_latency*1000:.2f}")
    
    def generate_report(self, output_dir: str = "benchmark_results"):
        """Generate comprehensive benchmark report."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate plots
        self._generate_latency_plots(output_dir)
        self._generate_throughput_plots(output_dir)
        
        # Export Prometheus metrics
        write_to_textfile(f"{output_dir}/metrics.prom", self.registry)
        
        # Generate JSON report
        report = {
            "timestamp": datetime.now().isoformat(),
            "config": self.config,
            "results": [
                {
                    "operation": r.operation,
                    "total_requests": r.total_requests,
                    "successful_requests": r.successful_requests,
                    "failed_requests": r.failed_requests,
                    "duration_seconds": r.duration_seconds,
                    "throughput_ops_per_sec": r.throughput,
                    "latency_ms": {
                        "mean": r.mean_latency * 1000,
                        "median": r.median_latency * 1000,
                        "p95": r.p95_latency * 1000,
                        "p99": r.p99_latency * 1000,
                        "min": r.min_latency * 1000,
                        "max": r.max_latency * 1000,
                    }
                }
                for r in self.results
            ]
        }
        
        with open(f"{output_dir}/benchmark_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Generate markdown report
        self._generate_markdown_report(output_dir)
        
        print(f"\n📄 Benchmark report generated in {output_dir}/")
    
    def _generate_latency_plots(self, output_dir: str):
        """Generate latency distribution plots."""
        plt.figure(figsize=(12, 8))
        
        for i, result in enumerate(self.results):
            if result.latencies:
                plt.subplot(2, 3, i + 1)
                plt.hist(np.array(result.latencies) * 1000, bins=50, alpha=0.7)
                plt.xlabel("Latency (ms)")
                plt.ylabel("Frequency")
                plt.title(f"{result.operation} Latency Distribution")
                plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/latency_distributions.png")
        plt.close()
    
    def _generate_throughput_plots(self, output_dir: str):
        """Generate throughput comparison plots."""
        operations = [r.operation for r in self.results]
        throughputs = [r.throughput for r in self.results]
        
        plt.figure(figsize=(10, 6))
        plt.bar(operations, throughputs, alpha=0.7)
        plt.xlabel("Operation")
        plt.ylabel("Throughput (ops/sec)")
        plt.title("DNS Operations Throughput Comparison")
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"{output_dir}/throughput_comparison.png")
        plt.close()
    
    def _generate_markdown_report(self, output_dir: str):
        """Generate markdown benchmark report."""
        with open(f"{output_dir}/benchmark_report.md", "w") as f:
            f.write("# DNS Performance Benchmark Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            f.write("## Summary\n\n")
            f.write("| Operation | Requests | Success Rate | Throughput (ops/s) | Mean Latency (ms) | P95 Latency (ms) |\n")
            f.write("|-----------|----------|--------------|-------------------|-------------------|------------------|\n")
            
            for r in self.results:
                success_rate = (r.successful_requests / r.total_requests * 100) if r.total_requests > 0 else 0
                f.write(f"| {r.operation} | {r.total_requests} | {success_rate:.1f}% | ")
                f.write(f"{r.throughput:.1f} | {r.mean_latency*1000:.2f} | {r.p95_latency*1000:.2f} |\n")
            
            f.write("\n## Detailed Results\n\n")
            for r in self.results:
                f.write(f"### {r.operation}\n\n")
                f.write(f"- **Total Requests**: {r.total_requests}\n")
                f.write(f"- **Successful**: {r.successful_requests}\n")
                f.write(f"- **Failed**: {r.failed_requests}\n")
                f.write(f"- **Duration**: {r.duration_seconds:.2f}s\n")
                f.write(f"- **Throughput**: {r.throughput:.2f} ops/sec\n")
                f.write(f"\n**Latency Statistics (ms)**:\n")
                f.write(f"- Mean: {r.mean_latency*1000:.2f}\n")
                f.write(f"- Median: {r.median_latency*1000:.2f}\n")
                f.write(f"- P95: {r.p95_latency*1000:.2f}\n")
                f.write(f"- P99: {r.p99_latency*1000:.2f}\n")
                f.write(f"- Min: {r.min_latency*1000:.2f}\n")
                f.write(f"- Max: {r.max_latency*1000:.2f}\n\n")


@pytest.mark.performance
@pytest.mark.asyncio
class TestDNSPerformance:
    """Performance test suite."""
    
    @pytest.fixture
    def benchmark_config(self):
        """Configuration for benchmarks."""
        return {
            "powerdns": {
                "enabled": True,
                "api_url": os.getenv("POWERDNS_API_URL", "http://localhost:8053/api/v1"),
                "api_key": os.getenv("POWERDNS_API_KEY", "test-api-key"),
                "default_zone": "bench.test.local.",
                "default_ttl": 60,
                "timeout": 10,
                "retry_attempts": 1,
            },
            "powerdns_host": os.getenv("POWERDNS_HOST", "localhost"),
            "powerdns_port": int(os.getenv("POWERDNS_PORT", "5353")),
        }
    
    async def test_quick_performance_check(self, benchmark_config):
        """Quick performance sanity check."""
        suite = DNSBenchmarkSuite(benchmark_config)
        await suite.setup()
        
        try:
            # Small benchmark
            result = await suite.benchmark_create_records(10, concurrency=5)
            
            # Basic assertions
            assert result.successful_requests > 0
            assert result.throughput > 0
            assert result.mean_latency < 1.0  # Under 1 second
            
        finally:
            await suite.teardown()
    
    @pytest.mark.skipif(
        not os.getenv("RUN_FULL_BENCHMARKS"),
        reason="Full benchmarks disabled by default"
    )
    async def test_full_benchmark_suite(self, benchmark_config):
        """Run full benchmark suite."""
        suite = DNSBenchmarkSuite(benchmark_config)
        await suite.setup()
        
        try:
            # Run all benchmarks
            await suite.benchmark_create_records(1000, concurrency=50)
            await suite.benchmark_read_records(5000, num_existing=200, concurrency=100)
            await suite.benchmark_update_records(500, concurrency=25)
            await suite.benchmark_delete_records(500, concurrency=25)
            await suite.benchmark_dns_resolution(2000, concurrency=100)
            await suite.benchmark_concurrent_operations(duration_seconds=60)
            
            # Generate report
            suite.generate_report()
            
        finally:
            await suite.teardown()


if __name__ == "__main__":
    """Run benchmarks directly."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="DNS Performance Benchmark")
    parser.add_argument("--api-url", default="http://localhost:8053/api/v1")
    parser.add_argument("--api-key", default="test-api-key")
    parser.add_argument("--zone", default="bench.test.local.")
    parser.add_argument("--dns-host", default="localhost")
    parser.add_argument("--dns-port", type=int, default=5353)
    parser.add_argument("--quick", action="store_true", help="Run quick benchmark")
    
    args = parser.parse_args()
    
    config = {
        "powerdns": {
            "enabled": True,
            "api_url": args.api_url,
            "api_key": args.api_key,
            "default_zone": args.zone,
            "default_ttl": 60,
            "timeout": 10,
            "retry_attempts": 1,
        },
        "powerdns_host": args.dns_host,
        "powerdns_port": args.dns_port,
    }
    
    async def run_benchmarks():
        suite = DNSBenchmarkSuite(config)
        await suite.setup()
        
        try:
            if args.quick:
                print("Running quick benchmark...")
                await suite.benchmark_create_records(100, concurrency=10)
                await suite.benchmark_read_records(500, num_existing=50, concurrency=20)
            else:
                print("Running full benchmark suite...")
                await suite.benchmark_create_records(1000, concurrency=50)
                await suite.benchmark_read_records(5000, num_existing=200, concurrency=100)
                await suite.benchmark_update_records(500, concurrency=25)
                await suite.benchmark_delete_records(500, concurrency=25)
                await suite.benchmark_dns_resolution(2000, concurrency=100)
                await suite.benchmark_concurrent_operations(duration_seconds=60)
            
            suite.generate_report()
            
        finally:
            await suite.teardown()
    
    asyncio.run(run_benchmarks())