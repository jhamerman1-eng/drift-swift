#!/usr/bin/env python3
import json

# The correct JSON array format
correct_wallet_data = [174,47,154,16,202,193,206,113,199,190,53,133,169,175,31,56,222,53,138,189,224,216,117,173,10,149,53,45,73,46,49,18,93,131,45,18,18,209,161,212,247,175,76,106,148,248,161,76,149,181,165,68,119,40,116,85,153,72,139,161,76,136,164,142]

# Write to the correct file
with open('.beta_dev_wallet.json', 'w') as f:
    json.dump(correct_wallet_data, f, indent=2)

print("✅ Wallet format fixed!")
print("📁 .beta_dev_wallet.json now contains proper JSON array format")
print("🚀 Ready to run: python launch_hedge_beta_real.py")
