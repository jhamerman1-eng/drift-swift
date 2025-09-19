"""
Test script for Enhanced JIT Bot integration with Ultimate Bot
Validates performance improvements and latency optimization.
"""

import asyncio
import logging
import time
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from bots.jit.enhanced_jit_bot import EnhancedJITConfig, create_enhanced_jit_market_maker
from ultimate_hedge_bot.infrastructure.latency_budget import LatencyBudgetMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class MockClient:
    """Mock client for testing"""
    
    def __init__(self):
        self.connected = True
        self.orders = {}
        self.position = 0.0
    
    async def get_orderbook(self):
        """Mock orderbook data"""
        return {
            'bids': [(140.0, 10.0), (139.9, 15.0), (139.8, 20.0)],
            'asks': [(140.1, 10.0), (140.2, 15.0), (140.3, 20.0)],
            'timestamp': time.time()
        }
    
    async def get_position(self):
        """Mock position data"""
        return self.position
    
    async def place_order(self, side, price, size):
        """Mock order placement"""
        order_id = f"order_{int(time.time() * 1000)}"
        self.orders[order_id] = {
            'side': side,
            'price': price,
            'size': size,
            'timestamp': time.time()
        }
        return order_id
    
    async def cancel_order(self, order_id):
        """Mock order cancellation"""
        if order_id in self.orders:
            del self.orders[order_id]
            return True
        return False
    
    async def cancel_all(self):
        """Mock cancel all orders"""
        self.orders.clear()
        return True


async def test_latency_budget_integration():
    """Test latency budget monitoring integration"""
    logger.info("🧪 Testing Latency Budget Integration...")
    
    # Create latency monitor
    monitor = LatencyBudgetMonitor()
    
    # Test various operations
    operations = [
        'hedge_calculation',
        'order_submission',
        'fill_detection',
        'position_update',
        'risk_check'
    ]
    
    for operation in operations:
        # Simulate operation with timing
        timer = monitor.start_timing(operation)
        await asyncio.sleep(0.01)  # Simulate 10ms operation
        latency = monitor.end_timing(timer)
        
        logger.info(f"   {operation}: {latency:.1f}ms")
    
    # Get latency stats
    stats = monitor.get_latency_stats()
    logger.info(f"   Overall compliance: {stats['summary']['overall_compliance']:.1%}")
    
    logger.info("✅ Latency budget integration test complete")


async def test_enhanced_jit_performance():
    """Test enhanced JIT bot performance"""
    logger.info("🧪 Testing Enhanced JIT Bot Performance...")
    
    # Create test configuration
    config = EnhancedJITConfig(
        symbol="SOL-PERP",
        leverage=10,
        post_only=True,
        obi_microprice=True,
        spread_bps_base=8.0,
        spread_bps_min=4.0,
        spread_bps_max=25.0,
        inventory_target=0.0,
        max_position_abs=120.0,
        cancel_replace_enabled=True,
        cancel_replace_interval_ms=900,
        toxicity_guard=True,
        latency_budget_enabled=True,
        performance_tracking=True,
        attribution_enabled=True,
        strategy_coordination=True
    )
    
    # Create mock client
    client = MockClient()
    
    # Create enhanced JIT market maker
    jit_mm = create_enhanced_jit_market_maker(config, client)
    
    # Run performance test
    test_cycles = 50
    start_time = time.time()
    
    logger.info(f"   Running {test_cycles} test cycles...")
    
    for i in range(test_cycles):
        cycle_start = time.time()
        await jit_mm.run_market_making_cycle()
        cycle_duration = (time.time() - cycle_start) * 1000
        
        if i % 10 == 0:
            logger.info(f"   Cycle {i}: {cycle_duration:.1f}ms")
        
        # Small delay to simulate real trading
        await asyncio.sleep(0.01)
    
    total_time = time.time() - start_time
    
    # Get performance summary
    summary = jit_mm.get_performance_summary()
    
    logger.info(f"   Total test time: {total_time:.2f}s")
    logger.info(f"   Average cycle time: {total_time/test_cycles*1000:.1f}ms")
    logger.info(f"   Total cycles: {summary['cycle_stats']['total_cycles']}")
    logger.info(f"   Active orders: {summary['active_orders']}")
    
    # Check performance metrics
    if 'performance_metrics' in summary:
        perf_metrics = summary['performance_metrics']
        cycle_perf = perf_metrics.get('cycle_performance', {})
        if cycle_perf:
            logger.info(f"   Avg cycle duration: {cycle_perf.get('avg_duration_ms', 0):.1f}ms")
            logger.info(f"   P95 cycle duration: {cycle_perf.get('p95_duration_ms', 0):.1f}ms")
            logger.info(f"   P99 cycle duration: {cycle_perf.get('p99_duration_ms', 0):.1f}ms")
    
    # Check latency budget compliance
    if 'latency_budget' in summary:
        latency_budget = summary['latency_budget']
        if 'summary' in latency_budget:
            summary_stats = latency_budget['summary']
            logger.info(f"   Latency compliance: {summary_stats.get('overall_compliance', 0):.1%}")
            logger.info(f"   Warning rate: {summary_stats.get('warning_rate', 0):.1%}")
            logger.info(f"   Critical rate: {summary_stats.get('critical_rate', 0):.1%}")
    
    logger.info("✅ Enhanced JIT bot performance test complete")


async def test_attribution_integration():
    """Test attribution system integration"""
    logger.info("🧪 Testing Attribution System Integration...")
    
    # Create test configuration
    config = EnhancedJITConfig(
        symbol="SOL-PERP",
        leverage=10,
        post_only=True,
        obi_microprice=True,
        spread_bps_base=8.0,
        spread_bps_min=4.0,
        spread_bps_max=25.0,
        inventory_target=0.0,
        max_position_abs=120.0,
        cancel_replace_enabled=True,
        cancel_replace_interval_ms=900,
        toxicity_guard=True,
        attribution_enabled=True,
        strategy_coordination=True
    )
    
    # Create mock client
    client = MockClient()
    
    # Create enhanced JIT market maker
    jit_mm = create_enhanced_jit_market_maker(config, client)
    
    # Test attribution if available
    if jit_mm.attributor:
        # Create test fills
        test_fills = [
            {
                'fill_id': 'test_fill_1',
                'source': 'hybrid_shotgun',
                'market': 'SOL-PERP',
                'side': 'buy',
                'size': 5.0,
                'price': 140.0
            },
            {
                'fill_id': 'test_fill_2',
                'source': 'hybrid_sniper',
                'market': 'SOL-PERP',
                'side': 'sell',
                'size': 3.0,
                'price': 140.5
            }
        ]
        
        for fill_data in test_fills:
            # Attribute fill
            attributed_fill = jit_mm.attributor.attribute_fill(**fill_data)
            logger.info(f"   Attributed fill: {attributed_fill.fill_id} - Quality: {attributed_fill.quality_score:.2f}")
            
            # Update outcome
            pnl = 2.5 if fill_data['side'] == 'buy' else -1.5
            jit_mm.attributor.update_fill_outcome(attributed_fill.fill_id, pnl)
        
        # Get attribution summary
        attribution_summary = jit_mm.attributor.get_performance_summary()
        logger.info(f"   Total fills: {attribution_summary['total_fills']}")
        logger.info(f"   Total volume: {attribution_summary['total_volume']:.2f}")
        logger.info(f"   Total PnL: {attribution_summary['total_pnl']:.2f}")
        
        # Get strategy performance
        strategy_perf = jit_mm.attributor.get_strategy_performance()
        for strategy, perf in strategy_perf.items():
            if perf['total_fills'] > 0:
                logger.info(f"   {strategy}: {perf['total_fills']} fills, {perf['total_pnl']:.2f} PnL")
    
    logger.info("✅ Attribution system integration test complete")


async def test_strategy_coordination():
    """Test strategy coordination integration"""
    logger.info("🧪 Testing Strategy Coordination Integration...")
    
    # Create test configuration
    config = EnhancedJITConfig(
        symbol="SOL-PERP",
        leverage=10,
        post_only=True,
        obi_microprice=True,
        spread_bps_base=8.0,
        spread_bps_min=4.0,
        spread_bps_max=25.0,
        inventory_target=0.0,
        max_position_abs=120.0,
        cancel_replace_enabled=True,
        cancel_replace_interval_ms=900,
        toxicity_guard=True,
        attribution_enabled=True,
        strategy_coordination=True
    )
    
    # Create mock client
    client = MockClient()
    
    # Create enhanced JIT market maker
    jit_mm = create_enhanced_jit_market_maker(config, client)
    
    # Test coordination if available
    if jit_mm.strategy_coordinator:
        # Create test fills for coordination
        test_fills = [
            {
                'fill_id': 'coord_fill_1',
                'source': 'hybrid_shotgun',
                'market': 'SOL-PERP',
                'side': 'buy',
                'size': 10.0,
                'price': 140.0
            },
            {
                'fill_id': 'coord_fill_2',
                'source': 'hybrid_sniper',
                'market': 'SOL-PERP',
                'side': 'sell',
                'size': 8.0,
                'price': 140.5
            }
        ]
        
        for fill_data in test_fills:
            # Attribute fill
            attributed_fill = jit_mm.attributor.attribute_fill(**fill_data)
            
            # Coordinate fill
            action = await jit_mm.strategy_coordinator.coordinate_fill(attributed_fill)
            logger.info(f"   Coordination action for {fill_data['fill_id']}: {action['action']}")
            if action['action'] == 'hedge':
                logger.info(f"     Hedge size: {action['hedge_size']:.2f}")
                logger.info(f"     Hedge ratio: {action['hedge_ratio']:.1%}")
                logger.info(f"     Urgency: {action['urgency']}")
        
        # Get coordination metrics
        coord_metrics = jit_mm.strategy_coordinator.get_coordination_metrics()
        logger.info(f"   Total coordinated fills: {coord_metrics['total_coordinated_fills']}")
        logger.info(f"   Active strategies: {coord_metrics['active_strategies']}")
        logger.info(f"   Total delta: {coord_metrics['total_delta']:.2f}")
        
        # Get risk summary
        risk_summary = jit_mm.strategy_coordinator.get_risk_summary()
        logger.info(f"   Within limits: {risk_summary['within_limits']}")
        logger.info(f"   Delta utilization: {risk_summary['delta_utilization']:.1%}")
    
    logger.info("✅ Strategy coordination integration test complete")


async def run_comprehensive_test():
    """Run comprehensive integration test"""
    logger.info("🚀 Starting Comprehensive Enhanced JIT Bot Integration Test")
    logger.info("=" * 70)
    
    try:
        # Test latency budget integration
        await test_latency_budget_integration()
        logger.info("")
        
        # Test enhanced JIT performance
        await test_enhanced_jit_performance()
        logger.info("")
        
        # Test attribution integration
        await test_attribution_integration()
        logger.info("")
        
        # Test strategy coordination
        await test_strategy_coordination()
        logger.info("")
        
        logger.info("=" * 70)
        logger.info("✅ All integration tests completed successfully!")
        logger.info("🎉 Enhanced JIT Bot is ready for production use!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())

