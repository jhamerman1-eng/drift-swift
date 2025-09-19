# 🚀 Trend Bot v3.0 - Production-Ready Scaffold

**Directional Alpha Engine for Drift Protocol**

A sophisticated trend-following trading bot that captures medium to long-horizon moves in perpetual markets using advanced technical analysis and regime-aware position sizing.

---

## 📊 **User Stories Implementation Status**

| User Story | Status | Implementation |
|------------|--------|---------------|
| **TREND-001**: MACD + Momentum Cross | ✅ **COMPLETE** | `bots/trend/main_enhanced.py` |
| **TREND-005**: Anti-Chop Filters (ATR/ADX) | ✅ **COMPLETE** | `bots/trend/filters_enhanced.py` |
| **ENCH-TREND-012**: RBC Entry Filters | ✅ **COMPLETE** | `bots/trend/entries.py` + `orchestrator/regime_classifier.py` |
| **TREND-007**: OCO Stop Emulation | ✅ **COMPLETE** | `bots/trend/exits.py` |
| **TREND-008**: PnL Attribution | ✅ **COMPLETE** | `services/attribution/store.py` |

---

## 🎯 **Core Features**

### **📈 MACD + Momentum Strategy (TREND-001)**
- **Fast/Slow EMA**: 12/26 period exponential moving averages
- **Signal Line**: 9-period EMA of MACD line
- **Momentum Filter**: 14-period price momentum confirmation
- **Signal Combination**: MACD histogram + normalized momentum

### **🛡️ Enhanced Anti-Chop Filters (TREND-005)**
- **ATR Filter**: Minimum 1.5% normalized Average True Range
- **ADX Filter**: Minimum 20.0 Average Directional Index
- **Volume Filter**: Current volume vs 20-period moving average
- **Bollinger Width**: Detects market squeezes and breakouts
- **Price Range**: Recent price movement analysis

### **🎛️ Regime-Based Sizing (ENCH-TREND-012)**
- **Superburst**: 2.0x position size in strong breakouts (ADX > 35)
- **Trending**: 1.5x position size in trending markets (ADX > 25)
- **Mean Revert**: 0.75x position size in mean-reverting conditions
- **Choppy**: 0.0x position size (no trading in choppy markets)

### **🎯 OCO Stop Emulation (TREND-007)**
- **Stop Loss**: Configurable percentage-based stops (default 1%)
- **Take Profit**: Configurable profit targets (default 2%)
- **Order Monitoring**: Real-time fill detection and cancellation
- **Reduce-Only**: All exit orders are reduce-only for safety

### **📊 PnL Attribution (TREND-008)**
- **Multi-Format Storage**: CSV, SQLite, and JSON backends
- **Feature Tagging**: Every fill tagged with strategy and regime
- **Performance Analytics**: Win rate, Sharpe ratio, drawdown tracking
- **Export Capabilities**: Parquet export for advanced analysis

---

## 🚀 **Quick Start**

### **1. Basic Setup**
```bash
# Clone and setup
git clone <your-repo>
cd drift-swift

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DRIFT_ENV=devnet
export SWIFT_API_KEY=your_api_key
export WALLET_PATH=./wallet.json
```

### **2. Development Mode**
```bash
# Run with enhanced features (dry-run mode)
export DRY_RUN=1
python bots/trend/main_enhanced.py

# Or use the original main for backward compatibility
python bots/trend/main.py
```

### **3. Production Deployment**
```bash
# Using Docker Compose (recommended)
docker-compose -f docker/docker-compose.trend.yml up -d

# Or run directly
python bots/trend/main_enhanced.py --config configs/trend/filters_enhanced.yaml
```

---

## 📁 **Project Structure**

```
drift-swift/
├── bots/trend/
│   ├── main.py                 # Original trend bot (backward compatible)
│   ├── main_enhanced.py        # Enhanced v3.0 with all features
│   ├── filters.py              # Legacy filter (stubbed)
│   ├── filters_enhanced.py     # Production anti-chop filters
│   ├── entries.py              # RBC regime-based entry logic
│   └── exits.py                # OCO stop emulation system
├── services/attribution/
│   └── store.py                # PnL attribution logging
├── configs/trend/
│   ├── filters.yaml            # Legacy configuration
│   └── filters_enhanced.yaml   # Production configuration
├── docker/
│   ├── Dockerfile.trend        # Production Docker image
│   └── docker-compose.trend.yml # Full deployment stack
└── requirements.txt            # Production dependencies
```

---

## ⚙️ **Configuration**

### **Core Strategy Parameters**
```yaml
trend:
  # MACD Configuration
  macd:
    fast: 12              # Fast EMA period
    slow: 26              # Slow EMA period
    signal: 9             # Signal line period
  
  # Position sizing
  position_scaler: 1.0    # Base position multiplier
  max_position_usd: 5000  # Maximum position size
  min_notional_usd: 250   # Minimum trade size
  
  # Risk management
  stop_loss_pct: 0.01     # 1% stop loss
  take_profit_pct: 0.02   # 2% take profit
```

### **Feature Flags**
```yaml
trend:
  use_enhanced_filters: true  # Enable anti-chop filters
  use_rbc_sizing: true        # Enable regime-based sizing
  use_oco_stops: true         # Enable OCO stop emulation
  use_attribution: true       # Enable PnL attribution
```

### **Filter Configuration**
```yaml
filters:
  atr_min: 0.015              # 1.5% minimum ATR
  adx_min: 20.0               # Minimum ADX for trend
  require_all_filters: false  # ANY vs ALL filter logic
  enabled_filters:
    - "atr"                   # Average True Range
    - "adx"                   # Average Directional Index
```

---

## 🔧 **Advanced Features**

### **Real-Time Monitoring**
- **Prometheus Metrics**: Exported on port 9112
- **Grafana Dashboards**: Pre-configured trend bot dashboard
- **Health Checks**: Comprehensive system health monitoring
- **Structured Logging**: JSON-formatted logs with correlation IDs

### **Risk Management**
- **Position Limits**: Configurable maximum position sizes
- **Drawdown Protection**: Daily loss limits and emergency stops
- **Regime Awareness**: Automatic position sizing based on market conditions
- **OCO Safety**: Automatic stop-loss and take-profit management

### **Data & Analytics**
- **Attribution Store**: Multi-format data storage (CSV, SQLite, JSON)
- **Performance Analytics**: Real-time win rate and Sharpe ratio calculation
- **Regime Performance**: Track performance by market regime
- **Export Capabilities**: Parquet export for advanced analysis

---

## 🚀 **Production Deployment**

### **Docker Deployment (Recommended)**
```bash
# Full production stack with monitoring
docker-compose -f docker/docker-compose.trend.yml --profile full up -d

# Basic trend bot only
docker-compose -f docker/docker-compose.trend.yml up -d trend-bot

# With research tools
docker-compose -f docker/docker-compose.trend.yml --profile research up -d
```

### **Environment Variables**
```bash
# Core configuration
DRIFT_ENV=devnet                    # or mainnet-beta
SWIFT_API_KEY=your_api_key
WALLET_PATH=/path/to/wallet.json

# Feature flags
USE_ENHANCED_FILTERS=true
USE_RBC_SIZING=true
USE_OCO_STOPS=true
USE_ATTRIBUTION=true

# Risk limits
MAX_POSITION_USD=5000
MAX_DAILY_LOSS_USD=1000
STOP_LOSS_PCT=0.01
TAKE_PROFIT_PCT=0.02

# Monitoring
METRICS_PORT=9112
LOG_LEVEL=INFO
```

### **Health Monitoring**
```bash
# Check metrics endpoint
curl http://localhost:9112/metrics

# Check container health
docker-compose ps

# View logs
docker-compose logs -f trend-bot
```

---

## 📊 **Monitoring & Observability**

### **Prometheus Metrics**
- `trend_orders_submitted_total`: Total orders submitted
- `trend_orders_filled_total`: Total orders filled
- `trend_skips_chop_total`: Trades skipped due to chop detection
- `trend_regime_transitions_total`: Regime changes detected
- `trend_oco_pairs_active`: Active OCO pairs
- `trend_pnl_realized_usd`: Realized PnL in USD

### **Grafana Dashboard**
- **Trading Activity**: Order flow, fill rates, signal frequency
- **Performance**: PnL curves, win rates, drawdown analysis
- **Risk Metrics**: Position sizes, leverage, exposure
- **System Health**: CPU, memory, network, error rates

### **Attribution Analytics**
```python
from services.attribution.store import AttributionStore

store = AttributionStore()

# Get performance summary
summary = store.get_performance_summary(feature="trend", days_back=30)
print(f"Total PnL: ${summary['overall']['total_pnl_usd']:.2f}")
print(f"Win Rate: {summary['overall']['avg_win_rate']:.1f}%")

# Export for analysis
store.export_to_parquet("trend_analysis.parquet", days_back=90)
```

---

## 🧪 **Testing & Validation**

### **Unit Tests**
```bash
# Run all trend bot tests
pytest tests/test_trend_*.py -v

# Test specific components
pytest tests/test_trend_filters.py::TestEnhancedAntiChopFilter -v
pytest tests/test_trend_exits.py::TestOCOManager -v
pytest tests/test_attribution.py::TestAttributionStore -v
```

### **Integration Tests**
```bash
# Test with mock drift client
pytest tests/test_trend_integration.py -v

# Backtest on historical data
python scripts/backtest_trend.py --start 2024-01-01 --end 2024-12-31
```

### **Performance Benchmarks**
```bash
# Benchmark indicator calculations
python scripts/benchmark_indicators.py

# Profile memory usage
python -m memory_profiler bots/trend/main_enhanced.py
```

---

## 🔍 **Troubleshooting**

### **Common Issues**

**1. Anti-Chop Filters Blocking All Trades**
```yaml
# Solution: Relax filter thresholds
filters:
  atr_min: 0.010        # Lower from 0.015
  adx_min: 15.0         # Lower from 20.0
  require_all_filters: false  # Ensure this is false
```

**2. OCO Orders Not Filling**
```yaml
# Solution: Adjust order parameters
oco:
  max_slippage_bps: 15.0    # Increase from 10.0
  use_post_only: false      # Disable for faster fills
```

**3. Attribution Store Errors**
```bash
# Solution: Check permissions and disk space
mkdir -p data/attribution
chmod 755 data/attribution
df -h  # Check available disk space
```

### **Debug Mode**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Enable component-specific debugging
export DEBUG_SIGNALS=true
export DEBUG_FILTERS=true
export DEBUG_REGIME=true
```

---

## 📈 **Performance Optimization**

### **Recommended Settings by Environment**

**Development:**
```yaml
trend:
  min_notional_usd: 10      # Small trades
  max_position_usd: 100     # Small positions
filters:
  atr_min: 0.005            # Relaxed filters
  adx_min: 10.0
development:
  debug_signals: true       # Full debugging
```

**Production:**
```yaml
trend:
  min_notional_usd: 250     # Meaningful trade sizes
  max_position_usd: 5000    # Production limits
filters:
  atr_min: 0.015            # Strict filters
  adx_min: 20.0
development:
  debug_signals: false      # Minimal logging
```

---

## 🤝 **Contributing**

1. **Follow the established patterns** in the enhanced components
2. **Add comprehensive tests** for new features
3. **Update configuration schemas** when adding parameters
4. **Maintain backward compatibility** with existing configurations
5. **Document new user stories** in the format established above

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔗 **Related Projects**

- **JIT Market Maker**: `bots/jit/main.py` - Microstructure edge capture
- **Hedge Bot**: `bots/hedge/main.py` - Delta and funding management
- **Orchestrator**: `orchestrator/master.py` - Multi-bot coordination
- **Swift Integration**: `libs/drift/drivers/swift.py` - Swift API connectivity

---

## 📧 **Support**

For questions, issues, or feature requests:
- **GitHub Issues**: [Create an issue](https://github.com/your-repo/issues)
- **Documentation**: See `docs/` directory for detailed guides
- **Examples**: Check `examples/` for usage patterns

---

**🎯 Trend Bot v3.0 - Capturing Alpha in Directional Markets** 

*Built for Drift Protocol • Powered by Advanced Technical Analysis • Production-Ready*



