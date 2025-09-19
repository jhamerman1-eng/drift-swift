"""
Comprehensive Testing Framework - Feature Flagged

Backtesting, shadow testing, and Monte Carlo simulation for jitter strategies.
Only available when comprehensive_testing feature flag is enabled.

Features:
- Historical Swift order replay
- Shadow testing (parallel execution without real orders)
- Monte Carlo regime simulations
- Strategy comparison and validation
"""

import asyncio
import logging
import time
import json
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..feature_flags import has_comprehensive_testing
from ..types import StrategySource, AttributionData

logger = logging.getLogger("jitter.advanced.testing")

class TestType(Enum):
    """Types of tests available"""
    BACKTEST = "backtest"               # Historical data replay
    SHADOW_TEST = "shadow_test"         # Live parallel execution
    MONTE_CARLO = "monte_carlo"         # Simulated scenarios
    STRESS_TEST = "stress_test"         # Extreme market conditions
    A_B_TEST = "a_b_test"              # Strategy comparison

class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TestConfiguration:
    """Configuration for a test run"""
    test_id: str
    test_type: TestType
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    data_source: str = "historical"
    strategies_to_test: List[str] = field(default_factory=list)
    expected_duration_seconds: float = 3600.0

@dataclass
class TestResult:
    """Results from a test execution"""
    test_id: str
    test_type: TestType
    status: TestStatus
    start_timestamp: float
    end_timestamp: Optional[float] = None
    total_orders_processed: int = 0
    fills_generated: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_latency_ms: float = 0.0
    error_count: int = 0
    strategy_comparisons: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    detailed_metrics: Dict[str, Any] = field(default_factory=dict)

class ComprehensiveTestingFramework:
    """
    Advanced testing framework for jitter strategies.
    
    Only functional when feature flag is enabled, otherwise provides basic validation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = has_comprehensive_testing()
        
        if not self.enabled:
            logger.info("🧪 Comprehensive Testing Framework DISABLED (feature flag off)")
            return
        
        # Test management
        self.active_tests: Dict[str, TestConfiguration] = {}
        self.test_results: Dict[str, TestResult] = {}
        self.test_data_cache: Dict[str, List[Dict[str, Any]]] = {}
        
        # Data sources
        self.historical_data_path = config.get("historical_data_path", "data/historical_orders")
        self.live_data_buffer: List[Dict[str, Any]] = []
        
        # Shadow testing
        self.shadow_strategies: Dict[str, Any] = {}
        self.shadow_active = False
        
        # Monte Carlo parameters
        self.mc_scenarios = config.get("monte_carlo_scenarios", 1000)
        self.mc_regime_transitions = config.get("regime_transition_matrix", {})
        
        # Callbacks for strategy execution
        self.strategy_executors: Dict[str, Callable] = {}
        
        # Performance tracking
        self.max_concurrent_tests = config.get("max_concurrent_tests", 3)
        self.test_data_retention_days = config.get("data_retention_days", 30)
        
        logger.info("🧪 Comprehensive Testing Framework ENABLED")
        logger.info(f"   Max concurrent tests: {self.max_concurrent_tests}")
        logger.info(f"   Historical data path: {self.historical_data_path}")
    
    def is_available(self) -> bool:
        """Check if comprehensive testing framework is available"""
        return self.enabled
    
    async def run_backtest(self, config: TestConfiguration) -> str:
        """
        Run historical backtest using recorded Swift orders.
        
        Returns test_id for tracking.
        """
        if not self.enabled:
            logger.warning("🧪 Backtest requested but feature disabled")
            return ""
        
        try:
            test_id = config.test_id or f"backtest_{int(time.time())}"
            config.test_id = test_id
            
            # Check concurrent test limit
            if len(self.active_tests) >= self.max_concurrent_tests:
                raise ValueError("Maximum concurrent tests exceeded")
            
            # Load historical data
            historical_data = await self._load_historical_data(config)
            if not historical_data:
                raise ValueError("No historical data available for specified period")
            
            # Initialize test
            self.active_tests[test_id] = config
            result = TestResult(
                test_id=test_id,
                test_type=TestType.BACKTEST,
                status=TestStatus.RUNNING,
                start_timestamp=time.time()
            )
            self.test_results[test_id] = result
            
            logger.info(f"🧪 Starting backtest {test_id} with {len(historical_data)} orders")
            
            # Run backtest asynchronously
            asyncio.create_task(self._execute_backtest(config, historical_data, result))
            
            return test_id
            
        except Exception as e:
            logger.error(f"❌ Backtest setup failed: {e}")
            return ""
    
    async def _execute_backtest(self, config: TestConfiguration, historical_data: List[Dict[str, Any]], result: TestResult):
        """Execute backtest with historical data"""
        
        try:
            fills_by_strategy = {}
            pnl_by_strategy = {}
            latencies_by_strategy = {}
            
            # Initialize strategy tracking
            for strategy in config.strategies_to_test:
                fills_by_strategy[strategy] = []
                pnl_by_strategy[strategy] = 0.0
                latencies_by_strategy[strategy] = []
            
            # Process historical orders
            for i, order_data in enumerate(historical_data):
                result.total_orders_processed += 1
                
                # Test each strategy
                for strategy_name in config.strategies_to_test:
                    if strategy_name in self.strategy_executors:
                        start_time = time.time()
                        
                        try:
                            # Execute strategy (in simulation mode)
                            fill_result = await self._simulate_strategy_execution(
                                strategy_name, order_data, config
                            )
                            
                            if fill_result:
                                execution_time = (time.time() - start_time) * 1000  # ms
                                fills_by_strategy[strategy_name].append(fill_result)
                                pnl_by_strategy[strategy_name] += fill_result.get("pnl", 0.0)
                                latencies_by_strategy[strategy_name].append(execution_time)
                                result.fills_generated += 1
                        
                        except Exception as e:
                            result.error_count += 1
                            logger.warning(f"Strategy {strategy_name} error on order {i}: {e}")
                
                # Progress reporting
                if i % 1000 == 0 and i > 0:
                    progress = i / len(historical_data)
                    logger.info(f"🧪 Backtest {config.test_id} progress: {progress:.1%}")
            
            # Calculate final metrics
            await self._calculate_backtest_metrics(result, fills_by_strategy, pnl_by_strategy, latencies_by_strategy)
            
            result.status = TestStatus.COMPLETED
            result.end_timestamp = time.time()
            
            logger.info(f"🧪 Backtest {config.test_id} completed: {result.fills_generated} fills, {result.total_pnl:.2f} PnL")
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.end_timestamp = time.time()
            logger.error(f"❌ Backtest {config.test_id} failed: {e}")
        finally:
            # Cleanup
            if config.test_id in self.active_tests:
                del self.active_tests[config.test_id]
    
    async def start_shadow_testing(self, strategies: List[str], duration_seconds: float = 3600.0) -> str:
        """
        Start shadow testing - run strategies in parallel with live orders without placing real orders.
        
        Returns test_id for tracking.
        """
        if not self.enabled:
            logger.warning("🧪 Shadow testing requested but feature disabled")
            return ""
        
        try:
            test_id = f"shadow_{int(time.time())}"
            
            config = TestConfiguration(
                test_id=test_id,
                test_type=TestType.SHADOW_TEST,
                description=f"Shadow test of {strategies}",
                strategies_to_test=strategies,
                expected_duration_seconds=duration_seconds
            )
            
            self.active_tests[test_id] = config
            result = TestResult(
                test_id=test_id,
                test_type=TestType.SHADOW_TEST,
                status=TestStatus.RUNNING,
                start_timestamp=time.time()
            )
            self.test_results[test_id] = result
            
            # Start shadow testing
            self.shadow_active = True
            self.shadow_strategies = {strategy: [] for strategy in strategies}
            
            logger.info(f"🧪 Started shadow testing {test_id} for {duration_seconds}s")
            
            # Auto-stop after duration
            asyncio.create_task(self._auto_stop_shadow_test(test_id, duration_seconds))
            
            return test_id
            
        except Exception as e:
            logger.error(f"❌ Shadow test setup failed: {e}")
            return ""
    
    async def process_live_order_for_shadow_test(self, order_data: Dict[str, Any]):
        """Process live order through shadow strategies"""
        
        if not self.enabled or not self.shadow_active:
            return
        
        try:
            for strategy_name in self.shadow_strategies.keys():
                if strategy_name in self.strategy_executors:
                    # Execute strategy in shadow mode
                    fill_result = await self._simulate_strategy_execution(
                        strategy_name, order_data, None, shadow_mode=True
                    )
                    
                    if fill_result:
                        self.shadow_strategies[strategy_name].append(fill_result)
        
        except Exception as e:
            logger.warning(f"❌ Shadow test processing error: {e}")
    
    async def run_monte_carlo_simulation(self, config: TestConfiguration) -> str:
        """
        Run Monte Carlo simulation with various market scenarios.
        
        Returns test_id for tracking.
        """
        if not self.enabled:
            logger.warning("🧪 Monte Carlo simulation requested but feature disabled")
            return ""
        
        try:
            test_id = config.test_id or f"monte_carlo_{int(time.time())}"
            config.test_id = test_id
            
            self.active_tests[test_id] = config
            result = TestResult(
                test_id=test_id,
                test_type=TestType.MONTE_CARLO,
                status=TestStatus.RUNNING,
                start_timestamp=time.time()
            )
            self.test_results[test_id] = result
            
            logger.info(f"🧪 Starting Monte Carlo simulation {test_id} with {self.mc_scenarios} scenarios")
            
            # Run simulation asynchronously
            asyncio.create_task(self._execute_monte_carlo_simulation(config, result))
            
            return test_id
            
        except Exception as e:
            logger.error(f"❌ Monte Carlo setup failed: {e}")
            return ""
    
    async def _execute_monte_carlo_simulation(self, config: TestConfiguration, result: TestResult):
        """Execute Monte Carlo simulation"""
        
        try:
            scenario_results = []
            
            for scenario_idx in range(self.mc_scenarios):
                # Generate scenario
                scenario_data = self._generate_market_scenario(config)
                
                # Test strategies on scenario
                scenario_result = {}
                for strategy_name in config.strategies_to_test:
                    strategy_pnl = 0.0
                    strategy_fills = 0
                    
                    for order_data in scenario_data:
                        if strategy_name in self.strategy_executors:
                            fill_result = await self._simulate_strategy_execution(
                                strategy_name, order_data, config
                            )
                            
                            if fill_result:
                                strategy_pnl += fill_result.get("pnl", 0.0)
                                strategy_fills += 1
                    
                    scenario_result[strategy_name] = {
                        "pnl": strategy_pnl,
                        "fills": strategy_fills
                    }
                
                scenario_results.append(scenario_result)
                result.total_orders_processed += len(scenario_data)
                
                # Progress reporting
                if scenario_idx % 100 == 0 and scenario_idx > 0:
                    progress = scenario_idx / self.mc_scenarios
                    logger.info(f"🧪 Monte Carlo {config.test_id} progress: {progress:.1%}")
            
            # Analyze results
            await self._analyze_monte_carlo_results(result, scenario_results)
            
            result.status = TestStatus.COMPLETED
            result.end_timestamp = time.time()
            
            logger.info(f"🧪 Monte Carlo {config.test_id} completed")
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.end_timestamp = time.time()
            logger.error(f"❌ Monte Carlo {config.test_id} failed: {e}")
        finally:
            if config.test_id in self.active_tests:
                del self.active_tests[config.test_id]
    
    async def _load_historical_data(self, config: TestConfiguration) -> List[Dict[str, Any]]:
        """Load historical Swift order data"""
        
        try:
            data_path = Path(self.historical_data_path)
            if not data_path.exists():
                logger.warning(f"Historical data path not found: {data_path}")
                return []
            
            # Load data files based on time range
            historical_data = []
            
            start_time = config.start_time or (time.time() - 86400)  # Default: last 24h
            end_time = config.end_time or time.time()
            
            # Simple file loading (in practice, use proper database/storage)
            for data_file in data_path.glob("*.json"):
                try:
                    with open(data_file, 'r') as f:
                        file_data = json.load(f)
                    
                    # Filter by time range
                    filtered_data = [
                        order for order in file_data
                        if start_time <= order.get("timestamp", 0) <= end_time
                    ]
                    
                    historical_data.extend(filtered_data)
                
                except Exception as e:
                    logger.warning(f"Failed to load {data_file}: {e}")
            
            # Sort by timestamp
            historical_data.sort(key=lambda x: x.get("timestamp", 0))
            
            return historical_data
            
        except Exception as e:
            logger.error(f"❌ Failed to load historical data: {e}")
            return []
    
    async def _simulate_strategy_execution(self, strategy_name: str, order_data: Dict[str, Any], 
                                         config: Optional[TestConfiguration], shadow_mode: bool = False) -> Optional[Dict[str, Any]]:
        """Simulate strategy execution on order data"""
        
        if strategy_name not in self.strategy_executors:
            return None
        
        try:
            # Call strategy executor in simulation mode
            executor = self.strategy_executors[strategy_name]
            
            # Add simulation context
            execution_context = {
                "simulation": True,
                "shadow_mode": shadow_mode,
                "test_config": config,
                "timestamp": time.time()
            }
            
            result = await executor(order_data, execution_context)
            return result
            
        except Exception as e:
            logger.warning(f"Strategy simulation error for {strategy_name}: {e}")
            return None
    
    def _generate_market_scenario(self, config: TestConfiguration) -> List[Dict[str, Any]]:
        """Generate synthetic market scenario for Monte Carlo"""
        
        scenario_length = config.parameters.get("scenario_length", 1000)
        base_price = config.parameters.get("base_price", 140.0)
        volatility = config.parameters.get("volatility", 0.02)
        
        scenario_data = []
        current_price = base_price
        
        for i in range(scenario_length):
            # Random walk with volatility
            price_change = np.random.normal(0, volatility * current_price)
            current_price += price_change
            current_price = max(current_price, 1.0)  # Prevent negative prices
            
            # Generate synthetic order
            order = {
                "timestamp": time.time() + i,
                "price": current_price,
                "size": np.random.exponential(2.0),  # Exponential size distribution
                "side": "buy" if np.random.random() > 0.5 else "sell",
                "market": "SOL-PERP",
                "synthetic": True
            }
            
            scenario_data.append(order)
        
        return scenario_data
    
    async def _auto_stop_shadow_test(self, test_id: str, duration_seconds: float):
        """Auto-stop shadow test after duration"""
        await asyncio.sleep(duration_seconds)
        await self.stop_shadow_testing(test_id)
    
    async def stop_shadow_testing(self, test_id: str) -> bool:
        """Stop active shadow testing"""
        
        if not self.enabled or test_id not in self.test_results:
            return False
        
        try:
            # Stop shadow testing
            self.shadow_active = False
            
            result = self.test_results[test_id]
            result.status = TestStatus.COMPLETED
            result.end_timestamp = time.time()
            
            # Calculate shadow test metrics
            await self._calculate_shadow_test_metrics(result)
            
            logger.info(f"🧪 Shadow testing {test_id} stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop shadow test {test_id}: {e}")
            return False
    
    async def _calculate_backtest_metrics(self, result: TestResult, fills_by_strategy: Dict, 
                                        pnl_by_strategy: Dict, latencies_by_strategy: Dict):
        """Calculate comprehensive backtest metrics"""
        
        # Overall metrics
        result.total_pnl = sum(pnl_by_strategy.values())
        total_fills = sum(len(fills) for fills in fills_by_strategy.values())
        result.fills_generated = total_fills
        
        if total_fills > 0:
            all_latencies = [lat for latencies in latencies_by_strategy.values() for lat in latencies]
            result.avg_latency_ms = np.mean(all_latencies) if all_latencies else 0.0
        
        # Strategy-specific metrics
        for strategy_name in fills_by_strategy.keys():
            fills = fills_by_strategy[strategy_name]
            pnl = pnl_by_strategy[strategy_name]
            latencies = latencies_by_strategy[strategy_name]
            
            if fills:
                profitable_fills = sum(1 for fill in fills if fill.get("pnl", 0) > 0)
                win_rate = profitable_fills / len(fills)
                
                # Calculate Sharpe ratio (simplified)
                pnl_series = [fill.get("pnl", 0) for fill in fills]
                sharpe = np.mean(pnl_series) / np.std(pnl_series) if np.std(pnl_series) > 0 else 0.0
                
                result.strategy_comparisons[strategy_name] = {
                    "fills": len(fills),
                    "total_pnl": pnl,
                    "win_rate": win_rate,
                    "sharpe_ratio": sharpe,
                    "avg_latency_ms": np.mean(latencies) if latencies else 0.0,
                    "avg_pnl_per_fill": pnl / len(fills)
                }
    
    async def _calculate_shadow_test_metrics(self, result: TestResult):
        """Calculate shadow test metrics"""
        
        for strategy_name, fills in self.shadow_strategies.items():
            if fills:
                total_pnl = sum(fill.get("pnl", 0) for fill in fills)
                profitable_fills = sum(1 for fill in fills if fill.get("pnl", 0) > 0)
                win_rate = profitable_fills / len(fills)
                
                result.strategy_comparisons[strategy_name] = {
                    "fills": len(fills),
                    "total_pnl": total_pnl,
                    "win_rate": win_rate,
                    "avg_pnl_per_fill": total_pnl / len(fills)
                }
        
        # Clear shadow data
        self.shadow_strategies = {}
    
    async def _analyze_monte_carlo_results(self, result: TestResult, scenario_results: List[Dict]):
        """Analyze Monte Carlo simulation results"""
        
        strategy_stats = {}
        
        for strategy_name in result.strategy_comparisons.keys():
            strategy_pnls = [scenario.get(strategy_name, {}).get("pnl", 0.0) for scenario in scenario_results]
            
            strategy_stats[strategy_name] = {
                "mean_pnl": np.mean(strategy_pnls),
                "std_pnl": np.std(strategy_pnls),
                "median_pnl": np.median(strategy_pnls),
                "worst_case": np.min(strategy_pnls),
                "best_case": np.max(strategy_pnls),
                "var_95": np.percentile(strategy_pnls, 5),  # 95% VaR
                "profitable_scenarios": sum(1 for pnl in strategy_pnls if pnl > 0) / len(strategy_pnls)
            }
        
        result.strategy_comparisons = strategy_stats
    
    def register_strategy_executor(self, strategy_name: str, executor: Callable):
        """Register strategy executor for testing"""
        self.strategy_executors[strategy_name] = executor
        logger.info(f"🧪 Registered strategy executor: {strategy_name}")
    
    def get_test_status(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a test"""
        if test_id in self.test_results:
            result = self.test_results[test_id]
            return {
                "test_id": test_id,
                "type": result.test_type.value,
                "status": result.status.value,
                "progress": self._calculate_test_progress(test_id),
                "fills_generated": result.fills_generated,
                "total_pnl": result.total_pnl,
                "error_count": result.error_count
            }
        return None
    
    def _calculate_test_progress(self, test_id: str) -> float:
        """Calculate test progress percentage"""
        if test_id not in self.active_tests or test_id not in self.test_results:
            return 1.0 if test_id in self.test_results else 0.0
        
        config = self.active_tests[test_id]
        result = self.test_results[test_id]
        
        if config.test_type == TestType.BACKTEST:
            # Estimate based on orders processed (rough estimate)
            return min(result.total_orders_processed / 10000, 1.0)
        elif config.test_type == TestType.SHADOW_TEST:
            # Based on elapsed time
            elapsed = time.time() - result.start_timestamp
            return min(elapsed / config.expected_duration_seconds, 1.0)
        else:
            return 0.5  # Unknown progress
    
    def get_testing_stats(self) -> Dict[str, Any]:
        """Get comprehensive testing framework statistics"""
        if not self.enabled:
            return {"feature_enabled": False}
        
        active_count = len(self.active_tests)
        completed_tests = [r for r in self.test_results.values() if r.status == TestStatus.COMPLETED]
        
        return {
            "feature_enabled": True,
            "active_tests": active_count,
            "completed_tests": len(completed_tests),
            "total_tests_run": len(self.test_results),
            "shadow_testing_active": self.shadow_active,
            "registered_strategies": list(self.strategy_executors.keys()),
            "max_concurrent_tests": self.max_concurrent_tests,
            "data_retention_days": self.test_data_retention_days
        }




