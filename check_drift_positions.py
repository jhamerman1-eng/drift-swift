#!/usr/bin/env python3
"""
Check current positions on Drift protocol
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

from driftpy.drift_client import DriftClient
from driftpy.keypair import load_keypair
from solana.rpc.async_api import AsyncClient
from anchorpy import Wallet
from driftpy.constants.numeric_constants import QUOTE_PRECISION, BASE_PRECISION
from driftpy.math.margin import MarginCategory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("position-checker")

async def check_positions():
    """Check current positions on Drift protocol"""
    try:
        logger.info("🔍 Checking Drift Protocol Positions")
        logger.info("=" * 50)
        
        # Load configuration
        config_path = Path("configs/core/drift_client.yaml")
        if not config_path.exists():
            logger.error("Config file not found: configs/core/drift_client.yaml")
            return
        
        import yaml
        with config_path.open("r") as f:
            config = yaml.safe_load(f)
        
        # Load wallet
        keypair_src = config.get("wallets", {}).get("maker_keypair_path") or os.getenv("DRIFT_KEYPAIR_PATH")
        if not keypair_src:
            logger.error("Wallet not configured")
            return
            
        keypair = load_keypair(keypair_src)
        wallet = Wallet(keypair)
        logger.info(f"Wallet: {wallet.public_key}")
        
        # Create DriftPy client
        rpc_url = config.get("rpc", {}).get("http_url") or os.getenv("DRIFT_RPC_URL")
        if not rpc_url:
            logger.error("RPC URL not configured")
            return
        
        drift_client = DriftClient(
            connection=AsyncClient(rpc_url),
            wallet=wallet,
            env="devnet"
        )
        
        # Subscribe to updates
        await drift_client.subscribe()
        logger.info("Connected to Drift protocol")
        
        # Get user account
        user_account = drift_client.get_user_account()
        if not user_account:
            logger.error("No user account found - need to create account first")
            return
        
        logger.info(f"User account: {user_account.authority}")
        
        # Get DriftUser for detailed position info
        drift_user = drift_client.get_user()
        
        # Check collateral status
        try:
            total_collateral = drift_user.get_total_collateral(MarginCategory.INITIAL, strict=True)
            free_collateral = drift_user.get_free_collateral(MarginCategory.INITIAL)
            margin_requirement = drift_user.get_margin_requirement(MarginCategory.INITIAL, strict=True)
            
            logger.info(f"💰 Collateral Status:")
            logger.info(f"   Total Collateral: ${total_collateral/QUOTE_PRECISION:.2f} USD")
            logger.info(f"   Free Collateral: ${free_collateral/QUOTE_PRECISION:.2f} USD")
            logger.info(f"   Margin Requirement: ${margin_requirement/QUOTE_PRECISION:.2f} USD")
            logger.info(f"   Utilization: {(margin_requirement/total_collateral*100):.1f}%" if total_collateral > 0 else "   Utilization: N/A")
        except Exception as e:
            logger.warning(f"Could not get collateral info: {e}")
        
        # Check perp positions
        logger.info(f"\n📊 Perpetual Positions:")
        perp_positions = drift_user.get_active_perp_positions()
        
        if not perp_positions:
            logger.info("   No active perpetual positions")
        else:
            total_perp_value = 0
            for i, pos in enumerate(perp_positions):
                if pos.base_asset_amount != 0 or pos.quote_asset_amount != 0:
                    base_amount = pos.base_asset_amount / BASE_PRECISION
                    quote_amount = pos.quote_asset_amount / QUOTE_PRECISION
                    
                    logger.info(f"   Position {i}:")
                    logger.info(f"     Market Index: {pos.market_index}")
                    logger.info(f"     Base Amount: {base_amount:.6f} SOL")
                    logger.info(f"     Quote Amount: ${quote_amount:.2f} USD")
                    logger.info(f"     Last Cumulative Interest: {pos.last_cumulative_funding_rate}")
                    
                    # Calculate position value
                    try:
                        # Get current oracle price
                        oracle_data = drift_client.get_oracle_price_data_for_perp_market(pos.market_index)
                        from driftpy.math.conversion import convert_to_number
                        oracle_price = convert_to_number(oracle_data.price)
                        
                        position_value = base_amount * oracle_price
                        total_perp_value += position_value
                        
                        logger.info(f"     Position Value: ${position_value:.2f} USD (at ${oracle_price:.2f})")
                    except Exception as e:
                        logger.warning(f"     Could not calculate position value: {e}")
            
            logger.info(f"   Total Perp Value: ${total_perp_value:.2f} USD")
        
        # Check spot positions
        logger.info(f"\n💎 Spot Positions:")
        spot_positions = drift_user.get_active_spot_positions()
        
        if not spot_positions:
            logger.info("   No active spot positions")
        else:
            for i, pos in enumerate(spot_positions):
                if pos.scaled_balance != 0:
                    logger.info(f"   Spot Position {i}:")
                    logger.info(f"     Market Index: {pos.market_index}")
                    logger.info(f"     Scaled Balance: {pos.scaled_balance}")
                    logger.info(f"     Balance Type: {pos.balance_type}")
        
        # Check open orders
        logger.info(f"\n📋 Open Orders:")
        try:
            # Get user account for orders
            user_account = drift_client.get_user_account()
            open_orders = user_account.orders
            
            active_orders = [order for order in open_orders if order.status == 1]  # 1 = Open
            if not active_orders:
                logger.info("   No open orders")
            else:
                logger.info(f"   {len(active_orders)} open orders:")
                for i, order in enumerate(active_orders):
                    logger.info(f"     Order {i}:")
                    logger.info(f"       Market Index: {order.market_index}")
                    logger.info(f"       Side: {'Long' if order.direction == 0 else 'Short'}")
                    logger.info(f"       Price: ${order.price/QUOTE_PRECISION:.4f}")
                    logger.info(f"       Size: {order.base_asset_amount/BASE_PRECISION:.6f} SOL")
                    logger.info(f"       Status: {order.status}")
        except Exception as e:
            logger.warning(f"Could not get open orders: {e}")
        
        # Check if position limit is reached
        try:
            # This is where the -5000 position limit warning comes from
            # Let's see what the actual position is
            total_perp_position = 0
            for pos in perp_positions:
                if pos.base_asset_amount != 0:
                    total_perp_position += pos.base_asset_amount / BASE_PRECISION
            
            logger.info(f"\n⚠️  Position Analysis:")
            logger.info(f"   Total Perp Position: {total_perp_position:.6f} SOL")
            logger.info(f"   Position Limit: -5000.0000 SOL")
            
            if abs(total_perp_position) >= 5000:
                logger.warning(f"   🚨 POSITION LIMIT REACHED!")
                logger.warning(f"   Current position ({total_perp_position:.6f}) exceeds limit (5000)")
            else:
                logger.info(f"   ✅ Position within limits")
                
        except Exception as e:
            logger.warning(f"Could not analyze position limits: {e}")
        
        await drift_client.unsubscribe()
        logger.info("\n✅ Position check complete")
        
    except Exception as e:
        logger.error(f"Error checking positions: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_positions())












