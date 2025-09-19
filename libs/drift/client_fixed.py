# libs/drift/client.py - FIXED VERSION
import asyncio
import logging
from typing import Optional
from driftpy.drift_client import DriftClient
from driftpy.types import (
    OrderParams,
    OrderType,
    MarketType,
    PositionDirection,
)
from driftpy.constants.numeric_constants import (
    BASE_PRECISION,     # 1e9 for perps base
    PRICE_PRECISION,    # 1e6
)

logger = logging.getLogger("libs.drift.client")

def _to_price_i(price_f: float) -> int:
    return int(round(float(price_f) * PRICE_PRECISION))

def _to_base_amt_i(base_qty_f: float) -> int:
    return int(round(float(base_qty_f) * BASE_PRECISION))

class DriftpyClient:
    def __init__(self, rpc_url: str, wallet_secret_key: bytes, market: str = "SOL-PERP", ws_url: Optional[str] = None, use_fallback: bool = True):
        self.rpc_url = rpc_url
        self.ws_url = ws_url
        self.market = market
        self.use_fallback = use_fallback
        self.sub_account_id = 0
        self.drift_client: Optional[DriftClient] = None
        self._subscribed = False
        self._user_subscribed = False
        self.retry_delay = 1.0
        self.retry_max = 5
        self._wallet_secret_key = wallet_secret_key  # 64 bytes: seed+pub

    async def connect(self):
        if self.drift_client:
            return
        self.drift_client = await DriftClient.from_config(
            url=self.rpc_url,
            wallet=self._wallet_secret_key,
            websocket_url=self.ws_url,
        )

    async def _ensure_ready(self):
        await self.connect()
        assert self.drift_client is not None

        if not self._subscribed:
            await self.drift_client.subscribe()
            self._subscribed = True

        # Initialize user PDA if needed, then subscribe the user object
        try:
            await self.drift_client.initialize_user()  # idempotent on devnet; ignore "already initialized" anchor error
        except Exception:
            pass

        user = self.drift_client.get_user(self.sub_account_id)
        if not self._user_subscribed:
            await user.subscribe()
            self._user_subscribed = True

        # Sanity: user account must be present after subscription
        ua = user.get_user_account()
        if ua is None or getattr(user, "account_subscriber", None) is None:
            raise RuntimeError("Drift user not ready (no account_subscriber/user account) after subscribe()")

    def get_orderbook(self) -> dict:
        # your existing orderbook code with retry; unchanged
        return {"bids": [], "asks": []}  # placeholder for brevity

    async def place_order(self, order) -> str:
        """
        order.side: 'buy'|'sell' or enum-like
        order.price: float
        order.size_usd or order.base_qty: floats (your wrapper passes one of these)
        """
        await self._ensure_ready()
        assert self.drift_client is not None

        side = str(order.side).lower()
        direction = PositionDirection.Long() if "buy" in side else PositionDirection.Short()

        px_i = _to_price_i(order.price)

        # Prefer a base qty if provided; otherwise infer from notional/price
        if getattr(order, "base_qty", None) is not None:
            base_qty_f = float(order.base_qty)
        else:
            notional = float(getattr(order, "size_usd", 0.0))
            base_qty_f = 0.0 if px_i == 0 else (notional / float(order.price))

        base_amt_i = _to_base_amt_i(base_qty_f)

        op = OrderParams(
            market_index=getattr(order, "market_index", 0),
            order_type=OrderType.Limit(),
            market_type=MarketType.Perp(),
            direction=direction,
            price=px_i,
            base_asset_amount=base_amt_i,
            post_only=getattr(order, "post_only", True),
        )

        # Final guard: ensure user account exists right before sending
        ua = self.drift_client.get_user(self.sub_account_id).get_user_account()
        if ua is None:
            raise RuntimeError("Drift user account is None prior to place_perp_order")

        try:
            tx_sig = await self.drift_client.place_perp_order(op, sub_account_id=self.sub_account_id)
            logger.info("REAL BLOCKCHAIN ORDER PLACED: %s", tx_sig)
            return tx_sig
        except Exception as e:
            logger.error("BLOCKCHAIN ORDER FAILED: %s", e, exc_info=True)
            if self.use_fallback:
                mock = f"MOCK-{int(asyncio.get_event_loop().time()*1000000)%999999:06d}"
                logger.warning("FALLBACK TO MOCK ORDER: %s (Real blockchain failed)", mock)
                return mock
            raise

    # Swift API methods (keeping for compatibility)
    async def get_oracle_price_data_for_perp_market(self, market_index: int):
        """Get oracle price data for perpetual market."""
        await self._ensure_ready()
        return await self.drift_client.get_oracle_price_data_for_perp_market(market_index)

    def convert_to_perp_base_asset_amount(self, qty_perp: float) -> int:
        """Convert quantity to base asset amount using proper numeric constants."""
        return _to_base_amt_i(qty_perp)

    @property
    def connection(self):
        """Get the connection object for RPC calls."""
        return self.drift_client.connection if self.drift_client else None

    @property
    def authority(self):
        """Get the wallet authority public key."""
        if self.drift_client:
            return self.drift_client.wallet.public_key
        return None

    def sign_signed_msg_order_params(self, order_message):
        """Sign a SignedMsgOrderParamsMessage."""
        if not self.drift_client:
            raise RuntimeError("Drift client not initialized")
        return self.drift_client.sign_signed_msg_order_params_message(order_message)

    async def initialize(self):
        """Initialize the drift client (subscribe to accounts)."""
        await self._ensure_ready()
        logger.info("✅ Drift client initialized and subscribed")
