# 🚨 CRITICAL FIX: Eliminate Hardcoded URL Configuration

**Date:** September 16, 2025  
**Priority:** HIGH - Prevents Regression  
**Component:** Swift Sidecar URL Configuration  

## 🎯 **Problem Statement**

The codebase had a recurring issue where hardcoded URLs were being used instead of the centralized configuration system, specifically:

```python
# ❌ WRONG - Hardcoded URL (keeps regressing)
if self.env_config.use_local_sidecar():
    self.sidecar_url = "http://localhost:8787"  # HARDCODED!
```

## ✅ **Solution Implemented**

**Fixed in:** `run_swift_mm_complete.py` lines 778-787

```python
# ✅ CORRECT - Always use centralized config
swift_config = self.env_config.get_swift_config()
self.sidecar_url = swift_config["base_url"]  # ALWAYS use config
```

## 🔧 **Technical Details**

### **Root Cause**
- Previous code ignored `environments.yaml` configuration for local environment
- Hardcoded `localhost:8787` instead of using `swift_config["base_url"]`
- Created inconsistency between configuration system and actual usage

### **Fix Implementation**
1. **Removed hardcoded URL assignment**
2. **Always use `swift_config["base_url"]`** from centralized config
3. **Added comprehensive warning comments** to prevent regression
4. **Maintains same functionality** but driven by configuration

### **Configuration Sources**
- **File:** `configs/environments.yaml`
- **Local:** `base_url: "http://localhost:8787"`
- **Devnet:** `base_url: "https://master.swift.drift.trade"`
- **Mainnet:** `base_url: "https://app.drift.trade"`

## 🚨 **CRITICAL: Regression Prevention**

### **Warning Signs of Regression**
- Any hardcoded URLs in Swift/sidecar initialization
- Code that bypasses `swift_config["base_url"]`
- Environment-specific URL assignment outside of `environments.yaml`

### **Code Review Checklist**
- [ ] No hardcoded URLs in Swift initialization
- [ ] All URLs come from `env_config.get_swift_config()`
- [ ] No environment-specific URL logic outside config files
- [ ] Configuration comments are preserved

## 📋 **Verification Steps**

1. **Check Configuration Usage:**
   ```python
   swift_config = self.env_config.get_swift_config()
   self.sidecar_url = swift_config["base_url"]  # ✅ CORRECT
   ```

2. **Verify No Hardcoded URLs:**
   ```bash
   grep -r "localhost:8787" --include="*.py" .
   # Should only return environment config files, not code files
   ```

3. **Test All Environments:**
   ```bash
   export DRIFT_ENVIRONMENT=local && python run_swift_mm_complete.py
   export DRIFT_ENVIRONMENT=devnet && python run_swift_mm_complete.py
   ```

## 🎯 **Benefits Achieved**

1. **Consistency:** All environments use centralized configuration
2. **Maintainability:** Single source of truth for URLs
3. **Flexibility:** Easy to change URLs without code modification
4. **Reliability:** Prevents configuration drift and inconsistencies

## 🔄 **Future Maintenance**

- **NEVER** hardcode URLs in Swift/sidecar initialization
- **ALWAYS** use `swift_config["base_url"]` from centralized config
- **PRESERVE** the warning comments in the code
- **UPDATE** this document if configuration structure changes

---

**This fix addresses a recurring regression issue. The comprehensive documentation and code comments should prevent future reversions to hardcoded URL patterns.**


