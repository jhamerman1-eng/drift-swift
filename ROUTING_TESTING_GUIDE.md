# 🔀 Smart Routing & Testing Guide

**Date:** September 16, 2025  
**Component:** Order Routing System  

## 🎯 **Overview**

The order routing system now provides **smart fallback routing for everyday use** with a **clean testing override** that doesn't affect the production code.

## ✅ **Normal Operation (Everyday Use)**

**Default Behavior:** Smart routing with full fallback chain

```bash
# Normal operation - uses smart routing
python run_swift_mm_complete.py
```

**Routing Flow:**
1. **JIT Service** (if enabled and healthy)
2. **Swift API** (your sidecar or external Swift) 
3. **DriftPy Direct** (final fallback)

**Benefits:**
- ✅ Reliable order placement with multiple fallbacks
- ✅ Performance optimization when JIT is available
- ✅ Graceful degradation when services are down
- ✅ Production-ready error handling

## 🧪 **Testing Mode (Direct On-Chain)**

**For Testing:** Force direct on-chain placement bypassing all intermediaries

```bash
# Testing mode - bypasses all fallbacks, goes direct to chain
export FORCE_DIRECT_ONCHAIN=true
python run_swift_mm_complete.py
```

**Testing Behavior:**
- 🔥 **Bypasses JIT, Swift API, all intermediaries**
- 🔥 **Goes directly to DriftPy on-chain placement**
- 🔥 **Clear logging shows testing mode is active**
- 🔥 **No code changes required**

## 🔧 **Configuration**

### **Environment Variables**

| Variable | Default | Purpose |
|----------|---------|---------|
| `FORCE_DIRECT_ONCHAIN` | `false` | Enable direct on-chain testing mode |

### **Runtime Control**

```bash
# Enable direct testing mode
export FORCE_DIRECT_ONCHAIN=true

# Disable direct testing mode (back to normal routing)
export FORCE_DIRECT_ONCHAIN=false
# OR
unset FORCE_DIRECT_ONCHAIN
```

## 📊 **Logging Indicators**

### **Normal Operation**
```
🎯 Routing order through JIT service: buy 1.0000 SOL @ $150.00
🚀 Placing order via Swift API (with signature fixes): buy 1.0000 SOL @ $150.00
🔄 Final fallback: DriftPy direct placement
```

### **Testing Mode**
```
🔥 TESTING MODE: Forcing DIRECT ON-CHAIN placement (bypassing all fallbacks)
  Set FORCE_DIRECT_ONCHAIN=false to enable normal routing
  Side: buy | Price: $150.0000 | Size: 1.0000 SOL
```

## 🎭 **Use Cases**

### **Development & Testing**
```bash
# Test direct on-chain functionality
export FORCE_DIRECT_ONCHAIN=true
python run_swift_mm_complete.py

# Test fallback behavior (simulate Swift failure)
# Stop your sidecar, then run normally
unset FORCE_DIRECT_ONCHAIN
python run_swift_mm_complete.py
```

### **Production Deployment**
```bash
# Always run without override for full reliability
python run_swift_mm_complete.py
```

### **Debugging**
```bash
# Force direct mode to isolate DriftPy issues
export FORCE_DIRECT_ONCHAIN=true
python run_swift_mm_complete.py

# Normal mode to test full routing stack
unset FORCE_DIRECT_ONCHAIN
python run_swift_mm_complete.py
```

## 🔄 **Migration Benefits**

### **Before (Broken)**
- ❌ Only direct on-chain placement
- ❌ No fallback reliability  
- ❌ Code changes required for testing
- ❌ Single point of failure

### **After (Fixed)**
- ✅ Smart routing with fallbacks for everyday use
- ✅ Clean testing override via environment variable
- ✅ No code changes needed for different modes
- ✅ Production-ready reliability

## 🚨 **Important Notes**

1. **Never commit with `FORCE_DIRECT_ONCHAIN=true`** - This should only be used for local testing
2. **Production should always use normal routing** - The fallback chain ensures reliability
3. **Testing mode logs clearly** - You'll always know when bypassing fallbacks
4. **Environment variable is checked at runtime** - No restarts needed to switch modes

---

**This approach gives you the best of both worlds: reliable everyday operation with easy testing capability.**
