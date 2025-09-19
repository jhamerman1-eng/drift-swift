# 🌍 Environment Configuration System

This document explains the **centralized environment configuration** for the Drift Market Making Bot.

## 📋 **Problem Solved**

Previously, environment configuration was scattered across multiple files with confusing terminology:
- ❌ "Development" mixed LOCAL and DEVNET
- ❌ "Production" was unclear between devnet testing and mainnet
- ❌ Configuration spread across multiple YAML files
- ❌ Hardcoded URLs throughout the codebase

## ✅ **Solution: Centralized Configuration**

**Single Source of Truth**: `configs/environments.yaml`
**Central Manager**: `libs/config/environment.py`

## 🎯 **Clear Environment Definitions**

| Environment | Description | Blockchain | Swift API | Purpose |
|-------------|-------------|------------|-----------|---------|
| **`local`** | Local development with mock sidecar | devnet | `localhost:8787` | 🧪 Development & Testing |
| **`devnet`** | Devnet testing with real Swift API | devnet | `master.swift.drift.trade` | 🌐 Integration Testing |
| **`mainnet`** | Production mainnet trading | mainnet-beta | `app.drift.trade` | 🚀 **LIVE TRADING** |

## 🚀 **Usage**

### **1. Set Environment**

```bash
# Option 1: Environment Variable (Recommended)
export DRIFT_ENVIRONMENT=local    # or devnet, mainnet
python run_swift_mm_complete.py

# Option 2: Test Environment
python scripts/set_environment.py local
python scripts/set_environment.py devnet
python scripts/set_environment.py mainnet
```

### **2. Use in Code**

```python
from libs.config.environment import get_environment_config

# Get current environment configuration
env_config = get_environment_config()

# Environment info
print(f"Environment: {env_config.get_environment()}")  # local, devnet, mainnet
print(f"Is Production: {env_config.is_production()}")  # True for mainnet only

# Swift configuration
swift_config = env_config.get_swift_config()
print(f"Swift URL: {swift_config['base_url']}")
print(f"Use Local Sidecar: {env_config.use_local_sidecar()}")

# Drift configuration  
print(f"Drift Env: {env_config.get_drift_env()}")
print(f"RPC URL: {env_config.get_rpc_url()}")

# JIT configuration
jit_config = env_config.get_jit_config()
print(f"JIT Enabled: {jit_config['enabled']}")
```

## 📁 **Configuration Files**

### **Primary Configuration**
- `configs/environments.yaml` - **SINGLE SOURCE OF TRUTH**

### **Implementation**
- `libs/config/environment.py` - Central configuration manager
- `libs/config/__init__.py` - Module exports

### **Tools**
- `scripts/set_environment.py` - Environment testing & validation

## 🔧 **Environment Details**

### **LOCAL Environment**
```yaml
environments:
  local:
    description: "Local development with mock sidecar"
    swift:
      base_url: "http://localhost:8787"
      use_local_sidecar: true
    drift:
      env: "devnet"  # Still use devnet blockchain
      rpc_url: "https://devnet.helius-rpc.com"
    jit:
      enabled: true
      base_url: "http://localhost:8787"
```

**Setup:**
1. Start sidecar: `cd services/jit-maker && npm start`
2. Run bot: `export DRIFT_ENVIRONMENT=local && python run_swift_mm_complete.py`
3. **All orders route to localhost:8787 (mock)**

### **DEVNET Environment**
```yaml
environments:
  devnet:
    description: "Devnet testing with real Swift API"
    swift:
      base_url: "https://master.swift.drift.trade"
      use_local_sidecar: false
    drift:
      env: "devnet"
      rpc_url: "https://devnet.helius-rpc.com"
    jit:
      enabled: false  # Use real Swift API
```

**Setup:**
1. Set environment: `export DRIFT_ENVIRONMENT=devnet`
2. Run bot: `python run_swift_mm_complete.py`
3. **Orders route to master.swift.drift.trade (real API)**

### **MAINNET Environment**
```yaml
environments:
  mainnet:
    description: "Production mainnet trading"
    swift:
      base_url: "https://app.drift.trade"
      use_local_sidecar: false
    drift:
      env: "mainnet-beta"
      rpc_url: "https://mainnet.helius-rpc.com"
    jit:
      enabled: false  # Use real Swift API
```

**Setup:**
1. Set environment: `export DRIFT_ENVIRONMENT=mainnet`
2. Run bot: `python run_swift_mm_complete.py`
3. **⚠️ WARNING: REAL MONEY TRADING!**
4. **Orders route to app.drift.trade (PRODUCTION)**

## 🔒 **Safety Features**

### **Environment Validation**
```python
validation = env_config.validate_configuration()
if not validation["valid"]:
    print(f"Issues: {validation['issues']}")
```

### **Production Checks**
```python
if env_config.is_production():
    print("⚠️ WARNING: Running in PRODUCTION mode!")
```

### **Configuration Summary**
```python
summary = env_config.validate_configuration()["config_summary"]
# Shows: drift_env, rpc_url, swift_url, use_local_sidecar, jit_enabled
```

## 🔄 **Migration Benefits**

### **Before (Scattered)**
- Multiple config files: `configs/core/drivers.yaml`, hardcoded URLs
- Confusing terminology: "development" vs "production"
- Environment logic spread across bot code

### **After (Centralized)**
- ✅ Single source of truth: `configs/environments.yaml`
- ✅ Clear terminology: `local` / `devnet` / `mainnet`
- ✅ Environment-aware configuration: automatic URL selection
- ✅ Validation and safety checks
- ✅ Easy environment switching

## 🚀 **Production Deployment**

```bash
# Production checklist:
export DRIFT_ENVIRONMENT=mainnet
export HELIUS_API_KEY=your_mainnet_api_key

# Validate configuration
python scripts/set_environment.py mainnet

# Run bot (LIVE TRADING!)
python run_swift_mm_complete.py
```

## 📝 **Notes**

- **Default environment**: `local` (safe for development)
- **Environment variable**: `DRIFT_ENVIRONMENT` overrides default
- **API keys**: Automatically added to RPC URLs if `HELIUS_API_KEY` is set
- **Backward compatibility**: Bot still accepts legacy config format
- **Validation**: All configurations are validated on startup

---

**🎯 Result**: Clean, centralized, unambiguous environment management with clear separation between LOCAL development, DEVNET testing, and MAINNET production! 🚀



