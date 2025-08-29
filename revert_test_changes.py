#!/usr/bin/env python3
"""
REVERT TEST CHANGES - Restore original conservative bot thresholds
This script reverts the testing changes we made to make bots more aggressive
"""

import re

def revert_hedge_bot():
    """Revert hedge bot to original conservative threshold"""
    print("🔄 Reverting Hedge Bot to original thresholds...")

    with open("bots/hedge/main.py", "r") as f:
        content = f.read()

    # Revert the threshold changes
    content = re.sub(
        r'# Determine if hedging is necessary - TESTING: More aggressive threshold\n        if notional_abs < 1e-10:  # TESTING: Much more aggressive - trade even with tiny exposure\n            # TESTING: For demo purposes, force a hedge trade even with no exposure\n            logger\.info\("🔄 FORCED HEDGE \(TESTING\): No exposure detected, creating synthetic exposure"\)\n            notional_abs = 10\.0  # TESTING: Force \$10 hedge position\n            exposure = 5\.0  # TESTING: Assume \$5 long position to hedge',
        '# Determine if hedging is necessary\n        if notional_abs < 1e-6:',
        content
    )

    with open("bots/hedge/main.py", "w") as f:
        f.write(content)

    print("✅ Hedge Bot reverted to original conservative threshold (1e-6)")

def revert_trend_bot():
    """Revert trend bot to original conservative threshold"""
    print("📈 Reverting Trend Bot to original thresholds...")

    with open("bots/trend/main.py", "r") as f:
        content = f.read()

    # Revert the threshold changes
    content = re.sub(
        r'# Scale by position_scaler and max_position_usd - TESTING: More aggressive\n    scaler = float\(trend_cfg\.get\("position_scaler", 1\.0\)\)  # TESTING: Increased from 0\.1 to 1\.0\n    max_pos = float\(trend_cfg\.get\("max_position_usd", 5000\)\)\n    notional = scaler \* signal_strength \* max_pos\n    # Determine side based on notional - TESTING: Much more aggressive threshold\n    if abs\(notional\) < 0\.01:  # TESTING: Much lower threshold from 1\.0 to 0\.01\n        # TESTING: For demo purposes, create a synthetic trend signal\n        logger\.info\("📈 FORCED TREND \(TESTING\): Weak signal detected, creating synthetic trend"\)\n        notional = 25\.0 if signal_strength > 0 else -25\.0  # TESTING: Force \$25 position',
        '# Scale by position_scaler and max_position_usd\n    scaler = float(trend_cfg.get("position_scaler", 0.1))\n    max_pos = float(trend_cfg.get("max_position_usd", 5000))\n    notional = scaler * signal_strength * max_pos\n    # Determine side based on notional\n    if abs(notional) < 1.0:  # ignore tiny signals',
        content
    )

    with open("bots/trend/main.py", "w") as f:
        f.write(content)

    print("✅ Trend Bot reverted to original conservative threshold (1.0)")

def main():
    """Revert all test changes to original conservative behavior"""
    print("🔄 REVERSING TEST CHANGES - Restoring Conservative Bot Behavior")
    print("=" * 70)
    print("This will restore the original conservative thresholds:")
    print("• Hedge Bot: 1e-6 threshold (was 1e-10)")
    print("• Trend Bot: 1.0 threshold (was 0.01)")
    print("• Trend Bot: 0.1 scaler (was 1.0)")
    print()

    revert_hedge_bot()
    revert_trend_bot()

    print()
    print("✅ ALL TEST CHANGES REVERTED!")
    print("=" * 70)
    print("Bots are now back to their original conservative behavior.")
    print("They will only trade when conditions are strongly favorable.")
    print("This is the recommended production configuration.")

if __name__ == "__main__":
    main()


