# 📋 CODING RULES: Wallet Corruption Prevention

**Effective Date:** September 16, 2025  
**Priority:** CRITICAL  
**Scope:** All Wallet Loading Code  

## 🚨 **RULE #1: Wallet Corruption Detection**

### **Error Pattern Recognition** ⚠️
When you encounter this error:
```
ValueError: signature error: Cannot decompress Edwards point
```

**IMMEDIATE ACTION REQUIRED:**
1. **Stop all operations** - This indicates corrupted wallet data
2. **Run repair script** - Use `repair_devnet_wallet.py` 
3. **Verify fix** - Test wallet loading before continuing
4. **Update bug registry** - Mark as resolved with repair details

### **Root Cause Analysis**
- **Primary Cause**: Corrupted 64-byte keypair (invalid public key portion)
- **Secondary Causes**: 
  - Manual wallet file edits
  - JSON parsing with trailing whitespace
  - File corruption during operations
  - Incorrect keypair generation

## 🔧 **RULE #2: Wallet Repair Process**

### **Standard Repair Script**
```bash
# For .devnet_wallet.json corruption
python repair_devnet_wallet.py

# For other wallet files, adapt the script:
# 1. Change path to target wallet file
# 2. Run repair process
# 3. Verify with test command
```

### **Repair Script Pattern**
```python
# Extract secret key (first 32 bytes)
sk = b[:32]

# Derive correct public key from secret key  
signing_key = SigningKey(sk)
pub = signing_key.verify_key.encode()

# Rebuild the 64-byte keypair
fixed = sk + pub
```

## 🧪 **RULE #3: Mandatory Wallet Validation**

### **Pre-commit Checks**
```bash
# Always validate wallet before bot startup
python -c "from solders.keypair import Keypair; import json; data = json.load(open('.devnet_wallet.json')); kp = Keypair.from_bytes(bytes(data)); print(f'✅ Wallet valid: {kp.pubkey()}')"
```

### **Unit Test Requirements**
- **Every wallet loading function** must have validation tests
- **Test both valid and corrupted** keypair scenarios
- **Verify error handling** for Edwards point decompression failures
- **Test repair script** functionality

## 📝 **RULE #4: Code Implementation**

### **Wallet Loading Functions**
```python
async def _load_wallet(self):
    """Load wallet with corruption detection and repair"""
    try:
        # Standard wallet loading logic
        keypair_bytes = bytes(wallet_data)
        self.keypair = Keypair.from_bytes(keypair_bytes)
        
    except ValueError as e:
        if "Cannot decompress Edwards point" in str(e):
            logger.error("🚨 WALLET CORRUPTION DETECTED")
            logger.error("🔧 Run repair script: python repair_devnet_wallet.py")
            raise WalletCorruptionError("Wallet corrupted - run repair script")
        else:
            raise
```

### **Error Classification**
```python
class WalletCorruptionError(Exception):
    """Raised when wallet keypair is corrupted"""
    pass

def is_edwards_point_error(error: Exception) -> bool:
    """Check if error is Edwards point decompression failure"""
    return "Cannot decompress Edwards point" in str(error)
```

## 🔄 **RULE #5: Prevention Strategies**

### **File Handling**
- **Never manually edit** wallet JSON files
- **Always use proper JSON formatting** (no trailing whitespace)
- **Validate after any file operations**
- **Backup wallet files** before modifications

### **Development Workflow**
1. **Before coding**: Validate wallet integrity
2. **During development**: Run unit tests regularly
3. **After changes**: Verify wallet loading works
4. **Before deployment**: Run full wallet validation suite

## 📊 **RULE #6: Monitoring and Alerting**

### **Log Patterns to Watch**
```
ERROR | Failed to load wallet: signature error: Cannot decompress Edwards point
ERROR | Wallet file: .devnet_wallet.json
ERROR | Wallet data keys: array format
```

### **Automated Detection**
- **CI/CD Pipeline**: Include wallet validation tests
- **Health Checks**: Verify wallet loading in startup
- **Error Monitoring**: Alert on Edwards point errors

## 🎯 **ENFORCEMENT**

### **Code Review Checklist**
- [ ] Wallet loading has proper error handling
- [ ] Edwards point errors are specifically caught
- [ ] Repair script is referenced in error messages
- [ ] Unit tests cover corruption scenarios
- [ ] Wallet validation is performed at startup

### **Testing Requirements**
- [ ] Test with valid 64-byte keypair
- [ ] Test with corrupted 64-byte keypair
- [ ] Test with 32-byte secret key
- [ ] Test repair script functionality
- [ ] Test error message clarity

---

**This rule prevents wallet corruption issues and ensures quick resolution when they occur.**


