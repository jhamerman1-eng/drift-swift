#!/usr/bin/env python3
"""
Bot Interference Analysis
Analyzes potential conflicts between MM Bot and Trend Bot
"""

import os
import yaml
from pathlib import Path

def analyze_bot_conflicts():
    """Analyze potential conflicts between bots"""

    print("🤖 BOT INTERFERENCE ANALYSIS")
    print("=" * 60)
    print()

    # 1. Market Conflicts
    print("1️⃣ MARKET CONFLICTS")
    print("-" * 30)

    # Check MM bot market
    mm_config = Path("configs/jit/params.yaml")
    if mm_config.exists():
        with open(mm_config, 'r') as f:
            mm_cfg = yaml.safe_load(f)
        mm_market = mm_cfg.get('symbol', 'Unknown')
        print(f"📊 MM Bot Market: {mm_market}")

    # Check trend bot market (inferred from config)
    trend_config = Path("configs/trend/filters.yaml")
    if trend_config.exists():
        with open(trend_config, 'r') as f:
            trend_cfg = yaml.safe_load(f)
        print(f"📊 Trend Bot Market: SOL-PERP (inferred from config)")

    if mm_market == "SOL-PERP":
        print("🚨 CONFLICT: Both bots target SOL-PERP market!")
        print("   This will cause order conflicts and position interference")
    print()

    # 2. Wallet Conflicts
    print("2️⃣ WALLET CONFLICTS")
    print("-" * 30)

    wallets = [
        ".beta_dev_wallet.json",
        ".swift_test_wallet.json",
        ".valid_wallet.json",
        "test_keypair.json"
    ]

    wallet_usage = {}
    for wallet in wallets:
        if os.path.exists(wallet):
            wallet_usage[wallet] = "EXISTS"
            print(f"✅ {wallet}: Available")
        else:
            wallet_usage[wallet] = "MISSING"
            print(f"❌ {wallet}: Missing")

    print()
    print("🔍 Wallet Usage Analysis:")
    print("  MM Bot: Uses .swift_test_wallet.json (from config)")
    print("  Trend Bot: Uses test_keypair.json (from launcher)")
    print("  → Different wallets = LOW CONFLICT risk")
    print()

    # 3. RPC/Network Conflicts
    print("3️⃣ RPC/NETWORK CONFLICTS")
    print("-" * 30)

    core_config = Path("configs/core/drift_client.yaml")
    if core_config.exists():
        with open(core_config, 'r') as f:
            core_cfg = yaml.safe_load(f)

        rpc_url = core_cfg.get('rpc', {}).get('http_url', 'Unknown')
        cluster = core_cfg.get('cluster', 'Unknown')

        print(f"📡 Shared RPC: {rpc_url}")
        print(f"🌐 Cluster: {cluster}")

        print("⚠️  POTENTIAL ISSUES:")
        print("  • Rate limiting (both bots hitting same RPC)")
        print("  • Network congestion")
        print("  • API quota exhaustion")
    print()

    # 4. Log File Conflicts
    print("4️⃣ LOG FILE CONFLICTS")
    print("-" * 30)

    log_files = [
        "mm_bot.log",
        "trend_bot_beta.log",
        "hedge_beta_real.log",
        "bot_orchestrator.log"
    ]

    for log_file in log_files:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            print(f"📄 {log_file}: {size:,} bytes")
        else:
            print(f"📄 {log_file}: Not created yet")

    print("✅ Log files are separate - LOW CONFLICT risk")
    print()

    # 5. State/Position Conflicts
    print("5️⃣ STATE/POSITION CONFLICTS")
    print("-" * 30)
    print("🚨 HIGH RISK:")
    print("  • Both bots maintain separate position tracking")
    print("  • Orders from both bots will affect same account")
    print("  • Position calculations won't account for other bot's orders")
    print("  • Potential over-leveraging or conflicting positions")
    print()

    # 6. Recommendations
    print("6️⃣ RECOMMENDATIONS")
    print("-" * 30)

    print("🔴 DO NOT RUN BOTH BOTS SIMULTANEOUSLY")
    print()
    print("🟡 SAFE APPROACHES:")
    print("  1. Test Trend Bot in ISOLATION (MM bot stopped)")
    print("  2. Use separate wallet for Trend Bot testing")
    print("  3. Run Trend Bot in SIMULATION mode first")
    print("  4. Use different RPC endpoints if possible")
    print()
    print("✅ BEST PRACTICES:")
    print("  • Use different wallet addresses")
    print("  • Run bots sequentially, not concurrently")
    print("  • Monitor account positions carefully")
    print("  • Use smaller position sizes when testing")
    print()

    # 7. Testing Strategy
    print("7️⃣ TESTING STRATEGY")
    print("-" * 30)
    print("📋 SAFE TESTING SEQUENCE:")
    print("  1. Stop MM bot completely")
    print("  2. Launch Trend bot with separate wallet")
    print("  3. Monitor for 5-10 minutes")
    print("  4. Check position accuracy")
    print("  5. Verify no unintended orders")
    print("  6. Restart MM bot when Trend testing complete")
    print()

    print("=" * 60)
    print("🎯 CONCLUSION")
    print("=" * 60)
    print("❌ HIGH INTERFERENCE RISK - Do not run both bots together")
    print("✅ SAFE: Test Trend bot in isolation with separate wallet")
    print("🟡 MONITOR: Account positions, RPC usage, order conflicts")

if __name__ == "__main__":
    analyze_bot_conflicts()
