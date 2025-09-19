th"""
Compute Budget Metrics and Cost Tracking

This module provides comprehensive metrics collection and cost tracking
for compute budget optimization across the Drift Swift trading system.

Key Features:
- Transaction cost monitoring by strategy
- Compute budget utilization tracking
- Cost optimization effectiveness metrics
- Priority level performance analysis
- Real-time cost attribution
"""

import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class ComputeBudgetMetrics:
    """Comprehensive compute budget metrics tracker"""

    # Cost tracking
    total_transaction_cost: float = 0.0
    total_compute_units_used: int = 0
    total_orders_with_compute_budget: int = 0

    # Strategy breakdown
    strategy_costs: Dict[str, float] = field(default_factory=dict)
    strategy_compute_units: Dict[str, int] = field(default_factory=dict)
    strategy_order_count: Dict[str, int] = field(default_factory=dict)

    # Priority level tracking
    priority_costs: Dict[str, float] = field(default_factory=dict)
    priority_success_rates: Dict[str, float] = field(default_factory=dict)

    # Time-based metrics
    hourly_costs: Dict[str, float] = field(default_factory=dict)
    daily_costs: Dict[str, float] = field(default_factory=dict)

    # Optimization metrics
    cost_savings_estimate: float = 0.0
    optimization_effectiveness: float = 0.0

    # Market condition impact
    market_condition_costs: Dict[str, float] = field(default_factory=dict)

    def record_transaction_cost(
        self,
        strategy: str,
        priority_level: str,
        compute_units: int,
        compute_price_micro_lamports: int,
        market_condition: str = "normal",
        success: bool = True
    ):
        """
        Record a transaction cost for metrics tracking

        Args:
            strategy: Trading strategy (shotgun, sniper, twap, etc.)
            priority_level: Priority level (low, medium, high, critical)
            compute_units: Number of compute units used
            compute_price_micro_lamports: Price per compute unit in micro-lamports
            market_condition: Market condition (volatile, calm, toxic)
            success: Whether the transaction was successful
        """
        # Calculate transaction cost in lamports
        transaction_cost_lamports = (compute_units * compute_price_micro_lamports) // 1_000_000

        # Update totals
        self.total_transaction_cost += transaction_cost_lamports
        self.total_compute_units_used += compute_units
        self.total_orders_with_compute_budget += 1

        # Update strategy metrics
        if strategy not in self.strategy_costs:
            self.strategy_costs[strategy] = 0.0
            self.strategy_compute_units[strategy] = 0
            self.strategy_order_count[strategy] = 0

        self.strategy_costs[strategy] += transaction_cost_lamports
        self.strategy_compute_units[strategy] += compute_units
        self.strategy_order_count[strategy] += 1

        # Update priority metrics
        if priority_level not in self.priority_costs:
            self.priority_costs[priority_level] = 0.0

        self.priority_costs[priority_level] += transaction_cost_lamports

        # Update market condition metrics
        if market_condition not in self.market_condition_costs:
            self.market_condition_costs[market_condition] = 0.0

        self.market_condition_costs[market_condition] += transaction_cost_lamports

        # Update time-based metrics
        current_hour = datetime.now().strftime("%Y-%m-%d-%H")
        current_day = datetime.now().strftime("%Y-%m-%d")

        if current_hour not in self.hourly_costs:
            self.hourly_costs[current_hour] = 0.0
        self.hourly_costs[current_hour] += transaction_cost_lamports

        if current_day not in self.daily_costs:
            self.daily_costs[current_day] = 0.0
        self.daily_costs[current_day] += transaction_cost_lamports

        # Update success rates
        if priority_level not in self.priority_success_rates:
            self.priority_success_rates[priority_level] = {"success": 0, "total": 0}

        self.priority_success_rates[priority_level]["total"] += 1
        if success:
            self.priority_success_rates[priority_level]["success"] += 1

        # Calculate rolling success rate
        success_data = self.priority_success_rates[priority_level]
        if success_data["total"] > 0:
            success_rate = success_data["success"] / success_data["total"]
            self.priority_success_rates[priority_level]["rate"] = success_rate

        logger.debug(f"Recorded transaction cost: {transaction_cost_lamports} lamports for {strategy} strategy")

    def calculate_cost_savings_estimate(self, baseline_price_micro_lamports: int = 5000) -> float:
        """
        Estimate cost savings compared to baseline pricing

        Args:
            baseline_price_micro_lamports: Baseline price per compute unit

        Returns:
            Estimated savings in lamports
        """
        if self.total_compute_units_used == 0:
            return 0.0

        # Calculate what cost would have been at baseline
        baseline_cost = (self.total_compute_units_used * baseline_price_micro_lamports) // 1_000_000

        # Calculate actual cost
        actual_cost = self.total_transaction_cost

        # Savings is baseline minus actual
        savings = baseline_cost - actual_cost
        self.cost_savings_estimate = savings

        return savings

    def get_cost_efficiency_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive cost efficiency metrics

        Returns:
            Dictionary with cost efficiency analysis
        """
        metrics = {
            "total_cost_lamports": self.total_transaction_cost,
            "total_compute_units": self.total_compute_units_used,
            "total_orders": self.total_orders_with_compute_budget,
            "avg_cost_per_order": 0.0,
            "avg_cost_per_compute_unit": 0.0,
            "strategy_breakdown": {},
            "priority_breakdown": {},
            "market_condition_breakdown": {},
            "time_based_costs": {
                "hourly": dict(sorted(self.hourly_costs.items())),
                "daily": dict(sorted(self.daily_costs.items()))
            }
        }

        # Calculate averages
        if self.total_orders_with_compute_budget > 0:
            metrics["avg_cost_per_order"] = self.total_transaction_cost / self.total_orders_with_compute_budget

        if self.total_compute_units_used > 0:
            metrics["avg_cost_per_compute_unit"] = self.total_transaction_cost / self.total_compute_units_used

        # Strategy breakdown
        for strategy in self.strategy_costs:
            order_count = self.strategy_order_count[strategy]
            total_cost = self.strategy_costs[strategy]
            compute_units = self.strategy_compute_units[strategy]

            metrics["strategy_breakdown"][strategy] = {
                "total_cost": total_cost,
                "order_count": order_count,
                "compute_units": compute_units,
                "avg_cost_per_order": total_cost / order_count if order_count > 0 else 0,
                "cost_percentage": (total_cost / self.total_transaction_cost * 100) if self.total_transaction_cost > 0 else 0
            }

        # Priority breakdown
        for priority in self.priority_costs:
            total_cost = self.priority_costs[priority]
            success_data = self.priority_success_rates.get(priority, {"rate": 0.0})

            metrics["priority_breakdown"][priority] = {
                "total_cost": total_cost,
                "success_rate": success_data.get("rate", 0.0),
                "cost_percentage": (total_cost / self.total_transaction_cost * 100) if self.total_transaction_cost > 0 else 0
            }

        # Market condition breakdown
        for condition in self.market_condition_costs:
            total_cost = self.market_condition_costs[condition]

            metrics["market_condition_breakdown"][condition] = {
                "total_cost": total_cost,
                "cost_percentage": (total_cost / self.total_transaction_cost * 100) if self.total_transaction_cost > 0 else 0
            }

        return metrics

    def get_optimization_recommendations(self) -> List[str]:
        """
        Generate optimization recommendations based on metrics

        Returns:
            List of optimization recommendations
        """
        recommendations = []

        # Analyze strategy costs
        if self.strategy_costs:
            highest_cost_strategy = max(self.strategy_costs.items(), key=lambda x: x[1])
            lowest_cost_strategy = min(self.strategy_costs.items(), key=lambda x: x[1])

            if highest_cost_strategy[1] > lowest_cost_strategy[1] * 2:
                recommendations.append(
                    f"Consider optimizing {highest_cost_strategy[0]} strategy - "
                    f"it's {highest_cost_strategy[1]/lowest_cost_strategy[1]:.1f}x more expensive than {lowest_cost_strategy[0]}"
                )

        # Analyze priority effectiveness
        for priority, success_data in self.priority_success_rates.items():
            success_rate = success_data.get("rate", 0.0)
            if success_rate < 0.8:  # Less than 80% success rate
                recommendations.append(
                    f"Review {priority} priority transactions - success rate is only {success_rate:.1%}"
                )

        # Analyze market condition costs
        if "volatile" in self.market_condition_costs and "calm" in self.market_condition_costs:
            volatile_cost = self.market_condition_costs["volatile"]
            calm_cost = self.market_condition_costs["calm"]

            if volatile_cost > calm_cost * 1.5:
                recommendations.append(
                    "Volatile market conditions are significantly increasing costs - "
                    "consider adjusting priority levels or strategy during volatility"
                )

        # Cost savings analysis
        savings = self.calculate_cost_savings_estimate()
        if savings > 0:
            recommendations.append(
                f"Compute budget optimization has saved approximately {savings:.0f} lamports compared to baseline"
            )

        if not recommendations:
            recommendations.append("No specific optimization recommendations at this time")

        return recommendations

    def reset_metrics(self, timeframe: str = "daily"):
        """
        Reset metrics based on timeframe

        Args:
            timeframe: Timeframe for reset ("hourly", "daily", "weekly", "monthly")
        """
        if timeframe == "hourly":
            # Keep only current hour's data
            current_hour = datetime.now().strftime("%Y-%m-%d-%H")
            self.hourly_costs = {k: v for k, v in self.hourly_costs.items() if k.endswith(f"-{current_hour.split('-')[-1]}")}
        elif timeframe == "daily":
            # Reset daily metrics but keep historical data
            self.daily_costs = {}
            self.hourly_costs = {}
        elif timeframe == "weekly":
            # Reset all time-based metrics
            self.hourly_costs = {}
            self.daily_costs = {}
        elif timeframe == "monthly":
            # Full reset
            self.hourly_costs = {}
            self.daily_costs = {}

        logger.info(f"Reset compute budget metrics for timeframe: {timeframe}")

class ComputeBudgetMonitor:
    """Real-time compute budget monitoring and alerting"""

    def __init__(self, metrics: ComputeBudgetMetrics):
        self.metrics = metrics
        self.alerts = []
        self.thresholds = {
            "max_hourly_cost": 1_000_000,  # 1 SOL per hour
            "max_daily_cost": 10_000_000,  # 10 SOL per day
            "min_success_rate": 0.85,      # 85% success rate
            "cost_anomaly_threshold": 2.0  # 2x normal cost
        }

    def check_alerts(self) -> List[str]:
        """
        Check for cost and performance alerts

        Returns:
            List of active alerts
        """
        alerts = []

        # Hourly cost alert
        current_hour = datetime.now().strftime("%Y-%m-%d-%H")
        hourly_cost = self.metrics.hourly_costs.get(current_hour, 0)

        if hourly_cost > self.thresholds["max_hourly_cost"]:
            alerts.append(
                f"⚠️ HIGH HOURLY COST: {hourly_cost} lamports "
                f"(threshold: {self.thresholds['max_hourly_cost']})"
            )

        # Daily cost alert
        current_day = datetime.now().strftime("%Y-%m-%d")
        daily_cost = self.metrics.daily_costs.get(current_day, 0)

        if daily_cost > self.thresholds["max_daily_cost"]:
            alerts.append(
                f"🚨 HIGH DAILY COST: {daily_cost} lamports "
                f"(threshold: {self.thresholds['max_daily_cost']})"
            )

        # Success rate alerts
        for priority, success_data in self.metrics.priority_success_rates.items():
            success_rate = success_data.get("rate", 1.0)
            if success_rate < self.thresholds["min_success_rate"]:
                alerts.append(
                    f"❌ LOW SUCCESS RATE: {priority} priority at {success_rate:.1%} "
                    f"(threshold: {self.thresholds['min_success_rate']:.1%})"
                )

        # Cost anomaly detection
        if len(self.metrics.strategy_costs) > 1:
            costs = list(self.metrics.strategy_costs.values())
            avg_cost = sum(costs) / len(costs)
            max_cost = max(costs)

            if max_cost > avg_cost * self.thresholds["cost_anomaly_threshold"]:
                highest_cost_strategy = max(self.metrics.strategy_costs.items(), key=lambda x: x[1])
                alerts.append(
                    f"🔍 COST ANOMALY: {highest_cost_strategy[0]} strategy costs "
                    f"{highest_cost_strategy[1]} lamports "
                    f"({highest_cost_strategy[1]/avg_cost:.1f}x average)"
                )

        self.alerts = alerts
        return alerts

    def get_monitoring_report(self) -> Dict[str, Any]:
        """
        Get comprehensive monitoring report

        Returns:
            Dictionary with monitoring data and alerts
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "metrics_summary": self.metrics.get_cost_efficiency_metrics(),
            "alerts": self.check_alerts(),
            "thresholds": self.thresholds,
            "recommendations": self.metrics.get_optimization_recommendations(),
            "health_status": "healthy"
        }

        # Determine overall health status
        if any("🚨" in alert for alert in report["alerts"]):
            report["health_status"] = "critical"
        elif any("⚠️" in alert or "❌" in alert for alert in report["alerts"]):
            report["health_status"] = "warning"
        else:
            report["health_status"] = "healthy"

        return report

# Global instances for system-wide usage
compute_budget_metrics = ComputeBudgetMetrics()
compute_budget_monitor = ComputeBudgetMonitor(compute_budget_metrics)

def record_compute_budget_usage(
    strategy: str,
    priority_level: str,
    compute_units: int,
    compute_price_micro_lamports: int,
    market_condition: str = "normal",
    success: bool = True
):
    """
    Convenience function to record compute budget usage

    This function can be called from anywhere in the system to track
    compute budget usage and costs.
    """
    compute_budget_metrics.record_transaction_cost(
        strategy=strategy,
        priority_level=priority_level,
        compute_units=compute_units,
        compute_price_micro_lamports=compute_price_micro_lamports,
        market_condition=market_condition,
        success=success
    )

def get_compute_budget_report() -> Dict[str, Any]:
    """
    Get a comprehensive compute budget report

    Returns:
        Full compute budget monitoring report
    """
    return compute_budget_monitor.get_monitoring_report()

# Example usage and integration points
if __name__ == "__main__":
    # Example of how to use the metrics system
    print("🔧 Compute Budget Metrics Demo")

    # Record some sample transactions
    record_compute_budget_usage(
        strategy="twap",
        priority_level="high",
        compute_units=800_000,
        compute_price_micro_lamports=15_000,
        market_condition="volatile",
        success=True
    )

    record_compute_budget_usage(
        strategy="shotgun",
        priority_level="critical",
        compute_units=600_000,
        compute_price_micro_lamports=20_000,
        market_condition="volatile",
        success=True
    )

    # Get and display report
    report = get_compute_budget_report()
    print(f"Health Status: {report['health_status']}")
    print(f"Total Cost: {report['metrics_summary']['total_cost_lamports']} lamports")
    print(f"Active Alerts: {len(report['alerts'])}")

    if report['alerts']:
        print("Alerts:")
        for alert in report['alerts']:
            print(f"  {alert}")

    print("Recommendations:")
    for rec in report['recommendations']:
        print(f"  • {rec}")


