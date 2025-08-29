# Environment Setup Guide

This guide helps you securely configure your Drift trading environment with proper API key management.

## 🚀 Quick Start

### Option 1: Interactive Setup (Recommended)

1. **Run the environment setup script:**
   ```cmd
   setup_environment.bat
   ```

2. **Choose option 1** to securely enter your Helius API key

3. **Choose option 3** to save your configuration to a `.env` file

4. **Run the main setup:**
   ```cmd
   setup_devnet_trading.bat
   ```

### Option 2: Python Setup (Alternative)

```cmd
python setup_environment.py
```

## 📋 Available Scripts

### `setup_environment.bat` - Interactive Environment Setup
- Secure API key input (not displayed as you type)
- Environment validation and testing
- Generate persistent `.env` configuration file
- Comprehensive setup testing

### `setup_environment.py` - Python Environment Setup
- Cross-platform compatibility
- Advanced features and error handling
- Command-line options available

### `load_environment.bat` - Load Saved Configuration
- Quickly load environment variables from `.env` file
- Perfect for daily use after initial setup

### `setup_devnet_trading.bat` - Main Trading Setup
- Validates environment and dependencies
- Sets up trading configuration
- Provides trading commands and safety notes

## 🔐 Security Features

### ✅ What We Do Right:
- **No hardcoded secrets** in any script
- **Secure password input** using PowerShell/Getpass
- **Environment variables** for sensitive data
- **API key validation** before acceptance
- **File integrity checks** for wallet files
- **Comprehensive testing** before trading

### ❌ What We Avoid:
- Exposing private keys in plain text
- Hardcoding API keys in scripts
- Storing sensitive data in version control
- Weak password input methods

## 📝 Step-by-Step Setup

### 1. Initial Setup

```cmd
# Run environment setup
setup_environment.bat

# Choose option 1: Set API Key (secure input)
# Enter your Helius API key when prompted

# Choose option 3: Generate environment file
# This creates a .env file with your configuration
```

### 2. Daily Usage

```cmd
# Load your saved environment
load_environment.bat

# Run the trading setup
setup_devnet_trading.bat
```

### 3. Testing Your Setup

```cmd
# Test environment (batch script)
setup_environment.bat
# Choose option 6: Test environment setup

# Test environment (Python script)
python setup_environment.py --test
```

## 🧪 Environment Testing

The setup scripts include comprehensive testing:

- ✅ **API Key**: Validates presence and format
- ✅ **Python**: Checks version and availability
- ✅ **Dependencies**: Tests required packages (driftpy)
- ✅ **Wallet**: Verifies wallet file existence and integrity
- ✅ **Project**: Confirms required files are present

## 🔑 Getting Your API Key

1. Visit [Helius.dev](https://helius.dev)
2. Sign up for an account
3. Create a new API key
4. Copy the key (it should look like: `2728d54b-ce26-4696-bb4d-dc8170fcd494`)

## 📁 File Structure

After setup, you'll have these files:

```
drift-swift/
├── .env                    # Your environment configuration (KEEP PRIVATE!)
├── .devnet_wallet.json     # Your wallet file (KEEP SECURE!)
├── setup_environment.bat   # Environment setup script
├── setup_environment.py    # Python environment setup
├── load_environment.bat    # Quick environment loader
└── setup_devnet_trading.bat # Main trading setup
```

## ⚠️ Security Best Practices

### 🔴 NEVER:
- Commit `.env` files to version control
- Share your API keys or private keys
- Hardcode secrets in scripts
- Store sensitive files in public locations

### ✅ ALWAYS:
- Use environment variables for sensitive data
- Keep private keys offline when possible
- Use secure input methods for passwords
- Test your setup before trading
- Back up your wallet securely

## 🆘 Troubleshooting

### "DRIFT_API_KEY environment variable not set"
```cmd
# Run setup script
setup_environment.bat

# Choose option 1 to set API key
```

### "Python not found" or "driftpy not installed"
```cmd
# Install Python from python.org
# Then install dependencies
pip install -r requirements.txt
```

### "Wallet file not found"
```cmd
# Generate a new wallet securely
python create_keypair.py

# Or use the test wallet (DevNet only)
python create_test_wallet.py
```

### "Environment file not found"
```cmd
# Generate environment file
setup_environment.bat
# Choose option 3: Generate environment file
```

## 📞 Support

If you encounter issues:

1. Run the test suite: `setup_environment.bat` → Option 6
2. Check the troubleshooting section above
3. Verify your API key is valid at [Helius.dev](https://helius.dev)
4. Ensure all required files are present in the directory

## 🎯 Next Steps

After successful setup:

1. **Get DevNet SOL**: Visit https://faucet.solana.com
2. **Test connection**: Run `python devnet_test_connection.py`
3. **Check wallet balance**: Run `python check_wallet_funds.py`
4. **Start trading**: Run `python run_mm_bot_v2.py --env devnet --cfg configs/core/drift_client.yaml`

---

**Remember**: Always test with small amounts first and never risk more than you can afford to lose!


