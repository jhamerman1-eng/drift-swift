# libs/drift/swift_submit.py
"""
Swift submit (market taker) — minimal, working example:
- Build OrderParams
- Create SignedMsgOrderParamsMessage (slot + uuid)
- Sign with your wallet
- POST to Swift /orders

Requires: driftpy, anchorpy, solana, httpx
"""

from __future__ import annotations
import os
import json
import uuid
import httpx
from typing import Any, Dict

from driftpy.drift_client import DriftClient
from driftpy.types import (
    OrderParams,
    OrderType,
    MarketType,
    SignedMsgOrderParamsMessage,
    PositionDirection,
)

SWIFT_BASE = os.getenv("SWIFT_BASE", "https://swift.drift.trade")  # can be overridden

def _gen_uuid() -> str:
    # Swift expects a UUID; drift utils have helpers, but this works fine.
    return str(uuid.uuid4())

async def swift_market_taker(
    drift_client: DriftClient,
    *,
    market_index: int,
    direction: PositionDirection,
    qty_perp: float,
    auction_ms: int = 50,
) -> Dict[str, Any]:
    """
    Place a small market-taker order via Swift.
    - Uses oracle price for auction range.
    - qty_perp is in base units (e.g., SOL size).
    Returns Swift JSON response.
    """

    # 1) Define order params (oracle bounds for auction)
    oracle_info = await drift_client.get_oracle_price_data_for_perp_market(market_index)
    high_price = oracle_info.price * 1.01
    low_price = oracle_info.price

    order_params = OrderParams(
        market_index=market_index,
        order_type=OrderType.Market(),
        market_type=MarketType.Perp(),
        direction=direction,
        base_asset_amount=drift_client.convert_to_perp_base_asset_amount(qty_perp),
        auction_start_price=low_price,
        auction_end_price=high_price,
        auction_duration=auction_ms,
    )

    # 2) Generate + sign message
    slot_resp = await drift_client.connection._provider.rpc_request("getSlot", [])
    slot = slot_resp["result"]

    order_message = SignedMsgOrderParamsMessage(
        signed_msg_order_params=order_params,
        sub_account_id=drift_client.active_sub_account_id,
        slot=slot,
        uuid=_gen_uuid(),
        stop_loss_order_params=None,
        take_profit_order_params=None,
    )

    signed_msg = drift_client.sign_signed_msg_order_params(order_message)

    payload = {
        "market_type": "perp",
        "market_index": market_index,
        "message": signed_msg.order_params,  # serialized order params
        "signature": signed_msg.signature,   # signature over message
        "taker_authority": str(drift_client.authority),  # base58 pubkey
    }

    # 3) Submit to Swift
    async with httpx.AsyncClient(base_url=SWIFT_BASE, timeout=15.0) as s:
        r = await s.post("/orders", json=payload)
        r.raise_for_status()
        return r.json()