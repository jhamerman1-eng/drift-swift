#!/usr/bin/env python3
"""
Advanced Bot Orchestrator Launcher
Easy-to-use launcher for the advanced orchestrator with health monitoring and auto-restart

Usage:
  python launch_advanced_orchestrator.py          # Use default config
  python launch_advanced_orchestrator.py --config configs/core/drift_client.yaml
  python launch_advanced_orchestrator.py --metrics-port 9100 --health-port 9124

Features:
- Health monitoring with HTTP endpoints (/health, /ready, /status)
- Automatic restart with backoff on bot failures
- Prometheus metrics collection
- Centralized environment management
- Graceful shutdown handling
"""

import argparse
import os
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Advanced Bot Orchestrator Launcher")
    parser.add_argument("--config", default="configs/core/drift_client.yaml",
                       help="Path to configuration file")
    parser.add_argument("--metrics-port", type=int, default=9100,
                       help="Prometheus metrics port")
    parser.add_argument("--health-port", type=int, default=9124,
                       help="Health server port")
    parser.add_argument("--env", default="devnet",
                       help="Environment (devnet/mainnet)")

    args = parser.parse_args()

    # Set environment variables for the orchestrator
    os.environ["METRICS_PORT"] = str(args.metrics_port)
    os.environ["HEALTH_PORT"] = str(args.health_port)
    os.environ["DRIFT_ENV"] = args.env

    # Check if config file exists
    if not Path(args.config).exists():
        print(f"⚠️  Config file not found: {args.config}")
        print("Using default environment variables...")

    print("🚀 Launching Advanced Bot Orchestrator")
    print("=" * 50)
    print(f"📊 Metrics server: http://localhost:{args.metrics_port}")
    print(f"🏥 Health server: http://localhost:{args.health_port}")
    print(f"⚙️  Config: {args.config}")
    print(f"🌐 Environment: {args.env}")
    print()
    print("Health Endpoints:")
    print("  /health - Health check")
    print("  /ready  - Readiness check")
    print("  /status - Detailed status")
    print()
    print("Press Ctrl+C to stop all bots")
    print("=" * 50)

    # Import and run the advanced orchestrator
    try:
        from orchestrator.master import main as orchestrator_main
        sys.exit(orchestrator_main())
    except ImportError as e:
        print(f"❌ Failed to import orchestrator: {e}")
        print("Make sure you're in the correct directory and all dependencies are installed")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Orchestrator stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()


