import asyncio
import json
import yaml
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solana.rpc.commitment import Commitment

async def airdrop_sol():
    # Load configuration
    cfg = yaml.safe_load(open("configs/core/drift_client.yaml", "r", encoding="utf-8"))
    secret = json.load(open(cfg["wallets"]["maker_keypair_path"], "r", encoding="utf-8"))
    kp = Keypair.from_bytes(bytes(secret))
    
    # Connect to devnet
    conn = AsyncClient(cfg["rpc"]["http_url"])
    
    try:
        print(f"Airdropping 2 SOL to wallet: {kp.pubkey()}")
        
        # Request airdrop
        result = await conn.request_airdrop(
            kp.pubkey(), 
            2_000_000_000,  # 2 SOL in lamports
            commitment=Commitment("confirmed")
        )
        
        if result.value:
            print(f"Airdrop successful! Signature: {result.value}")
            
            # Wait for confirmation
            print("Waiting for confirmation...")
            await asyncio.sleep(5)
            
            # Check new balance
            balance = await conn.get_balance(kp.pubkey())
            print(f"New wallet balance: {balance.value / 1e9:.6f} SOL")
        else:
            print("Airdrop failed")
            
    except Exception as e:
        print(f"Error during airdrop: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(airdrop_sol())
