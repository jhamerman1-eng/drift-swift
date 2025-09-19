# MM Bot Fix Verification Guide

## 🚨 CRITICAL ISSUE: MM Bot Not Running Properly

The MM bot appears to start but crashes after 17 seconds with JSON serialization errors. This means **no actual market making is happening**.

## 📋 Verification Steps

### 1. Quick Health Check
```bash
python test_mm_bot_health.py
```
This runs all verification tests automatically and gives you a complete health report.

### 2. Individual Tests

#### Basic Verification
```bash
python verify_mm_bot_fix.py
```

#### Continuous Monitoring
```bash
python monitor_mm_bot.py
```
Keep this running in a separate terminal while the bot operates.

### 3. Manual Testing

#### Start Bot with Logging
```bash
cd drift-bots
python run_mm_bot.py --env devnet --cfg ../configs/core/drift_client.yaml > ../mm_bot.log 2>&1 &
```

#### Monitor in Real-time
```bash
# Terminal 1: Run bot
python run_mm_bot.py --env devnet --cfg configs/core/drift_client.yaml

# Terminal 2: Monitor logs
tail -f mm_bot.log | grep -E "Order|Error|JSON"
```

## ✅ SUCCESS CRITERIA

### Bot should show:
- ✅ **Runtime > 1 minute** (not just 17 seconds)
- ✅ **"Order placed" messages** every few seconds
- ✅ **No JSON serialization errors**
- ✅ **Continuous operation** without crashes

### Expected Log Output:
```
2025-01-XX XX:XX:XX | INFO | Order placed: buy 0.05 SOL @ $150.25
2025-01-XX XX:XX:XX | INFO | Order placed: sell 0.05 SOL @ $150.35
2025-01-XX XX:XX:XX | INFO | Spread updated: 5.0 bps
```

## 🔍 FAILURE INDICATORS

### 🚨 Critical Issues:
- ❌ Bot crashes within 30 seconds
- ❌ JSON serialization errors
- ❌ "TypeError: Object of type bytes is not JSON serializable"
- ❌ No order placement messages

### ⚠️ Warning Signs:
- ⚠️ Bot runs but places no orders
- ⚠️ Frequent error messages
- ⚠️ Memory usage keeps growing

## 🛠️ TROUBLESHOOTING

### If bot still crashes:
1. **Check line 466** in your MM bot code
2. **Examine the payload** being sent to Swift
3. **Consider alternative serialization** (pickle, base64, etc.)
4. **Test with simpler payload** first

### If bot runs but doesn't trade:
1. **Check wallet balance** and permissions
2. **Verify RPC endpoints** are accessible
3. **Check market data** is being received
4. **Review spread calculations**

## 📊 MONITORING TOOLS

### Real-time Health Monitor
```bash
python monitor_mm_bot.py
```
Shows live status including:
- Orders placed
- Error counts
- JSON errors
- Runtime duration
- Last order time

### Log Analysis
```bash
# Count errors
grep -i "error\|exception" mm_bot.log | wc -l

# Count orders
grep -i "order" mm_bot.log | wc -l

# Check for JSON errors
grep -i "json" mm_bot.log | grep -i "error\|serializable"
```

## 🎯 QUICK VERIFICATION

Run this one-liner to check if the fix worked:
```bash
python -c "
import subprocess, time
proc = subprocess.Popen(['python', 'drift-bots/run_mm_bot.py', '--env', 'devnet', '--cfg', 'configs/core/drift_client.yaml'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(30)
if proc.poll() is None:
    print('✅ SUCCESS: Bot survived 30 seconds')
    proc.terminate()
else:
    print('❌ FAILED: Bot crashed within 30 seconds')
"
```

## 📞 NEXT STEPS

1. **Apply the JSON serialization fix**
2. **Run verification tests**
3. **Start continuous monitoring**
4. **Let bot run for several minutes**
5. **Verify continuous order placement**

**The key is: Bot must run > 1 minute AND place orders continuously.**

