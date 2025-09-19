# 🚀 **DRIFT SWIFT v1.0.0 DEPLOYMENT GUIDE**

## **PRODUCTION DEPLOYMENT PROCEDURES**

This guide provides step-by-step instructions for deploying Drift Swift v1.0.0 in production environments.

---

## **📋 PRE-DEPLOYMENT CHECKLIST**

### **System Requirements**
- [ ] Python 3.8+ installed
- [ ] Solana CLI tools installed and configured
- [ ] Valid Solana keypair with sufficient collateral
- [ ] Stable internet connection (>100 Mbps recommended)
- [ ] Linux/Windows server with 4GB+ RAM

### **Environment Setup**
- [ ] DRIFT_ENVIRONMENT variable set (`devnet` or `mainnet`)
- [ ] KEYPAIR_PATH pointing to valid Solana keypair
- [ ] RPC endpoint configured and tested
- [ ] Swift API access validated

### **Security Validation**
- [ ] Keypair stored securely with appropriate permissions
- [ ] Environment variables properly configured
- [ ] No sensitive data in logs or config files
- [ ] Network security policies in place

### **Financial Preparation**
- [ ] Sufficient USDC collateral deposited (minimum $500 recommended)
- [ ] Risk limits configured appropriately
- [ ] Position limits set based on risk tolerance
- [ ] Emergency procedures documented

---

## **🛠️ INSTALLATION PROCEDURE**

### **Step 1: Download Release**
```bash
# Navigate to project directory
cd /path/to/drift-swift

# Verify release files
ls releases/v1.0.0-production/
# Should contain: src/, docs/, tests/, configs/, README.md
```

### **Step 2: Install Dependencies**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Verify critical packages
python -c "import driftpy, anchorpy, solders; print('Dependencies OK')"
```

### **Step 3: Environment Configuration**
```bash
# Set environment variables
export DRIFT_ENVIRONMENT=devnet  # or mainnet for production
export KEYPAIR_PATH=/path/to/your/keypair.json
export USE_MOCK=false

# Verify environment
python -c "from libs.config.environment import get_environment_config; print(get_environment_config().validate_configuration())"
```

### **Step 4: Configuration Validation**
```bash
# Test configuration loading
python -c "
import yaml
with open('releases/v1.0.0-production/configs/production_dual_bots.yaml') as f:
    config = yaml.safe_load(f)
    print('Configuration loaded successfully')
    print(f'Environment: {config[\"environment\"][\"name\"]}')
"
```

### **Step 5: Run Pre-Deployment Tests**
```bash
# Navigate to test directory
cd releases/v1.0.0-production/tests

# Run comprehensive test suite
python run_tests.py --all

# Verify all tests pass
echo "Test exit code: $?"
```

---

## **🚀 DEPLOYMENT EXECUTION**

### **Step 1: Production Validation**
```bash
# Run system validation
cd releases/v1.0.0-production/tests
python run_tests.py --system

# Ensure 100% pass rate for system tests
```

### **Step 2: Deploy Production System**
```bash
# Navigate to source directory
cd releases/v1.0.0-production/src

# Execute production deployment
python deploy_production_dual_bots.py
```

### **Step 3: Verify Deployment**
```bash
# Check system health
curl http://localhost:9124/health

# Check metrics
curl http://localhost:9100/metrics | grep drift_swift

# Monitor logs
tail -f logs/production_deployment.log
```

### **Step 4: Validate Trading Operations**
```bash
# Monitor initial trading activity
grep "ORDER PLACED" logs/production_deployment.log

# Check position tracking
grep "Position Update" logs/production_deployment.log

# Verify risk management
grep "Risk Check" logs/production_deployment.log
```

---

## **📊 MONITORING SETUP**

### **Metrics Dashboard**
```bash
# Access Prometheus metrics
open http://localhost:9100

# Key metrics to monitor:
# - orders_placed_total
# - order_success_rate  
# - current_position
# - system_health_status
# - order_latency_seconds
```

### **Health Monitoring**
```bash
# Health check endpoint
curl -s http://localhost:9124/health | jq

# Expected response:
{
  "status": "healthy",
  "components": {
    "drift_client": "ready",
    "swift_api": "connected", 
    "orderbook": "streaming",
    "position_tracker": "active"
  }
}
```

### **Log Monitoring**
```bash
# Monitor real-time logs
tail -f logs/production_deployment.log | grep -E "(ERROR|WARNING|SUCCESS)"

# Monitor bot-specific logs
tail -f logs/jit-mm-swift.log | grep "\[MM\]"
tail -f logs/hedge-bot.log | grep "\[H\]"
```

---

## **⚠️ PRODUCTION SAFEGUARDS**

### **Emergency Procedures**

#### **Immediate Stop**
```bash
# Kill all bot processes
pkill -f "deploy_production_dual_bots.py"
pkill -f "python.*bot"

# Verify all processes stopped
ps aux | grep -E "(deploy_|bot|swift)" | grep -v grep
```

#### **Position Flattening**
```bash
# Access emergency controls
python -c "
from run_swift_mm_complete import CompleteSwiftMMBot
# Emergency position flattening would be implemented here
print('Emergency procedures available')
"
```

#### **System Health Check**
```bash
# Quick health validation
python releases/v1.0.0-production/tests/run_tests.py --system
```

### **Risk Monitoring**

#### **Position Limits**
- Monitor `current_position` metric
- Alert if position exceeds configured limits
- Automatic position reduction when approaching limits

#### **Collateral Monitoring**
- Track `free_collateral_usd` metric
- Alert if collateral falls below 150% requirement
- Automatic trading pause on low collateral

#### **Performance Monitoring**
- Monitor `order_success_rate` (target: >95%)
- Track `order_latency_p95` (target: <100ms)
- Alert on system degradation

---

## **🔧 CONFIGURATION MANAGEMENT**

### **Runtime Configuration Updates**

#### **Order Size Adjustment**
```bash
# Update configuration file
nano configs/live_trading_config.yaml

# Modify order sizes
buy_order_size: 0.6  # Increase buy size
sell_order_size: 0.4  # Increase sell size

# Restart system for changes
pkill -f deploy_production_dual_bots
python releases/v1.0.0-production/src/deploy_production_dual_bots.py
```

#### **Risk Parameter Updates**
```bash
# Update risk limits
nano releases/v1.0.0-production/configs/production_dual_bots.yaml

# Modify risk management section
risk_management:
  max_position_usd: 2000.0  # Increase limit
  max_daily_loss_usd: 200.0  # Increase limit
```

### **Environment Switching**

#### **Devnet to Mainnet Migration**
```bash
# 1. Stop current system
pkill -f deploy_production_dual_bots

# 2. Update environment
export DRIFT_ENVIRONMENT=mainnet
export KEYPAIR_PATH=/path/to/mainnet/keypair.json

# 3. Update configuration
sed -i 's/devnet/mainnet/g' releases/v1.0.0-production/configs/production_dual_bots.yaml

# 4. Validate configuration
python releases/v1.0.0-production/tests/run_tests.py --system

# 5. Deploy to mainnet
python releases/v1.0.0-production/src/deploy_production_dual_bots.py
```

---

## **📈 PERFORMANCE OPTIMIZATION**

### **Latency Optimization**

#### **Network Configuration**
```bash
# Optimize network settings
echo 'net.core.rmem_max = 134217728' >> /etc/sysctl.conf
echo 'net.core.wmem_max = 134217728' >> /etc/sysctl.conf
sysctl -p
```

#### **Process Priority**
```bash
# Run with higher priority
nice -n -10 python releases/v1.0.0-production/src/deploy_production_dual_bots.py
```

### **Resource Optimization**

#### **Memory Management**
```bash
# Monitor memory usage
watch -n 5 'ps aux | grep python | grep -E "(deploy_|bot)" | awk "{print \$6}" | sort -n'

# Set memory limits if needed
ulimit -m 1048576  # 1GB limit
```

#### **CPU Optimization**
```bash
# Monitor CPU usage
top -p $(pgrep -f deploy_production_dual_bots)

# Set CPU affinity for critical processes
taskset -c 0,1 python releases/v1.0.0-production/src/deploy_production_dual_bots.py
```

---

## **🔄 MAINTENANCE PROCEDURES**

### **Daily Maintenance**

#### **Morning Checklist**
```bash
# 1. Check system health
curl -s http://localhost:9124/health | jq '.status'

# 2. Review overnight logs
grep -E "(ERROR|CRITICAL)" logs/production_deployment.log | tail -20

# 3. Verify position status
curl -s http://localhost:9100/metrics | grep current_position

# 4. Check collateral levels
grep "Collateral Status" logs/jit-mm-swift.log | tail -5
```

#### **Evening Review**
```bash
# 1. Daily performance summary
grep "Market Making Stats" logs/production_deployment.log | tail -10

# 2. Risk metrics review
grep "Risk Check" logs/jit-mm-swift.log | tail -20

# 3. Error analysis
grep "ERROR" logs/*.log | wc -l

# 4. Backup logs
tar -czf logs/backup-$(date +%Y%m%d).tar.gz logs/*.log
```

### **Weekly Maintenance**

#### **System Update**
```bash
# 1. Update dependencies
pip install --upgrade driftpy anchorpy solders

# 2. Run full test suite
python releases/v1.0.0-production/tests/run_tests.py --all

# 3. Performance analysis
grep "latency" logs/*.log | awk '{print $NF}' | sort -n | tail -100

# 4. Configuration review
diff configs/live_trading_config.yaml configs/live_trading_config.yaml.backup
```

---

## **🆘 TROUBLESHOOTING**

### **Common Issues**

#### **Bot Not Starting**
```bash
# Check environment variables
env | grep DRIFT

# Validate configuration
python -c "
import yaml
with open('configs/live_trading_config.yaml') as f:
    print(yaml.safe_load(f))
"

# Check dependencies
pip check
```

#### **Orders Not Placing**
```bash
# Check Swift API connectivity
curl -s https://master.swift.drift.trade/health

# Verify collateral
grep "LOW COLLATERAL" logs/jit-mm-swift.log | tail -5

# Check position limits
grep "Position utilization" logs/jit-mm-swift.log | tail -5
```

#### **High Latency**
```bash
# Check network connectivity
ping -c 5 api.devnet.solana.com

# Monitor system resources
top -bn1 | grep python

# Check for competing processes
netstat -tulpn | grep :8787
```

### **Recovery Procedures**

#### **Graceful Restart**
```bash
# 1. Send graceful shutdown signal
pkill -TERM -f deploy_production_dual_bots

# 2. Wait for graceful shutdown
sleep 30

# 3. Force kill if necessary
pkill -KILL -f deploy_production_dual_bots

# 4. Restart system
python releases/v1.0.0-production/src/deploy_production_dual_bots.py
```

#### **Emergency Recovery**
```bash
# 1. Immediate stop
pkill -9 -f "python.*bot"

# 2. Clear any stuck orders (if needed)
# Manual intervention required via Drift UI

# 3. Validate system state
python releases/v1.0.0-production/tests/run_tests.py --system

# 4. Restart with validation
python releases/v1.0.0-production/src/deploy_production_dual_bots.py
```

---

## **📞 SUPPORT AND ESCALATION**

### **Support Channels**
- **Technical Issues**: Check troubleshooting guide first
- **Performance Issues**: Review monitoring metrics
- **Configuration Help**: Consult configuration documentation
- **Emergency Issues**: Use emergency procedures

### **Escalation Procedures**
1. **Level 1**: Automated recovery and restart
2. **Level 2**: Manual intervention and configuration adjustment
3. **Level 3**: System shutdown and manual analysis
4. **Level 4**: Emergency position flattening and system halt

---

**🔒 Remember: Always test changes in devnet before applying to mainnet!**
