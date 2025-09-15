# Trend Bot Beta Launcher - Usage Guide

## Overview

The `launch_trend_beta.py` script has been improved with better error handling, CLI configuration, and security practices.

## Key Improvements

✅ **Fixed syntax error** in `bots/trend/main.py`  
✅ **Consolidated logging** - removed duplicate logging setup  
✅ **Fixed deprecated asyncio calls** - replaced `get_event_loop()` with `get_running_loop()`  
✅ **Moved API key to environment variable** - no more hardcoded keys  
✅ **Improved error logging** - using `logger.exception()` for stack traces  
✅ **Added CLI argument parsing** - configurable network, RPC, keypair  

## Environment Setup

1. **Set your Helius API key:**
   ```bash
   # Windows
   set HELIUS_API_KEY=your_api_key_here
   
   # Linux/Mac
   export HELIUS_API_KEY=your_api_key_here
   ```

2. **Ensure your keypair file exists:**
   - Default: `.swift_test_wallet.json`
   - Or specify with `--keypair` argument

## Usage Examples

### Basic Usage (Devnet)
```bash
python launch_trend_beta.py
```

### With Custom Keypair
```bash
python launch_trend_beta.py --keypair .valid_wallet.json
```

### With Custom RPC/WS URLs
```bash
python launch_trend_beta.py --rpc https://your-rpc-url.com --ws wss://your-ws-url.com
```

### All Options
```bash
python launch_trend_beta.py \
  --network devnet \
  --rpc https://devnet.helius-rpc.com/?api-key=your_key \
  --ws wss://devnet.helius-rpc.com/?api-key=your_key \
  --keypair .swift_test_wallet.json \
  --config configs/core/drift_client.yaml
```

## CLI Arguments

- `--network`: Network to use (devnet, mainnet-beta) - default: devnet
- `--rpc`: Custom RPC URL (overrides API key-based URL)
- `--ws`: Custom WebSocket URL (overrides API key-based URL)  
- `--keypair`: Path to keypair file - default: .swift_test_wallet.json
- `--config`: Path to drift client config - default: configs/core/drift_client.yaml

## Error Handling

- **Missing API key**: Clear error message if `HELIUS_API_KEY` not set
- **Missing keypair**: Validates keypair file exists with helpful path info
- **Missing config**: Validates config file exists with helpful path info
- **Better logging**: Uses `logger.exception()` for stack traces in error cases

## Security

- ✅ No hardcoded API keys in source code
- ✅ API key read from environment variable
- ✅ Keypair path validation
- ✅ Config file validation

## Logging

- Uses centralized `setup_critical_logging("trend-bot")`
- Consistent logging format
- File output to `trend_bot_beta.log`
- Console output for real-time monitoring





