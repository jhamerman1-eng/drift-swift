# 🔧 SCRIPTS - Utility Scripts and Tools

This directory contains utility scripts and tools for managing, deploying, monitoring, and maintaining the Drift Swift trading system. These scripts provide operational support and automation for the trading infrastructure.

## 📁 Directory Structure

```
scripts/
├── bots/                           # Bot Management Scripts
│   ├── run_hedge_bot.py           # ⭐ Hedge bot launcher
│   ├── run_trend_bot_working.py   # Working trend bot launcher
│   ├── run_all_bots_a.py          # Run all bots simultaneously
│   └── bot_health_monitor.py      # Bot health monitoring
├── deployment/                    # Deployment Scripts
│   ├── deploy_devnet.py           # Devnet deployment
│   ├── deploy_production.py       # Production deployment
│   └── rollback_deployment.py     # Deployment rollback
├── monitoring/                    # Monitoring and Analytics
│   ├── system_health_check.py     # System health monitoring
│   ├── performance_monitor.py     # Performance monitoring
│   └── alert_manager.py           # Alert management
├── maintenance/                   # Maintenance Scripts
│   ├── cleanup_logs.py            # Log file cleanup
│   ├── database_maintenance.py    # Database maintenance
│   └── backup_configs.py          # Configuration backup
├── testing/                       # Testing Utilities
│   ├── run_performance_tests.py   # Performance test runner
│   ├── validate_configs.py        # Configuration validation
│   └── test_data_generator.py     # Test data generation
└── utilities/                     # General Utilities
    ├── wallet_manager.py          # Wallet management utilities
    ├── market_data_collector.py   # Market data collection
    └── config_migrator.py         # Configuration migration
```

## 🚀 Bot Management Scripts (`bots/`)

### **`run_hedge_bot.py`** - Hedge Bot Launcher
**Purpose**: Clean, simple hedge bot launcher with proper error handling.

```bash
# Run hedge bot with default configuration
python scripts/bots/run_hedge_bot.py

# Run with custom configuration
python scripts/bots/run_hedge_bot.py --config=configs/hedge/custom.yaml

# Run in test mode
python scripts/bots/run_hedge_bot.py --test-mode
```

**Features**:
- Proper error handling and logging
- Configuration validation
- Health monitoring integration
- Graceful shutdown handling

### **`run_trend_bot_working.py`** - Trend Bot Launcher
**Purpose**: Working trend bot implementation with real price data.

```bash
# Run trend bot with MACD strategy
python scripts/bots/run_trend_bot_working.py

# Run with custom timeframe
python scripts/bots/run_trend_bot_working.py --timeframe=5m

# Run with multiple markets
python scripts/bots/run_trend_bot_working.py --markets=SOL-PERP,BTC-PERP
```

**Features**:
- Real price data integration
- Multi-timeframe analysis
- Technical indicator support
- Risk management integration

### **`run_all_bots_a.py`** - Multi-Bot Orchestration
**Purpose**: Run all bots simultaneously with coordination.

```bash
# Run all bots with default allocation
python scripts/bots/run_all_bots_a.py

# Run with custom capital allocation
python scripts/bots/run_all_bots_a.py --capital=50000

# Run specific bot combination
python scripts/bots/run_all_bots_a.py --bots=jit,hedge,trend
```

**Features**:
- Unified capital allocation
- Cross-bot coordination
- Real-time monitoring
- Automatic restart on failures

## 🚀 Deployment Scripts (`deployment/`)

### **`deploy_devnet.py`** - Development Deployment
**Purpose**: Deploy system to devnet for testing.

```bash
# Deploy to devnet
python scripts/deployment/deploy_devnet.py

# Deploy with specific configuration
python scripts/deployment/deploy_devnet.py --config=devnet_test

# Deploy with monitoring
python scripts/deployment/deploy_devnet.py --enable-monitoring
```

### **`deploy_production.py`** - Production Deployment
**Purpose**: Deploy system to production with safety checks.

```bash
# Deploy to production (with confirmations)
python scripts/deployment/deploy_production.py

# Deploy with specific version
python scripts/deployment/deploy_production.py --version=v1.2.0

# Deploy with rollback plan
python scripts/deployment/deploy_production.py --enable-rollback
```

**Safety Features**:
- Pre-deployment validation
- Configuration verification
- Health check integration
- Automatic rollback capability

## 📊 Monitoring Scripts (`monitoring/`)

### **`system_health_check.py`** - System Health Monitoring
**Purpose**: Comprehensive system health monitoring.

```bash
# Run health check
python scripts/monitoring/system_health_check.py

# Continuous monitoring
python scripts/monitoring/system_health_check.py --continuous

# Generate health report
python scripts/monitoring/system_health_check.py --report
```

**Health Checks**:
- Bot status and performance
- Database connectivity
- API endpoint availability
- Resource utilization
- Error rate monitoring

### **`performance_monitor.py`** - Performance Monitoring
**Purpose**: Real-time performance monitoring and alerting.

```bash
# Start performance monitoring
python scripts/monitoring/performance_monitor.py

# Monitor specific metrics
python scripts/monitoring/performance_monitor.py --metrics=latency,throughput

# Generate performance report
python scripts/monitoring/performance_monitor.py --report --duration=24h
```

**Monitored Metrics**:
- Order placement latency
- Capital allocation performance
- Bot coordination efficiency
- System resource usage
- Error rates and exceptions

## 🔧 Maintenance Scripts (`maintenance/`)

### **`cleanup_logs.py`** - Log File Management
**Purpose**: Automated log file cleanup and archival.

```bash
# Clean logs older than 7 days
python scripts/maintenance/cleanup_logs.py --days=7

# Archive logs before cleanup
python scripts/maintenance/cleanup_logs.py --archive

# Clean specific log types
python scripts/maintenance/cleanup_logs.py --type=debug,trace
```

### **`backup_configs.py`** - Configuration Backup
**Purpose**: Backup and version control for configurations.

```bash
# Backup all configurations
python scripts/maintenance/backup_configs.py

# Backup with timestamp
python scripts/maintenance/backup_configs.py --timestamp

# Restore from backup
python scripts/maintenance/backup_configs.py --restore=backup_20231215
```

## 🧪 Testing Utilities (`testing/`)

### **`run_performance_tests.py`** - Performance Test Runner
**Purpose**: Execute performance benchmarks and generate reports.

```bash
# Run all performance tests
python scripts/testing/run_performance_tests.py

# Run specific test category
python scripts/testing/run_performance_tests.py --category=latency

# Compare with baseline
python scripts/testing/run_performance_tests.py --baseline=v1.0.0
```

### **`validate_configs.py`** - Configuration Validation
**Purpose**: Validate all configuration files for syntax and logic errors.

```bash
# Validate all configurations
python scripts/testing/validate_configs.py

# Validate specific configuration
python scripts/testing/validate_configs.py --config=jit_template.yaml

# Validate with schema
python scripts/testing/validate_configs.py --schema-check
```

## 🛠️ General Utilities (`utilities/`)

### **`wallet_manager.py`** - Wallet Management
**Purpose**: Comprehensive wallet management utilities.

```bash
# Create new wallet
python scripts/utilities/wallet_manager.py create --name=test_wallet

# Check wallet balance
python scripts/utilities/wallet_manager.py balance --wallet=test_wallet

# Transfer funds
python scripts/utilities/wallet_manager.py transfer --from=wallet1 --to=wallet2 --amount=1.0
```

**Features**:
- Secure wallet creation
- Balance monitoring
- Fund transfers
- Keypair management
- Multi-wallet support

### **`market_data_collector.py`** - Market Data Collection
**Purpose**: Collect and store market data for analysis.

```bash
# Start data collection
python scripts/utilities/market_data_collector.py start

# Collect specific markets
python scripts/utilities/market_data_collector.py --markets=SOL-PERP,BTC-PERP

# Export collected data
python scripts/utilities/market_data_collector.py export --format=csv
```

## 📋 Common Usage Patterns

### **Bot Management Workflow**
```bash
# 1. Validate configuration
python scripts/testing/validate_configs.py

# 2. Run health check
python scripts/monitoring/system_health_check.py

# 3. Deploy to devnet
python scripts/deployment/deploy_devnet.py

# 4. Monitor performance
python scripts/monitoring/performance_monitor.py --continuous

# 5. Run specific bot
python scripts/bots/run_hedge_bot.py
```

### **Maintenance Workflow**
```bash
# Daily maintenance
python scripts/maintenance/cleanup_logs.py --days=7
python scripts/maintenance/backup_configs.py
python scripts/monitoring/system_health_check.py --report

# Weekly maintenance
python scripts/testing/run_performance_tests.py
python scripts/maintenance/database_maintenance.py
```

### **Deployment Workflow**
```bash
# 1. Pre-deployment validation
python scripts/testing/validate_configs.py
python scripts/testing/run_performance_tests.py

# 2. Deploy to staging
python scripts/deployment/deploy_devnet.py --config=staging

# 3. Run integration tests
python -m pytest tests/integration/

# 4. Deploy to production
python scripts/deployment/deploy_production.py

# 5. Post-deployment monitoring
python scripts/monitoring/system_health_check.py
python scripts/monitoring/performance_monitor.py
```

## 🔒 Security and Safety

### **Script Security Features**
- Input validation and sanitization
- Secure credential handling
- Audit logging for all operations
- Role-based access control
- Safe failure modes

### **Safety Checks**
```python
# Example safety check pattern
def validate_environment():
    """Validate environment before script execution."""
    if os.getenv("ENVIRONMENT") == "production":
        confirmation = input("This will affect PRODUCTION. Continue? (yes/no): ")
        if confirmation.lower() != "yes":
            print("Operation cancelled.")
            sys.exit(1)

def backup_before_changes():
    """Create backup before making changes."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backup_{timestamp}"
    shutil.copytree("configs/", backup_path)
    print(f"Backup created: {backup_path}")
```

## 📈 Monitoring and Alerting

### **Health Check Integration**
```python
# Health check example
def check_system_health():
    """Comprehensive system health check."""
    checks = {
        "drift_client": check_drift_connectivity(),
        "swift_api": check_swift_availability(),
        "database": check_database_connection(),
        "bots": check_bot_status(),
        "resources": check_resource_usage()
    }
    
    failed_checks = [name for name, status in checks.items() if not status]
    
    if failed_checks:
        send_alert(f"Health check failures: {failed_checks}")
    
    return all(checks.values())
```

### **Performance Monitoring**
```python
# Performance monitoring example
def monitor_performance():
    """Monitor key performance metrics."""
    metrics = {
        "jit_latency_p95": measure_jit_latency(),
        "capital_allocation_speed": measure_allocation_speed(),
        "orderbook_processing_rate": measure_ob_processing(),
        "error_rate": calculate_error_rate()
    }
    
    # Check for performance degradation
    for metric, value in metrics.items():
        threshold = PERFORMANCE_THRESHOLDS.get(metric)
        if threshold and value > threshold:
            send_alert(f"Performance degradation: {metric} = {value}")
    
    return metrics
```

## 🔧 Script Development Guidelines

### **Best Practices**
1. **Error Handling**: Comprehensive error handling with meaningful messages
2. **Logging**: Structured logging for all operations
3. **Configuration**: Use configuration files instead of hardcoded values
4. **Validation**: Validate inputs and environment before execution
5. **Documentation**: Clear docstrings and usage examples

### **Script Template**
```python
#!/usr/bin/env python3
"""
Script Description: Brief description of what the script does
Usage: python script_name.py [options]
Author: Development Team
"""

import argparse
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main script function."""
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Script logic here
        logger.info("Script started")
        
        # ... implementation ...
        
        logger.info("Script completed successfully")
        
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## 📞 Script Support

### **Getting Help**
```bash
# Get help for any script
python scripts/bots/run_hedge_bot.py --help
python scripts/deployment/deploy_production.py --help

# List all available scripts
ls -la scripts/*/

# Check script dependencies
python scripts/utilities/check_dependencies.py
```

### **Troubleshooting**
- **Permission Issues**: Ensure scripts have execute permissions
- **Environment Issues**: Verify environment variables are set
- **Configuration Issues**: Run validation scripts first
- **Dependency Issues**: Check requirements and imports

The scripts directory provides comprehensive operational support for the entire Drift Swift trading system, from development through production deployment and ongoing maintenance.
