#!/usr/bin/env python3
"""
Devnet bootstrap: ensure wallet funded, Drift user account exists, and report collateral.
Production-ready version with proper error handling, airdrop, and cleanup.
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from typing import Optional

from solders.pubkey import Pubkey as PublicKey
from solana.rpc.async_api import AsyncClient as AsyncSolClient

# Project client
from libs.drift.client import build_client_from_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("devnet_init")

DRIFT_CONFIG_PATH = "configs/core/drift_client.yaml"
DEFAULT_SUB_ACCOUNT = 0
DEVNET_RPC = os.getenv("SOLANA_RPC_DEVNET", "https://api.devnet.solana.com")
MIN_SOL_BAL = float(os.getenv("MIN_SOL_BAL", "1.0"))         # fund for tx fees etc.
AIRDROP_SOL = float(os.getenv("AIRDROP_SOL", "2.0"))         # one-shot airdrop amount
USER_WAIT_SECS = int(os.getenv("USER_WAIT_SECS", "20"))      # wait for user acct

@dataclass
class BootstrapResult:
    wallet_pubkey: str
    sol_balance: float
    user_created: bool
    total_collateral_usd: Optional[float]

async def airdrop_if_needed(sol_client: AsyncSolClient, pubkey: PublicKey) -> float:
    """Ensure the wallet has at least MIN_SOL_BAL (devnet)."""
    bal_resp = await sol_client.get_balance(pubkey)
    if "result" not in bal_resp or "value" not in bal_resp["result"]:
        raise RuntimeError(f"Unexpected balance response: {bal_resp}")
    lamports = bal_resp["result"]["value"]
    sol = lamports / 1_000_000_000
    logger.info(".6f")

    if sol >= MIN_SOL_BAL:
        return sol

    logger.info(".1f")
    sig_resp = await sol_client.request_airdrop(pubkey, int(AIRDROP_SOL * 1_000_000_000))
    sig = sig_resp.get("result")
    if not sig:
        raise RuntimeError(f"Airdrop failed: {sig_resp}")

    # Confirm quickly
    await sol_client.confirm_transaction(sig, commitment="confirmed")
    bal_resp = await sol_client.get_balance(pubkey, commitment="confirmed")
    lamports = bal_resp["result"]["value"]
    sol = lamports / 1_000_000_000
    logger.info(".6f")
    return sol

async def wait_for_user(client, sub_account: int, timeout_s: int) -> bool:
    """Poll until the Drift user is visible or timeout."""
    for i in range(timeout_s):
        try:
            # Use our client's public method to get user
            user = client.get_user(sub_account=sub_account)
            if user is not None:
                return True
        except Exception:
            pass
        await asyncio.sleep(1)
    return False

async def initialize_devnet_account() -> BootstrapResult:
    # 1) Load wallet (optional; used for display + sanity)
    try:
        with open(".stable_wallet.json", "r") as f:
            wallet_data = json.load(f)
        wallet_pubkey = wallet_data.get("public_key")
        if not wallet_pubkey:
            raise ValueError("Missing 'public_key' in .stable_wallet.json")
    except FileNotFoundError:
        logger.warning("⚠️ .stable_wallet.json not found. Proceeding with client's configured keypair.")
        wallet_pubkey = None

    # 2) Force devnet mode and build Drift client
    os.environ["DRIFT_ENV"] = "devnet"
    client = await build_client_from_config(DRIFT_CONFIG_PATH)

    try:
        await client.initialize()
        logger.info("✅ Drift client initialized (devnet)")

        # Get authority from client to ensure we fund the right wallet
        authority = str(client.authority)  # Use public property
        if wallet_pubkey and wallet_pubkey != authority:
            logger.warning(f"⚠️ Wallet file pubkey ({wallet_pubkey}) != client authority ({authority}). Using client authority.")
        wallet_pubkey = authority

        # 3) Ensure we have SOL on devnet (for tx fees & deposits)
        sol_client = AsyncSolClient(DEVNET_RPC)
        try:
            sol_balance = await airdrop_if_needed(sol_client, PublicKey.from_string(wallet_pubkey))
        finally:
            await sol_client.close()

        # 4) Ensure Drift user account exists
        user_created = False
        try:
            user = client.get_user(sub_account=DEFAULT_SUB_ACCOUNT)
            if user:
                logger.info("✅ Drift user account already exists")
            else:
                raise Exception("No user returned")
        except Exception:
            logger.info("📝 Creating Drift user account...")
            # Use our client's public initialization method (avoid private _driver)
            await client.initialize()  # This handles user account creation
            user_created = True

            # Wait for indexing/state
            ok = await wait_for_user(client, DEFAULT_SUB_ACCOUNT, USER_WAIT_SECS)
            if not ok:
                raise TimeoutError("User account not visible after creation timeout")

        # 5) Report collateral
        user = client.get_user(sub_account=DEFAULT_SUB_ACCOUNT)
        total_collateral = None
        if user:
            # Get total collateral (our client returns float USD)
            tc = await user.get_total_collateral()
            total_collateral = float(tc) if tc else 0.0
            logger.info(".2f")
        else:
            logger.info("ℹ️ User handle not available yet to query collateral.")

        return BootstrapResult(
            wallet_pubkey=wallet_pubkey,
            sol_balance=sol_balance,
            user_created=user_created,
            total_collateral_usd=total_collateral,
        )

    finally:
        # 6) Clean close the Drift client
        try:
            await client.close()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        res = asyncio.run(initialize_devnet_account())
        logger.info("🎉 Devnet bootstrap complete!")
        logger.info(f"   Wallet: {res.wallet_pubkey}")
        logger.info(".6f")
        logger.info(f"   User created this run: {res.user_created}")
        if res.total_collateral_usd is not None:
            logger.info(".2f")
        logger.info("💡 Next: deposit collateral (devnet) and place a tiny test order.")
    except Exception as e:
        logger.error(f"❌ Bootstrap failed: {e}")
        sys.exit(1)
