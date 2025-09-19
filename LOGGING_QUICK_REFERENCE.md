# 🚀 Logging Quick Reference Card

## 📋 **Daily Operations**

### **Morning Check**
```bash
# Quick health check (no changes)
python monitor_logging.py --dry-run
```

### **Weekly Maintenance**
```bash
# Clean up old logs
python monitor_logging.py --maintenance-only
```

### **Monthly Audit**
```bash
# Full system audit
python audit_logging.py
```

## 🔍 **Troubleshooting**

### **Log Files Not Created**
```bash
# Check if logs directory exists
ls -la logs/

# Verify logging_config import
python -c "from libs.logging_config import setup_critical_logging; print('OK')"
```

### **Large Log Files**
```bash
# Check log sizes
python monitor_logging.py --dry-run

# Manual cleanup
python monitor_logging.py --maintenance-only
```

### **Encoding Issues (Windows)**
```bash
# Set console encoding
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
```

## 📊 **Log Levels**

| Level | Usage | Example |
|-------|-------|---------|
| `DEBUG` | Detailed debugging | `logger.debug(f"Processing {order_id}")` |
| `INFO` | General information | `logger.info("Bot started successfully")` |
| `WARNING` | Potential issues | `logger.warning("High latency detected")` |
| `ERROR` | Serious problems | `logger.error(f"Order failed: {error}")` |
| `CRITICAL` | Fatal errors | `logger.critical("Circuit breaker activated")` |

## 🏗️ **Adding Logging to New Code**

### **Critical Applications**
```python
from libs.logging_config import setup_critical_logging
logger = setup_critical_logging("app-name")

# Use logger
logger.info("Application started")
logger.error("Something went wrong")
```

### **Utility Applications**
```python
from libs.logging_config import setup_utility_logging
logger = setup_utility_logging("utility-name")

# Use logger
logger.info("Utility completed")
```

## 📁 **File Locations**

- **Logs**: `logs/` directory
- **Configuration**: `libs/logging_config.py`
- **Backups**: `backups/logging_migration/`
- **Reports**: `logs/*_report.json`

## ⚡ **Quick Commands**

### **Check Log Health**
```bash
python monitor_logging.py --dry-run
```

### **View Recent Logs**
```bash
# Last 50 lines of MM bot
tail -50 logs/jit-mm-swift.log

# Last 100 lines with errors
grep "ERROR" logs/*.log | tail -100
```

### **Check Log Sizes**
```bash
# Windows
dir logs\*.log /s

# Linux/Mac
du -h logs/*.log
```

## 🚨 **Emergency Procedures**

### **Log Disk Full**
```bash
# Immediate cleanup
python monitor_logging.py --maintenance-only

# Check disk space
df -h  # Linux/Mac
dir     # Windows
```

### **Critical Logging Failure**
```bash
# Verify configuration
python -c "from libs.logging_config import *; print('Config OK')"

# Check file permissions
ls -la logs/
```

### **Performance Issues**
```bash
# Check log file sizes
python monitor_logging.py --dry-run

# Reduce log level temporarily
export LOG_LEVEL=WARNING
```

## 📈 **Monitoring Dashboard**

### **Key Metrics to Watch**
- **Total Log Size**: Should be < 1GB
- **Individual Log Size**: Should be < 100MB
- **Log Age**: Should be < 30 days
- **Error Count**: Monitor for spikes
- **Activity Level**: Ensure recent log entries

### **Alert Thresholds**
- 🟢 **Green**: All systems healthy
- 🟡 **Yellow**: Warnings detected
- 🔴 **Red**: Critical issues found

## 🔧 **Configuration Tuning**

### **Environment Variables**
```bash
# Global log level
export LOG_LEVEL=INFO

# Disable file logging (development)
export LOG_FILE_ENABLED=false

# Custom log directory
export LOG_DIR=/custom/logs
```

### **Custom Settings**
```python
# High-volume application
logger = setup_critical_logging(
    app_name="high-volume-bot",
    log_level="WARNING",  # Reduce log volume
    enable_file_logging=True,
    enable_console_logging=False  # Console off for performance
)
```

## 📞 **Support Commands**

### **System Information**
```bash
# Log system info
python -c "
from libs.logging_config import log_system_info, get_mm_bot_logger
logger = get_mm_bot_logger()
log_system_info(logger)
"
```

### **Test Logging**
```bash
# Test all loggers
python -c "
from libs.logging_config import *
for name in ['jit-mm-swift', 'hedge-bot', 'trend-bot']:
    logger = get_existing_logger(name)
    logger.info(f'Test message from {name}')
"
```

---

**💡 Remember: Good logging saves debugging time and provides operational insights!**

