# 🔄 Drift Bots Regression Checklist

## Overview
This checklist ensures that critical bugs and issues are not reintroduced during development. Each item represents a previously resolved issue that should be tested before deployment.

## 🚨 Critical Regression Tests (Block Deployment)

### ASYNC-001: Orderbook Await Misuse Prevention
**Issue:** "object Orderbook can't be used in 'await' expression" error

**Test Steps:**
- [ ] Verify `await client.get_orderbook()` pattern is used correctly
- [ ] Confirm Orderbook object is accessed synchronously after await
- [ ] Test OrderbookSnapshot wrapper prevents misuse
- [ ] Validate SafeAwaitError is raised for incorrect usage

**Files to Check:**
- [ ] `run_mm_bot_only.py` - MM bot orderbook handling
- [ ] `libs/drift/client.py` - DriftpyClient.get_orderbook()
- [ ] `libs/market/orderbook_snapshot.py` - Snapshot wrapper
- [ ] All bot files using orderbook data

**Prevention Code:**
```python
# ✅ CORRECT - await the method, then use synchronously
ob = await client.get_orderbook()
mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0

# ❌ WRONG - don't await the orderbook object itself
# await orderbook  # This will fail
```

### PORT-001: Prometheus/Grafana Port Conflicts
**Issue:** Port 9090/3000 already allocated preventing monitoring launch

**Test Steps:**
- [ ] Stop any existing Docker containers: `docker ps -aq | xargs docker stop`
- [ ] Verify ports 9090, 3000, 9100 are free: `netstat -ano | findstr :9090`
- [ ] Launch monitoring stack: `docker-compose -f docker-compose.monitoring.yml up -d`
- [ ] Verify Grafana accessible: http://localhost:3000
- [ ] Verify Prometheus accessible: http://localhost:9090

**Files to Check:**
- [ ] `docker-compose.monitoring.yml` - Port mappings
- [ ] `start_beta_bots.bat` - Port conflict detection
- [ ] `launch_beta_bots.py` - Docker launch commands

### SYNTAX-001: Python Syntax Errors in Launch Scripts
**Issue:** Missing newlines between statements causing SyntaxError

**Test Steps:**
- [ ] Run syntax check: `python -m py_compile launch_beta_bots.py`
- [ ] Verify all logger statements have proper line breaks
- [ ] Test execution: `python launch_beta_bots.py --dry-run`
- [ ] Check all Python files for similar patterns

**Pattern to Avoid:**
```python
# ❌ WRONG - missing newline
logger.info("Message")variable += 1

# ✅ CORRECT - proper line breaks
logger.info("Message")
variable += 1
```

### CROSS-PLATFORM-001: Windows/Unix Command Compatibility
**Issue:** Unix commands failing on Windows PowerShell

**Test Steps:**
- [ ] Test batch file on Windows: `start_beta_bots.bat --dry-run`
- [ ] Test shell script on Linux/Mac: `./start_beta_bots.sh --dry-run`
- [ ] Verify platform detection in Python scripts
- [ ] Test all external commands work on target platform

**Command Mappings:**
| Unix Command | Windows Equivalent | Status |
|-------------|-------------------|---------|
| `ls -la` | `Get-ChildItem -Force` | ✅ Fixed |
| `chmod +x` | N/A (batch files) | ✅ Fixed |
| `grep` | `findstr` | ✅ Fixed |
| `netstat -tulpn` | `netstat -ano` | ✅ Fixed |

## ⚠️ High Priority Regression Tests

### WALLET-001: Wallet Connection & Balance
**Test Steps:**
- [ ] Verify `.beta_dev_wallet.json` exists and is readable
- [ ] Test wallet balance: `solana balance .beta_dev_wallet.json`
- [ ] Confirm wallet has sufficient SOL for gas fees
- [ ] Validate wallet address in configuration

### CONFIG-001: Configuration Validation
**Test Steps:**
- [ ] Test YAML parsing: `python -c "import yaml; yaml.safe_load(open('configs/core/drift_client.yaml'))"`
- [ ] Verify all required fields present
- [ ] Test environment variable interpolation
- [ ] Validate network endpoints are reachable

## 🔧 Medium Priority Regression Tests

### METRICS-001: Prometheus Metrics
**Test Steps:**
- [ ] Verify metrics server starts on port 9109
- [ ] Check metrics endpoint: http://localhost:9109/metrics
- [ ] Validate custom metrics are registered
- [ ] Test metrics updates during bot operation

### HEALTH-001: Health Endpoints
**Test Steps:**
- [ ] Test health endpoint: http://localhost:9109/health
- [ ] Test readiness endpoint: http://localhost:9109/ready
- [ ] Verify health checks return correct status
- [ ] Test health degradation scenarios

## 📊 Performance Regression Tests

### JIT-001: Market Maker Performance
**Test Steps:**
- [ ] Monitor iteration rate (should be > 0.5 iterations/second)
- [ ] Check spread calculation accuracy
- [ ] Verify order placement success rate
- [ ] Monitor memory usage and CPU utilization

## 🧪 Testing Commands

### Quick Regression Test
```bash
# Run all critical regression tests
python -c "
import asyncio
from libs.drift.client import build_client_from_config

async def test():
    try:
        client = await build_client_from_config('configs/core/drift_client.yaml')
        ob = await client.get_orderbook()
        if ob.bids and ob.asks:
            print('✅ ASYNC-001 PASSED: Orderbook fetch successful')
        else:
            print('❌ ASYNC-001 FAILED: Empty orderbook')
    except Exception as e:
        print(f'❌ ASYNC-001 FAILED: {e}')

asyncio.run(test())
"
```

### Full System Test
```bash
# 1. Test syntax
python -m py_compile launch_beta_bots.py

# 2. Test configuration
python launch_beta_bots.py --dry-run

# 3. Test wallet
solana balance .beta_dev_wallet.json

# 4. Test ports
netstat -ano | findstr :9090
```

## 📋 Checklist Usage

- [ ] **Before Development**: Review relevant regression tests
- [ ] **During Development**: Run affected regression tests
- [ ] **Before Commit**: Execute full regression suite
- [ ] **Before Deployment**: Complete all critical tests

## 🚨 Emergency Procedures

If regression detected:
1. **Stop immediately**: `Ctrl+C` or kill bot processes
2. **Revert changes**: `git revert` problematic commit
3. **Run full tests**: Execute complete regression checklist
4. **Document issue**: Add to BUG_TRACKING.md
5. **Fix root cause**: Implement permanent solution

## 📞 Support

- Check BUG_TRACKING.md for known issues
- Review git history for similar problems
- Test with `--dry-run` first
- Use mock mode for debugging

---

**Last Updated:** 2025-01-11
**Version:** 1.0
**Status:** 🟢 Active
