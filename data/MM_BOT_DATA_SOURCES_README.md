# 📊 MM Bot Data Sources & Feeds Documentation

## Overview
This document provides a comprehensive breakdown of all data sources and feeds used by the Market Making (MM) Bot in the Drift/Swift trading ecosystem.

## 📈 Data Architecture

The MM Bot uses a multi-source data architecture with the following key components:
- **Primary On-Chain Data**: DriftPy client for blockchain state
- **Real-Time Order Flow**: Swift WebSocket for incoming orders
- **Execution Optimization**: DLOB API for auction parameters
- **Order Execution**: Swift Sidecar HTTP API
- **Internal Analytics**: Price history and volatility calculations
- **Fallback Systems**: Mock data for development/testing

---

## 🔧 Data Sources Breakdown

### **Source 1: DriftPy Client (Primary On-Chain Data)**

**Purpose**: Provides foundational blockchain state and market data from Solana

**Data Types**:
- **Orderbook Data** - L2 orderbook depth via `get_l2_orderbook(market_index, depth)`
- **Oracle Price Data** - Real-time oracle prices via `get_oracle_price_data_for_perp_market(market_index)`
- **Position Data** - Current user positions and P&L via `DriftUser.get_user_account()`
- **Market State** - Slot information for staleness checks
- **Collateral Data** - Free collateral and account balances

**Implementation Details**:
```python
# L2 Orderbook Fetch
ob = client.get_l2_orderbook(market_index=0, depth=10)

# Oracle Price Data
oracle_data = client.get_oracle_price_data_for_perp_market(0)
price = convert_to_number(oracle_data.price)
```

**Configuration**:
- Located in: `libs/drift/client.py`
- Protocol abstraction: `DriftClientProtocol`
- Adapter pattern: `DriftpyClientAdapter`

---

### **Source 2: Swift WebSocket (Real-Time Order Flow)**

**Purpose**: Real-time order flow processing and JIT trading opportunities

**Data Types**:
- **Swift Order Messages** - Incoming order flow via WebSocket subscription
- **Auction Parameters** - Start/end prices and duration from Swift orders
- **Order Decoding** - Signed message decoding via DriftPy integration
- **Taker Authority** - Order originator identification
- **Market Index Mapping** - SOL-PERP (0), BTC-PERP (1), ETH-PERP (2)

**Implementation Details**:
```python
# WebSocket Connection Setup
swift_ws_client = SwiftWebSocketClient(
    keypair=keypair,
    drift_client=drift_client,
    drift_env="devnet"
)

# Message Processing
async def process_order(order_message):
    decoded = decode_signed_msg_order_params_message(message_buffer)
    # Process for JIT trading
```

**Configuration**:
- WebSocket URL: `SWIFT_WS_URL=wss://swift.drift.trade/ws`
- API Key: `SWIFT_API_KEY` for authentication
- Enabled via: `SWIFT_WS_ENABLED=1`

---

### **Source 3: DLOB API (Auction Optimization)**

**Purpose**: Optimizes order execution through auction parameters

**Data Types**:
- **Auction Parameters** - Optimal execution parameters via `fetch_auction_params()`
- **Price Discovery** - Market depth and liquidity data
- **Execution Timing** - Auction duration and price bounds
- **Market Intelligence** - Order flow analysis and edge calculation

**Implementation Details**:
```python
# Fetch Auction Parameters
auction_params = fetch_auction_params(cfg, order)
# Returns: {
#   "auction_duration": int,
#   "auction_start_price": int,
#   "auction_end_price": int
# }

# Conservative Defaults
if not auction_params:
    auction_params = get_conservative_auction_defaults(order)
```

**Configuration**:
- Base URL: `https://dlob.drift.trade`
- Timeout: 0.6 seconds
- Located in: `libs/market/auction.py`

---

### **Source 4: Swift Sidecar HTTP API (Order Execution)**

**Purpose**: Handles order placement, cancellation, and status tracking

**Data Types**:
- **Order Placement** - POST `/orders` for order submission
- **Order Cancellation** - POST `/orders/{id}/cancel` for order management
- **Order Status** - GET `/orders/status` for order tracking
- **Envelope Creation** - Signed message preparation and submission

**Implementation Details**:
```python
# Order Placement
payload = {
    "market_index": 0,
    "market_type": "perp",
    "order_type": "limit",
    "side": "buy",
    "base_asset_amount": size_int,
    "price": price_int,
    "post_only": True
}

response = await self._sidecar_post("orders", payload)
```

**Configuration**:
- Sidecar URL: `SWIFT_FORWARD_BASE=http://localhost:8080`
- Timeout: 1.2 seconds
- Retries: 3 attempts

---

### **Source 5: Internal Price History (Volatility Calculation)**

**Purpose**: Risk management and dynamic spread adjustment

**Data Types**:
- **Price History Buffer** - Last 100 prices for volatility calculation
- **Real Volatility** - Rolling volatility calculation from price changes
- **Price Tolerance** - Dynamic spread adjustment based on volatility
- **Risk Management** - Position sizing based on price volatility

**Implementation Details**:
```python
# Price History Management
self.price_history: List[float] = []
self.max_price_history = 100

# Volatility Calculation
def calculate_real_volatility(self, window: int = 10):
    returns = []
    for i in range(1, len(self.price_history)):
        ret = (self.price_history[i] - self.price_history[i-1]) / self.price_history[i-1]
        returns.append(ret)
    return np.std(returns) * np.sqrt(252)  # Annualized volatility
```

**Configuration**:
- History length: 100 prices
- Volatility window: 10 periods
- Located in: `run_swift_mm_complete.py`

---

### **Source 6: Mock Data Fallbacks (Development/Testing)**

**Purpose**: Development, testing, and fallback scenarios

**Data Types**:
- **Mock Orderbook** - Fallback when real orderbook unavailable
- **Mock Oracle Prices** - Conservative price estimates
- **Mock Position Data** - Test position scenarios
- **Mock Swift Orders** - Development order flow simulation

**Implementation Details**:
```python
# Mock Orderbook Fallback
mock_ob = {
    "bids": [[price * 0.999, 100], [price * 0.998, 150]],
    "asks": [[price * 1.001, 100], [price * 1.002, 150]]
}

# Mock Price Generation
def _generate_mock_price(self):
    base_price = 242.0  # SOL price
    # Add small random variation
    variation = (hash(str(int(time.time()))) % 201 - 100) / 10000
    return base_price * (1 + variation)
```

---

## 🔄 Data Flow Architecture

```
DriftPy Client ──────→ Orderbook + Oracle ──────→ Price Discovery
        ↓
Swift WebSocket ──────→ Order Flow ──────────────→ JIT Trading Logic
        ↓
DLOB API ──────────────→ Auction Params ──────────→ Optimal Execution
        ↓
Swift Sidecar ─────────→ Order Placement ─────────→ Live Trading
        ↓
Internal Buffer ───────→ Volatility Calc ─────────→ Risk Management
        ↓
Mock Fallbacks ────────→ Development/Testing ────→ Stable Operation
```

---

## ⚙️ Configuration Overview

### Environment Variables
```bash
# Swift Configuration
SWIFT_WS_ENABLED=1
SWIFT_WS_URL=wss://swift.drift.trade/ws
SWIFT_API_KEY=your_key
SWIFT_FORWARD_BASE=http://localhost:8080

# Environment
DRIFT_ENV=devnet

# DLOB Configuration
DLOB_BASE_URL=https://dlob.drift.trade
DLOB_TIMEOUT=0.6
```

### Configuration Files
- **Main Config**: `configs/core/drivers.yaml`
- **Environment Config**: `configs/environments.yaml`
- **Trend Bot Config**: `configs/trend/live_testing.yaml`

---

## 📊 Key Metrics & Monitoring

### Prometheus Metrics (Port 9111)
- `cancel_replace_total` - Order management operations
- `swift_orders_received_total` - Incoming order flow
- `jit_trading_opportunities` - JIT trading opportunities
- `order_placement_errors` - Error tracking

### Attribution Data
- **File**: `data/attribution/trend_fills.csv`
- **Columns**: timestamp, symbol, side, price, size, notional_usd, feature, strategy, regime
- **Purpose**: Trade attribution and P&L tracking

---

## 🚨 Error Handling & Resilience

### Circuit Breakers
- Oracle staleness detection
- WebSocket connection monitoring
- API rate limiting
- Graceful degradation to mock data

### Fallback Mechanisms
1. **Primary → DriftPy**: On-chain data
2. **Secondary → Mock**: Development/testing
3. **Tertiary → Conservative**: Safe defaults

---

## 🔧 Integration Points

### Trend Bot Integration
- **Market Data Feed**: `libs/common/marketdata.py`
- **Swift Driver**: `libs/drift/swift_driver.py`
- **OCO Manager**: `bots/trend/exits.py`

### Orchestrator Integration
- **Master Controller**: `orchestrator/master.py`
- **Environment Config**: `libs/config/environment.py`

---

## 📈 Performance Characteristics

### Latency Requirements
- **DLOB API**: < 600ms timeout
- **Swift Sidecar**: < 1200ms timeout
- **WebSocket**: Real-time (< 100ms)
- **DriftPy**: Variable (RPC dependent)

### Data Freshness
- **Oracle Prices**: < 5 seconds stale
- **Orderbook**: < 1 second stale
- **Auction Params**: < 30 seconds cache

---

## 🛠️ Development & Testing

### Test Scenarios
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end data flow
- **Load Tests**: High-frequency order scenarios
- **Failure Tests**: Network outage simulation

### Mock Data Generation
- **Deterministic**: Consistent test results
- **Realistic**: Market-like price movements
- **Configurable**: Adjustable volatility parameters

---

## 📚 Related Documentation

- **Trend Bot**: `README_TREND_V3.md`
- **Swift Integration**: `libs/drift/swift_envelope.py`
- **Configuration**: `configs/core/drivers.yaml`
- **Environment Setup**: `docker/docker-compose.swift.yml`

---

## 🔄 Update History

- **v1.0**: Initial multi-source architecture
- **v2.0**: Added DLOB auction optimization
- **v3.0**: Enhanced error handling and monitoring
- **Current**: Production-ready with comprehensive fallback systems

---

*This documentation provides the complete data architecture for the MM Bot. For implementation details, refer to the source code in the respective modules.*



