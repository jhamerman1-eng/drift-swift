# 🎯 ExecutionRouter: Intent-Based Order Routing

## 📋 **Overview**

The ExecutionRouter implements proper maker vs taker order routing with correct flag enforcement, precision normalization, and intelligent fallback handling.

## 🏗️ **Architecture Principles**

### **Intent-Based Routing:**
```python
class ExecIntent(str, Enum):
    MAKER = "maker"   # Resting quotes (market making)
    TAKER = "taker"   # JIT responses (aggressive fills)
```

### **Routing Rules:**
- **Maker Orders** → **DriftPy Only** (post-only, no IOC)
- **Taker Orders** → **Swift First**, fallback to DriftPy (IOC, no post-only)

## 🔄 **Cancel/Replace Rules**

### **❗ CRITICAL: Cancel Where You Placed**

**"If you placed an order through Swift, you must also cancel it through Swift."**

This is because Swift is the authoritative layer managing those orders. Trying to cancel them directly on Drift may not work or may desync state.

### **Why This Separation Matters:**
- **Prevent mismatches**: If you send a cancel to Drift for an order that only exists in Swift, Drift won't recognize the ID
- **Avoid ghost orders**: If Swift thinks an order is live but you bypass it and cancel on Drift, the Swift → Drift sync may re-post it
- **Keep attribution clean**:
  - Maker cancel churn → measured in Drift IDs
  - JIT cancel churn → measured in Swift IDs

### **Implementation:**
```python
async def cancel(self, order_id: str, intent: ExecIntent):
    if intent == ExecIntent.MAKER:
        # Maker orders always go through Drift
        return await self.drift.cancel_order(order_id)
    elif intent == ExecIntent.TAKER:
        # Taker orders prefer Swift cancel
        if self.swift and self.swift_enabled:
            return await self.swift.cancel_order(order_id)
        # If no Swift available, just log (expected for some setups)
        logger.info("No Swift cancel available; skipping")
```

## 🏷️ **Flag Enforcement**

### **Maker Orders (Resting Quotes):**
```python
# Enforced automatically by router
post_only = PostOnlyParams.MUST_POST_ONLY
immediate_or_cancel = False
```

### **Taker Orders (JIT Responses):**
```python
# Enforced automatically by router  
post_only = PostOnlyParams.NONE
immediate_or_cancel = True  # Prefer IOC to avoid leftovers
```

### **Belt-and-Suspenders Protection:**
The router enforces these flags regardless of what upstream callers provide, preventing accidental order misclassification.

## 📏 **Precision & Tick Compliance**

### **Before Submit:**
```python
# Normalize to exchange requirements
price = tick_normalizer(price)
quantity = lot_normalizer(quantity)

# Validate post-only doesn't cross after normalization
if intent == MAKER and would_cross_spread(price):
    nudge_price_away_from_spread(price)
```

### **Prevent Crossing:**
If tick normalization would push a post-only price across the spread, the router either:
1. Nudges the price away by one tick
2. Rejects the order with a clear error

## 🔄 **Swift Mode Guard**

```python
# If Swift not configured, skip straight to Drift
if not self.swift_enabled:
    logger.info("Swift disabled, routing taker to Drift fallback")
    return await self._place_via_drift(params, intent=TAKER)
```

## 🔁 **Idempotency & Retries**

### **Error Classification:**
```python
class ErrorType(str, Enum):
    TRANSIENT = "transient"   # Network, timeout, rate limit → RETRY
    PERMANENT = "permanent"   # Rejected, insufficient funds → NO RETRY  
    UNKNOWN = "unknown"       # Conservative → NO RETRY
```

### **Retry Logic:**
- **Transient errors**: Exponential backoff retry (0.1s, 0.5s, 1.0s)
- **Permanent errors**: Immediate failure, no retry
- **Client-side idempotency keys**: Prevent duplicate orders

## 📊 **Metrics & Attribution**

### **Comprehensive Labeling:**
```python
metrics.inc("orders_total", {
    "intent": "maker|taker",
    "driver": "drift|swift", 
    "result": "success|fail",
    "context": "skew_update|refresh|inventory|jit_response"
})
```

### **Separate P&L Tracking:**
- **MM vs JIT attribution**: Clean separation for performance analysis
- **Churn counters**: Track cancel/replace frequency by intent
- **Latency monitoring**: Per-driver performance metrics

## 🚀 **Usage Examples**

### **Market Making Bot Integration:**
```python
from libs.execution import ExecutionRouter, ExecIntent

# Initialize router
router = ExecutionRouter(
    drift_client=drift_client,
    swift_client=swift_client,
    tick_normalizer=lambda p: round(p, 4),  # 4 decimal places
    lot_normalizer=lambda q: round(q, 6),   # 6 decimal places
    swift_enabled=True
)

# Place maker quote (resting)
result = await router.place(
    order_params={
        "price": 150.1234,
        "base_asset_amount": 1.5,
        "direction": "buy"
    },
    intent=ExecIntent.MAKER,
    context="refresh"
)

# Place taker response (JIT)
result = await router.place(
    order_params={
        "price": 150.05,
        "base_asset_amount": 0.5, 
        "direction": "sell"
    },
    intent=ExecIntent.TAKER,
    context="jit_response"
)

# Cancel/replace with intent
await router.cancel(order_id, ExecIntent.MAKER)
await router.replace(order_id, new_params, ExecIntent.TAKER)
```

### **Hedge Bot Integration:**
```python
# Hedge orders are typically aggressive (taker-like)
result = await router.place(
    order_params=hedge_params,
    intent=ExecIntent.TAKER,  # IOC preferred for hedges
    context="inventory"
)
```

## 🧪 **Testing Framework**

### **Critical Test Cases:**
```python
def test_maker_routes_to_drift_only():
    """Maker orders never call Swift"""
    
def test_taker_tries_swift_fallback_drift():
    """Taker orders: Swift first, Drift fallback"""
    
def test_flag_enforcement():
    """Verify post_only/IOC flags are enforced"""
    
def test_cancel_same_place_rule():
    """Cancel in same driver where placed"""
    
def test_precision_normalization():
    """Tick/lot rounding before submit"""
    
def test_error_classification():
    """Transient errors retry, permanent don't"""
```

## 📋 **Implementation Checklist**

- ✅ **Intent-based routing**: Maker/Taker split implemented
- ✅ **Flag enforcement**: Post-only/IOC automatically applied  
- ✅ **Cancel/replace separation**: Routes by intent
- ✅ **Precision normalization**: Tick/lot rounding
- ✅ **Error classification**: Transient vs permanent
- ✅ **Retry logic**: Exponential backoff for transients
- ✅ **Metrics tracking**: Comprehensive labeling
- ✅ **Swift mode guard**: Graceful fallback when disabled
- ✅ **Idempotency keys**: Client-side deduplication

## 🎯 **Benefits**

### **For Market Making:**
- **Clean separation**: Resting quotes vs JIT responses
- **Correct flags**: No accidental aggressive orders from MM
- **Attribution**: Clear P&L separation between strategies

### **For JIT Trading:**
- **Swift-first**: Lowest latency for time-sensitive fills
- **Robust fallback**: Drift backup when Swift unavailable
- **Proper IOC**: No unintended passive leftovers

### **For Operations:**
- **Centralized routing**: Single place to change execution logic
- **Rich metrics**: Deep visibility into order flow
- **Error handling**: Intelligent retries and classification

## 🎉 **Result: Bulletproof Order Execution**

**No more routing confusion, flag mistakes, or cancel/replace mismatches!** 

The ExecutionRouter ensures every order goes to the right place with the right flags, every time. 🚀
