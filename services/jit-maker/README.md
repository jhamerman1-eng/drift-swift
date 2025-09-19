# JIT Maker Service

Complete implementation of JIT (Just-In-Time) maker service for Drift Protocol, satisfying all user stories US-JIT-001 through US-JIT-005.

## Features Implemented

### ✅ US-JIT-001: Subscribe & De-dupe Swift + Auction streams
- `SwiftOrderSubscriber`, `AuctionSubscriber`, `SlotSubscriber` 
- De-duplication logic with `isSignedMsgOrder` filtering
- Unified event emission: `{uuid, takerAuthority, subAccountId, marketIndex, direction, baseAssetAmount, auctionParams, slot}`
- Health endpoint with subscriber status
- Metrics: `jit_swift_orders_total`, `jit_dedup_drops_total`, `jit_unified_events_total`

### ✅ US-JIT-002: Build correct atomic tx bundle via JIT
- `POST /jit/place_and_make` endpoint
- Uses `getPlaceAndMakeSignedMsgPerpOrderIxs` with proper instruction ordering
- Slot-skew guard (reject if `currentSlot - signedSlot > slotSkewMax`)
- Returns `{txSig, makerOrderId, duration}` on success
- Metrics: `jit_place_total{result,reason}`

### ✅ US-JIT-003: Priority fee & compute budget choreography  
- Accepts `precedingIxs` (base64-encoded instructions)
- Auto-composes `setComputeUnitLimit` and `setComputeUnitPrice` if omitted
- Supports `overrideCustomIxIndex` for proper instruction linking

### ✅ US-JIT-004: Safe cancel/replace with versioning
- `POST /jit/cancel_replace` endpoint with order versioning
- Tombstones per `(marketIndex, side, level)` with configurable TTL
- Client order ID versioning: `order_v1`, `order_v2`, etc.
- Metrics: `jit_cancel_replace_total{phase,result}`

### ✅ US-JIT-005: Python bridge & feature flag rollout
- Python `JITClient` in `libs/jit/client.py`
- Feature flag: `feature.jit.enabled` routes MM to JIT service
- Smoke test command: `scripts/jit_smoke_test.py`
- Graceful fallback to Swift/DriftPy when JIT disabled

## Quick Start

### 1. Environment Setup

```bash
# Required environment variables
export RPC_URL="https://api.devnet.solana.com"
export DRIFT_ENV="devnet"
export MAKER_KEYPAIR='[1,2,3,...]'  # Your keypair as JSON array
export JIT_PROXY_PROGRAM_ID="JITProxyProgramIdHere"

# Optional configuration
export MARKET_INDEXES="0,1,2"  # SOL,BTC,ETH perp markets
export SLOT_SKEW_MAX="30"      # Max slot drift
export TOMB_TTL_MS="800"       # Tombstone TTL
export PORT="8787"             # Service port
```

### 2. Install & Run

```bash
cd services/jit-maker
npm install
npm start
```

### 3. Health Check

```bash
curl http://localhost:8787/health
# Returns: {"ok": true, "subscribers": {...}, "metrics": {...}}
```

### 4. Python Integration

```python
from libs.jit.client import JITClient

# Initialize client
client = JITClient("http://localhost:8787")

# Health check
if client.health():
    print("JIT service ready")

# Smoke test
result = client.smoke_test()
print(f"Smoke test: {result}")
```

### 5. Market Making Bot Integration

```python
# In your bot configuration
config = {
    "feature": {
        "jit": {
            "enabled": True,  # Enable JIT routing
            "base_url": "http://localhost:8787",
            "timeout_seconds": 1.2
        }
    }
}

# Bot will automatically route orders through JIT when enabled
bot = CompleteSwiftMMBot(config)
await bot.initialize()  # JIT client auto-initialized if feature enabled
```

## API Endpoints

### Health & Metrics

- `GET /health` - Service health with subscriber status
- `GET /metrics` - Prometheus metrics

### JIT Operations

- `POST /jit/place_and_make` - Atomic taker/maker order placement
- `POST /jit/cancel_replace` - Versioned order cancel/replace

### Request/Response Examples

#### Place and Make
```bash
curl -X POST http://localhost:8787/jit/place_and_make \
  -H "Content-Type: application/json" \
  -d '{
    "orderMessageRaw": {
      "uuid": "...",
      "taker_authority": "...",
      "order_message": "deadbeef...",
      "order_signature": "dGVzdA=="
    },
    "signedMessage": {
      "signedMsgOrderParams": {
        "marketIndex": 0,
        "direction": {"long": true},
        "baseAssetAmount": "1000000000"
      }
    },
    "maker": {
      "side": "bid",
      "price": 200.5,
      "size": 0.01,
      "postOnly": true
    }
  }'
```

Response:
```json
{
  "txSig": "5J7Yn...",
  "makerOrderId": null,
  "duration": 245
}
```

## Monitoring

The service exposes Prometheus metrics at `/metrics`:

- `jit_swift_orders_total` - Swift orders received
- `jit_dedup_drops_total` - Duplicate orders dropped  
- `jit_unified_events_total` - Unified events emitted
- `jit_place_total{result,reason}` - Place operations
- `jit_cancel_replace_total{phase,result}` - Cancel/replace operations

## Testing

### Smoke Test
```bash
python scripts/jit_smoke_test.py --url http://localhost:8787 --verbose
```

### Manual Testing
```bash
# Health check
npm run health

# Metrics check  
npm run metrics

# Test invalid request (should return error gracefully)
curl -X POST http://localhost:8787/jit/place_and_make \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Swift Orders    │───▶│ De-duplication   │───▶│ Unified Events  │
│ Auction Events  │    │ & Filtering      │    │ (Single Stream) │
│ Slot Updates    │    └──────────────────┘    └─────────────────┘
└─────────────────┘                                       │
                                                          ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Python MM Bot   │───▶│ JIT Service      │───▶│ Drift Protocol  │
│ (via feature    │    │ /place_and_make  │    │ (Atomic Txns)   │
│  flag routing)  │    │ /cancel_replace  │    └─────────────────┘
└─────────────────┘    └──────────────────┘                       
```

## Development

### Building
```bash
npm run build  # Compile TypeScript
```

### Development Mode
```bash
npm run dev    # Watch mode with auto-reload
```

### Adding Features
1. Add new endpoints in `src/enhanced-index.ts`
2. Update metrics in `src/metrics.ts`  
3. Add corresponding Python client methods in `libs/jit/client.py`
4. Update feature flag routing in `run_swift_mm_complete.py`
5. Add tests to `scripts/jit_smoke_test.py`

## Production Deployment

1. **Environment**: Set all required environment variables
2. **Health Monitoring**: Monitor `/health` endpoint  
3. **Metrics**: Scrape `/metrics` with Prometheus
4. **Feature Flags**: Enable via `feature.jit.enabled=true`
5. **Fallback**: Service degrades gracefully to Swift/DriftPy

## Troubleshooting

### Common Issues

**Service won't start**
- Check `MAKER_KEYPAIR` and `JIT_PROXY_PROGRAM_ID` env vars
- Verify RPC URL is reachable
- Check port 8787 is available

**Health check fails**
- Verify all subscribers (swift, auction, drift, slot) are connected
- Check network connectivity to Drift protocol
- Review service logs for connection errors

**Orders fail**  
- Check slot skew (orders may be stale)
- Verify taker authority and signing authority
- Check maker order parameters (price, size, market)

**Python integration issues**
- Ensure `libs/jit/client.py` is in Python path
- Check JIT service URL in bot configuration
- Verify feature flag is enabled: `feature.jit.enabled=true`

## What is Atomic Transaction Bundling?

**Atomic Transaction Bundling** in the context of your Drift Swift system refers to the ability to combine multiple blockchain instructions into a single transaction that either succeeds completely or fails completely. This is a key feature of the JIT (Just-In-Time) maker service. Here's what it specifically means:

### Core Concept
Atomic Transaction Bundling allows you to package together:
1. **Ed25519 signature verification instruction** (to verify the taker's signed order)
2. **Place signed message instruction** (to place the taker's order)
3. **Place and make instruction** (to simultaneously place the maker's counter-order)
4. **Priority fee and compute budget instructions** (for transaction prioritization)

All these instructions execute as a single atomic unit - if any one fails, the entire transaction is rolled back.

### Technical Implementation
From the code I examined, here's how it works:

```typescript
```

## Infrastructure Ready, Needs Routing Fix

The phrase "Infrastructure ready, needs routing fix" refers to the current state where:

### ✅ Infrastructure is Ready:
1. **JIT Service is Complete**: The TypeScript service at `services/jit-maker/` is fully implemented with all required endpoints
2. **Python Bridge**: The `JITClient` in `libs/jit/client.py` provides the Python interface
3. **Configuration System**: Feature flags and YAML configs are in place
4. **Monitoring & Metrics**: Health endpoints and Prometheus metrics are implemented
5. **Testing**: Smoke tests and integration tests are available

### ⚠️ Routing Fix Needed:
The "routing fix" refers to properly enabling the **feature flag routing** in the market making bot. Currently, the system has:

1. **Feature Flag**: `feature.jit.enabled` in `configs/features/jit.yaml`
2. **Routing Logic**: Code that checks if JIT is enabled and routes orders accordingly
3. **Fallback Mechanism**: If JIT fails, it falls back to Swift/DriftPy

The routing fix involves ensuring that:

```yaml
# In configs/features/jit.yaml
feature:
  jit:
    enabled: true  # This must be set to true to enable JIT routing
    base_url: "http://localhost:8787"
    timeout_seconds: 1.2
```

And in the Python code (`run_swift_mm_complete.py`), the routing logic:

```python
# US-JIT-005: Initialize JIT client for feature flag routing
async def _initialize_jit_client(self):
    """Initialize JIT client based on feature flag configuration"""
    if not JIT_CLIENT_AVAILABLE:
        logger.warning("JIT client not available, using fallback routing")
        return
        
    jit_config = self.config.get("feature", {}).get("jit", {})
    if not jit_config.get("enabled", False):
        logger.info("JIT feature disabled, using Swift/DriftPy routing")
        return
```

## What's Needed for Full Deployment:

1. **Set Feature Flag**: Enable `feature.jit.enabled=true` in production config
2. **Start JIT Service**: Run the TypeScript service (`npm start` in `services/jit-maker/`)
3. **Configure Environment**: Set required environment variables (`RPC_URL`, `DRIFT_ENV`, `MAKER_KEYPAIR`, etc.)
4. **Monitor Health**: Ensure `/health` endpoint shows all subscribers connected
5. **Verify Routing**: Confirm orders are being routed through JIT service instead of direct Swift/DriftPy calls

The system is architecturally complete but needs the runtime configuration and service deployment to activate the atomic transaction bundling feature.



