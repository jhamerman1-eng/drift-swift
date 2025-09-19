#!/usr/bin/env python3
"""
Test Collateral Calculation - Debug why free collateral is $0.00
"""

import asyncio
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_collateral_calculation():
    """Test the exact collateral calculation the bot uses"""
    logger.info("TESTING COLLATERAL CALCULATION")
    logger.info("=" * 50)
    
    try:
        from driftpy.drift_client import DriftClient
        from driftpy.account_subscription_config import AccountSubscriptionConfig
        from solders.keypair import Keypair
        from solana.rpc.async_api import AsyncClient
        
        # Load wallet
        with open(".stable_wallet.json", 'r') as f:
            wallet_data = json.load(f)
        
        keypair_bytes = bytes(wallet_data['keypair'])
        keypair = Keypair.from_bytes(keypair_bytes)
        logger.info(f"Wallet: {keypair.pubkey()}")
        
        # Connect
        connection = AsyncClient("https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494")
        
        drift_client = DriftClient(
            connection=connection,
            wallet=keypair,
            env="devnet",
            account_subscription=AccountSubscriptionConfig("websocket")
        )
        
        await drift_client.subscribe()
        logger.info("Connected to Drift")
        
        # Get user account
        drift_user = drift_client.get_user()
        user_account = drift_user.get_user_account()
        
        logger.info("=== SPOT POSITIONS ===")
        total_collateral_value = 0.0
        for i, spot_pos in enumerate(user_account.spot_positions):
            if spot_pos.scaled_balance > 0 and str(spot_pos.balance_type) == "SpotBalanceType.Deposit()":
                logger.info(f"Position {i}: Market {spot_pos.market_index}, Balance: {spot_pos.scaled_balance}")
                
                if spot_pos.market_index == 0:  # SOL
                    sol_balance = spot_pos.scaled_balance / 1e9
                    try:
                        market = drift_user.get_perp_market_account(0)
                        sol_price = float(market.amm.last_oracle_price) / 1e6
                        usd_value = sol_balance * sol_price
                        total_collateral_value += usd_value
                        logger.info(f"  SOL: {sol_balance:.4f} @ ${sol_price:.2f} = ${usd_value:.2f}")
                    except Exception as e:
                        usd_value = sol_balance * 200
                        total_collateral_value += usd_value
                        logger.info(f"  SOL: {sol_balance:.4f} @ $200.00 = ${usd_value:.2f} (fallback)")
                elif spot_pos.market_index == 1:  # USDC
                    usdc_balance = spot_pos.scaled_balance / 1e6
                    total_collateral_value += usdc_balance
                    logger.info(f"  USDC: {usdc_balance:.2f}")
        
        logger.info(f"TOTAL COLLATERAL: ${total_collateral_value:.2f}")
        
        logger.info("\n=== PERP POSITIONS ===")
        used_collateral_value = 0.0
        for i, perp_pos in enumerate(user_account.perp_positions):
            if perp_pos.base_asset_amount != 0:
                logger.info(f"Position {i}: Market {perp_pos.market_index}, Amount: {perp_pos.base_asset_amount}")
                logger.info(f"  Quote Amount: {perp_pos.quote_asset_amount}")
                logger.info(f"  Unrealized PnL: {perp_pos.quote_asset_amount / 1e6:.2f} USD")
                
                try:
                    market = drift_user.get_perp_market_account(perp_pos.market_index)
                    sol_price = float(market.amm.last_oracle_price) / 1e6
                    position_value = abs(perp_pos.base_asset_amount) / 1e9 * sol_price
                    
                    if perp_pos.base_asset_amount < 0:  # Short position
                        unrealized_pnl = perp_pos.quote_asset_amount / 1e6
                        if unrealized_pnl > 0:  # Profitable short
                            margin_used = position_value * 0.05
                            used_collateral_value += margin_used
                            logger.info(f"  Profitable short: ${position_value:.2f} value, ${margin_used:.2f} margin (5%)")
                        else:
                            margin_used = position_value * 0.1
                            used_collateral_value += margin_used
                            logger.info(f"  Unprofitable short: ${position_value:.2f} value, ${margin_used:.2f} margin (10%)")
                    else:  # Long position
                        margin_used = position_value * 0.1
                        used_collateral_value += margin_used
                        logger.info(f"  Long position: ${position_value:.2f} value, ${margin_used:.2f} margin (10%)")
                except Exception as e:
                    logger.info(f"  Error calculating position: {e}")
        
        logger.info(f"USED COLLATERAL: ${used_collateral_value:.2f}")
        
        free_collateral_value = total_collateral_value - used_collateral_value
        logger.info(f"FREE COLLATERAL: ${free_collateral_value:.2f}")
        
        if free_collateral_value > 0:
            logger.info("SUCCESS: Bot should be able to place orders!")
        else:
            logger.info("ISSUE: Free collateral is $0.00 - this explains why orders aren't placing")
        
        # Cleanup
        await drift_client.unsubscribe()
        await connection.close()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_collateral_calculation())
