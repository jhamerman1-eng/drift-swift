# JIT v3 Engine Blockchain Testing Plan
**Comprehensive guide for testing JIT v3 on Solana devnet**

## 🎯 **Prerequisites**

### **1. Environment Setup**
```bash
# Set devnet environment
export DRIFT_ENVIRONMENT=devnet
export DRIFT_ENV=devnet  
export SWIFT_FORWARD_BASE=https://beta.drift.trade
```

### **2. Wallet & Account Requirements**
- ✅ **Devnet wallet**: `.devnet_wallet.json` (already configured)
- ✅ **SOL balance**: Minimum 10 SOL for fees and collateral
- ✅ **Drift account**: Initialized and funded
- ✅ **Trading permissions**: Account must be enabled for trading

### **3. Dependencies Check**
```bash
# Verify all required packages
pip install -r requirements.txt
python -c "import driftpy, asyncio, yaml, prometheus_client; print('All deps OK')"
```

## 📋 **Step-by-Step Testing Protocol**

### **Phase 1: Real Client Integration** ⚠️

#### **Step 1.1: Create Real DriftPy Adapter**
Create `libs/drift/real_client_adapter.py`:

```python
"""
Real DriftPy client adapter for JIT v3 engine
Bridges JIT v3 interface with actual DriftPy client
"""

import asyncio
from typing import Dict, Any, Optional
from driftpy.drift_client import DriftClient
from driftpy.account_subscription_config import AccountSubscriptionConfig
from libs.drift.client import build_client_from_config

class RealDriftClientAdapter:
    """Adapter to make DriftPy client compatible with JIT v3 interface"""
    
    def __init__(self, drift_client: DriftClient):
        self.drift_client = drift_client
        
    async def get_orderbook(self) -> Dict[str, Any]:
        """Get real orderbook from Drift DLOB"""
        try:
            # Get SOL-PERP market (index 0)
            dlob = await self.drift_client.get_dlob()
            market_account = self.drift_client.get_perp_market_account(0)
            
            # Get L2 orderbook
            l2 = dlob.get_l2_orderbook_sync(
                market_index=0,
                market_type=MarketType.Perp(),
                depth=5  # Get top 5 levels
            )
            
            if not l2.bids or not l2.asks:
                return None
                
            return {
                "bids": [[level.price, level.size] for level in l2.bids],
                "asks": [[level.price, level.size] for level in l2.asks],
                "best_bid": l2.bids[0].price,
                "best_ask": l2.asks[0].price
            }
        except Exception as e:
            logger.error(f"Failed to get orderbook: {e}")
            return None
    
    async def get_position(self) -> float:
        """Get current SOL-PERP position"""
        try:
            position = self.drift_client.get_perp_position(0)
            if position:
                return position.base_asset_amount / 1e9  # Convert to SOL
            return 0.0
        except Exception:
            return 0.0
    
    async def quote_two_sided(self, ref_price: float, spread: float, size_mult: float, 
                             do_cr: bool, bid_size: float = None, ask_size: float = None):
        """Place real two-sided quotes via DriftPy"""
        try:
            bid_price = ref_price - spread / 2
            ask_price = ref_price + spread / 2
            
            # Use provided sizes or calculate from size_mult
            bid_amount = bid_size or (0.1 * size_mult)  # Base 0.1 SOL
            ask_amount = ask_size or (0.1 * size_mult)
            
            # Convert to base units
            bid_amount_base = int(bid_amount * 1e9)
            ask_amount_base = int(ask_amount * 1e9)
            bid_price_base = int(bid_price * 1e6)
            ask_price_base = int(ask_price * 1e6)
            
            # Cancel existing orders if do_cr
            if do_cr:
                await self.cancel_all()
            
            # Place bid order
            bid_params = OrderParams(
                order_type=OrderType.Limit(),
                market_type=MarketType.Perp(),
                direction=PositionDirection.Long(),
                market_index=0,
                base_asset_amount=bid_amount_base,
                price=bid_price_base,
                post_only=PostOnlyParams.TryPostOnly(),
                reduce_only=False
            )
            
            # Place ask order  
            ask_params = OrderParams(
                order_type=OrderType.Limit(),
                market_type=MarketType.Perp(),
                direction=PositionDirection.Short(),
                market_index=0,
                base_asset_amount=ask_amount_base,
                price=ask_price_base,
                post_only=PostOnlyParams.TryPostOnly(),
                reduce_only=False
            )
            
            # Execute orders
            await self.drift_client.place_orders([bid_params, ask_params])
            
            logger.info(f"Real orders placed: bid {bid_amount:.3f}@${bid_price:.4f}, "
                       f"ask {ask_amount:.3f}@${ask_price:.4f}")
            
        except Exception as e:
            logger.error(f"Failed to place orders: {e}")
            raise
    
    async def cancel_all(self):
        """Cancel all open orders"""
        try:
            await self.drift_client.cancel_all_orders()
        except Exception as e:
            logger.error(f"Failed to cancel orders: {e}")


async def build_real_client_adapter(config_path: str) -> RealDriftClientAdapter:
    """Build real DriftPy client adapter"""
    # Use existing DriftPy client
    drift_client = await build_client_from_config(config_path)
    return RealDriftClientAdapter(drift_client.drift_client)
```

#### **Step 1.2: Create Blockchain Test Configuration**
Create `configs/jit/v3_devnet.yaml`:

```yaml
# JIT v3 Real Blockchain Testing Configuration
driver: real_drift  # Use real DriftPy client

# Environment
environment: devnet
cluster: devnet

# Market settings
market: "SOL-PERP"
market_index: 0

# Conservative settings for initial testing
loop_secs: 2.0  # Slower loop for safety

# JIT Engine Configuration
jit:
  # Conservative sizing for testing
  base_size: 0.05  # Start with small size (0.05 SOL)
  max_position: 2.0  # Conservative position limit
  
  # Wider spreads for safety
  min_spread_bps: 5.0   # 5 bps minimum
  max_spread_bps: 100.0  # Wide max for safety
  
  # Microprice settings
  microprice:
    enabled: true
  obi_weights:
    low: 0.6      # Conservative weights initially
    normal: 0.5
    high: 0.4
  
  # Toxicity settings
  skew:
    enabled: true
    toxicity_threshold: 0.5  # Lower threshold for safety
    skew_multiplier: 2.0     # More aggressive spreading
  
  # Cancel/replace settings
  cancel_replace_v2:
    enabled: true
    min_lifetime_ms: 500   # Longer lifetime for testing
    price_move_bps: 2.0    # Larger move threshold

# Safety limits
safety:
  max_daily_trades: 3000
  max_order_value_usd: 50  # $50 max per order
  position_check_interval: 10  # Check position every 10 iterations

# Logging
log_level: INFO
enable_debug_metrics: true
```

### **Phase 2: Safety Testing** 🛡️

#### **Step 2.1: Pre-flight Checks**
Create `scripts/jit_v3_preflight.py`:

```python
#!/usr/bin/env python3
"""
JIT v3 Pre-flight Safety Checks
Verify all systems before live testing
"""

import asyncio
from libs.drift.real_client_adapter import build_real_client_adapter

async def preflight_checks():
    print("🔍 JIT v3 Pre-flight Checks")
    
    # 1. Wallet & Balance Check
    client = await build_real_client_adapter("configs/core/drift_client.yaml")
    
    # Check SOL balance
    balance = await client.get_sol_balance()
    print(f"✅ SOL Balance: {balance:.4f} SOL")
    assert balance >= 5.0, "Need at least 5 SOL for testing"
    
    # Check Drift account
    position = await client.get_position()
    print(f"✅ Current Position: {position:.4f} SOL")
    
    # 2. Market Data Check
    orderbook = await client.get_orderbook()
    assert orderbook is not None, "Failed to get orderbook"
    print(f"✅ Orderbook: bid=${orderbook['best_bid']:.4f}, ask=${orderbook['best_ask']:.4f}")
    
    # 3. Configuration Validation
    from libs.config.config_loader import load_yaml_with_env
    config = load_yaml_with_env("configs/jit/v3_devnet.yaml")
    assert config['jit']['base_size'] <= 0.1, "Base size too large for testing"
    print(f"✅ Config: base_size={config['jit']['base_size']}")
    
    # 4. Engine Component Test
    from bots.jit.engine import JITEngine
    engine = JITEngine(client, config['jit'], "SOL-PERP")
    decision = await engine.step()
    assert decision is not None, "Engine failed to produce decision"
    print(f"✅ Engine Test: ref=${decision.ref_price:.4f}, spread={decision.spread_bps:.1f}bps")
    
    print("\n🎉 All pre-flight checks passed! Ready for testing.")

if __name__ == "__main__":
    asyncio.run(preflight_checks())
```

#### **Step 2.2: Dry Run Test**
```bash
# Run pre-flight checks
python scripts/jit_v3_preflight.py

# If all checks pass, proceed to dry run
```

### **Phase 3: Live Testing** 🚀

#### **Step 3.1: Limited Live Test (5 minutes)**
```bash
# Terminal 1: Start metrics monitoring
curl -s localhost:9113/metrics | grep jit_

# Terminal 2: Run limited test
timeout 300 python -m bots.orchestrator.main \
  --client-config configs/jit/v3_devnet.yaml \
  --name jit_v3_live_test \
  --metrics-port 9113
```

#### **Step 3.2: Monitor Key Metrics**
Watch for:
- **Orders placed/cancelled**: Should see real blockchain transactions
- **Position changes**: Track actual SOL-PERP position
- **Error rates**: Should be < 5%
- **Spread consistency**: Should match configured parameters

#### **Step 3.3: Extended Testing (1 hour)**
```bash
# If 5-minute test successful, run longer test
timeout 3600 python -m bots.orchestrator.main \
  --client-config configs/jit/v3_devnet.yaml \
  --name jit_v3_extended_test \
  --metrics-port 9113
```

## 📊 **Success Criteria**

### **Technical Metrics**
- [ ] **Order Success Rate**: > 95%
- [ ] **Position Tracking**: Accurate within 0.01 SOL
- [ ] **Spread Compliance**: Within configured min/max bounds
- [ ] **Error Rate**: < 5% of iterations
- [ ] **Latency**: Quote refresh < 500ms average

### **Financial Metrics**  
- [ ] **P&L Stability**: Daily P&L within ±$10
- [ ] **Position Limits**: Never exceed 2.0 SOL position
- [ ] **Risk Controls**: No single order > $50 value

### **Operational Metrics**
- [ ] **Uptime**: > 99% during test period
- [ ] **Memory Usage**: Stable (no leaks)
- [ ] **Log Quality**: Clear error messages, actionable alerts

## ⚠️ **Safety Protocols**

### **Kill Switch Triggers**
- Position > 2.5 SOL (absolute)
- Daily loss > $25
- Error rate > 10% over 10 minutes
- Connection loss > 30 seconds

### **Manual Overrides**
```bash
# Emergency stop
pkill -f "bots.orchestrator.main"

# Cancel all orders
python -c "
import asyncio
from libs.drift.real_client_adapter import build_real_client_adapter
async def emergency_cancel():
    client = await build_real_client_adapter('configs/core/drift_client.yaml')
    await client.cancel_all()
asyncio.run(emergency_cancel())
"
```

## 🎯 **Expected Outcomes**

### **Phase 1**: Mock testing ✅ **COMPLETED**
- All components integrated successfully
- 106 mock iterations without errors
- Proper regime detection and spread management

### **Phase 2**: Real client integration 
- Real orderbook data feeding JIT engine
- Actual order placement on devnet
- Position tracking with real balances

### **Phase 3**: Production readiness
- Stable operation for extended periods
- Profitable edge over baseline mid-price quoting
- Ready for mainnet deployment with higher size limits

---

## 🚨 **CRITICAL NEXT ACTION**

**Step 1**: Create the `RealDriftClientAdapter` in `libs/drift/real_client_adapter.py`
**Step 2**: Run pre-flight checks with `python scripts/jit_v3_preflight.py`  
**Step 3**: Execute 5-minute live test on devnet

This will prove the JIT v3 engine works with real blockchain data and order execution! 🚀
