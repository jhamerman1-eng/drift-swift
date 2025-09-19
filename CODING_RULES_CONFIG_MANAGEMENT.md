# 📋 CODING RULES: Configuration Management

**Effective Date:** September 16, 2025  
**Priority:** CRITICAL  
**Scope:** All Swift/Sidecar Configuration Code  

## 🚨 **RULE #1: NO HARDCODED URLs**

### **PROHIBITED PATTERNS** ❌
```python
# NEVER do this - hardcoded URLs
self.sidecar_url = "http://localhost:8787"
self.swift_url = "https://master.swift.drift.trade"
base_url = "https://app.drift.trade"

# NEVER do this - environment-specific hardcoding
if environment == "local":
    url = "http://localhost:8787"
elif environment == "devnet":
    url = "https://master.swift.drift.trade"
```

### **REQUIRED PATTERNS** ✅
```python
# ALWAYS do this - use centralized config
swift_config = self.env_config.get_swift_config()
self.sidecar_url = swift_config["base_url"]

# ALWAYS do this - get from configuration system
env_config = get_environment_config()
swift_config = env_config.get_swift_config()
```

## 🎯 **RULE #2: Centralized Configuration**

### **Single Source of Truth**
- **File:** `configs/environments.yaml`
- **Manager:** `libs/config/environment.py`
- **Usage:** Always through `env_config.get_swift_config()`

### **Configuration Access Pattern**
```python
# ✅ CORRECT - Standard pattern for all components
from libs.config.environment import get_environment_config

env_config = get_environment_config()
swift_config = env_config.get_swift_config()
base_url = swift_config["base_url"]
```

## 🔍 **RULE #3: Code Review Requirements**

### **Mandatory Checks**
- [ ] No hardcoded URLs in Swift/sidecar initialization
- [ ] All URLs obtained through `get_swift_config()`
- [ ] No environment-specific URL logic outside config files
- [ ] Configuration comments preserved

### **Search Commands for Review**
```bash
# Check for hardcoded URLs
grep -r "localhost:8787" --include="*.py" .
grep -r "master.swift.drift.trade" --include="*.py" .
grep -r "app.drift.trade" --include="*.py" .

# Should only return config files, NOT code files
```

## 📝 **RULE #4: Documentation Requirements**

### **Code Comments**
- Add warning comments for configuration-critical sections
- Reference this document in configuration initialization
- Explain why centralized config is used

### **Example Comment Block**
```python
# ========================================================================
# CRITICAL CONFIGURATION - Use centralized config only
# See: CODING_RULES_CONFIG_MANAGEMENT.md
# NEVER hardcode URLs - always use swift_config["base_url"]
# ========================================================================
```

## 🚨 **RULE #5: Regression Prevention**

### **Common Regression Patterns**
1. **Quick fixes** that hardcode URLs "temporarily"
2. **Copy-paste code** from old patterns
3. **Environment-specific logic** that bypasses config
4. **Missing imports** that lead to hardcoding fallbacks

### **Prevention Strategies**
- Keep warning comments in place
- Regular grep searches for hardcoded patterns
- Code review checklist enforcement
- Configuration validation in CI/CD

## 🔧 **RULE #6: Exception Handling**

### **When Configuration Fails**
```python
# ✅ CORRECT - Fail fast with clear error
try:
    swift_config = env_config.get_swift_config()
    base_url = swift_config["base_url"]
except Exception as e:
    logger.error(f"Failed to load Swift configuration: {e}")
    raise ConfigurationError("Swift configuration required")

# ❌ WRONG - Fallback to hardcoded URL
try:
    swift_config = env_config.get_swift_config()
    base_url = swift_config["base_url"]
except:
    base_url = "http://localhost:8787"  # NEVER DO THIS
```

## 📋 **RULE #7: Environment Variables**

### **Acceptable Pattern**
```python
# ✅ ACCEPTABLE - Environment variable override for config
api_key = config.get("swift_api_key") or os.getenv("SWIFT_API_KEY", "")
timeout = config.get("timeout") or int(os.getenv("SWIFT_TIMEOUT", "30"))
```

### **Unacceptable Pattern**
```python
# ❌ WRONG - Environment variable for URLs
base_url = os.getenv("SWIFT_URL", "http://localhost:8787")
```

## 🎯 **ENFORCEMENT**

### **Pre-commit Checks**
1. Run configuration validation script
2. Search for hardcoded URL patterns
3. Verify config file accessibility
4. Test all environment configurations

### **Review Process**
- All Swift/sidecar changes require configuration review
- Document any new configuration requirements
- Update this rules document if patterns change

---

**These rules prevent the recurring hardcoded URL regression issue and ensure maintainable configuration management.**


