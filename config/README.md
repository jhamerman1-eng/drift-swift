# Core Configuration System

Production-grade configuration management for Drift trading bots with immutable settings, environment overlays, and comprehensive validation.

## ✨ Features

- **🔒 Immutable & Validated**: Frozen Pydantic models with comprehensive validation
- **📚 Contract Versioning**: SemVer-based configuration contracts with schema checksums
- **🌍 Environment Overlays**: Ordered precedence: defaults → environment → site → local → ENV
- **🔄 Thread-Safe Caching**: MT-safe cache with file modification time guards
- **🔐 Secrets Hardening**: File permission enforcement, SecretStr wrapper, KMS-ready
- **🏥 Health Checks**: Severity-based validation (critical vs warn) with mocked testing
- **📸 Snapshots & Provenance**: Git SHA, schema checksums, file mtimes, system info
- **🤖 Bot Profiles**: Inheritance with guardrails (JIT, Hedge, Trend strategies)
- **🛠️ Ops CLI**: Report, health, print, diff, snapshot, reload commands
- **🧪 Comprehensive Tests**: Unit tests with concurrency, mocking, error scenarios

## 📁 Structure

```
config/
├── core/                    # Core configuration system
│   ├── settings.py          # Immutable CoreSettings with contract versioning
│   ├── loader.py            # Environment overlays with precedence
│   ├── cache.py             # Thread-safe cache with mtime guards
│   ├── health.py            # Health checks with severity levels
│   ├── validator.py         # Startup validation & "who am I" report
│   ├── observability.py     # Snapshots, provenance, git tracking
│   └── diff.py              # Configuration diffing with DeepDiff
├── profiles/                # Bot-specific configurations
│   ├── base.py              # BaseProfile with shared risk limits
│   ├── jit.py               # JIT market maker profile
│   ├── hedge.py             # Hedge bot profile
│   ├── trend.py             # Trend following profile
│   └── manager.py           # Profile loading & validation
├── secrets/                 # Secure secrets management
│   ├── manager.py           # SecretManager with file permissions
│   └── exceptions.py        # Secrets-related exceptions
├── data/                    # Configuration files
│   ├── defaults/            # Base configuration
│   │   └── core.yaml        # Default core settings
│   ├── environments/        # Environment-specific overlays
│   │   ├── devnet.yaml      # Devnet overrides
│   │   ├── testnet.yaml     # Testnet overrides
│   │   ├── site.yaml        # Site-specific (optional)
│   │   └── local.yaml       # Local overrides (gitignored)
│   └── profiles/            # Bot profile configurations
│       ├── base.yaml        # Base profile settings
│       ├── jit.yaml         # JIT market maker settings
│       ├── hedge.yaml       # Hedge bot settings
│       └── trend.yaml       # Trend following settings
├── schemas/                 # Generated JSON schemas (CI-managed)
├── snapshots/               # Configuration snapshots
├── tests/                   # Comprehensive test suite
├── manager.py               # CLI tool for operations
└── env_example.txt          # Environment variables template
```

## 🚀 Quick Start

### 1. Import and Use

```python
from config.core import get_core
from config.profiles import get_bot_profile

# Get core configuration (cached, thread-safe)
core = get_core()

# Get bot-specific profile
jit_profile = get_bot_profile("jit")
hedge_profile = get_bot_profile("hedge")

# Check environment
if core.is_production():
    print("🚨 Running in PRODUCTION")
else:
    print("🧪 Running in DEVELOPMENT")

# Use configuration
rpc_url = core.rpc.primary_url
max_position = jit_profile.risk_limits.max_position_usd
```

### 2. Environment Setup

```bash
# Copy environment template
cp config/env_example.txt .env

# Configure your settings
export NETWORK=devnet
export KEYPAIR_PATH=/path/to/keypair.json
export LOG_LEVEL=DEBUG
```

### 3. CLI Operations

```bash
# Show comprehensive report
python -m config.manager report

# Run health checks
python -m config.manager health

# Print configuration
python -m config.manager print --format json

# Create snapshot
python -m config.manager snapshot

# Compare configurations
python -m config.manager diff --from old.json --to new.json

# Validate everything
python -m config.manager validate
```

## 🏗️ Configuration Precedence

Settings are loaded with the following precedence (highest wins):

1. **Environment Variables** (highest precedence)
2. **local.yaml** (gitignored local overrides)
3. **site.yaml** (site-specific settings)
4. **{NETWORK}.yaml** (network environment: devnet, testnet, mainnet-beta)
5. **defaults/core.yaml** (base defaults)

### Environment Variable Mapping

```bash
# Simple values
LOG_LEVEL=DEBUG                    → logging.level = "DEBUG"
RPC_TIMEOUT_SECONDS=30            → rpc.timeout_seconds = 30

# Nested configuration
RPC__PRIMARY_URL=https://...      → rpc.primary_url = "https://..."
SWIFT__ENABLED__BOOL=false        → swift.enabled = false

# Lists
DEFAULT_MARKETS__PRIMARY_MARKETS__LIST=SOL-PERP,ETH-PERP
→ default_markets.primary_markets = ["SOL-PERP", "ETH-PERP"]

# Type casting with suffixes
SOME_FLAG__BOOL=true              → some_flag = true (boolean)
SOME_NUMBER__INT=42               → some_number = 42 (integer)
SOME_DATA__JSON={"x":1}           → some_data = {"x": 1} (parsed JSON)
```

## 🤖 Bot Profiles

### Profile Hierarchy

```python
BaseProfile                    # Shared risk limits, order caps
├── JITProfile                # Market making specific
├── HedgeProfile              # Cross-venue hedging  
└── TrendProfile              # Momentum strategies
```

### Profile Features

- **Risk Limits**: Position size, leverage, drawdown limits
- **Order Caps**: Rate limits, size constraints, latency budgets  
- **Strategy Config**: Mode selection, parameters, feature flags
- **Validation**: Guardrails prevent invalid configurations
- **Inheritance**: Shared base settings with bot-specific extensions

### Example Usage

```python
from config.profiles import get_bot_profile

# Load JIT profile
jit = get_bot_profile("jit")

# Check if should hedge
if jit.jit_mode == "shotgun":
    clip_size = jit.get_quote_size(base_size=100, market_conditions={})

# Validate risk limits
if jit.check_position_limits(current_position=50000, new_order=10000):
    print("✅ Order within limits")

# Get effective spread
spread = jit.get_effective_spread(market_volatility=1.2, inventory_ratio=0.1)
```

## 🔐 Secrets Management

### Features

- **File Permission Enforcement**: Requires 0600 (owner read/write only)
- **SecretStr Wrapper**: Prevents accidental logging of sensitive data
- **Multiple Sources**: File paths, environment variables, default locations
- **Validation**: Keypair format, length, base58 decoding checks

### Usage

```python
from config.secrets import load_keypair, SecretStr

# Load keypair with validation
keypair_info = load_keypair()
print(f"Public key: {keypair_info.public_key}")
print(f"Source: {keypair_info.source}")

# Secure string handling
secret = SecretStr("sensitive_data")
print(secret)  # Prints: **********
actual_value = secret.get_secret_value()  # Get real value when needed
```

## 🏥 Health Checks

### Severity Levels

- **Critical**: Must pass for trading (RPC, wallet, network)
- **Warning**: Should pass but not blocking (Swift sidecar, disk space)

### Built-in Checks

- **RPC Endpoint**: Solana RPC health and connectivity
- **Swift Sidecar**: Optional fast execution service
- **Wallet File**: Keypair validation and permissions
- **Network**: Basic connectivity check
- **Disk Space**: Available storage monitoring

### Usage

```python
from config.core import run_health_checks, format_health_report

# Run all health checks
results = await run_health_checks(
    rpc_url="https://api.devnet.solana.com",
    swift_url="http://localhost:8080"
)

# Format report
report = format_health_report(results)
print(report)

# Check if should proceed
if results["should_proceed"]:
    print("✅ All critical checks passed")
else:
    print("❌ Critical failures - do not trade")
```

## 📸 Snapshots & Observability

### Features

- **Git Provenance**: SHA, branch, dirty status, ahead/behind
- **Schema Tracking**: Contract version, schema checksums
- **File Monitoring**: Modification times of all config files
- **System Info**: Hostname, platform, Python version, process info
- **Environment Hash**: Hash of relevant env var names (not values)

### Usage

```python
from config.core import write_snapshot, get_provenance

# Create configuration snapshot
snapshot_path = write_snapshot(core)
print(f"Snapshot saved: {snapshot_path}")

# Get current provenance
provenance = get_provenance()
print(f"Git: {provenance['git']['branch']} @ {provenance['git']['sha'][:8]}")
```

## 🔄 Cache Management

### Features

- **Thread Safety**: Uses RLock for concurrent access
- **Generation Counter**: Tracks reload cycles for change detection
- **File Monitoring**: Automatic reload when files change
- **Force Reload**: Manual reload regardless of file changes

### Usage

```python
from config.core import get_core, reload_if_changed, get_generation

# Get cached configuration
core = get_core()

# Check current generation
gen = get_generation()

# Reload if files changed
was_reloaded = reload_if_changed()
if was_reloaded:
    print(f"Config reloaded, new generation: {get_generation()}")
```

## 🛠️ CLI Tool

The configuration manager provides a comprehensive CLI for operational tasks:

```bash
# Comprehensive system report
python -m config.manager report --bot-type jit

# Health checks with wallet validation
python -m config.manager health --wallet-path ~/.config/solana/id.json

# Configuration printing
python -m config.manager print --format json --bot-type hedge

# Configuration comparison
python -m config.manager diff --from snapshot1.json --to snapshot2.json --save

# Snapshot creation
python -m config.manager snapshot --output-dir ./backups

# Live reload
python -m config.manager reload

# Comprehensive validation
python -m config.manager validate --wallet-path ./keypair.json
```

### Exit Codes

- **0**: Success
- **1**: Configuration/validation errors
- **130**: Interrupted by user

## 🧪 Testing

The system includes comprehensive tests covering:

- **Core Settings**: Contract versioning, validation, immutability
- **Loader**: Environment overlays, type casting, precedence
- **Cache**: Thread safety, mtime guards, reload behavior
- **Secrets**: File permissions, SecretStr wrapper, validation
- **Health**: Severity levels, mocked responses, error handling
- **Profiles**: Inheritance, guardrails, validation

### Running Tests

```bash
# Run all tests
cd config
python -m pytest tests/ -v

# Run specific test module
python -m pytest tests/test_core_settings.py -v

# Run with coverage
python -m pytest tests/ --cov=config --cov-report=html
```

## 🔧 Advanced Configuration

### Contract Versioning

The configuration system uses semantic versioning for configuration contracts:

```yaml
contract_version: "1.2.0"  # Major.Minor.Patch
```

- **Major**: Breaking changes requiring code updates
- **Minor**: Backward-compatible additions
- **Patch**: Bug fixes and clarifications

### Schema Checksums

Every configuration includes a schema checksum for validation:

```python
core = get_core()
checksum = core.get_schema_checksum()  # 16-char SHA256 hash
```

### Kill Switches

Emergency controls for risk management:

```yaml
kill_switches:
  global_trading: false         # Stop all trading
  new_positions: false          # Prevent new position opens
  position_increases: false     # Prevent position size increases
  high_frequency_trading: false # Disable HFT strategies
```

### Feature Flags

Runtime feature toggles:

```yaml
feature_flags:
  enhanced_routing: true
  cross_venue_hedging: true
  advanced_position_tracking: true
  confidence_pricing: true
  jit_optimization: true
```

## 🚨 Production Checklist

Before deploying to production:

- [ ] **Environment Variables**: All required vars set securely
- [ ] **Wallet Permissions**: Keypair files have 0600 permissions
- [ ] **Network Configuration**: Correct RPC endpoints for mainnet
- [ ] **Kill Switches**: All switches set to `false`
- [ ] **Health Checks**: All critical checks passing
- [ ] **Contract Version**: Correct version for deployment
- [ ] **Profile Validation**: All bot profiles validate successfully
- [ ] **Snapshot Created**: Baseline snapshot for comparison
- [ ] **Monitoring**: Metrics and logging properly configured

## 📊 Monitoring

The system provides extensive observability:

- **Configuration Changes**: Automatic snapshots on reload
- **Health Status**: Continuous monitoring of critical systems
- **Performance**: Latency tracking for configuration operations
- **Errors**: Comprehensive error reporting and recovery
- **Audit Trail**: Complete history of configuration changes

## 🤝 Contributing

When modifying the configuration system:

1. **Schema Changes**: Update contract version appropriately
2. **Tests**: Add tests for new functionality
3. **Documentation**: Update this README and code comments
4. **Validation**: Ensure all existing configs still validate
5. **Snapshots**: Test snapshot/restore functionality

## 📚 Architecture

The configuration system follows these principles:

- **Immutability**: All settings are frozen after creation
- **Validation**: Comprehensive validation at load time
- **Separation of Concerns**: Core vs. bot-specific configuration
- **Fail-Fast**: Invalid configurations prevent startup
- **Observability**: Full traceability of configuration sources
- **Security**: Secure handling of sensitive information
- **Performance**: Cached with intelligent reloading
- **Operational**: Rich CLI tooling for production use

This system provides the foundation for reliable, secure, and observable configuration management across all Drift trading bots.
