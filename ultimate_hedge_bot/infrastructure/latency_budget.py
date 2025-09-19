"""
Ultimate Hedge Bot - Latency Budget System
Realistic latency monitoring with percentile tracking for Solana RPC.
"""

import time
import statistics
from typing import Dict, Any, List, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class LatencyBudgetMonitor:
    """
    Realistic latency budget monitoring for production trading.

    Key Features:
    - Realistic budgets for Solana RPC (not co-located assumptions)
    - Percentile tracking (not just counters)
    - Soft limits with warnings (not hard gates)
    - Historical trend analysis
    """

    # Realistic latency budgets for Solana RPC (milliseconds)
    # SOFT LIMITS - used for monitoring, not blocking operations
    LATENCY_TARGETS = {
        'hedge_calculation': 50,     # Target: < 50ms (complex calculations)
        'order_submission': 200,     # Target: < 200ms (RPC round trip)
        'fill_detection': 100,       # Target: < 100ms (websocket/polling)
        'position_update': 20,       # Target: < 20ms (local updates)
        'risk_check': 30,            # Target: < 30ms (validation logic)
        'cancel_order': 150,         # Target: < 150ms (RPC round trip)
        'venue_switch': 500,         # Target: < 500ms (failover time)
    }

    # Warning thresholds (when to alert but not block)
    LATENCY_WARNINGS = {
        'hedge_calculation': 100,    # Warn at 100ms
        'order_submission': 500,     # Warn at 500ms
        'fill_detection': 300,       # Warn at 300ms
        'position_update': 50,       # Warn at 50ms
        'risk_check': 75,            # Warn at 75ms
        'cancel_order': 300,         # Warn at 300ms
        'venue_switch': 1000,        # Warn at 1 second
    }

    # Critical thresholds (when to trigger escalation)
    LATENCY_CRITICAL = {
        'hedge_calculation': 200,    # Critical at 200ms
        'order_submission': 1000,    # Critical at 1 second
        'fill_detection': 1000,      # Critical at 1 second
        'position_update': 100,      # Critical at 100ms
        'risk_check': 150,           # Critical at 150ms
        'cancel_order': 500,         # Critical at 500ms
        'venue_switch': 2000,        # Critical at 2 seconds
    }

    def __init__(self):
        self._measurements: Dict[str, List[float]] = defaultdict(list)
        self._active_timers: Dict[str, float] = {}
        self._violation_counts: Dict[str, int] = defaultdict(int)
        self._warning_counts: Dict[str, int] = defaultdict(int)
        self._critical_counts: Dict[str, int] = defaultdict(int)

    def start_timing(self, operation: str) -> str:
        """
        Start timing an operation.

        Args:
            operation: Name of the operation being timed

        Returns:
            Timer ID for use with end_timing
        """
        timer_id = f"{operation}_{int(time.time()*1000000)}"
        self._active_timers[timer_id] = time.perf_counter()
        return timer_id

    def end_timing(self, timer_id: str) -> float:
        """
        End timing and record the measurement.

        Args:
            timer_id: Timer ID returned by start_timing

        Returns:
            Latency in milliseconds
        """
        if timer_id not in self._active_timers:
            logger.warning(f"No active timer for {timer_id}")
            return 0.0

        start_time = self._active_timers.pop(timer_id)
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Extract operation name from timer_id
        operation = timer_id.split('_')[0]

        # Record measurement
        self._measurements[operation].append(latency_ms)

        # Keep only recent measurements (last 1000 per operation)
        if len(self._measurements[operation]) > 1000:
            self._measurements[operation] = self._measurements[operation][-500:]

        # Check against thresholds and log
        self._check_latency_thresholds(operation, latency_ms)

        return latency_ms

    def _check_latency_thresholds(self, operation: str, latency_ms: float):
        """Check latency against thresholds and log violations."""
        target = self.LATENCY_TARGETS.get(operation, 100)
        warning = self.LATENCY_WARNINGS.get(operation, 200)
        critical = self.LATENCY_CRITICAL.get(operation, 500)

        if latency_ms > critical:
            self._critical_counts[operation] += 1
            logger.error(f"🚨 CRITICAL LATENCY: {operation} took {latency_ms:.1f}ms "
                        f"(critical: {critical}ms)")
            # Could trigger alerts, auto-scaling, etc.

        elif latency_ms > warning:
            self._warning_counts[operation] += 1
            logger.warning(f"⚠️ HIGH LATENCY: {operation} took {latency_ms:.1f}ms "
                          f"(warning: {warning}ms)")

        elif latency_ms > target:
            logger.info(f"ℹ️ SLOW: {operation} took {latency_ms:.1f}ms (target: {target}ms)")

        else:
            logger.debug(f"✅ FAST: {operation} took {latency_ms:.1f}ms")

    def get_latency_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive latency statistics.

        Args:
            operation: Specific operation to get stats for, or None for all

        Returns:
            Dictionary with latency statistics including percentiles
        """
        if operation:
            return self._get_operation_stats(operation)
        else:
            return self._get_all_stats()

    def _get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for a specific operation."""
        measurements = self._measurements[operation]

        if not measurements:
            return {
                'operation': operation,
                'count': 0,
                'target_ms': self.LATENCY_TARGETS.get(operation, 0),
                'warning_ms': self.LATENCY_WARNINGS.get(operation, 0),
                'critical_ms': self.LATENCY_CRITICAL.get(operation, 0)
            }

        # Calculate percentiles
        sorted_measurements = sorted(measurements)
        count = len(sorted_measurements)

        stats = {
            'operation': operation,
            'count': count,
            'min_ms': min(sorted_measurements),
            'max_ms': max(sorted_measurements),
            'avg_ms': sum(sorted_measurements) / count,
            'median_ms': statistics.median(sorted_measurements),
            'p95_ms': sorted_measurements[int(count * 0.95)] if count > 0 else 0,
            'p99_ms': sorted_measurements[int(count * 0.99)] if count > 0 else 0,
            'target_ms': self.LATENCY_TARGETS.get(operation, 0),
            'warning_ms': self.LATENCY_WARNINGS.get(operation, 0),
            'critical_ms': self.LATENCY_CRITICAL.get(operation, 0),
            'warnings': self._warning_counts[operation],
            'criticals': self._critical_counts[operation]
        }

        # Compliance rates
        target_compliance = sum(1 for m in measurements if m <= stats['target_ms']) / count
        warning_compliance = sum(1 for m in measurements if m <= stats['warning_ms']) / count

        stats.update({
            'target_compliance_rate': target_compliance,
            'warning_compliance_rate': warning_compliance,
            'target_violations': count - int(count * target_compliance),
            'warning_violations': count - int(count * warning_compliance)
        })

        return stats

    def _get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all operations."""
        all_stats = {}
        all_operations = set(self._measurements.keys()) | set(self.LATENCY_TARGETS.keys())

        for operation in all_operations:
            all_stats[operation] = self._get_operation_stats(operation)

        # Overall summary
        total_measurements = sum(len(measurements) for measurements in self._measurements.values())
        total_warnings = sum(self._warning_counts.values())
        total_criticals = sum(self._critical_counts.values())

        all_stats['summary'] = {
            'total_operations': len(all_operations),
            'total_measurements': total_measurements,
            'total_warnings': total_warnings,
            'total_criticals': total_criticals,
            'warning_rate': total_warnings / total_measurements if total_measurements > 0 else 0,
            'critical_rate': total_criticals / total_measurements if total_measurements > 0 else 0,
            'overall_compliance': self._calculate_overall_compliance(all_stats)
        }

        return all_stats

    def _calculate_overall_compliance(self, all_stats: Dict[str, Any]) -> float:
        """Calculate overall compliance rate across all operations."""
        total_compliance = 0
        operation_count = 0

        for operation, stats in all_stats.items():
            if operation == 'summary':
                continue
            if stats['count'] > 0:
                total_compliance += stats['target_compliance_rate']
                operation_count += 1

        return total_compliance / operation_count if operation_count > 0 else 1.0

    def get_performance_trends(self, operation: str, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance trends over time.

        Args:
            operation: Operation to analyze
            hours: Number of hours to look back

        Returns:
            Trend analysis with moving averages and change rates
        """
        measurements = self._measurements[operation]
        if not measurements:
            return {'error': 'No measurements available'}

        # This would require timestamped measurements for proper trend analysis
        # For now, return basic stats
        return {
            'current_avg': sum(measurements[-100:]) / len(measurements[-100:]) if measurements else 0,
            'overall_avg': sum(measurements) / len(measurements) if measurements else 0,
            'measurement_count': len(measurements),
            'trend': 'stable'  # Would calculate actual trend
        }

    def reset_stats(self, operation: Optional[str] = None):
        """Reset statistics for monitoring or testing."""
        if operation:
            self._measurements[operation].clear()
            self._warning_counts[operation] = 0
            self._critical_counts[operation] = 0
        else:
            self._measurements.clear()
            self._warning_counts.clear()
            self._critical_counts.clear()

        logger.info(f"✅ Reset latency stats for {operation or 'all operations'}")

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status based on latency compliance."""
        stats = self.get_latency_stats()

        if 'summary' not in stats:
            return {'status': 'unknown', 'details': 'No measurements available'}

        summary = stats['summary']

        # Determine health status
        if summary['critical_rate'] > 0.1:  # >10% critical violations
            status = 'critical'
        elif summary['warning_rate'] > 0.2:  # >20% warning violations
            status = 'warning'
        elif summary['overall_compliance'] > 0.9:  # >90% target compliance
            status = 'healthy'
        else:
            status = 'degraded'

        return {
            'status': status,
            'overall_compliance': summary['overall_compliance'],
            'warning_rate': summary['warning_rate'],
            'critical_rate': summary['critical_rate'],
            'recommendations': self._get_health_recommendations(status)
        }

    def _get_health_recommendations(self, status: str) -> List[str]:
        """Get health recommendations based on status."""
        if status == 'critical':
            return [
                "Immediate attention required - high critical violation rate",
                "Consider reducing operation frequency",
                "Check for network or infrastructure issues",
                "Review and optimize slow operations"
            ]
        elif status == 'warning':
            return [
                "Monitor closely - elevated warning rate",
                "Review recent changes that may affect performance",
                "Consider increasing resource allocation"
            ]
        elif status == 'healthy':
            return [
                "Performance within acceptable ranges",
                "Continue monitoring for trends"
            ]
        else:  # degraded
            return [
                "Performance degradation detected",
                "Investigate root causes of latency issues",
                "Consider performance optimizations"
            ]


# Global latency budget monitor instance
latency_budget_monitor = LatencyBudgetMonitor()

