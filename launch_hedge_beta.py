#!/usr/bin/env python3
"""
Hedge Bot - Beta.Drift.Trade Launcher
Launches the Hedge Bot specifically in the beta.drift.trade environment.
"""

import asyncio
import logging
import sys
import os
import io
from pathlib import Path
from typing import Dict, Any

# Add libs directory to path
sys.path.append(str(Path(__file__).parent / "libs"))

# Fix Windows console encoding issues
def ensure_utf8_console():
    """Ensure Windows console can handle UTF-8 characters."""
    # Set environment variables for UTF-8
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "UTF-8")

    try:
        # Try to reconfigure stdout/stderr for UTF-8
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        else:
            # Fallback for older Python versions
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

    # Prevent logging from crashing on encoding errors
    logging.raiseExceptions = False

# Apply the fix
ensure_utf8_console()

# Hedge sizing guards to prevent division by zero (will be loaded from config)
EPS_PRICE   = 1e-6
EPS_ATR     = 1e-9
MIN_EQUITY  = 1e-2  # $0.01

def safe_hedge_sizing(delta_usd: float, mid: float|None, atr: float|None, equity_usd: float|None):
    """
    Returns (qty, reason). If qty is None, action is SKIP and 'reason' explains why.
    """
    # 0) No delta → nothing to do
    if abs(delta_usd) < 1e-6:
        return None, "NO_DELTA"

    # 1) Validate preconditions commonly missing at startup / SIM
    if mid is None or mid <= EPS_PRICE:
        return None, "NO_PRICE"

    if equity_usd is None or equity_usd <= MIN_EQUITY:
        return None, "NO_EQUITY"

    # 2) Urgency guarded against ATR=0
    atr_val = abs(atr or 0.0)
    urgency = abs(delta_usd) / max(atr_val, EPS_ATR)
    if not (urgency == urgency):  # NaN check
        urgency = 0.0
    urgency = min(urgency, 10.0)

    # 3) Size in contracts: $delta / price (guarded)
    qty = - delta_usd / max(abs(mid), EPS_PRICE)

    if abs(qty) < 1e-6:
        return None, "DUST"

    return qty, f"urgency={urgency:.2f}"

# Configure logging
    handlers=[
        logging.FileHandler('hedge_beta.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import bot components
from libs.drift.client import build_client_from_config, DriftpyClient
from libs.order_management import PositionTracker, OrderManager
from orchestrator.risk_manager import RiskManager
from bots.hedge.main import hedge_iteration
from libs.rpc_manager import RPCManager, DEFAULT_RPC_CONFIG, load_rpc_config_from_file

# Load hedge guardrails from config
def load_hedge_guardrails():
    """Load hedge guardrails from config file and update global variables."""
    global EPS_PRICE, EPS_ATR, MIN_EQUITY

    try:
        import yaml
        import os
        config_path = os.path.join(os.path.dirname(__file__), "configs", "hedge", "routing.yaml")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                hedge_config = yaml.safe_load(f)

            guardrails = hedge_config.get('hedge', {}).get('guardrails', {})
            if guardrails:
                EPS_PRICE = guardrails.get('eps_price', EPS_PRICE)
                EPS_ATR = guardrails.get('eps_atr', EPS_ATR)
                MIN_EQUITY = guardrails.get('min_equity_usd', MIN_EQUITY)
                logger.info("[CONFIG] Loaded hedge guardrails from routing.yaml")
                logger.info(f"[CONFIG] EPS_PRICE: {EPS_PRICE}, EPS_ATR: {EPS_ATR}, MIN_EQUITY: {MIN_EQUITY}")
                return True
    except Exception as e:
        logger.warning(f"[CONFIG] Could not load hedge guardrails: {e}")

    logger.warning("[CONFIG] Using default guardrail values")
    return False

# Load the guardrails
load_hedge_guardrails()

class HedgeBetaLauncher:
    """Launcher for Hedge Bot in beta.drift.trade environment."""

    def __init__(self):
        self.client = None
        self.position_tracker = PositionTracker()
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager()
        self.iteration_count = 0
        self.errors = []
        self.rpc_manager = RPCManager()
        self.current_env = 'mainnet'  # Default environment

    async def setup_rpc_manager(self, environment: str = 'mainnet'):
        """Setup RPC manager with endpoints for the specified environment."""
        logger.info(f"[RPC] Setting up RPC manager for {environment} environment")
        
        # Try to load from configuration file first
        config = load_rpc_config_from_file()
        
        if config and environment in config:
            logger.info(f"[RPC] Using configuration from configs/rpc_endpoints.yaml")
            self.rpc_manager.add_endpoints_from_config(config)
            logger.info(f"[RPC] Loaded {len(self.rpc_manager.endpoints)} endpoints for {environment}")
        elif environment in DEFAULT_RPC_CONFIG:
            logger.info(f"[RPC] Using default configuration for {environment}")
            self.rpc_manager.add_endpoints_from_config(DEFAULT_RPC_CONFIG)
            logger.info(f"[RPC] Loaded {len(self.rpc_manager.endpoints)} endpoints for {environment}")
        else:
            logger.warning(f"[RPC] No configuration found for {environment}, using fallback endpoints")
            # Add fallback endpoints
            fallback_endpoints = [
                {
                    'name': 'Solana Labs',
                    'http': 'https://api.mainnet-beta.solana.com',
                    'ws': 'wss://api.mainnet-beta.solana.com',
                    'priority': 50,
                    'max_rps': 50,
                    'timeout': 10.0,
                    'retry_after': 30.0
                }
            ]
            
            for endpoint_data in fallback_endpoints:
                from libs.rpc_manager import RPCEndpoint
# Setup centralized logging
from libs.logging_config import setup_critical_logging
logger = setup_critical_logging("hedge-bot")
                endpoint = RPCEndpoint(
                    name=endpoint_data['name'],
                    http_url=endpoint_data['http'],
                    ws_url=endpoint_data['ws'],
                    priority=endpoint_data['priority'],
                    max_requests_per_second=endpoint_data['max_rps'],
                    timeout=endpoint_data['timeout'],
                    retry_after_rate_limit=endpoint_data['retry_after']
                )
                self.rpc_manager.add_endpoint(endpoint)
        
        # Start health monitoring
        self.rpc_manager.start_health_monitoring()
        
        # Test initial connectivity
        working_endpoint = await self.rpc_manager.select_best_endpoint()
        if working_endpoint:
            logger.info(f"[RPC] ✅ Initial endpoint selected: {working_endpoint.name}")
            return True
        else:
            logger.error("[RPC] ❌ No working endpoints found")
            return False

    async def initialize_beta_client(self) -> bool:
        """Initialize Drift client for beta environment."""
        try:
            logger.info("[INIT] Initializing Drift client for beta.drift.trade...")

            # Set beta environment variables
            os.environ['ENV'] = 'mainnet'
            self.current_env = 'mainnet'

            # Setup RPC manager with automatic failover
            if not await self.setup_rpc_manager('mainnet'):
                logger.error("[RPC] Failed to setup RPC manager - aborting")
                return False

            # Get current working endpoint and set environment variables
            current_endpoint = self.rpc_manager.current_endpoint
            if current_endpoint:
                os.environ['DRIFT_HTTP_URL'] = current_endpoint.http_url
                os.environ['DRIFT_WS_URL'] = current_endpoint.ws_url
                logger.info(f"[RPC] Using {current_endpoint.name} RPC endpoint")
            else:
                logger.error("[RPC] No working RPC endpoint available")
                return False

            os.environ['USE_MOCK'] = 'false'  # Use real client for beta

            # Build client from config
            self.client = await build_client_from_config('configs/core/drift_client.yaml')

            if isinstance(self.client, DriftpyClient):
                logger.info("[SUCCESS] DriftpyClient initialized for beta")
                logger.info("[INFO] Connected to: https://beta.drift.trade")
                logger.info("[INFO] Using simulation mode - orders will be logged but not executed")
                logger.warning("[WARNING] This is a SIMULATION - no real orders will be placed!")
                logger.warning("[INFO] To place real orders, use the working DriftpyClient from drift-bots/ directory")

                # Client is ready to use (no initialization needed for simulation)
                return True
            else:
                logger.error("[ERROR] Expected DriftpyClient but got different client type")
                return False

        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize beta client: {e}")
            self.errors.append(f"Client initialization failed: {e}")
            return False

    async def check_wallet_status(self) -> bool:
        """Check wallet balance and connection."""
        try:
            if not hasattr(self.client, 'solana_client') or not self.client.solana_client:
                logger.warning("[WARNING] No Solana client available")
                return False

            if not hasattr(self.client, 'keypair'):
                logger.warning("[WARNING] No wallet keypair available")
                return False

            # Get balance
            balance = await self.client.solana_client.get_balance(self.client.keypair.pubkey())
            balance_sol = balance.value / 1e9

            logger.info("[BALANCE] Beta Wallet Status:")
            logger.info(f"   Address: {self.client.keypair.pubkey()}")
            logger.info(f"   Balance: {balance_sol:.4f} SOL")
            if balance_sol < 0.01:
                logger.warning("[WARNING] LOW BALANCE - Need SOL for beta trading")
                logger.warning("[INFO] Get SOL from: https://faucet.solana.com")
                logger.warning(f"[INFO] Send to: {self.client.keypair.pubkey()}")
                return False
            else:
                logger.info("[SUCCESS] Sufficient balance for beta trading")
                return True

        except Exception as e:
            logger.error(f"[ERROR] Error checking wallet status: {e}")
            return False

    async def run_hedge_trading_loop(self):
        """Main hedge trading loop for beta environment."""
        logger.info("[TRADE] Starting Hedge Bot trading loop on beta.drift.trade...")
        logger.info("[INFO] View positions at: https://beta.drift.trade")

        # Beta-specific hedge configuration (conservative)
        hedge_cfg = {
            "hedge": {
                "max_inventory_usd": 100.0,  # Conservative for beta
                "urgency_threshold": 0.7,
                "ioc": {"max_slippage_bps": 5},
                "passive": {"max_slippage_bps": 2}
            }
        }

        while True:
            try:
                self.iteration_count += 1
                logger.info(f"[TRADE] Starting beta hedge iteration #{self.iteration_count}")

                                # Run hedge iteration with safe sizing guards and RPC failover
                try:
                    await hedge_iteration(hedge_cfg, self.client, self.risk_manager,
                                    self.position_tracker, self.order_manager)
                except ZeroDivisionError as e:
                    logger.warning(f"[HEDGE][GUARD] Caught division by zero in hedge_iteration: {e}")
                    logger.warning("[HEDGE][GUARD] This indicates ATR/price/equity are zero - continuing safely")
                except Exception as e:
                    # Check if this is an RPC-related error that might benefit from failover
                    error_msg = str(e).lower()
                    if any(keyword in error_msg for keyword in ['rpc', 'connection', 'timeout', '429', 'rate limit']):
                        logger.warning(f"[RPC] RPC-related error detected: {e}")
                        logger.info("[RPC] Attempting to switch to backup RPC endpoint...")
                        
                        # Try to switch to a different RPC endpoint
                        new_endpoint = await self.rpc_manager.select_best_endpoint()
                        if new_endpoint and new_endpoint != self.rpc_manager.current_endpoint:
                            logger.info(f"[RPC] Switched to backup endpoint: {new_endpoint.name}")
                            # Update environment variables for next iteration
                            os.environ['DRIFT_HTTP_URL'] = new_endpoint.http_url
                            os.environ['DRIFT_WS_URL'] = new_endpoint.ws_url
                        else:
                            logger.warning("[RPC] No backup endpoint available")
                    
                    # Re-raise the exception for now (you might want to handle this differently)
                    raise

                # Log status
                logger.info("[STATUS] Beta Hedge Iteration Status:")
                logger.info(f"   Net Exposure: ${self.position_tracker.net_exposure:.2f}")
                logger.info(f"   Total Volume: ${self.position_tracker.volume:.2f}")
                logger.info(f"   Open Orders: {len(self.order_manager._orders)}")
                
                # Log RPC status
                rpc_status = self.rpc_manager.get_status_summary()
                logger.info(f"   RPC Status: {rpc_status['current_endpoint']} ({rpc_status['available_endpoints']}/{rpc_status['total_endpoints']} available)")

                # Check if we have positions to display
                if hasattr(self.client, 'get_positions'):
                    positions = self.client.get_positions()
                    if positions:
                        logger.info(f"   Active Positions: {len(positions)}")
                        for pos in positions:
                            logger.info(f"      {pos.market}: {pos.size:.4f} @ ${pos.avg_price:.4f}")
                    else:
                        logger.info("   Active Positions: None")

                risk_state = self.risk_manager.evaluate(self.position_tracker.net_exposure)
                logger.info(f"   Risk State: Drawdown {risk_state.drawdown_pct:.2f}%")

                # Check balance every 5 iterations
                if self.iteration_count % 5 == 0:
                    await self.check_wallet_status()

                # Wait before next iteration (slightly slower for beta)
                await asyncio.sleep(8)

            except Exception as e:
                logger.error(f"[ERROR] Error in beta hedge iteration {self.iteration_count}: {e}")
                self.errors.append(f"Iteration {self.iteration_count} error: {e}")

                # Wait longer after errors
                await asyncio.sleep(15)

    async def run(self):
        """Main execution method for beta hedge trading."""
        logger.info("[LAUNCH] Starting Hedge Bot for beta.drift.trade")
        logger.info("=" * 70)
        logger.info("[IMPORTANT] This will place REAL orders on beta.drift.trade!")
        logger.info("[INFO] Beta environment uses real SOL but testnet conditions")
        logger.info("=" * 70)

        try:
            # Step 1: Initialize beta client
            if not await self.initialize_beta_client():
                logger.error("[ERROR] Beta client initialization failed - aborting")
                return

            # Step 2: Check wallet status
            if not await self.check_wallet_status():
                logger.error("[ERROR] Wallet check failed - aborting")
                return

            # Step 3: Start hedge trading loop
            logger.info("[STARTING] Beginning REAL beta hedge trading session...")
            logger.info(f"[INFO] Wallet: {self.client.keypair.pubkey()}")
            logger.info("[INFO] View trades on: https://beta.drift.trade")

            await self.run_hedge_trading_loop()

        except KeyboardInterrupt:
            logging.info("[SHUTDOWN] Received shutdown signal")
        except Exception as e:
            logging.error(f"[ERROR] Fatal error in beta execution: {e}")
            self.errors.append(f"Fatal error: {e}")
        finally:
            # Cleanup
            logging.info("[CLEANUP] Starting cleanup...")

            if self.client and hasattr(self.client, 'close'):
                try:
                    await self.client.close()
                    logging.info("[SUCCESS] Beta client closed successfully")
                except Exception as e:
                    logging.error(f"[ERROR] Error closing beta client: {e}")

            # Final summary
            logging.info("=" * 70)
            logging.info("[SUMMARY] BETA HEDGE TRADING SESSION COMPLETE")
            logging.info("=" * 70)
            logging.info(f"Total Iterations: {self.iteration_count}")
            logging.info(f"Net Exposure: ${self.position_tracker.net_exposure:.2f}")
            logging.info(f"Total Volume: ${self.position_tracker.volume:.2f}")
            
            # RPC Summary
            if hasattr(self, 'rpc_manager'):
                rpc_summary = self.rpc_manager.get_status_summary()
                logging.info("=" * 70)
                logging.info("[RPC SUMMARY] RPC Endpoint Performance")
                logging.info("=" * 70)
                logging.info(f"Current Endpoint: {rpc_summary['current_endpoint']}")
                logging.info(f"Total Endpoints: {rpc_summary['total_endpoints']}")
                logging.info(f"Available Endpoints: {rpc_summary['available_endpoints']}")
                logging.info(f"Failover Count: {rpc_summary['failover_count']}")
                
                for name, health in rpc_summary['endpoints'].items():
                    logging.info(f"  {name}: {health['status']} (errors: {health['error_count']})")

            if self.errors:
                logging.warning(f"Errors Encountered: {len(self.errors)}")
                for i, error in enumerate(self.errors[-5:], 1):  # Show last 5
                    logging.warning(f"  {i}. {error}")
            else:
                logging.info("Errors: None - Clean beta session!")

            logging.info("=" * 70)

async def main():
    """Entry point."""
    launcher = HedgeBetaLauncher()
    await launcher.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("[SHUTDOWN] Beta hedge bot interrupted by user")
    except Exception as e:
        logging.error(f"[ERROR] Beta hedge bot failed: {e}")
        sys.exit(1)
