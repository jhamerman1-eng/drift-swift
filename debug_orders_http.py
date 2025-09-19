#!/usr/bin/env python3
"""
ULTIMATE DEBUG: Query Drift data via HTTP RPC - no dependencies
"""
import asyncio
import logging
import json
import httpx
from base58 import b58decode, b58encode
from solders.keypair import Keypair

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

async def debug_via_rpc():
    """Get real data directly from Solana RPC"""
    try:
        logger.info("=== ULTIMATE DEBUG: Direct RPC queries ===")
        
        # Load wallet
        with open('.valid_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        
        if isinstance(wallet_data, dict) and 'keypair' in wallet_data:
            keypair_data = wallet_data['keypair']
        else:
            keypair_data = wallet_data
            
        keypair = Keypair.from_bytes(bytes(keypair_data))
        wallet_pubkey = str(keypair.pubkey())
        logger.info(f"Wallet: {wallet_pubkey}")
        
        # RPC endpoint
        rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            
            # === STEP 1: Get user account data ===
            logger.info("\n=== Getting User Account Data ===")
            
            # Drift program ID on devnet
            drift_program_id = "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH"
            
            # Get program accounts owned by our wallet
            params = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getProgramAccounts",
                "params": [
                    drift_program_id,
                    {
                        "filters": [
                            {
                                "memcmp": {
                                    "offset": 8,  # Skip discriminator
                                    "bytes": wallet_pubkey
                                }
                            }
                        ],
                        "encoding": "base64"
                    }
                ]
            }
            
            response = await client.post(rpc_url, json=params)
            data = response.json()
            
            if "result" in data:
                accounts = data["result"]
                logger.info(f"Found {len(accounts)} Drift accounts for wallet")
                
                for i, account in enumerate(accounts):
                    logger.info(f"Account {i}: {account['pubkey']}")
                    
            else:
                logger.error(f"RPC Error: {data}")
            
            # === STEP 2: Query SOL balance ===
            logger.info("\n=== Getting SOL Balance ===")
            
            params = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [wallet_pubkey]
            }
            
            response = await client.post(rpc_url, json=params)
            data = response.json()
            
            if "result" in data:
                balance = data["result"]["value"] / 1e9  # Convert lamports to SOL
                logger.info(f"SOL Balance: {balance:.6f} SOL")
            else:
                logger.error(f"Balance Error: {data}")
            
            # === STEP 3: Get recent transactions ===
            logger.info("\n=== Getting Recent Transactions ===")
            
            params = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    wallet_pubkey,
                    {"limit": 10}
                ]
            }
            
            response = await client.post(rpc_url, json=params)
            data = response.json()
            
            if "result" in data:
                transactions = data["result"]
                logger.info(f"Recent transactions: {len(transactions)}")
                
                for tx in transactions[:5]:  # Show last 5
                    logger.info(f"TX: {tx['signature'][:16]}... (slot {tx.get('slot', 'N/A')})")
                    
            else:
                logger.error(f"Transactions Error: {data}")
                
        logger.info("\n=== ULTIMATE DEBUG COMPLETE ===")
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

# Additionally, let's check if there are ANY orders by checking recent transactions
async def check_recent_orders():
    """Check if there were recent order transactions"""
    try:
        logger.info("\n=== CHECKING FOR RECENT ORDER ACTIVITY ===")
        
        # Load wallet
        with open('.valid_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        
        if isinstance(wallet_data, dict) and 'keypair' in wallet_data:
            keypair_data = wallet_data['keypair']
        else:
            keypair_data = wallet_data
            
        keypair = Keypair.from_bytes(bytes(keypair_data))
        wallet_pubkey = str(keypair.pubkey())
        
        rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get recent signatures
            params = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    wallet_pubkey,
                    {"limit": 50}
                ]
            }
            
            response = await client.post(rpc_url, json=params)
            data = response.json()
            
            if "result" in data:
                transactions = data["result"]
                
                # Count order-related transactions
                place_orders = 0
                cancel_orders = 0
                
                for tx in transactions:
                    # Get transaction details
                    tx_params = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getTransaction",
                        "params": [
                            tx["signature"],
                            {"encoding": "json", "maxSupportedTransactionVersion": 0}
                        ]
                    }
                    
                    tx_response = await client.post(rpc_url, json=tx_params)
                    tx_data = tx_response.json()
                    
                    if "result" in tx_data and tx_data["result"]:
                        logs = tx_data["result"]["meta"].get("logMessages", [])
                        
                        for log in logs:
                            if "PlacePerpOrder" in log:
                                place_orders += 1
                                logger.info(f"PLACE ORDER found: {tx['signature'][:16]}...")
                                break
                            elif "CancelOrder" in log:
                                cancel_orders += 1
                                logger.info(f"CANCEL ORDER found: {tx['signature'][:16]}...")
                                break
                    
                    # Don't hammer the RPC
                    await asyncio.sleep(0.1)
                
                logger.info(f"Recent activity: {place_orders} place orders, {cancel_orders} cancel orders")
                
    except Exception as e:
        logger.error(f"Order check error: {e}")

async def main():
    await debug_via_rpc()
    await check_recent_orders()

if __name__ == "__main__":
    asyncio.run(main())
