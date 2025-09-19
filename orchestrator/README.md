# Drift-Swift Bot Orchestrator

The orchestrator provides comprehensive bot lifecycle management, health monitoring, and market regime-aware decision making for the Drift-Swift trading system.

## Features

- **Bot Lifecycle Management**: Start, stop, and restart individual bots or all bots
- **Health Monitoring**: HTTP health endpoints (`/health`, `/ready`, `/status`) with detailed bot status
- **Consolidated Metrics**: Unified Prometheus metrics collection for all components
- **Market Regime Classification**: Automatic market regime detection for smarter trading decisions
- **Graceful Shutdown**: Signal handling and clean resource cleanup

## Architecture

```
orchestrator/
├── master.py              # Main orchestrator with health server and bot management
├── regime_classifier.py   # Market regime classification engine
├── __init__.py           # Package initialization
└── README.md             # This file

services/
└── metrics.py            # Consolidated metrics service

configs/regime/
└── thresholds.yaml       # Regime classification parameters
```

## Quick Start

### Running the Orchestrator

```bash
# Basic usage
python orchestrator/master.py --env testnet

# With custom ports
python orchestrator/master.py --env mainnet --metrics-port 9100 --health-port 9124

# Disable health server
python orchestrator/master.py --env testnet --no-health-server
```

### Health Endpoints

Once running, the orchestrator exposes health endpoints:

```bash
# Health check (returns 200 if healthy, 503 if not)
curl http://localhost:9124/health

# Readiness check (returns 200 if all bots running, 503 if not)
curl http://localhost:9124/ready

# Detailed status
curl http://localhost:9124/status
```

### Metrics

Prometheus metrics are available at `http://localhost:9100/metrics` and include:

- **Bot Metrics**: State, uptime, orders placed, P&L, position size
- **Orchestrator Metrics**: Total bots, running bots, error bots, operations
- **Trading Metrics**: Spreads, mid prices, orderbook imbalance
- **Market Metrics**: Price, volatility, technical indicators, regime classification

## Market Regime Classification

The orchestrator includes intelligent market regime detection:

### Supported Regimes

- **TRENDING_UP**: Strong upward momentum
- **TRENDING_DOWN**: Strong downward momentum
- **SIDEWAYS**: Range-bound market
- **HIGH_VOLATILITY**: Increased market volatility
- **LOW_VOLATILITY**: Decreased market volatility
- **BREAKOUT**: Price breaking through resistance/support
- **CONSOLIDATION**: Market in consolidation phase

### Regime-Aware Trading

Bots automatically adjust behavior based on detected regimes:

```python
from orchestrator.regime_classifier import get_regime_classifier, MarketData

# Get regime classifier
classifier = get_regime_classifier()

# Classify current market
market_data = MarketData(
    symbol="SOL-PERP",
    price=150.0,
    volume=1000000,
    timestamp=time.time(),
    rsi=65.0,
    atr=2.5,
    adx=30.0
)

regime_result = classifier.classify_regime(market_data)
print(f"Regime: {regime_result.regime.value}, Confidence: {regime_result.confidence}")
```

### Configuration

Regime thresholds are configurable in `configs/regime/thresholds.yaml`:

```yaml
thresholds:
  trend_strength_min: 0.5
  volatility_high_threshold: 0.05
  breakout_volume_multiplier: 1.5
  # ... more parameters
```

## Integration with Bots

### Trend Bot Integration

The trend bot uses regime classification for entry decisions:

```python
from bots.trend.entries import regime_classifier_entry_allowed, get_regime_adjusted_trend_params

# Check if entry is allowed based on regime
if regime_classifier_entry_allowed("SOL-PERP", price, volume, rsi=rsi, adx=adx):
    # Adjust parameters based on regime
    adjusted_params = get_regime_adjusted_trend_params(base_params, "SOL-PERP", price, volume)
    # Use adjusted parameters for trading
```

### JIT Bot Integration

The JIT bot adjusts spreads and position limits based on regime:

```python
from bots.jit.regime_integration import get_jit_regime_integration

regime_integration = get_jit_regime_integration()

# Check if should quote in current regime
should_quote, reason = regime_integration.should_quote_in_regime(
    "SOL-PERP", price, volume, atr=atr, adx=adx
)

if should_quote:
    # Get regime-adjusted spreads
    adjusted_spread = regime_integration.get_regime_adjusted_spreads(
        base_spread_bps, symbol="SOL-PERP", price=price, volume=volume
    )
    # Use adjusted spread for market making
```

## Monitoring and Alerting

### Key Metrics to Monitor

```prometheus
# Bot health
bot_state{bot_name="jit"} == 2  # RUNNING
bot_uptime_seconds{bot_name="trend"} > 3600  # Uptime > 1 hour

# Orchestrator health
orchestrator_running_bots == orchestrator_total_bots  # All bots running
orchestrator_error_bots == 0  # No error states

# Market regime
market_regime_confidence > 0.7  # High confidence classifications
```

### Alerting Rules

```yaml
groups:
  - name: drift_bots
    rules:
      - alert: BotDown
        expr: bot_state == 4  # ERROR state
        for: 5m
        labels:
          severity: critical

      - alert: OrchestratorUnhealthy
        expr: orchestrator_error_bots > 0
        for: 2m
        labels:
          severity: warning

      - alert: RegimeClassificationLowConfidence
        expr: market_regime_confidence < 0.5
        for: 10m
        labels:
          severity: info
```

## Configuration

### Environment Variables

- `DRIFT_ENV`: Environment (testnet/mainnet)
- `METRICS_PORT`: Prometheus metrics port (default: 9100)
- `HEALTH_PORT`: Health server port (default: 9124)

### Command Line Options

```bash
python orchestrator/master.py --help
```

## Development

### Adding New Regimes

1. Add new regime to `MarketRegime` enum in `regime_classifier.py`
2. Update classification logic in `_determine_primary_regime()`
3. Add regime-specific adjustments in bot integration modules
4. Update `thresholds.yaml` with new parameters
5. Add tests for new regime detection

### Extending Metrics

1. Add new metrics to `MetricsService` in `services/metrics.py`
2. Update bot/orchestrator code to record new metrics
3. Add metric to monitoring dashboards
4. Update alerting rules if needed

## Troubleshooting

### Common Issues

1. **Port conflicts**: Check if metrics/health ports are available
2. **Import errors**: Ensure all dependencies are installed
3. **Regime classification failures**: Check technical indicator data availability
4. **Bot startup failures**: Verify bot configurations and dependencies

### Logs

The orchestrator produces structured logs with the following levels:
- `INFO`: Normal operations, status updates
- `WARNING`: Non-critical issues, fallback behavior
- `ERROR`: Critical errors requiring attention

### Debugging

```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
python orchestrator/master.py --env testnet

# Test regime classification
python -c "
from orchestrator.regime_classifier import get_regime_classifier, MarketData
import time
classifier = get_regime_classifier()
data = MarketData('SOL-PERP', 150.0, 1000000, time.time())
result = classifier.classify_regime(data)
print(f'Regime: {result.regime}, Confidence: {result.confidence}')
"
```

## Future Enhancements

- **Machine Learning Regimes**: ML-based regime detection
- **Multi-timeframe Analysis**: Cross-timeframe regime confirmation
- **Custom Regime Strategies**: User-defined regime strategies
- **Historical Backtesting**: Regime-aware backtesting framework
- **Real-time Adaptation**: Dynamic parameter adjustment based on regime changes


