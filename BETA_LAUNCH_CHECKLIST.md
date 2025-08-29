# 🚀 Beta.Drift.Trade Launch Checklist

## Pre-Launch Safety Checks

### 🔑 Wallet & Authentication
- [ ] Wallet keypair exists and is readable
- [ ] Wallet has sufficient SOL for gas fees (~0.01 SOL minimum)
- [ ] Wallet address is correctly configured in beta_environment_config.yaml
- [ ] Backup of wallet keypair is stored securely

### 🌐 Network Configuration
- [ ] RPC endpoint (api.mainnet-beta.solana.com) is reachable
- [ ] Swift API endpoint (swift.drift.trade) is accessible
- [ ] Network latency is acceptable (< 500ms)
- [ ] DNS resolution works correctly

### ⚙️ Bot Configuration
- [ ] All required Python packages are installed
- [ ] beta_environment_config.yaml exists and is valid YAML
- [ ] Risk management settings are appropriate for your capital
- [ ] Bot-specific parameters are tuned for beta environment
- [ ] Mock mode is enabled for initial testing

### 🛡️ Risk Management
- [ ] Circuit breaker is enabled and thresholds are set
- [ ] Portfolio rails are configured (soft stop, pause, circuit breaker)
- [ ] Crash sentinel v2 is enabled with appropriate sigma thresholds
- [ ] Maximum position sizes are within acceptable limits
- [ ] Maximum inventory exposure is set appropriately

### 📊 Monitoring & Health
- [ ] Prometheus metrics port is available
- [ ] Health endpoints are enabled
- [ ] Grafana dashboard is accessible (optional)
- [ ] Log files are writable
- [ ] Alerting system is configured (optional)

## Launch Steps

### Step 1: Environment Preparation
```bash
# 1. Ensure you're in the project directory
cd /path/to/drift-swift

# 2. Create your wallet (if not exists)
solana-keygen new --outfile .beta_wallet.json

# 3. Fund your wallet with devnet SOL (for testing)
# Visit: https://faucet.solana.com/

# 4. Verify wallet balance
solana balance .beta_wallet.json
```

### Step 2: Configuration Setup
```bash
# 1. Copy and edit beta configuration
cp beta_environment_config.yaml my_beta_config.yaml

# 2. Edit wallet path in my_beta_config.yaml
# Change: maker_keypair_path: ".beta_wallet.json"

# 3. Adjust risk settings based on your capital
# Recommended starting values:
# max_position_size_usd: 25.0
# max_inventory_usd: 100.0
```

### Step 3: Dry Run Test
```bash
# Always test first with dry-run!
python launch_beta_bots.py --dry-run --config my_beta_config.yaml

# Or using quick scripts:
start_beta_bots.bat --dry-run
./start_beta_bots.sh --dry-run
```

### Step 4: Mock Mode Testing
```bash
# Test with mock client (no real trades)
python launch_beta_bots.py --config my_beta_config.yaml

# Verify:
# - Bots start successfully
# - Metrics are generated: http://localhost:9109/metrics
# - Health endpoints work: http://localhost:9109/health
# - No errors in logs
```

### Step 5: Live Trading (Use Extreme Caution!)
```bash
# ONLY when you're confident in the setup:
python launch_beta_bots.py --config my_beta_config.yaml --real

# Immediate monitoring:
# - Watch logs for any errors
# - Monitor metrics dashboard
# - Check wallet balance periodically
# - Be ready to stop bots with Ctrl+C
```

## Post-Launch Monitoring

### Real-time Health Checks
```bash
# Health status
curl -s localhost:9109/health

# Readiness status
curl -s localhost:9109/ready

# Current metrics
curl -s localhost:9109/metrics | grep -E "(orchestrator_up|crash_sentinel_state|portfolio_rails_state)"
```

### What to Monitor Closely
- [ ] Orchestrator stays "up" (orchestrator_up = 1)
- [ ] No circuit breaker triggers (crash_sentinel_state < 2)
- [ ] Portfolio rails remain normal (portfolio_rails_state = 0)
- [ ] Bot iteration rates are reasonable (not too high/low)
- [ ] No repeated errors in logs
- [ ] Wallet balance doesn't decrease unexpectedly fast

### Emergency Stop Procedures
If anything seems wrong:

1. **Immediate Stop**: Press `Ctrl+C` in the bot terminal
2. **Check Logs**: Review logs for error details
3. **Verify Positions**: Check if any positions were opened
4. **Manual Closure**: Close any open positions manually if needed

## Troubleshooting Common Issues

### ❌ "Wallet keypair not found"
```bash
# Solution: Create wallet
solana-keygen new --outfile .beta_wallet.json

# Or update config path
# Edit beta_environment_config.yaml
# maker_keypair_path: "path/to/your/wallet.json"
```

### ❌ "RPC endpoint unreachable"
```bash
# Check network connectivity
ping api.mainnet-beta.solana.com

# Verify endpoint
curl -s https://api.mainnet-beta.solana.com -w "%{http_code}"
```

### ❌ "Insufficient SOL balance"
```bash
# Check balance
solana balance .beta_wallet.json

# Get devnet SOL from faucet
# Visit: https://faucet.solana.com/
```

### ❌ "Port already in use"
```bash
# Find process using port 9109
netstat -ano | findstr :9109

# Kill the process
taskkill /PID <PID_NUMBER> /F
```

## Success Criteria

- [ ] All bots start without errors
- [ ] Metrics are being generated
- [ ] Health endpoints return "healthy"
- [ ] No circuit breaker triggers in first 30 minutes
- [ ] Bot iteration rates are stable
- [ ] Logs show normal operation (no repeated errors)

## 📞 Support

If you encounter issues:

1. Check this checklist first
2. Review bot logs in `logs/` directory
3. Verify configuration in `beta_environment_config.yaml`
4. Test with `--dry-run` first
5. Check metrics at `http://localhost:9109/metrics`

---

**🎯 Remember**: Beta testing is high-risk. Start small, monitor closely, and be ready to stop immediately if anything seems off!
