# 📊 Grafana Dashboard Setup for Drift Bots v3.0

## Overview

The Grafana dashboard provides real-time monitoring and visualization of your Drift trading bots' performance, health, and risk metrics. It connects to Prometheus to scrape metrics from the orchestrator.

## Prerequisites

- **Grafana** (v8.0+ recommended)
- **Prometheus** (v2.30+ recommended)
- **Drift Bots v3.0** running with metrics enabled

## 🚀 Quick Setup

### 1. Install Grafana

```bash
# Ubuntu/Debian
sudo apt-get install grafana

# Or using Docker
docker run -d -p 3000:3000 grafana/grafana
```

### 2. Install Prometheus

```bash
# Ubuntu/Debian
sudo apt-get install prometheus

# Or using Docker
docker run -d -p 9090:9090 prom/prometheus
```

### 3. Configure Prometheus

Create `/etc/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'drift-bots'
    static_configs:
      - targets: ['localhost:9109']  # Your metrics port
    scrape_interval: 5s
```

### 4. Import Dashboard

1. **Access Grafana**: Open http://localhost:3000 (admin/admin)

2. **Add Prometheus Data Source**:
   - Go to Configuration → Data Sources
   - Add Prometheus: http://localhost:9090

3. **Import Dashboard**:
   - Go to Dashboards → Import
   - Upload `grafana_dashboard.json` or paste its contents
   - Select your Prometheus data source

## 📈 Dashboard Panels Explained

### 1. **System Health Overview**
- **Orchestrator Status**: Shows if the master bot orchestrator is running
- **Ready Status**: Indicates if client is connected and all tasks are operational

### 2. **Bot Activity (Iterations/Minute)**
- Real-time iteration rates for each bot (Hedge, Trend, JIT, Monitor)
- Helps identify which bots are most active

### 3. **Crash Sentinel State by Market**
- **NORMAL** (🟢): All systems operational
- **DE_RISK** (🟡): Reduced position sizes due to high volatility
- **HALT** (🔴): Trading completely stopped due to extreme conditions

### 4. **Portfolio Rails State**
- **NORMAL** (🟢): Full position sizes allowed
- **SOFT_STOP** (🟡): Reduced position sizes (-7.5% threshold)
- **TREND_PAUSE** (🟠): Significant pause (-12.5% threshold)
- **CIRCUIT_BREAKER** (🔴): Emergency stop (-20% threshold)

### 5. **JIT Bot Quote Latency**
- Heatmap showing time from market tick to quote placement
- Critical for measuring execution speed

### 6. **Bot Performance Trends**
- Time-series graph of bot iteration rates
- Helps identify performance bottlenecks

### 7. **System Alerts**
- Real-time alerts for critical system events
- Automatic notifications when thresholds are breached

## 🔧 Configuration Options

### Metrics Port Configuration

The orchestrator exposes metrics on the port specified by `--metrics-port`:

```bash
# Default metrics port
python run_all_bots.py --mock --metrics-port 9109

# Custom port
python run_all_bots.py --mock --metrics-port 8080
```

### Prometheus Scraping

Update your Prometheus config to match your metrics port:

```yaml
scrape_configs:
  - job_name: 'drift-bots'
    static_configs:
      - targets: ['your-server:9109']  # Change port as needed
    scrape_interval: 5s
```

## 🎯 Advanced Features

### Custom Alerts

Add these alerts in Grafana for proactive monitoring:

```yaml
# Orchestrator Down Alert
ALERT OrchestratorDown
  IF orchestrator_up == 0
  FOR 30s
  LABELS { severity = "critical" }
  ANNOTATIONS {
    summary = "Drift Orchestrator is DOWN",
    description = "The master bot orchestrator has stopped running"
  }

# High Latency Alert
ALERT HighJITLatency
  IF histogram_quantile(0.95, rate(jit_tick_to_quote_seconds_bucket[5m])) > 0.1
  FOR 1m
  LABELS { severity = "warning" }
  ANNOTATIONS {
    summary = "High JIT Bot latency detected",
    description = "95th percentile quote latency > 100ms"
  }
```

### Multiple Environments

For multiple bot deployments, use labels:

```bash
# Production
python run_all_bots.py --env prod --metrics-port 9109

# Staging
python run_all_bots.py --env staging --metrics-port 9110
```

Update Prometheus config:

```yaml
scrape_configs:
  - job_name: 'drift-bots-prod'
    static_configs:
      - targets: ['prod-server:9109']
    labels:
      environment: 'production'

  - job_name: 'drift-bots-staging'
    static_configs:
      - targets: ['staging-server:9110']
    labels:
      environment: 'staging'
```

## 📊 Metrics Reference

| Metric | Type | Description |
|--------|------|-------------|
| `orchestrator_up` | Gauge | 1 if orchestrator running, 0 if stopped |
| `orchestrator_ready` | Gauge | 1 if client connected and tasks running |
| `bot_iterations_total{bot=...}` | Counter | Total iterations per bot |
| `crash_sentinel_state{market=...}` | Gauge | 0=normal, 1=de_risk, 2=halt |
| `portfolio_rails_state{portfolio=...}` | Gauge | 0=normal, 1=soft, 2=pause, 3=breaker |
| `jit_tick_to_quote_seconds` | Summary | Time from tick to quote placement |

## 🐛 Troubleshooting

### Dashboard Shows No Data

1. **Check Prometheus targets**: http://localhost:9090/targets
2. **Verify metrics endpoint**: curl http://localhost:9109/metrics
3. **Check bot logs** for metrics server startup messages

### Panels Show Errors

1. **Verify data source**: Ensure Prometheus is selected
2. **Check query syntax**: Use Query Inspector in Grafana
3. **Validate metric names**: Match exactly with what's exposed

### Performance Issues

1. **Reduce scrape interval** if dashboard is slow
2. **Use appropriate time ranges** (don't query years of data)
3. **Optimize queries** with proper label selectors

## 🔄 Updating the Dashboard

To modify the dashboard:

1. Export current dashboard as JSON
2. Edit the JSON configuration
3. Import the updated version
4. Test all panels are working correctly

## 📞 Support

For issues with the dashboard:
1. Check Grafana logs: `sudo journalctl -u grafana`
2. Check Prometheus logs: `sudo journalctl -u prometheus`
3. Verify bot metrics are being generated correctly

---

**🎯 Pro Tip**: Set up alerts for critical metrics to get notified when the system needs attention!
