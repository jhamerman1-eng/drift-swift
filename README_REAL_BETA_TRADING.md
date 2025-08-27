# 🚀 REAL Beta Trading Setup - Drift Protocol

**IMPORTANT**: This document is for REAL trading on beta.drift.trade. **NO SIMULATION** - actual orders will be placed on the blockchain!

## ⚠️ CRITICAL WARNINGS

- **REAL ORDERS**: This will place actual trades on Drift Protocol devnet
- **REAL SOL SPENT**: You need funded wallets with SOL for gas fees
- **BETA ENVIRONMENT**: Using devnet - trades are real but with test conditions
- **MONITOR CLOSELY**: Keep an eye on your positions and wallet balance

## 📋 Prerequisites

### Required Software
- Python 3.8+
- Solana CLI tools
- Git

### Required Packages
```bash
pip install driftpy solana solders anchorpy
```

## 🚀 Step-by-Step Setup

### Step 1: Wallet Setup
```bash
# Create and fund your beta wallet
python setup_beta_wallet.py
```

This will:
- Create `.beta_dev_wallet.json` if it doesn't exist
- Display your wallet address
- Provide funding instructions

### Step 2: Fund Your Wallet
1. **Copy your wallet address** from the setup output
2. **Go to [Solana Faucet](https://faucet.solana.com)**
3. **Select "Devnet" network**
4. **Paste your wallet address**
5. **Request 1-2 SOL** (sufficient for beta testing)
6. **Wait 30-60 seconds** for confirmation

### Step 3: Verify Setup
```bash
# Verify your balance
python setup_beta_wallet.py
```

### Step 4: Start REAL Beta Trading
```bash
# Launch the hedge bot with REAL orders
python launch_hedge_beta_real.py
```

## 📊 What Happens During Real Trading

### Bot Behavior
- **REAL ORDERS**: Places actual perpetual futures orders on Drift Protocol
- **RISK MANAGEMENT**: Uses conservative limits (max $50 inventory)
- **POSITION MONITORING**: Tracks real positions on beta.drift.trade
- **BALANCE CHECKS**: Verifies SOL balance every 5 iterations

### Monitoring
- **Live Dashboard**: https://beta.drift.trade
- **Log Files**: `hedge_beta_real.log`
- **Console Output**: Real-time status updates

### Risk Controls
- Maximum inventory: $50 USD
- Conservative slippage: 5 bps IOC, 3 bps passive
- Urgency threshold: 0.8 (high confidence required)
- Balance checks every 5 iterations

## 🛡️ Safety Features

### Circuit Breakers
- Balance verification before trading
- Error handling with extended delays
- Graceful shutdown on interruption

### Wallet Protection
- Minimum balance checks (0.01 SOL)
- Clear funding instructions
- No trading without sufficient balance

## 📈 Expected Behavior

### Successful Run
```
[LAUNCH] Starting REAL Hedge Bot for beta.drift.trade
[INIT] Initializing REAL Drift client for beta.drift.trade...
[SUCCESS] REAL Drift client initialized and ready for beta trading!
[SUCCESS] Connected to beta.drift.trade - READY FOR REAL ORDERS!
[TRADE] Starting REAL beta hedge iteration #1
[STATUS] REAL Beta Hedge Iteration Status:
   Net Exposure: $12.50
   Total Volume: $12.50
   Active Positions: 1
   Risk State: Drawdown 0.00%
```

### Error Conditions
- **Insufficient Balance**: Bot stops with funding instructions
- **Connection Issues**: Automatic retry with fallback
- **DriftPy Errors**: Clear error messages with troubleshooting steps

## 🔧 Troubleshooting

### "Wallet keypair not found"
```bash
# Recreate wallet
python setup_beta_wallet.py
```

### "Insufficient SOL balance"
```bash
# Fund wallet at https://faucet.solana.com
# Then verify with:
python setup_beta_wallet.py
```

### "DriftPy not available"
```bash
# Install required packages
pip install driftpy solana solders anchorpy
```

### "RPC endpoint unreachable"
- Check internet connection
- Verify Solana devnet status
- Try again in a few minutes

## 📊 Performance Monitoring

### Key Metrics to Watch
- **Net Exposure**: Should stay under $50
- **Error Count**: Should be 0 for clean runs
- **Iteration Rate**: ~6 iterations per minute
- **SOL Balance**: Monitor gas fee consumption

### Log Analysis
```bash
# View recent activity
tail -f hedge_beta_real.log

# Search for errors
grep "ERROR" hedge_beta_real.log

# Count successful iterations
grep "REAL beta hedge iteration" hedge_beta_real.log | wc -l
```

## 🛑 Emergency Stop

### Immediate Stop
```bash
# Press Ctrl+C in the terminal running the bot
```

### Manual Position Closure
1. Go to https://beta.drift.trade
2. Connect your wallet
3. Manually close any open positions
4. Withdraw remaining SOL if needed

## 🔄 Restarting After Interrupt

### Clean Restart
```bash
# Simply run again - bot will reconnect and continue
python launch_hedge_beta_real.py
```

### After Wallet Funding
```bash
# Verify balance first
python setup_beta_wallet.py

# Then restart trading
python launch_hedge_beta_real.py
```

## 📈 Success Criteria

- [ ] Bot starts without errors
- [ ] Wallet balance verified
- [ ] Orders appear on beta.drift.trade
- [ ] No repeated errors in logs
- [ ] Positions managed according to risk limits
- [ ] Clean shutdown on interruption

## 🎯 Next Steps

### After Successful Test
- Monitor bot behavior for 30+ minutes
- Adjust risk parameters if needed
- Consider increasing position sizes for production

### For Production Use
- Use dedicated wallet with more SOL
- Implement additional monitoring
- Consider multiple bot instances

---

**🚨 FINAL REMINDER**: This places REAL orders on Drift Protocol. Monitor your positions and wallet balance closely!
