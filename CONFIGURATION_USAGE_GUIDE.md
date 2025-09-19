# 🔒 LOCKED PRODUCTION CONFIGURATION GUIDE

## 🚨 CRITICAL NOTICE

**This configuration is LOCKED and VERIFIED for production use.**

- **DO NOT modify** `production_config_locked.py`
- **DO NOT modify** settings without approval
- **Test all changes** in devnet first
- **Document all changes** before implementation

## 🌐 ENVIRONMENT SWITCHING

### For DEVNET (Beta.Drift) - Safe Testing:
```bash
export DRIFT_ENV=devnet
python production_config_locked.py
```

### For MAINNET (App.Drift) - Production/Real Funds:
```bash
export DRIFT_ENV=mainnet
python production_config_locked.py
```

## 📋 LOCKED SETTINGS SUMMARY

### Network Configuration:
- **Devnet RPC**: `https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494`
- **Mainnet RPC**: `https://mainnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494`
- **WebSocket**: Uses corresponding Helius WebSocket endpoints

### Wallet Configuration:
- **File**: `.valid_wallet.json` (LOCKED)
- **Public Key**: `A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW` (LOCKED)
- **Status**: ✅ VERIFIED WORKING

### Trading Parameters:
- **Order Size**: 0.01 SOL (LOCKED)
- **Max Orders/Side**: 1 (LOCKED)
- **Spread**: 8 basis points (LOCKED)
- **Max Order Size**: $1,000 USD (LOCKED)

### Risk Management:
- **Daily Loss Limit**: $5,000 USD (LOCKED)
- **Max Position**: 120 SOL (LOCKED)
- **Test Mode**: False (LOCKED)
- **Post Only**: True (LOCKED)

### Performance Settings:
- **Tick Interval**: 100ms (LOCKED)
- **Stats Interval**: 5 seconds (LOCKED)
- **Max Consecutive Errors**: 10 (LOCKED)

## 🚀 DEPLOYMENT INSTRUCTIONS

### Step 1: Environment Setup
```bash
# For devnet testing:
export DRIFT_ENV=devnet

# For mainnet production:
export DRIFT_ENV=mainnet
```

### Step 2: Configuration Validation
```bash
python production_config_locked.py
```
Expected output shows:
- ✅ Environment correctly set
- ✅ All validations pass
- ✅ Ready for deployment message

### Step 3: Bot Deployment
```bash
# Using the locked configuration
python run_swift_mm_complete.py
```

## ⚠️ SAFETY CHECKLIST

### Before Devnet Testing:
- [ ] Environment set to `DRIFT_ENV=devnet`
- [ ] Wallet file `.valid_wallet.json` exists
- [ ] Configuration validation passes
- [ ] No real funds in wallet

### Before Mainnet Production:
- [ ] Environment set to `DRIFT_ENV=mainnet`
- [ ] Wallet has sufficient SOL for trading
- [ ] All risk limits verified
- [ ] Emergency stop procedures documented
- [ ] Backup wallet secured
- [ ] Monitoring systems active

## 🔧 MAINTENANCE PROCEDURES

### Configuration Changes:
1. **NEVER modify** `production_config_locked.py` directly
2. Create feature branch for changes
3. Test changes in devnet environment
4. Document all changes with rationale
5. Get approval before merging

### Emergency Procedures:
1. Set `DRIFT_ENV=devnet` to switch to safe testing
2. Use emergency stop if needed
3. Check logs for error details
4. Contact support if issues persist

## 📊 MONITORING CHECKLIST

### During Operation:
- [ ] Bot logs show successful connections
- [ ] P&L tracking is active
- [ ] Risk limits are respected
- [ ] Performance metrics within expected ranges
- [ ] No consecutive error warnings

### Daily Checks:
- [ ] Configuration hasn't been modified
- [ ] Wallet balance is sufficient
- [ ] Risk limits are appropriate
- [ ] Backup systems are functional

## 🚨 EMERGENCY CONTACTS

If you encounter issues:
1. Switch to devnet immediately: `export DRIFT_ENV=devnet`
2. Check configuration: `python production_config_locked.py`
3. Review logs for error details
4. Contact development team if needed

## 📝 CHANGE LOG

### Version 1.0.0 - Initial Locked Configuration
- ✅ Verified wallet configuration
- ✅ Locked all production settings
- ✅ Implemented environment switching
- ✅ Added comprehensive validation
- ✅ Production deployment ready

---

**🔒 CONFIGURATION LOCKED - DO NOT MODIFY WITHOUT APPROVAL**

**Last Verified**: September 13, 2025
**Environment**: Devnet & Mainnet Ready
**Status**: ✅ PRODUCTION DEPLOYMENT READY


