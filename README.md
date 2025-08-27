# Drift Bots v3.0 (All Three Bots, Production-Ready Scaffold)

This release implements a **production-ready scaffold** for the **Orchestrator**, **JIT Maker**, **Hedge**, and **Trend** bots with health checks, metrics, and risk rails.

- **Orchestrator**: CLI + YAML config merge, Prometheus `/metrics`, `/health` and `/ready`
- **JIT Bot**: OBI v1 microprice + spoof filter, toxicity-based skew, Crash Sentinel v2, Cancel/Replace v2 (flagged), Portfolio rails
- **Hedge Bot**: Portfolio delta aggregator, urgency scoring, IOC vs passive routing
- **Trend Bot**: MACD/momentum + ATR/ADX (anti-chop), RBC filters, execution with partial fill handling
- **Client**: Swift sidecar/forwarding driver (optional) **or** Local ACK driver for offline smoke tests

> ✅ Safe-by-default: No keys embedded. Configure via `.env` and `configs/core/drift_client.yaml`.

## 🚀 Quickstart

### Option 1: Ultra-Quick Beta Launch (Recommended)

```bash
# 🚀 For Windows users:
start_beta_bots.bat --dry-run    # Preview first (safe!)
start_beta_bots.bat --mock       # Test with mock client
start_beta_bots.bat --real       # LIVE trading (use with caution!)

# 🚀 For Linux/Mac users:
./start_beta_bots.sh --dry-run   # Preview first (safe!)
./start_beta_bots.sh --mock      # Test with mock client
./start_beta_bots.sh --real      # LIVE trading (use with caution!)
```

### Option 2: Manual Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure for beta.drift.trade
cp beta_environment_config.yaml beta_environment_config.yaml.backup
# Edit beta_environment_config.yaml with your wallet path and settings

# 3. Launch with safety checks
python launch_beta_bots.py --dry-run    # Preview configuration
python launch_beta_bots.py              # Launch bots (mock mode by default)

# 4. Check health and metrics
curl -s localhost:9109/health ; echo
curl -s localhost:9109/ready ; echo
curl -s localhost:9109/metrics | head
```

### ⚠️ Safety First for Live Trading

Before going live, ensure:

- ✅ Wallet has sufficient SOL for fees (~0.01 SOL minimum)
- ✅ Risk management settings are appropriate for your capital
- ✅ Circuit breaker and crash sentinel are enabled
- ✅ Monitoring dashboard is accessible
- ✅ You understand the bot strategies and their risks

### 🖥️ Visual Monitoring

```bash
# Start the monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Access dashboards:
# - Grafana: http://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9090
# - Bot Metrics: http://localhost:9109/metrics
```

## Layout

```
bots/                  # Individual bot implementations
  hedge/              # Hedge bot with urgency scoring
  jit/                # JIT maker with micro-pricing
  trend/              # Trend following with indicators
libs/                  # Core libraries
  drift/              # Client implementations
  metrics.py          # Prometheus metrics
  order_management.py # Position and order tracking
  risk/               # Risk management components
configs/              # YAML configurations
  core/               # Client and core settings
  hedge/              # Hedge bot parameters
  jit/                # JIT bot parameters
  trend/              # Trend bot parameters
run_all_bots.py       # Main orchestrator entry point
```

## CLI Options

```bash
python run_all_bots.py --help

# Use mock client for testing
python run_all_bots.py --mock --metrics-port 9109

# Use real client (requires credentials)
python run_all_bots.py --real --client-config configs/core/drift_client.yaml
```

## Health Endpoints

- `/health` - Always returns OK (liveness probe)
- `/ready` - Returns READY when client connected and all bots running (readiness probe)
- `/metrics` - Prometheus metrics for monitoring

## Configuration

See `configs/orchestrator.yaml` for bot-specific settings and `configs/core/drift_client.yaml` for client configuration.

## Notes

- **Mock Mode**: Use `--mock` for testing without real credentials
- **Real Mode**: Requires `.env` file with proper Drift credentials
- **Health Checks**: Use `/ready` for load balancer health checks
- **Metrics**: Prometheus-compatible metrics available at `/metrics`
