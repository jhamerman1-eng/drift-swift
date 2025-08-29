# 🚀 MANUAL SOLANA DEVNET AIRDROP INSTRUCTIONS

Since programmatic airdrops are blocked by Cloudflare protection, here are the manual methods to get SOL:

## Method 1: Web Faucet (Recommended)

### Step 1: Open the faucet
Go to: https://faucet.solana.com/

### Step 2: Request SOL for your wallets
- **Wallet 1**: `G4aTeEx1pVMXcMKDjnnEyucqxmi3StxcAsLE9CcQZGzD`
- **Wallet 2**: `6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW`

### Step 3: Complete captcha/verification
- The faucet may require you to complete a captcha
- Sometimes it asks you to enable JavaScript (which you already have)

### Step 4: Amount selection
- Request **1 SOL** per wallet (sufficient for ~1000 trades)
- Maximum is usually 2 SOL per request

## Method 2: Alternative Faucets

If the main faucet doesn't work, try these alternatives:

1. **QuickNode Faucet**: https://faucet.quicknode.com/solana/devnet
2. **Solana Labs Discord**: Join and use `!faucet` command
3. **Phantom Wallet**: If you have Phantom, it has a built-in faucet

## Method 3: Command Line (if you have Solana CLI)

```bash
# Install Solana CLI if you don't have it
# Then run:
solana airdrop 1 G4aTeEx1pVMXcMKDjnnEyucqxmi3StxcAsLE9CcQZGzD --url https://api.devnet.solana.com
solana airdrop 1 6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW --url https://api.devnet.solana.com
```

## Verification Steps

After getting SOL, verify your balances:

### Option A: Use the script I created
```bash
python check_wallet_funds.py
```

### Option B: Check manually on explorer
- Wallet 1: https://explorer.solana.com/address/G4aTeEx1pVMXcMKDjnnEyucqxmi3StxcAsLE9CcQZGzD?cluster=devnet
- Wallet 2: https://explorer.solana.com/address/6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW?cluster=devnet

## What You Need

**Minimum SOL required**: 0.01 SOL per wallet
- For transaction fees (~0.000005 SOL per trade)
- For Drift protocol fees

**Recommended SOL**: 0.5-1 SOL per wallet
- Covers ~1000-2000 trades
- Provides buffer for network congestion

## Troubleshooting

### If faucet shows error:
1. **Wait 30 seconds** and try again
2. **Use a different browser** (Chrome/Firefox)
3. **Try incognito/private mode**
4. **Use a VPN** if rate limited by IP

### If still failing:
1. **Check faucet status**: Sometimes faucets are temporarily down
2. **Try different time of day**
3. **Use Discord faucet** as alternative

## Next Steps After Getting SOL

Once you have SOL in your wallets:

1. **Verify balances**: `python check_wallet_funds.py`
2. **Start trading**: Your bots are ready to trade!
3. **Monitor performance**: Use the dashboard to track P&L

## Your Wallet Addresses (Save these!)

```
Wallet 1 (32-byte seed): G4aTeEx1pVMXcMKDjnnEyucqxmi3StxcAsLE9CcQZGzD
Wallet 2 (64-byte secret): 6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW
```

**Important**: Keep your private keys safe! The ones you provided are for devnet testing only.


