"""
Performance monitoring and metrics collection.

This module provides utilities for collecting and reporting
performance metrics for the MCP server.
"""

import statistics
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from typing import Any

import psutil

from .vultr_logging import get_logger

logger = get_logger(__name__)


@dataclass
class APIMetrics:
    """Metrics for API calls."""

    endpoint: str
    method: str
    count: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    errors: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def avg_time(self) -> float:
        """Average response time."""
        return self.total_time / max(1, self.count)

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as percentage."""
        total_requests = self.cache_hits + self.cache_misses
        return (self.cache_hits / max(1, total_requests)) * 100


@dataclass
class SystemMetrics:
    """System resource metrics."""

    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float


class PerformanceMonitor:
    """
    Performance monitoring and metrics collection.
    """

    def __init__(self, window_size: int = 1000):
        """
        Initialize performance monitor.

        Args:
            window_size: Number of recent measurements to keep
        """
        self.window_size = window_size
        self.api_metrics: dict[str, APIMetrics] = defaultdict(
            lambda: APIMetrics(endpoint="", method="")
        )
        self.response_times: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self.system_metrics: deque = deque(maxlen=window_size)
        self.lock = threading.Lock()

        # Track system baseline
        self._baseline_metrics: SystemMetrics | None = None
        self._collect_baseline()

    def _collect_baseline(self) -> None:
        """Collect baseline system metrics."""
        try:
            process = psutil.Process()
            self._baseline_metrics = SystemMetrics(
                timestamp=time.time(),
                cpu_percent=psutil.cpu_percent(),
                memory_percent=process.memory_percent(),
                memory_mb=process.memory_info().rss / 1024 / 1024,
                disk_io_read_mb=0.0,
                disk_io_write_mb=0.0,
                network_sent_mb=0.0,
                network_recv_mb=0.0,
            )
            logger.debug("Baseline metrics collected", **asdict(self._baseline_metrics))
        except Exception as e:
            logger.warning("Failed to collect baseline metrics", error=str(e))

    def record_api_call(
        self,
        endpoint: str,
        method: str,
        duration: float,
        success: bool = True,
        cache_hit: bool = False,
    ) -> None:
        """
        Record an API call metric.

        Args:
            endpoint: API endpoint
            method: HTTP method
            duration: Call duration in seconds
            success: Whether the call was successful
            cache_hit: Whether this was a cache hit
        """
        key = f"{method.upper()}:{endpoint}"

        with self.lock:
            metrics = self.api_metrics[key]
            if not metrics.endpoint:  # First time
                metrics.endpoint = endpoint
                metrics.method = method.upper()

            metrics.count += 1
            metrics.total_time += duration
            metrics.min_time = min(metrics.min_time, duration)
            metrics.max_time = max(metrics.max_time, duration)

            if not success:
                metrics.errors += 1

            if cache_hit:
                metrics.cache_hits += 1
            else:
                metrics.cache_misses += 1

            # Store recent response times for percentile calculations
            self.response_times[key].append(duration)

        logger.debug(
            "API call recorded",
            endpoint=endpoint,
            method=method,
            duration=duration,
            success=success,
            cache_hit=cache_hit,
        )

    def collect_system_metrics(self) -> None:
        """Collect current system metrics."""
        try:
            process = psutil.Process()
            disk_io = psutil.disk_io_counters()
            network_io = psutil.net_io_counters()

            metrics = SystemMetrics(
                timestamp=time.time(),
                cpu_percent=psutil.cpu_percent(),
                memory_percent=process.memory_percent(),
                memory_mb=process.memory_info().rss / 1024 / 1024,
                disk_io_read_mb=(disk_io.read_bytes if disk_io else 0) / 1024 / 1024,
                disk_io_write_mb=(disk_io.write_bytes if disk_io else 0) / 1024 / 1024,
                network_sent_mb=(network_io.bytes_sent if network_io else 0)
                / 1024
                / 1024,
                network_recv_mb=(network_io.bytes_recv if network_io else 0)
                / 1024
                / 1024,
            )

            with self.lock:
                self.system_metrics.append(metrics)

        except Exception as e:
            logger.warning("Failed to collect system metrics", error=str(e))

    def get_api_summary(self) -> dict[str, Any]:
        """
        Get API performance summary.

        Returns:
            Dictionary with API metrics summary
        """
        with self.lock:
            summary = {}

            for key, metrics in self.api_metrics.items():
                if metrics.count > 0:
                    response_times = list(self.response_times[key])

                    percentiles = {}
                    if response_times:
                        percentiles = {
                            "p50": statistics.median(response_times),
                            "p95": statistics.quantiles(response_times, n=20)[18]
                            if len(response_times) > 1
                            else response_times[0],
                            "p99": statistics.quantiles(response_times, n=100)[98]
                            if len(response_times) > 1
                            else response_times[0],
                        }

                    summary[key] = {
                        "endpoint": metrics.endpoint,
                        "method": metrics.method,
                        "count": metrics.count,
                        "avg_time": metrics.avg_time,
                        "min_time": metrics.min_time,
                        "max_time": metrics.max_time,
                        "errors": metrics.errors,
                        "error_rate": (metrics.errors / metrics.count) * 100,
                        "cache_hit_rate": metrics.cache_hit_rate,
                        **percentiles,
                    }

            return summary

    def get_system_summary(self) -> dict[str, Any]:
        """
        Get system performance summary.

        Returns:
            Dictionary with system metrics summary
        """
        with self.lock:
            if not self.system_metrics:
                return {}

            recent_metrics = list(self.system_metrics)

            cpu_values = [m.cpu_percent for m in recent_metrics]
            memory_values = [m.memory_mb for m in recent_metrics]

            return {
                "cpu_percent": {
                    "current": cpu_values[-1] if cpu_values else 0,
                    "avg": statistics.mean(cpu_values) if cpu_values else 0,
                    "max": max(cpu_values) if cpu_values else 0,
                },
                "memory_mb": {
                    "current": memory_values[-1] if memory_values else 0,
                    "avg": statistics.mean(memory_values) if memory_values else 0,
                    "max": max(memory_values) if memory_values else 0,
                },
                "baseline_memory_mb": self._baseline_metrics.memory_mb
                if self._baseline_metrics
                else 0,
                "sample_count": len(recent_metrics),
            }

    def get_top_endpoints(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get top endpoints by call count.

        Args:
            limit: Number of top endpoints to return

        Returns:
            List of top endpoints with metrics
        """
        with self.lock:
            metrics_list = []

            for _key, metrics in self.api_metrics.items():
                if metrics.count > 0:
                    metrics_list.append(
                        {
                            "endpoint": f"{metrics.method} {metrics.endpoint}",
                            "count": metrics.count,
                            "avg_time": metrics.avg_time,
                            "error_rate": (metrics.errors / metrics.count) * 100,
                            "cache_hit_rate": metrics.cache_hit_rate,
                        }
                    )

            # Sort by call count
            metrics_list.sort(key=lambda x: x["count"], reverse=True)
            return metrics_list[:limit]

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        with self.lock:
            self.api_metrics.clear()
            self.response_times.clear()
            self.system_metrics.clear()
            self._collect_baseline()

        logger.info("All metrics reset")


# Global performance monitor instance
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return _performance_monitor


def record_api_call(
    endpoint: str,
    method: str,
    duration: float,
    success: bool = True,
    cache_hit: bool = False,
) -> None:
    """Record an API call metric."""
    _performance_monitor.record_api_call(endpoint, method, duration, success, cache_hit)


def get_metrics_summary() -> dict[str, Any]:
    """Get comprehensive metrics summary."""
    monitor = get_performance_monitor()

    # Collect current system metrics
    monitor.collect_system_metrics()

    return {
        "api_metrics": monitor.get_api_summary(),
        "system_metrics": monitor.get_system_summary(),
        "top_endpoints": monitor.get_top_endpoints(5),
        "timestamp": time.time(),
    }
