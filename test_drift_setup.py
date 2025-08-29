import asyncio
import json
import yaml
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from anchorpy.provider import Wallet
from driftpy.drift_client import DriftClient
from driftpy.account_subscription_config import AccountSubscriptionConfig

# Load configuration
cfg = yaml.safe_load(open("configs/core/drift_client.yaml", "r", encoding="utf-8"))
secret = json.load(open(cfg["wallets"]["maker_keypair_path"], "r", encoding="utf-8"))
kp = Keypair.from_bytes(bytes(secret))
conn = AsyncClient(cfg["rpc"]["http_url"])
dc = DriftClient(
    connection=conn, 
    wallet=Wallet(kp), 
    env="devnet",
    account_subscription=AccountSubscriptionConfig.default()
)

async def main():
    # Check wallet balance first
    try:
        balance = await conn.get_balance(kp.pubkey())
        print(f"Wallet balance: {balance.value / 1e9:.6f} SOL")
        
        if balance.value < 0.01 * 1e9:  # Less than 0.01 SOL
            print("Wallet has insufficient SOL. Please airdrop some SOL first.")
            print("You can use: solana airdrop 2 <wallet_address> --url devnet")
            return
    except Exception as e:
        print(f"Error checking balance: {e}")
        return

    await dc.subscribe()
    try:
        dc.get_user_account(0)
        print("user exists ✓")
    except Exception as e:
        print(f"initializing user… (error: {e})")
        try:
            await dc.initialize_user(sub_account_id=0)
            await asyncio.sleep(1.0)
            dc.get_user_account(0)
            print("user ready ✓")
        except Exception as init_error:
            print(f"Failed to initialize user: {init_error}")
    await dc.connection.close()

if __name__ == "__main__":
    asyncio.run(main())
