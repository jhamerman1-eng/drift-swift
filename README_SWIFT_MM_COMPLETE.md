# Complete Swift Market Making Bot

A comprehensive market making bot that integrates real order placement via Swift envelopes, Swift order reception and processing, and proper order management logic.

## 🚀 Features

### ✅ **Real Order Placement via Swift Envelopes**
- Creates properly signed Swift order envelopes
- Integrates with Drift Protocol via sidecar architecture
- Supports both limit and market orders
- Handles order cancellation through Swift envelopes

### ✅ **Swift Order Reception and Processing**
- WebSocket connection to Swift order feed
- Real-time order processing and JIT trading
- Configurable order filtering and validation
- Comprehensive error handling and logging

### ✅ **Proper Order Management Logic**
- Smart order tracking and lifecycle management
- Price-based order cancellation (stale order detection)
- Position-aware order placement
- Configurable risk management parameters

### ✅ **Advanced Market Making**
- Dynamic spread calculation based on market conditions
- Adaptive order sizing
- Real-time orderbook analysis
- Comprehensive statistics and monitoring

## 📁 File Structure

```
├── run_swift_mm_complete.py          # Main complete bot
├── start_swift_mm_bot.py             # Startup script
├── run_mm_bot_swift_sidecar_enhanced.py  # Enhanced sidecar bot
├── libs/drift/
│   ├── swift_envelope.py             # Swift envelope creation
│   ├── swift_receiver.py             # Swift order reception
│   └── swift_sidecar_driver.py       # Sidecar communication
├── services/swift-mm/                # Swift sidecar service
└── docker-compose.swift.yml          # Sidecar deployment
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Docker (for sidecar service)
- Valid Solana wallet (`.valid_wallet.json`)

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create wallet if needed
python create_test_wallet.py

# Start Swift sidecar (optional)
docker-compose -f docker-compose.swift.yml up -d
```

## 🚀 Usage

### Quick Start
```bash
# Start the complete bot
python start_swift_mm_bot.py
```

### Manual Start
```bash
# Set environment variables
export DRIFT_ENV=devnet
export SWIFT_SIDECAR_URL=http://localhost:8787
export SWIFT_WEBSOCKET_URL=wss://swift.drift.trade/ws

# Run the bot
python run_swift_mm_complete.py
```

### Enhanced Sidecar Bot
```bash
# Run the enhanced sidecar bot (without Swift order reception)
python run_mm_bot_swift_sidecar_enhanced.py
```

## ⚙️ Configuration

### Environment Variables
```bash
DRIFT_ENV=devnet                    # Drift environment
RPC_URL=https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494  # Solana RPC URL
SWIFT_SIDECAR_URL=http://localhost:8787  # Swift sidecar URL
SWIFT_WEBSOCKET_URL=wss://swift.drift.trade/ws  # Swift websocket URL
LOG_LEVEL=INFO                      # Logging level
```

### Bot Configuration
```python
config = {
    "order_size": 0.01,             # Order size in SOL
    "max_orders_per_side": 1,       # Max orders per side
    "price_tolerance": 0.01,        # Price movement tolerance
    "spread_bps": 8,                # Spread in basis points
    "wallet_file": ".valid_wallet.json"
}
```

## 📊 Architecture

### Swift Envelope Flow
```
1. Create Order Parameters
2. Generate Swift Envelope (signed)
3. Send to Swift Sidecar
4. Sidecar forwards to Drift Protocol
5. Order placed on blockchain
```

### Swift Order Reception Flow
```
1. Connect to Swift WebSocket
2. Receive order messages
3. Validate and filter orders
4. Execute JIT trades
5. Update statistics
```

### Order Management Flow
```
1. Get real-time orderbook
2. Calculate optimal prices
3. Cancel stale orders
4. Place new orders
5. Track order lifecycle
```

## 🔧 Components

### SwiftEnvelopeCreator
- Creates signed Swift order envelopes
- Handles order and cancel message creation
- Supports all Drift Protocol order types

### SwiftOrderReceiver
- WebSocket connection to Swift order feed
- Real-time order message processing
- Configurable order filtering

### SwiftOrderProcessor
- Processes incoming Swift orders
- Executes JIT trades
- Comprehensive error handling

### CompleteSwiftMMBot
- Main bot orchestrator
- Integrates all components
- Advanced order management

## 📈 Statistics

The bot provides comprehensive statistics:
- Orders placed/cancelled
- Swift orders received/processed
- JIT trades executed
- Success rates
- Active order counts

## 🚨 Error Handling

### Order Placement Errors
- Insufficient collateral detection
- Network connectivity issues
- Invalid order parameters
- Sidecar communication failures

### Swift Order Processing Errors
- WebSocket connection issues
- Invalid order messages
- JIT trade execution failures
- Signature verification errors

### Recovery Mechanisms
- Automatic reconnection
- Order retry logic
- Fallback to mock mode
- Comprehensive logging

## 🔍 Monitoring

### Logs
- Real-time order placement logs
- Swift order reception logs
- Error and warning messages
- Performance statistics

### Metrics
- Order success rates
- Latency measurements
- Error counts
- Resource usage

## 🛡️ Risk Management

### Position Limits
- Maximum position size
- Per-side order limits
- Price movement tolerance

### Order Validation
- Price and size validation
- Market type checking
- Authority verification

### Error Recovery
- Automatic order cancellation
- Connection retry logic
- Graceful degradation

## 🚀 Deployment

### Local Development
```bash
# Start sidecar
docker-compose -f docker-compose.swift.yml up -d

# Run bot
python start_swift_mm_bot.py
```

### Production
```bash
# Deploy sidecar
docker-compose -f docker-compose.swift.yml up -d --build

# Run bot with monitoring
python run_swift_mm_complete.py
```

## 📝 Examples

### Basic Market Making
```python
# The bot automatically:
# 1. Places buy/sell orders around mid price
# 2. Adjusts prices based on market conditions
# 3. Cancels stale orders
# 4. Processes Swift orders for JIT trading
```

### Custom Configuration
```python
config = {
    "order_size": 0.05,        # Larger orders
    "spread_bps": 12,          # Wider spread
    "max_orders_per_side": 2,  # More orders per side
    "price_tolerance": 0.02    # More price tolerance
}
```

## 🔧 Troubleshooting

### Common Issues
1. **Sidecar not responding**: Check Docker service
2. **Wallet not found**: Create wallet file
3. **Insufficient collateral**: Add more SOL
4. **WebSocket connection failed**: Check network

### Debug Mode
```bash
export LOG_LEVEL=DEBUG
python run_swift_mm_complete.py
```

## 📚 API Reference

### SwiftEnvelopeCreator
- `create_order_envelope(params, keypair)`: Create order envelope
- `create_cancel_envelope(order_id, authority, keypair)`: Create cancel envelope

### SwiftOrderReceiver
- `start(order_callback)`: Start receiving orders
- `stop()`: Stop receiving orders

### SwiftOrderProcessor
- `process_order(order)`: Process incoming order
- `get_stats()`: Get processing statistics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Check the logs for error messages
- Review the configuration
- Test with mock mode first
- Consult the Drift Protocol documentation



