# 🧠 MEMORY: Wallet Corruption Fix

**Memory ID:** WALLET-CORRUPTION-001  
**Created:** September 16, 2025  
**Priority:** CRITICAL  

## 🚨 **Error Pattern**

**Error Message:**
```
ValueError: signature error: Cannot decompress Edwards point
```

**Context:**
- Occurs during wallet loading in `run_swift_mm_complete.py` line 1157
- Affects bot initialization
- Bug ID: ERR-6E457E46

## 🔍 **Root Cause**

**Corrupted 64-byte keypair:**
- ✅ **Secret key portion (first 32 bytes)**: Valid
- ❌ **Public key portion (last 32 bytes)**: Corrupted
- **Result**: `Keypair.from_bytes()` fails with Edwards point decompression error

## 🔧 **Solution**

### **Immediate Fix**
```bash
# Run repair script
python repair_devnet_wallet.py
```

### **Repair Process**
1. **Extract secret key** (first 32 bytes from corrupted keypair)
2. **Derive correct public key** using `nacl.signing.SigningKey`
3. **Rebuild 64-byte keypair** with correct public key
4. **Verify fix** with test command

### **Code Pattern**
```python
# Extract secret key (first 32 bytes)
sk = b[:32]

# Derive correct public key from secret key
signing_key = SigningKey(sk)
pub = signing_key.verify_key.encode()

# Rebuild the 64-byte keypair
fixed = sk + pub
```

## 🧪 **Validation**

### **Test Command**
```bash
python -c "from solders.keypair import Keypair; import json; data = json.load(open('.devnet_wallet.json')); kp = Keypair.from_bytes(bytes(data)); print(f'✅ Wallet valid: {kp.pubkey()}')"
```

### **Unit Tests**
- Run `tests/test_wallet_validation.py` for comprehensive testing
- Tests cover valid keypairs, corruption detection, and repair functionality

## 📋 **Prevention**

### **Common Causes**
- Manual wallet file edits
- JSON parsing with trailing whitespace
- File corruption during operations
- Incorrect keypair generation

### **Prevention Measures**
- Always use proper JSON formatting (no trailing whitespace)
- Validate keypairs after any manual edits
- Use repair script if corruption is detected
- Run unit tests regularly

## 📁 **Related Files**

- **Repair Script**: `repair_devnet_wallet.py`
- **Unit Tests**: `tests/test_wallet_validation.py`
- **Coding Rules**: `CODING_RULES_WALLET_CORRUPTION.md`
- **Bug Registry**: `logs/bug_registry_active.json` (ERR-6E457E46)

## 🎯 **Quick Reference**

**When you see this error:**
1. **Stop** - Don't continue with corrupted wallet
2. **Run** - `python repair_devnet_wallet.py`
3. **Verify** - Test wallet loading
4. **Update** - Mark bug as resolved in registry

**This memory ensures quick resolution of wallet corruption issues.**
