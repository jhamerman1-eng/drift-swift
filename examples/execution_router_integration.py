#!/usr/bin/env python3
"""
ExecutionRouter Integration Example

Shows how to integrate the ExecutionRouter into existing bots
for proper maker/taker routing with flag enforcement.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock imports for demonstration
class MockDriftClient:
    """Mock Drift client"""
    async def place_perp_order(self, params: Dict[str, Any]) -> str:
        logger.info(f"📈 Drift order placed: {params}")
        return f"DRIFT_{int(asyncio.get_event_loop().time() * 1000) % 999999:06d}"
    
    async def cancel_order(self, order_id: str) -> bool:
        logger.info(f"❌ Drift order cancelled: {order_id}")
        return True
    
    async def modify_order(self, order_id: str, new_params: Dict[str, Any]) -> str:
        logger.info(f"🔄 Drift order modified: {order_id} -> {new_params}")
        return f"DRIFT_MOD_{order_id}"

class MockSwiftClient:
    """Mock Swift client"""
    async def place_signed(self, params: Dict[str, Any]) -> str:
        logger.info(f"⚡ Swift order placed: {params}")
        return f"SWIFT_{int(asyncio.get_event_loop().time() * 1000) % 999999:06d}"
    
    async def cancel_order(self, order_id: str) -> bool:
        logger.info(f"❌ Swift order cancelled: {order_id}")
        return True
    
    async def replace_order(self, order_id: str, new_params: Dict[str, Any]) -> str:
        logger.info(f"🔄 Swift order replaced: {order_id} -> {new_params}")
        return f"SWIFT_REP_{order_id}"

# Import ExecutionRouter
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from libs.execution import ExecutionRouter, ExecIntent

class EnhancedMarketMaker:
    """Market maker with ExecutionRouter integration"""
    
    def __init__(self):
        # Initialize clients
        self.drift_client = MockDriftClient()
        self.swift_client = MockSwiftClient()
        
        # Initialize ExecutionRouter with precision normalizers
        self.router = ExecutionRouter(
            drift_client=self.drift_client,
            swift_client=self.swift_client,
            tick_normalizer=lambda p: round(p, 4),  # 4 decimal places for price
            lot_normalizer=lambda q: round(q, 6),   # 6 decimal places for quantity
            swift_enabled=True,
            max_retries=3
        )
        
        # Track active orders
        self.active_orders = {}
    
    async def place_maker_quote(self, side: str, price: float, size: float) -> Optional[str]:
        """
        Place resting market making quote
        
        These are MAKER orders and will:
        - Route to Drift only (never Swift)
        - Have post_only=MUST_POST_ONLY enforced
        - Have immediate_or_cancel=False enforced
        """
        logger.info(f"🎯 Placing MAKER quote: {side} {size} @ ${price}")
        
        order_params = {
            "price": price,
            "base_asset_amount": size,
            "direction": side
        }
        
        result = await self.router.place(
            order_params=order_params,
            intent=ExecIntent.MAKER,
            context="refresh"  # Market making refresh
        )
        
        if result.success:
            self.active_orders[result.order_id] = {
                "intent": ExecIntent.MAKER,
                "side": side,
                "price": price,
                "size": size
            }
            logger.info(f"✅ Maker quote placed: {result.order_id} via {result.driver}")
            return result.order_id
        else:
            logger.error(f"❌ Maker quote failed: {result.error}")
            return None
    
    async def place_jit_response(self, side: str, price: float, size: float) -> Optional[str]:
        """
        Place JIT response to Swift taker order
        
        These are TAKER orders and will:
        - Route to Swift first, fallback to Drift
        - Have post_only=NONE enforced 
        - Have immediate_or_cancel=True enforced
        """
        logger.info(f"⚡ Placing JIT response: {side} {size} @ ${price}")
        
        order_params = {
            "price": price,
            "base_asset_amount": size,
            "direction": side
        }
        
        result = await self.router.place(
            order_params=order_params,
            intent=ExecIntent.TAKER,
            context="jit_response"  # JIT response to taker
        )
        
        if result.success:
            self.active_orders[result.order_id] = {
                "intent": ExecIntent.TAKER,
                "side": side,
                "price": price,
                "size": size
            }
            logger.info(f"✅ JIT response placed: {result.order_id} via {result.driver}")
            return result.order_id
        else:
            logger.error(f"❌ JIT response failed: {result.error}")
            return None
    
    async def update_maker_quote(self, order_id: str, new_price: float, new_size: float):
        """
        Update existing maker quote
        
        Uses replace() method which routes to correct driver based on intent
        """
        if order_id not in self.active_orders:
            logger.error(f"Order {order_id} not found in active orders")
            return
        
        order_info = self.active_orders[order_id]
        intent = order_info["intent"]
        
        logger.info(f"🔄 Updating {intent.value} order: {order_id}")
        
        new_params = {
            "price": new_price,
            "base_asset_amount": new_size,
            "direction": order_info["side"]
        }
        
        result = await self.router.replace(
            order_id=order_id,
            new_params=new_params,
            intent=intent
        )
        
        if result.success:
            # Update tracking
            order_info.update({"price": new_price, "size": new_size})
            logger.info(f"✅ Order updated: {result.order_id} via {result.driver}")
        else:
            logger.error(f"❌ Order update failed: {result.error}")
    
    async def cancel_order(self, order_id: str):
        """
        Cancel order using correct driver based on intent
        
        Critical: Cancels in the same place the order was placed!
        """
        if order_id not in self.active_orders:
            logger.error(f"Order {order_id} not found in active orders")
            return
        
        order_info = self.active_orders[order_id]
        intent = order_info["intent"]
        
        logger.info(f"❌ Cancelling {intent.value} order: {order_id}")
        
        result = await self.router.cancel(
            order_id=order_id,
            intent=intent
        )
        
        if result.success:
            del self.active_orders[order_id]
            logger.info(f"✅ Order cancelled via {result.driver}")
        else:
            logger.error(f"❌ Order cancel failed: {result.error}")
    
    async def run_market_making_demo(self):
        """Demonstrate market making with proper routing"""
        logger.info("🚀 Starting Market Making Demo with ExecutionRouter")
        logger.info("=" * 60)
        
        # 1. Place maker quotes (will route to Drift with post-only)
        logger.info("📊 Step 1: Placing maker quotes")
        bid_id = await self.place_maker_quote("buy", 149.95, 1.0)
        ask_id = await self.place_maker_quote("sell", 150.05, 1.0)
        
        await asyncio.sleep(1)
        
        # 2. Simulate JIT responses (will route to Swift first)
        logger.info("⚡ Step 2: Placing JIT responses")
        jit1_id = await self.place_jit_response("sell", 149.98, 0.5)
        jit2_id = await self.place_jit_response("buy", 150.02, 0.3)
        
        await asyncio.sleep(1)
        
        # 3. Update maker quotes (will use Drift modify)
        logger.info("🔄 Step 3: Updating maker quotes")
        if bid_id:
            await self.update_maker_quote(bid_id, 149.90, 1.2)
        if ask_id:
            await self.update_maker_quote(ask_id, 150.10, 0.8)
        
        await asyncio.sleep(1)
        
        # 4. Cancel some orders (routes by intent)
        logger.info("❌ Step 4: Cancelling orders")
        if jit1_id:
            await self.cancel_order(jit1_id)
        if ask_id:
            await self.cancel_order(ask_id)
        
        await asyncio.sleep(1)
        
        # 5. Show metrics
        logger.info("📊 Step 5: Execution metrics")
        metrics = self.router.get_metrics()
        logger.info(f"Execution stats: {metrics['execution_stats']}")
        
        logger.info("=" * 60)
        logger.info("✅ Market Making Demo completed!")

async def main():
    """Run the integration demo"""
    try:
        mm = EnhancedMarketMaker()
        await mm.run_market_making_demo()
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
