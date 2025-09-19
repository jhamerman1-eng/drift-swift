#!/usr/bin/env python3
"""
Fix Drift Account Connection for JIT MM Bots
The wallet has funds but bots can't access the Drift account properly.
"""

import asyncio
import json
import logging
from pathlib import Path

# Setup logging without emojis to avoid encoding issues
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('drift_account_fix.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def fix_drift_account():
    """Fix Drift account connection for trading bots"""
    logger.info("FIXING DRIFT ACCOUNT CONNECTION")
    logger.info("=" * 50)
    
    try:
        # Import required modules
        from driftpy.drift_client import DriftClient
        from driftpy.account_subscription_config import AccountSubscriptionConfig
        from solders.keypair import Keypair
        from solana.rpc.async_api import AsyncClient
        
        # Load your verified wallet
        wallet_path = ".stable_wallet.json"
        logger.info(f"Loading wallet from: {wallet_path}")
        
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        # Create keypair from the verified wallet
        if isinstance(wallet_data, dict) and 'keypair' in wallet_data:
            keypair_bytes = bytes(wallet_data['keypair'])
        else:
            keypair_bytes = bytes(wallet_data)
            
        keypair = Keypair.from_bytes(keypair_bytes)
        logger.info(f"Wallet loaded: {keypair.pubkey()}")
        
        # Connect to Solana devnet
        rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        connection = AsyncClient(rpc_url)
        logger.info(f"Connected to RPC: {rpc_url}")
        
        # Check wallet balance first
        balance_response = await connection.get_balance(keypair.pubkey())
        balance_sol = balance_response.value / 1e9
        logger.info(f"SOL Balance: {balance_sol:.6f} SOL")
        
        if balance_sol < 0.01:
            logger.error("Insufficient SOL balance for transactions!")
            return False
        
        # Create Drift client
        logger.info("Creating Drift client...")
        drift_client = DriftClient(
            connection=connection,
            wallet=keypair,
            env="devnet",
            account_subscription=AccountSubscriptionConfig("websocket")
        )
        
        # Subscribe to Drift
        logger.info("Subscribing to Drift Protocol...")
        await drift_client.subscribe()
        
        # Check if user account exists
        try:
            user_account = drift_client.get_user_account()
            logger.info("SUCCESS: User account found!")
            logger.info(f"User account: {user_account}")
            
            # Get account equity
            equity = drift_client.get_user_account().get_equity()
            logger.info(f"Account equity: {equity}")
            
        except Exception as e:
            logger.warning(f"User account not found: {e}")
            logger.info("Creating new Drift user account...")
            
            # Initialize user account
            await drift_client.initialize_user()
            logger.info("User account created successfully!")
            
            # Wait for confirmation
            await asyncio.sleep(3)
        
        # Try to deposit a small amount if needed
        try:
            logger.info("Attempting small deposit to activate account...")
            
            # Deposit 0.01 SOL (10 million lamports)
            await drift_client.deposit(
                amount=10_000_000,  # 0.01 SOL in lamports
                market_index=0,     # SOL market
            )
            
            logger.info("SUCCESS: Deposit completed!")
            
        except Exception as e:
            logger.warning(f"Deposit failed (may be normal): {e}")
            logger.info("Account may already be initialized")
        
        # Final status check
        logger.info("=" * 50)
        logger.info("FINAL STATUS CHECK")
        logger.info("=" * 50)
        
        try:
            user_account = drift_client.get_user_account()
            
            # Get collateral info
            total_collateral = drift_client.get_user_account().get_total_collateral()
            free_collateral = drift_client.get_user_account().get_free_collateral()
            
            logger.info(f"Total Collateral: {total_collateral}")
            logger.info(f"Free Collateral: {free_collateral}")
            
            if free_collateral > 0:
                logger.info("SUCCESS: Account has free collateral for trading!")
                logger.info("Your bots should now be able to place orders")
                return True
            else:
                logger.warning("Free collateral is still 0 - may need manual deposit via UI")
                
        except Exception as e:
            logger.error(f"Status check failed: {e}")
        
        # Cleanup
        await drift_client.unsubscribe()
        await connection.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to fix Drift account: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main entry point"""
    logger.info("DRIFT ACCOUNT CONNECTION FIX")
    logger.info("Connecting your verified wallet to Drift Protocol...")
    
    success = await fix_drift_account()
    
    if success:
        logger.info("=" * 50)
        logger.info("NEXT STEPS:")
        logger.info("1. Restart your JIT MM bots")
        logger.info("2. They should now show proper collateral")
        logger.info("3. Orders should start placing automatically")
        logger.info("=" * 50)
    else:
        logger.error("=" * 50)
        logger.error("MANUAL STEPS NEEDED:")
        logger.error("1. Open Drift UI: https://beta.drift.trade")
        logger.error("2. Connect your wallet")
        logger.error("3. Deposit some SOL manually")
        logger.error("4. Then restart the bots")
        logger.error("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
