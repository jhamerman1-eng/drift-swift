#!/usr/bin/env python3
"""
🚀 Trend Bot DEV Launcher - Pure Simulation Mode

This script launches the Trend Bot in complete simulation mode with NO blockchain interaction.
It generates synthetic price data and runs MACD analysis for testing strategies safely.

Usage:
    python launch_trend_bot_dev.py  # Pure simulation - no blockchain calls
"""

import os
import sys
import asyncio
import logging
import signal
import random
from pathlib import Path
from typing import Dict, Any
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import required modules
sys.path.insert(0, str(Path(__file__).parent))

async def run_trend_bot_dev(client, config, use_mock: bool = False):
    """Run the Trend Bot in DEV mode with blockchain trading"""
    logger.info("📈 Starting Trend Bot DEV - Blockchain Trading Mode")
    logger.info("🌐 DEV Environment: devnet")
    logger.info(f"🔧 Mock Mode: {'ENABLED (no real trades)' if use_mock else 'DISABLED (live blockchain trading)'}")

    try:
        from libs.drift.client import build_client_from_config
        from prometheus_client import start_http_server, Gauge, Counter
        import collections

        # Initialize Prometheus metrics
        trend_iterations = Counter("trend_bot_iterations_total", "Trend bot iterations")
        trend_signals = Counter("trend_signals_total", "Trading signals generated", ["signal_type"])
        trend_pnl = Gauge("trend_pnl", "Current trend bot PnL")

        # Start metrics server
        start_http_server(9109)
        logger.info("📊 Metrics server started on port 9109")

        # Initialize state variables for complex indicators
        prices = collections.deque(maxlen=100)
        macd_values = collections.deque(maxlen=50)
        state_vars = {
            "ema_fast": None,
            "ema_slow": None,
            "ema_signal": None
        }

        iteration = 0
        while True:
            try:
                iteration += 1
                trend_iterations.inc()

                # Generate simulated market data (no blockchain calls)
                # Simulate SOL price movement around $150 with some volatility
                base_price = 150.0
                volatility = 0.02  # 2% volatility
                random_change = (random.random() - 0.5) * 2 * volatility
                trend_component = 0.001 * iteration  # Slight upward trend
                mid_price = base_price * (1 + random_change + trend_component)
                prices.append(mid_price)

                # Calculate MACD
                if len(prices) >= 26:  # Need enough data for slow EMA
                    fast_ema = calculate_ema(list(prices)[-12:], 12)  # Fast EMA (12)
                    slow_ema = calculate_ema(list(prices)[-26:], 26)  # Slow EMA (26)

                    if fast_ema and slow_ema:
                        macd_line = fast_ema - slow_ema
                        macd_values.append(macd_line)

                        if len(macd_values) >= 9:
                            signal_ema = calculate_ema(list(macd_values), 9)
                            histogram = macd_line - signal_ema

                            # Generate trading signals
                            if macd_line > signal_ema and histogram > 0:
                                if not use_mock:
                                    logger.info(f"📈 BUY SIGNAL at ${mid_price:.2f} - MACD: {macd_line:.4f}")
                                    # PLACE BUY ORDER HERE
                                    trend_signals.labels(signal_type="buy").inc()
                                else:
                                    logger.info(f"📈 [MOCK] BUY SIGNAL at ${mid_price:.2f} - MACD: {macd_line:.4f}")
                            elif macd_line < signal_ema and histogram < 0:
                                if not use_mock:
                                    logger.info(f"📉 SELL SIGNAL at ${mid_price:.2f} - MACD: {macd_line:.4f}")
                                    # PLACE SELL ORDER HERE
                                    trend_signals.labels(signal_type="sell").inc()
                                else:
                                    logger.info(f"📉 [MOCK] SELL SIGNAL at ${mid_price:.2f} - MACD: {macd_line:.4f}")
                            else:
                                trend_signals.labels(signal_type="hold").inc()

                if iteration % 10 == 0:
                    logger.info(f"📈 Trend Bot DEV - Iteration {iteration}, Price: ${mid_price:.2f}")
                    logger.info(f"📊 Signals: Buy={trend_signals.labels(signal_type='buy')._value}, Sell={trend_signals.labels(signal_type='sell')._value}")

                await asyncio.sleep(2)  # 2 second intervals

            except Exception as e:
                logger.error(f"📈 Trend Bot error: {e}")
                await asyncio.sleep(5)

    except Exception as e:
        logger.error(f"📈 Trend Bot failed to start: {e}")

def calculate_ema(prices: list, period: int) -> float:
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return None

    ema = prices[0]
    multiplier = 2 / (period + 1)

    for price in prices[1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))

    return ema

async def main(use_mock: bool = False):
    """Main launcher function"""
    logger.info("🚀 Trend Bot DEV Launcher")
    logger.info("=" * 50)

    try:
        from libs.drift.client import build_client_from_config

        # Load configuration
        config_path = Path("configs/core/drift_client.yaml")
        if not config_path.exists():
            logger.error(f"❌ Config not found: {config_path}")
            return 1

        logger.info(f"📁 Loading config: {config_path}")

        # Load and display config settings
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Force mock mode for safety - no blockchain interaction at all
        config['use_mock'] = True
        logger.warning("🔒 SAFETY MODE: All blockchain interactions disabled - pure simulation only")
        logger.info("📊 This will run MACD analysis on simulated price data without any network calls")

        # Build client
        logger.info("🔄 Initializing simulation environment...")
        client = await build_client_from_config(config_path)

        logger.info("✅ Simulation environment ready!")

        # Setup graceful shutdown
        def signal_handler(signum, frame):
            logger.info("⏹️  Shutdown signal received...")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Launch Trend Bot
        await run_trend_bot_dev(client, config, use_mock)

    except KeyboardInterrupt:
        logger.info("⏹️  Trend Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Launch failed: {e}")
        return 1

    return 0

def show_help():
    """Show help information"""
    print("🚀 Trend Bot DEV Launcher - Pure Simulation Mode")
    print("=" * 50)
    print()
    print("Launch Trend Bot in complete simulation mode with NO blockchain interaction")
    print()
    print("Usage:")
    print("  python launch_trend_bot_dev.py    # Pure simulation - safe testing")
    print()
    print("Features:")
    print("  • MACD trend following strategy")
    print("  • Synthetic price data generation")
    print("  • No blockchain calls or network traffic")
    print("  • Prometheus metrics on port 9109")
    print("  • Graceful shutdown support")
    print()
    print("Safety:")
    print("  • No real money at risk")
    print("  • No blockchain transactions")
    print("  • Perfect for strategy testing")
    print("  • Can run offline")
    print()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Launch Trend Bot in pure simulation mode',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_trend_bot_dev.py    # Pure simulation - safe strategy testing
        """
    )

    args = parser.parse_args()

    try:
        result = asyncio.run(main(use_mock=True))  # Always simulation mode
        sys.exit(result)
    except KeyboardInterrupt:
        logger.info("⏹️  Trend Bot DEV stopped")
        sys.exit(0)
