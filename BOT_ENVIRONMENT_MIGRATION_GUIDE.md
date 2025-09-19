# 🌍 Bot Environment Configuration Migration Guide

This guide explains how all bots now use the **CENTRALIZED ENVIRONMENT CONFIGURATION** system.

## 🎯 **What Changed**

### **BEFORE (Scattered Configuration):**
```
❌ Each bot had its own config files
❌ Hardcoded environment variables
❌ Inconsistent terminology 
❌ Multiple sources of truth
```

### **AFTER (Centralized Configuration):**
```
✅ Single source of truth: configs/environments.yaml
✅ Centralized manager: libs/config/environment.py  
✅ Clear terminology: LOCAL/DEVNET/MAINNET
✅ Environment switching with DRIFT_ENVIRONMENT
```

## 📁 **Files Updated**

### **🤖 Bots Updated to Use Centralized Config:**
- ✅ `run_swift_mm_complete.py` - Market Making Bot
- ✅ `run_hedge_bot.py` - Hedge Bot  
- ✅ `run_trend_bot_beta.py` - Trend Bot
- ✅ `configs/orchestrator.yaml` - Orchestrator Config

### **🆕 New Files Created:**
- ✅ `configs/environments.yaml` - **SINGLE SOURCE OF TRUTH**
- ✅ `libs/config/environment.py` - Central configuration manager
- ✅ `launch_bot_universal.py` - Universal launcher for all bots

## 🚀 **How to Use**

### **1. Environment Selection**
```bash
# LOCAL: Mock sidecar for development
export DRIFT_ENVIRONMENT=local

# DEVNET: Real Swift API testing
export DRIFT_ENVIRONMENT=devnet  

# MAINNET: Production trading (REAL MONEY!)
export DRIFT_ENVIRONMENT=mainnet
```

### **2. Launch Any Bot**
```bash
# Using Universal Launcher (RECOMMENDED)
python launch_bot_universal.py --bot hedge
python launch_bot_universal.py --bot trend  
python launch_bot_universal.py --bot mm

# Or launch directly
python run_hedge_bot.py
python run_trend_bot_beta.py
python run_swift_mm_complete.py
```

### **3. Override Environment**
```bash
# Temporarily override environment
python launch_bot_universal.py --bot mm --env mainnet
```

## 🌍 **Environment Details**

| Environment | Blockchain | Swift API | JIT | Purpose |
|-------------|------------|-----------|-----|---------|
| **LOCAL** | devnet | `localhost:8787` | ✅ | 🧪 Development |
| **DEVNET** | devnet | `master.swift.drift.trade` | ❌ | 🌐 Testing |
| **MAINNET** | mainnet-beta | `app.drift.trade` | ❌ | 🚀 **PRODUCTION** |

## 🔧 **Configuration Architecture**

```
configs/environments.yaml (SINGLE SOURCE OF TRUTH)
    ↓
libs/config/environment.py (Central Manager)
    ↓
All Bots (run_*.py files)
```

### **Key Functions:**
```python
from libs.config.environment import get_environment_config

config = get_environment_config()
config.get_environment()          # "local", "devnet", "mainnet"
config.get_swift_config()         # Swift API configuration
config.get_jit_config()           # JIT service configuration
config.get_drift_env()            # Drift environment
config.get_rpc_url()              # RPC URL with API key
config.use_local_sidecar()        # True for local environment
config.is_production()            # True for mainnet
```

## 🔄 **Migration Benefits**

### **For Developers:**
- ✅ **Single Source of Truth**: No more hunting for config files
- ✅ **Environment Switching**: One env var changes everything
- ✅ **Consistency**: All bots use same configuration system
- ✅ **Validation**: Built-in configuration validation
- ✅ **Safety**: Production mode requires confirmation

### **For Operations:**
- ✅ **Simplified Deployment**: Just set `DRIFT_ENVIRONMENT`
- ✅ **Clear Terminology**: LOCAL/DEVNET/MAINNET (no confusion)
- ✅ **Universal Launcher**: One script to launch any bot
- ✅ **Environment Validation**: Catches configuration issues early

## 📋 **Validation Checklist**

Before running any bot, validate the configuration:
```bash
python scripts/set_environment.py local    # Test LOCAL
python scripts/set_environment.py devnet   # Test DEVNET  
python scripts/set_environment.py mainnet  # Test MAINNET
```

## ⚠️  **Breaking Changes**

### **Old Config Files (DEPRECATED):**
- ❌ `configs/core/drift_client.yaml`
- ❌ `configs/core/drift_client_beta.yaml`  
- ❌ Hardcoded environment variables in bot files

### **Migration Required:**
If you have custom bot scripts, update them to use:
```python
# OLD (DEPRECATED)
import yaml
with open("configs/core/drift_client.yaml", "r") as f:
    config = yaml.safe_load(f)

# NEW (CENTRALIZED)
from libs.config.environment import get_environment_config
env_config = get_environment_config()
```

## 🧪 **Testing**

Test all environments work correctly:
```bash
# Test LOCAL environment
export DRIFT_ENVIRONMENT=local
python launch_bot_universal.py --bot mm

# Test DEVNET environment  
export DRIFT_ENVIRONMENT=devnet
python launch_bot_universal.py --bot hedge

# Test MAINNET environment (CAREFUL!)
export DRIFT_ENVIRONMENT=mainnet
python launch_bot_universal.py --bot trend
```

## 📞 **Support**

### **Configuration Issues:**
1. Check `configs/environments.yaml` exists
2. Verify `DRIFT_ENVIRONMENT` is set correctly
3. Run validation: `python scripts/set_environment.py <env>`

### **Bot Failures:**
1. Check environment validation passes
2. Verify API keys are set (`HELIUS_API_KEY`)
3. Ensure local sidecar is running for LOCAL environment

## 🎉 **Result**

**Clean, centralized, unambiguous environment management across ALL bots!**

No more configuration confusion - just set `DRIFT_ENVIRONMENT` and go! 🚀



