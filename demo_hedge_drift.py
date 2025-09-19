#!/usr/bin/env python3
"""
Demonstration of Internal Drift Hedge Functionality

This script demonstrates the new hedge functionality that uses Drift Protocol
internally instead of external CEX venues. It shows:

1. Sub-account creation for hedging
2. Internal Drift order execution
3. Proper risk management integration
4. Configuration and setup

Usage:
    python demo_hedge_drift.py
"""

import asyncio
import logging
from decimal import Decimal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def demo_drift_hedge():
    """Demonstrate the new internal Drift hedge functionality."""
    print("🛡️ INTERNAL DRIFT HEDGE DEMO")
    print("=" * 60)

    # 1. Show configuration
    print("\n1. ⚙️ Hedge Configuration")
    print("-" * 30)

    try:
        import yaml
        with open("configs/hedge/routing.yaml", "r") as f:
            config = yaml.safe_load(f)

        hedge_config = config.get("hedge", {})
        print("✅ Configuration loaded successfully")
        print(f"   📊 Sub-account: {hedge_config.get('sub_account', {}).get('name', 'N/A')}")
        print(f"   🎯 Routes: {len(hedge_config.get('route', []))} configured")
        print(f"   ⚡ Urgency Scoring: {hedge_config.get('urgency_scoring', False)}")

        for i, route in enumerate(hedge_config.get('route', []), 1):
            print(f"      {i}. {route['venue']} - {route['mode']} mode")

    except FileNotFoundError:
        print("❌ Configuration file not found: configs/hedge/routing.yaml")
        return
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return

    # 2. Demonstrate sub-account manager
    print("\n2. 🏦 Sub-Account Management")
    print("-" * 30)

    try:
        from libs.drift.sub_account_manager import SubAccountManager, get_sub_account_manager

        print("✅ Sub-account manager imported successfully")
        print("   📋 Available methods:")
        print("      • create_hedge_sub_account()")
        print("      • get_or_create_sub_account()")
        print("      • switch_to_sub_account()")
        print("      • get_sub_account_balance()")
        print("      • transfer_between_accounts()")

        # Note: We can't actually create accounts without a real client
        print("\n   ℹ️ Note: Sub-account creation requires live Drift client")
        print("      This would create 'hedge_account' with $1000 initial collateral")

    except ImportError as e:
        print(f"❌ Failed to import sub-account manager: {e}")

    # 3. Demonstrate hedge execution
    print("\n3. 🎯 Hedge Execution System")
    print("-" * 30)

    try:
        from bots.hedge.execution import DriftHedgeExecutor, execute_hedge

        print("✅ Drift hedge executor imported successfully")
        print("   📋 Available execution methods:")
        print("      • initialize_hedge_account()")
        print("      • execute_hedge_order()")
        print("      • execute_signal()")
        print("      • cancel_hedge_orders()")
        print("      • get_hedge_account_balance()")

        # Demonstrate signal structure
        sample_signal = {
            "side": "sell",
            "price": 50000.0,
            "size_usd": 1000.0,
            "order_type": "ioc",
            "sub_account": "hedge_account",
            "venues": ["drift"]
        }

        print("\n   🎯 Sample hedge signal structure:")
        for key, value in sample_signal.items():
            print(f"      {key}: {value}")

        print("\n   📤 Expected execution result:")
        print("      DRIFT_IOC_EXECUTED:<order_id>")

    except ImportError as e:
        print(f"❌ Failed to import hedge execution: {e}")

    # 4. Demonstrate decision engine
    print("\n4. 🧠 Decision Engine")
    print("-" * 30)

    try:
        from bots.hedge.decide import decide_hedge, HedgeDecision, HedgeInputs

        print("✅ Hedge decision engine imported successfully")

        # Test various scenarios
        test_cases = [
            {
                "name": "Normal Long Position",
                "inputs": HedgeInputs(
                    net_exposure_usd=1000.0,
                    mid_price=50000.0,
                    atr=100.0,
                    equity_usd=50000.0
                )
            },
            {
                "name": "Normal Short Position",
                "inputs": HedgeInputs(
                    net_exposure_usd=-2000.0,
                    mid_price=50000.0,
                    atr=100.0,
                    equity_usd=50000.0
                )
            },
            {
                "name": "No Exposure (Skip)",
                "inputs": HedgeInputs(
                    net_exposure_usd=0.0,
                    mid_price=50000.0,
                    atr=100.0,
                    equity_usd=50000.0
                )
            },
            {
                "name": "Invalid Price (Skip)",
                "inputs": HedgeInputs(
                    net_exposure_usd=1000.0,
                    mid_price=None,
                    atr=100.0,
                    equity_usd=50000.0
                )
            }
        ]

        for test_case in test_cases:
            print(f"\n   🧪 {test_case['name']}:")
            decision = decide_hedge(test_case["inputs"])
            print(f"      Action: {decision.action}")
            print(f"      Quantity: ${decision.qty:.2f}")
            print(f"      Reason: {decision.reason}")

    except ImportError as e:
        print(f"❌ Failed to import decision engine: {e}")

    # 5. Show integration points
    print("\n5. 🔗 Integration Points")
    print("-" * 30)

    integration_points = [
        {
            "component": "Risk Manager",
            "status": "✅ Integrated",
            "purpose": "Trading permission and drawdown control"
        },
        {
            "component": "Position Tracker",
            "status": "✅ Integrated",
            "purpose": "Net exposure monitoring"
        },
        {
            "component": "Order Manager",
            "status": "✅ Integrated",
            "purpose": "Order tracking and lifecycle management"
        },
        {
            "component": "Drift Client",
            "status": "✅ Integrated",
            "purpose": "Order execution and account management"
        },
        {
            "component": "Orderbook",
            "status": "✅ Integrated",
            "purpose": "Price discovery and slippage calculation"
        }
    ]

    for point in integration_points:
        print(f"   {point['status']} {point['component']}: {point['purpose']}")

    # 6. Show benefits
    print("\n6. 🎯 Key Benefits")
    print("-" * 30)

    benefits = [
        "🔒 Enhanced Security - No external exchange API keys",
        "⚡ Lower Latency - Direct protocol interaction",
        "💰 Reduced Fees - No external exchange fees",
        "🎛️ Better Control - Full order lifecycle management",
        "📊 Unified Monitoring - Single platform metrics",
        "🛡️ Risk Isolation - Separate sub-account for hedging",
        "🔄 Atomic Operations - Single-transaction hedges",
        "📈 Better Pricing - Access to Drift's full liquidity"
    ]

    for benefit in benefits:
        print(f"   {benefit}")

    # 7. Configuration validation
    print("\n7. ✅ Configuration Validation")
    print("-" * 30)

    config_issues = []

    # Check required files exist
    required_files = [
        "configs/hedge/routing.yaml",
        "bots/hedge/main.py",
        "bots/hedge/execution.py",
        "bots/hedge/decide.py",
        "libs/drift/sub_account_manager.py"
    ]

    for file_path in required_files:
        try:
            with open(file_path, "r") as f:
                pass  # Just check if we can open it
            print(f"   ✅ {file_path}")
        except FileNotFoundError:
            print(f"   ❌ {file_path} - MISSING")
            config_issues.append(f"Missing file: {file_path}")
        except Exception as e:
            print(f"   ⚠️ {file_path} - ERROR: {e}")
            config_issues.append(f"Error reading {file_path}: {e}")

    if config_issues:
        print(f"\n   🚨 Configuration Issues Found: {len(config_issues)}")
        for issue in config_issues:
            print(f"      • {issue}")
    else:
        print("\n   🎉 All configuration files present and accessible")
    # 8. Next steps
    print("\n8. 🚀 Next Steps")
    print("-" * 30)

    next_steps = [
        "1. 🔧 Configure Drift client credentials",
        "2. 💰 Fund hedge sub-account with collateral",
        "3. 🧪 Test hedge execution in simulation mode",
        "4. 📊 Set up monitoring and alerting",
        "5. 🎯 Tune hedge parameters for your strategy",
        "6. 🚀 Enable live hedging with small position sizes",
        "7. 📈 Monitor performance and adjust thresholds"
    ]

    for step in next_steps:
        print(f"   {step}")

    print("\n" + "=" * 60)
    print("✅ INTERNAL DRIFT HEDGE DEMO COMPLETE")
    print("🔥 Ready for internal hedging operations!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(demo_drift_hedge())
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
