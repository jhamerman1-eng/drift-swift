# ⚙️ CONFIGS - Configuration Management

This directory contains all configuration files, templates, and management systems for the Drift Swift trading platform. It provides centralized, environment-aware configuration management with validation, hot-reloading, and feature flag support.

## 📁 Directory Structure

```
configs/
├── core/                           # Core System Configuration
│   ├── drift_client.yaml          # Drift client settings
│   ├── drift_client_beta.yaml     # Beta environment client config
│   └── environments.yaml          # ⭐ Centralized environment config
├── bots/                          # Bot-Specific Configurations
│   ├── jit_template.yaml          # JIT bot configuration template
│   ├── hedge_template.yaml        # Hedge bot configuration template
│   └── trend_template.yaml        # Trend bot configuration template
├── jitter/                        # Advanced Jitter Configurations
│   └── feature_flags.yaml         # ⭐ Feature flag management
├── hedge/                         # Hedging Configurations
│   └── routing.yaml               # ⭐ Hedge routing (Drift internal)
├── trend/                         # Trend Following Configurations
│   ├── filters.yaml               # Signal filtering parameters
│   └── filters_enhanced.yaml      # Enhanced filtering parameters
├── testing/                       # Testing Configurations
│   ├── 90_day_combined_system_test.yaml # Long-term simulation config
│   └── 30_day_abc_hedge_test_config.yaml # A/B/C test configuration
└── live_trading_config.yaml       # ⭐ Live trading configuration
```

## 🏗️ Configuration Categories

### 1. Core System Configuration (`core/`)

**Purpose**: Fundamental system settings and environment management.

#### Key Files:

**`environments.yaml`** - Centralized Environment Configuration
```yaml
# Multi-environment support
environments:
  local:
    drift_env: "devnet"
    rpc_url: "https://api.devnet.solana.com"
    swift_config:
      base_url: "http://localhost:8787"
      use_local_sidecar: true
    
  devnet:
    drift_env: "devnet"  
    rpc_url: "https://devnet.helius-rpc.com/?api-key=${HELIUS_API_KEY}"
    swift_config:
      base_url: "https://master.swift.drift.trade"
      use_local_sidecar: false
      
  production:
    drift_env: "mainnet"
    rpc_url: "https://your-production-rpc.com"
    swift_config:
      base_url: "https://master.swift.drift.trade"
    monitoring:
      enabled: true
      prometheus_port: 9090
      grafana_port: 3000
```

**`drift_client.yaml`** - Drift Client Configuration
```yaml
# Drift Protocol client settings
cluster: "devnet"
driver: "driftpy"
rpc:
  http_url: "${RPC_URL}"
  ws_url: "${WS_URL}"
wallets:
  maker_keypair_path: "${KEYPAIR_PATH}"
market_index: 0  # SOL-PERP
connection:
  timeout: 30
  retry_attempts: 3
  retry_delay: 1.0
```

### 2. Bot-Specific Configurations (`bots/`)

**Purpose**: Individual bot configuration templates and settings.

#### Templates:

**`jit_template.yaml`** - JIT Bot Configuration
```yaml
# JIT Market Making Bot Configuration
name: "jit"
sub_account: 0
target_leverage: 10.0
margin_mode: "cross"

# Core JIT parameters
symbol: "SOL-PERP"
post_only: true
obi_microprice: true

# Spread management
spread_bps:
  base: 8.0
  min: 4.0
  max: 20.0

# Position management
inventory_target: 0.0
max_position_abs: 120.0

# Performance settings
cancel_replace:
  enabled: true
  interval_ms: 800
  
toxicity_guard: true
latency_budget_enabled: true

# Regime-aware settings
regime_spreads:
  CALM: 6.0
  VOLATILE: 12.0
  TOXIC: 20.0
```

**`hedge_template.yaml`** - Hedge Bot Configuration
```yaml
# Hedge Bot Configuration
name: "hedge"
sub_account: 1
hedge_enabled: true

# Quality-first hedging
quality_thresholds:
  default_threshold: 0.65
  min_hedge_size: 1.5
  sniper_threshold: 0.75
  shotgun_threshold: 0.60

# Execution settings
execution:
  venue: "drift_internal"  # Use Drift Protocol internal hedging
  max_response_time_ms: 100
  cost_optimization: true

# Risk management
risk_limits:
  max_hedge_ratio: 0.80
  daily_hedge_limit: 5000.0  # USD
  
# CEX integration (disabled in favor of Drift internal)
cex_routing:
  enabled: false  # Migrated to Drift internal execution
```

**`trend_template.yaml`** - Trend Bot Configuration
```yaml
# Trend Following Bot Configuration
name: "trend"
sub_account: 2
target_leverage: 4.0

# Markets to trade
markets:
  - "SOL-PERP"
  - "BTC-PERP"
  - "ETH-PERP"

# Technical indicators
indicators:
  macd:
    enabled: true
    fast_period: 12
    slow_period: 26
    signal_period: 9
    
  rsi:
    enabled: true
    period: 14
    overbought: 70.0
    oversold: 30.0
    
  bollinger_bands:
    enabled: true
    period: 20
    std_dev: 2.0

# Timeframe settings
timeframes:
  primary: "15m"
  confirmation: ["5m", "1h"]

# Position management
position_sizing:
  method: "volatility"  # ATR-based sizing
  max_position_usd: 75000.0
  volatility_lookback: 20

# Risk management
risk:
  stop_loss_pct: 3.0
  trailing_stop_pct: 1.5
  take_profit_multiplier: 2.0
```

### 3. Feature Flag Management (`jitter/`)

**Purpose**: Advanced feature control and gradual rollout management.

**`feature_flags.yaml`** - Comprehensive Feature Flag System
```yaml
# Core system features
core_features:
  unified_capital_allocation: true
  real_time_coordination: true
  compute_budget_optimization: true
  
# Triple bot features
triple_bot_features:
  enhanced_jit: true
  quality_first_hedge: true
  trend_following: true
  cross_bot_coordination: true

# Advanced jitter features (start disabled for safety)
advanced_jitter_features:
  toggle_manager: false
  crash_sentinel: false
  hedge_coupling: false
  quality_filters: false
  realtime_optimization: false
  comprehensive_testing: false

# Performance features
performance_features:
  latency_optimization: true
  memory_optimization: true
  connection_pooling: true
  async_processing: true

# Safety features
safety_features:
  circuit_breakers: true
  position_limits: true
  error_recovery: true
  health_monitoring: true

# Experimental features (disabled by default)
experimental_features:
  ai_regime_detection: false
  quantum_pricing: false
  cross_chain_arbitrage: false
```

### 4. Hedge Configuration (`hedge/`)

**Purpose**: Hedging strategy and routing configuration.

**`routing.yaml`** - Hedge Routing Configuration
```yaml
# Hedge Routing Configuration (Updated for Drift Internal)
hedge_routing:
  default_venue: "drift_internal"
  
  # Disabled external CEX routing
  external_routes:
    enabled: false
    # CEX:BINANCE: disabled (migrated to Drift internal)
    # CEX:OKX: disabled (migrated to Drift internal)
    
  # Enable Drift Protocol internal hedging
  internal_routes:
    enabled: true
    DRIFT:INTERNAL:
      enabled: true
      sub_account: "hedge_account"
      priority: 1
      cost_tier: "optimized"

# Sub-account configuration
sub_accounts:
  hedge_account:
    id: 1
    purpose: "internal_hedging"
    max_leverage: 5.0
    risk_limit_usd: 10000.0

# Advanced hedging features
advanced_features:
  quality_first_hedging: true
  cost_optimization: true
  real_time_attribution: true
  
# Risk parameters
risk_parameters:
  max_hedge_size_usd: 5000.0
  quality_threshold: 0.65
  max_response_time_ms: 100
  
# Advanced settings
advanced_settings:
  hedge_coupling: true
  attribution_tracking: true
  performance_monitoring: true
```

### 5. Trend Configuration (`trend/`)

**Purpose**: Trend following strategy parameters and filtering.

**`filters.yaml`** - Signal Filtering Configuration
```yaml
# Trend Signal Filtering Configuration
signal_filters:
  
  # MACD filter settings
  macd:
    enabled: true
    signal_threshold: 0.05
    histogram_threshold: 0.02
    divergence_detection: true
    
  # RSI filter settings  
  rsi:
    enabled: true
    overbought_threshold: 70.0
    oversold_threshold: 30.0
    divergence_lookback: 5
    
  # Volume filter
  volume:
    enabled: true
    min_volume_ratio: 1.2  # vs. average volume
    volume_confirmation: true
    
  # Volatility filter
  volatility:
    enabled: true
    min_atr_multiple: 1.5
    max_atr_multiple: 4.0
    regime_adjustment: true

# Multi-timeframe confirmation
timeframe_confirmation:
  enabled: true
  primary_timeframe: "15m"
  confirmation_timeframes: ["5m", "1h"]
  min_confirmations: 2

# Regime-based adjustments
regime_adjustments:
  CALM:
    signal_threshold_multiplier: 0.8
    position_size_multiplier: 1.2
  VOLATILE:
    signal_threshold_multiplier: 1.2
    position_size_multiplier: 0.8
  TRENDING:
    signal_threshold_multiplier: 0.6
    position_size_multiplier: 1.5
```

### 6. Testing Configurations (`testing/`)

**Purpose**: Long-term testing and simulation configurations.

**`90_day_combined_system_test.yaml`** - Comprehensive System Test
```yaml
# 90-Day Combined System Test Configuration
test_configuration:
  name: "90-Day Combined System Test: JIT + Quality First Hedger + Trend"
  mode: "mock"
  duration_days: 90
  start_date: "2025-09-18"
  
  # Capital allocation for testing
  capital_allocation:
    enabled: true
    total_portfolio_usd: 20000
    target_utilization: 0.85
    dynamic_allocation: true
    regime_aware: true
    
  # Individual bot configurations
  jit_system:
    enabled: true
    allocation_weight: 0.40
    spread_bps_base: 8.0
    max_position_abs: 80.0
    
  hedge_system:
    enabled: true
    allocation_weight: 0.35
    quality_threshold: 0.65
    hedge_ratio: 0.75
    
  trend_system:
    enabled: true
    allocation_weight: 0.25
    max_position_usd: 5000.0
    leverage: 4.0

# Performance tracking
performance_tracking:
  enabled: true
  metrics:
    - total_pnl
    - win_rate
    - sharpe_ratio
    - max_drawdown
    - cross_bot_coordination_efficiency
  
# Safety settings
safety_settings:
  max_daily_loss: 1000.0
  max_portfolio_drawdown: 0.20
  circuit_breaker_enabled: true
```

### 7. Live Trading Configuration

**`live_trading_config.yaml`** - Production Trading Settings
```yaml
# Live Trading Configuration (Real Money)
cluster: "devnet"  # Use devnet for initial live testing
driver: "driftpy"

# Network configuration
rpc_url: "https://devnet.helius-rpc.com/?api-key=${HELIUS_API_KEY}"
swift:
  http_url: "https://master.swift.drift.trade"
  ws_url: "wss://master.swift.drift.trade/ws"

# Wallet configuration
wallets:
  maker_keypair_path: ".valid_wallet.json"
  jito_keypair_path: ".swift_test_wallet.json"

# Trading parameters
market_index: 0  # SOL-PERP
symbol: "SOL-PERP"
leverage: 10
post_only: true

# Risk management (conservative for live trading)
spread_bps:
  base: 8.0
  min: 4.0
  max: 25.0

inventory_target: 0.0
max_position_abs: 120.0

# Safety warnings
warnings:
  real_money_at_risk: true
  ensure_sufficient_balance: true
  understand_risks: true
```

## 🔧 Configuration Usage Patterns

### Environment-Aware Configuration Loading
```python
from libs.config.environment import get_environment_config

# Load environment-specific configuration
env_config = get_environment_config()
rpc_url = env_config.get_rpc_url()
swift_config = env_config.get_swift_config()

# Use in bot initialization
bot = MyBot(
    rpc_url=rpc_url,
    swift_url=swift_config["base_url"]
)
```

### Feature Flag Usage
```python
from libs.jitter.feature_flags import get_feature_flags

# Check feature flags before enabling functionality
flags = get_feature_flags()

if flags.is_enabled("enhanced_jit"):
    jit_bot = EnhancedJITBot()
else:
    jit_bot = StandardJITBot()

if flags.is_enabled("quality_first_hedge"):
    hedge_bot = QualityFirstHedger()
```

### Dynamic Configuration Updates
```python
# Hot-reload configuration changes
config_manager = CentralizedConfigManager()

# Watch for configuration changes
@config_manager.on_change("feature_flags.yaml")
def update_feature_flags(new_config):
    # Update runtime feature flags
    feature_flags.update(new_config)
    logger.info("Feature flags updated")
```

## 📊 Configuration Validation

### Schema Validation
```yaml
# Example configuration schema
jit_bot_schema:
  type: "object"
  required: ["symbol", "leverage", "spread_bps"]
  properties:
    symbol:
      type: "string"
      enum: ["SOL-PERP", "BTC-PERP", "ETH-PERP"]
    leverage:
      type: "number"
      minimum: 1
      maximum: 20
    spread_bps:
      type: "object"
      required: ["base", "min", "max"]
```

### Runtime Validation
```python
def validate_config(config: dict) -> bool:
    """Validate configuration before use"""
    
    # Check required fields
    required_fields = ["symbol", "leverage", "max_position_abs"]
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate ranges
    if not 1 <= config["leverage"] <= 20:
        raise ValueError("Leverage must be between 1 and 20")
        
    # Validate spread configuration
    spread = config.get("spread_bps", {})
    if spread.get("min", 0) >= spread.get("max", 100):
        raise ValueError("Min spread must be less than max spread")
    
    return True
```

## 🔐 Security and Secrets Management

### Environment Variable Usage
```yaml
# Use environment variables for sensitive data
rpc_url: "${RPC_URL}"
api_key: "${API_KEY}"
keypair_path: "${KEYPAIR_PATH}"
```

### Secrets Management
```python
import os
from pathlib import Path

# Secure wallet loading
def load_wallet_securely():
    keypair_path = os.getenv("KEYPAIR_PATH")
    if not keypair_path or not Path(keypair_path).exists():
        raise ValueError("Invalid or missing keypair path")
    
    # Load with proper permissions check
    if oct(os.stat(keypair_path).st_mode)[-3:] != "600":
        logger.warning("Keypair file permissions should be 600")
    
    return load_keypair(keypair_path)
```

## 🧪 Configuration Testing

### Test Configurations
```bash
# Validate all configurations
python scripts/validate_configs.py

# Test specific configuration
python -c "
from libs.config.config_loader import load_config
config = load_config('configs/bots/jit_template.yaml')
print('✅ Configuration valid')
"

# Test environment switching
export DRIFT_ENVIRONMENT=devnet
python -c "
from libs.config.environment import get_environment_config
env = get_environment_config()
print(f'Environment: {env.get_environment()}')
print(f'RPC URL: {env.get_rpc_url()}')
"
```

### Configuration Linting
```bash
# YAML syntax validation
yamllint configs/

# Schema validation
python scripts/validate_schemas.py configs/
```

## 📈 Configuration Monitoring

### Configuration Change Tracking
```python
# Track configuration changes
config_audit = {
    "timestamp": datetime.now(),
    "file": "feature_flags.yaml", 
    "user": os.getenv("USER"),
    "changes": {
        "enhanced_jit": {"old": False, "new": True},
        "quality_first_hedge": {"old": False, "new": True}
    }
}
```

### Performance Impact Monitoring
```python
# Monitor performance impact of configuration changes
@monitor_performance
def apply_config_change(config_file: str, changes: dict):
    # Apply configuration changes
    # Monitor performance before/after
    pass
```

## 🚀 Best Practices

### Configuration Management
1. **Use environment variables** for sensitive data
2. **Validate configurations** before deployment
3. **Version control** all configuration changes
4. **Test configurations** in isolated environments
5. **Document** all configuration options

### Feature Flag Management
1. **Start with features disabled** for safety
2. **Gradual rollout** of new features
3. **Monitor performance** after enabling features
4. **Quick rollback** capability for issues
5. **Clean up** unused feature flags

### Security Practices
1. **Never commit secrets** to version control
2. **Use proper file permissions** for sensitive files
3. **Rotate keys** regularly
4. **Audit configuration access**
5. **Encrypt sensitive configuration data**

---

## 📞 Configuration Support

### Troubleshooting
```bash
# Common configuration issues
python scripts/diagnose_config.py

# Environment verification
python scripts/verify_environment.py

# Feature flag status
python scripts/check_feature_flags.py
```

### Configuration Templates
Each configuration file includes:
- **Comprehensive comments** explaining each option
- **Example values** for different scenarios
- **Validation rules** and constraints
- **Performance implications** of different settings

For detailed configuration options and advanced usage, refer to the specific configuration files and their embedded documentation.
