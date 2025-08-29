# 🔧 Solana CLI Installation Guide - Windows

## Option 1: Automatic Installation (Recommended)

### Using winget (if available):
```powershell
winget install --id Solana.SolanaCLI --accept-source-agreements --accept-package-agreements
```

### Using Chocolatey (alternative):
```powershell
choco install solana
```

## Option 2: Manual Installation

1. **Download the installer:**
   - Go to: https://github.com/solana-labs/solana/releases/latest
   - Download: `solana-install-init-x86_64-pc-windows-msvc.exe`

2. **Run the installer:**
   - Execute the downloaded `.exe` file
   - Follow the installation wizard
   - Choose default installation directory

3. **Add to PATH:**
   - Open System Properties → Advanced → Environment Variables
   - Add to User PATH: `%USERPROFILE%\.local\share\solana\install\active_release\bin`
   - Or to System PATH: `C:\Users\[USERNAME]\.local\share\solana\install\active_release\bin`

## Verify Installation

After installation, open a **NEW** terminal and verify:

```bash
# Check version
solana --version

# Should show something like: solana-cli 1.18.x

# Check config
solana config get
```

## Set Network to Devnet

```bash
# Set to devnet for beta trading
solana config set --url https://api.devnet.solana.com

# Verify config
solana config get
```

## Troubleshooting

### "solana is not recognized"
- **Solution**: Add Solana to PATH (see step 3 above)
- **Alternative**: Use full path: `C:\Users\[USERNAME]\.local\share\solana\install\active_release\bin\solana.exe`

### Permission Errors
- **Solution**: Run terminal as Administrator for installation

### Network Issues
- **Solution**: Check firewall/antivirus settings
- **Alternative**: Use VPN if blocked

## Next Steps

Once Solana CLI is installed and working:

1. **Create wallet:**
   ```bash
   python setup_beta_wallet.py
   ```

2. **Fund wallet:**
   - Go to https://faucet.solana.com
   - Request devnet SOL

3. **Start real beta trading:**
   ```bash
   python launch_hedge_beta_real.py
   ```

## Alternative: Use Existing Wallet

If you already have a Solana wallet:

1. **Copy your keypair file** to the project directory
2. **Rename it** to `.beta_dev_wallet.json`
3. **Fund it** with devnet SOL if needed
4. **Skip wallet creation** and go directly to trading

---

**⚠️ IMPORTANT**: Beta trading requires SOL for gas fees. Start with at least 0.1 SOL.
