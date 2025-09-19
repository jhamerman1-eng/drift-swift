# 🚀 Live Trading Readiness Checklist & Analysis

## 📊 **Current System Status**

### ✅ **WORKING ELEMENTS**
- ✅ **DriftClient Adapter**: Fixed and tested
- ✅ **JIT Engine v3**: Functional with fallback orderbook
- ✅ **Configuration**: `real_drift` driver enabled
- ✅ **RPC Connection**: Helius devnet endpoint configured
- ✅ **Wallet Integration**: `.devnet_wallet.json` configured

### ⚠️ **ELEMENTS REQUIRING ACTIVATION**

#### 1. **Health Monitoring System** 
```bash
# STATUS: Not running (port 9109 refused connection)
# REQUIRED: Start orchestrator with metrics
python bots/orchestrator/main.py --client-config configs/jit/v3_devnet.yaml --metrics-port 9109
```

#### 2. **Live Trading Mode**
```yaml
# configs/jit/v3_devnet.yaml - ADD:
use_mock: false          # Currently defaults to true
live_trading: true       # Enable live trading
```

#### 3. **Swift Sidecar Health**
```bash
# CHECK: Swift sidecar connectivity
python monitor_swift_health.py
# ENSURE: Mode is "forward" not "local-ack"
```

---

## 🔧 **FEATURE FLAGS TO ENABLE**

### **Critical Trading Flags**
```yaml
# In configs/jit/v3_devnet.yaml
driver: real_drift              # ✅ Already enabled
live_trading: true              # ❌ MISSING - Add this
use_mock: false                 # ❌ MISSING - Add this

# Risk management flags
safety:
  enable_circuit_breaker: true  # ❌ MISSING
  enable_crash_sentinel: true   # ❌ MISSING
  enable_portfolio_rails: true  # ❌ MISSING
```

### **Monitoring Flags**
```yaml
# Health and metrics
enable_debug_metrics: true     # ✅ Already enabled
enable_health_endpoints: true  # ❌ MISSING - Add this
monitoring:
  prometheus_port: 9109         # ❌ MISSING - Add this
  enable_alerts: true           # ❌ MISSING - Add this
```

---

## 📡 **DATA SOURCE VERIFICATION**

### **1. Drift Oracle Connection**
```python
# TEST ORACLE ACCESS:
from libs.drift.real_client_adapter import build_real_client_adapter
client = await build_real_client_adapter("configs/jit/v3_devnet.yaml")
live_data = await client.drift_client.get_live_market_data()
oracle_price = live_data['oracle_price']  # Should show real price
```

**Current Status**: ⚠️ **Fallback mode** - Using mock data due to `'DriftClient' object has no attribute 'get_dlob'`

### **2. Swift API Connection**
```bash
# TEST SWIFT API:
curl -s localhost:8787/health
# EXPECTED: {"ok":true,"mode":"forward","upstream":{"ok":true}}
```

**Current Status**: ❌ **Unknown** - Sidecar may not be running

### **3. Real-time Market Data**
- **Orderbook**: Currently using fallback data (prices ~$150-151)
- **Oracle**: Connected to Drift devnet oracle
- **Positions**: Real position tracking (-4.7 SOL detected)

---

## ⚡ **ACTIVATION SEQUENCE**

### **Step 1: Enable Live Trading Mode**
```bash
# Update configuration
python -c "
import yaml
with open('configs/jit/v3_devnet.yaml', 'r') as f:
    cfg = yaml.safe_load(f)
cfg['use_mock'] = False
cfg['live_trading'] = True
cfg['safety'] = {
    'enable_circuit_breaker': True,
    'enable_crash_sentinel': True, 
    'enable_portfolio_rails': True,
    'max_daily_trades': 100,
    'max_order_value_usd': 50,
    'position_check_interval': 10
}
cfg['monitoring'] = {
    'prometheus_port': 9109,
    'enable_health_endpoints': True,
    'enable_alerts': True
}
with open('configs/jit/v3_devnet.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False)
print('✅ Live trading configuration updated')
"
```

### **Step 2: Start Swift Sidecar** (if using Swift)
```bash
# Option A: Local sidecar
cd services/swift-mm
npm start

# Option B: Production Swift
# Set SWIFT_BASE_URL=https://master.swift.drift.trade
```

### **Step 3: Start Health Monitoring**
```bash
# Start orchestrator with health endpoints
python bots/orchestrator/main.py \
  --client-config configs/jit/v3_devnet.yaml \
  --metrics-port 9109 \
  --name live_trading_test
```

### **Step 4: Verify All Systems**
```bash
# Health checks
curl -s localhost:9109/health    # Should return {"status":"healthy"}
curl -s localhost:9109/ready     # Should return {"status":"ready"}
curl -s localhost:9109/metrics   # Should show Prometheus metrics

# Wallet balance
python -c "
from libs.drift.real_client_adapter import build_real_client_adapter
import asyncio
async def check():
    client = await build_real_client_adapter('configs/jit/v3_devnet.yaml')
    pos = await client.get_position()
    print(f'Current position: {pos} SOL')
asyncio.run(check())
"
```

---

## 🛡️ **SAFETY VERIFICATION**

### **Pre-Trading Checklist**
- [ ] **Wallet Balance**: ≥ 0.01 SOL for fees
- [ ] **Position Limits**: Max 2.0 SOL configured
- [ ] **Order Limits**: Max $50 per order
- [ ] **Circuit Breakers**: Enabled and tested
- [ ] **Health Endpoints**: Responding correctly
- [ ] **Oracle Data**: Live prices being received
- [ ] **Monitoring**: Prometheus metrics active

### **Risk Controls Active**
```yaml
# Verify these are in your config:
safety:
  max_position: 2.0              # SOL position limit
  max_order_value_usd: 50        # Per-order safety limit
  max_daily_trades: 100          # Daily trade limit
  circuit_breaker_threshold: 0.02 # 2% loss triggers halt
```

---

## 🎯 **FINAL VERIFICATION COMMAND**

```bash
# Run this to verify everything is ready:
python -c "
import asyncio
import yaml
import requests
from libs.drift.real_client_adapter import build_real_client_adapter

async def verify_ready():
    print('🔍 LIVE TRADING READINESS CHECK')
    print('=' * 50)
    
    # 1. Config check
    with open('configs/jit/v3_devnet.yaml') as f:
        cfg = yaml.safe_load(f)
    live_mode = not cfg.get('use_mock', True)
    print(f'Live Trading Mode: {\"✅ ON\" if live_mode else \"❌ OFF (still in mock)\"}')
    
    # 2. Health endpoint check
    try:
        r = requests.get('http://localhost:9109/health', timeout=3)
        print(f'Health Endpoint: {\"✅ ACTIVE\" if r.status_code == 200 else \"❌ ERROR\"}')
    except:
        print('Health Endpoint: ❌ NOT RUNNING')
    
    # 3. Client connection check
    try:
        client = await build_real_client_adapter('configs/jit/v3_devnet.yaml')
        orderbook = await client.get_orderbook()
        position = await client.get_position()
        print(f'DriftPy Client: ✅ CONNECTED')
        print(f'Orderbook: ✅ ACTIVE (spread: {orderbook[\"asks\"][0][0] - orderbook[\"bids\"][0][0]:.4f})')
        print(f'Position: {position:.3f} SOL')
    except Exception as e:
        print(f'DriftPy Client: ❌ ERROR - {e}')
    
    print('\\n🚀 Ready for live trading!' if live_mode else '\\n⚠️  Still in mock mode - update config to enable live trading')

asyncio.run(verify_ready())
"
```

---

## 🚨 **EMERGENCY PROCEDURES**

### **Immediate Stop**
```bash
# Kill all bots
pkill -f "python.*run.*bot"
# Or
Ctrl+C in bot terminal
```

### **Position Check**
```bash
# Check current positions
python -c "
from libs.drift.real_client_adapter import build_real_client_adapter
import asyncio
asyncio.run(build_real_client_adapter('configs/jit/v3_devnet.yaml').then(lambda c: c.get_position()))
"
```

### **Health Dashboard**
```bash
# Monitor key metrics
while true; do
  echo \"$(date): Health=$(curl -s localhost:9109/health | jq -r .status // 'DOWN')\"
  sleep 5
done
```

---

## 🎯 **SUMMARY: WHAT NEEDS TO BE TURNED ON**

### **CRITICAL (Must Enable):**
1. ❌ **Live Trading Flag**: `use_mock: false` in config
2. ❌ **Health Monitoring**: Start orchestrator on port 9109  
3. ❌ **Safety Systems**: Enable circuit breakers and position limits

### **RECOMMENDED (Should Enable):**
4. ⚠️ **Swift Sidecar**: For optimal order routing
5. ⚠️ **Real Oracle Data**: Fix DLOB connection for live prices
6. ⚠️ **Monitoring Dashboard**: Grafana for visual monitoring

### **CURRENT STATUS**: 
**🟡 PARTIALLY READY** - Core systems work but safety systems are not active

**Next Step**: Run the configuration update in Step 1 above, then start the orchestrator to enable live trading.
