from pydantic import BaseModel, Field
from typing import Optional, Literal, List

Side = Literal["buy", "sell"]
OrderType = Literal["limit", "market", "post_only", "ioc", "fok"]

class OrderReq(BaseModel):
    market: str
    side: Side
    size: float
    price: Optional[float] = None
    type: OrderType = "limit"
    reduce_only: bool = False
    client_id: Optional[str] = None
    nonce: Optional[int] = None

class OrderResp(BaseModel):
    order_id: str | None = None
    status: Literal["accepted","rejected","filled","partial","cancelled"] = "accepted"
    reason: Optional[str] = None

class Market(BaseModel):
    symbol: str
    tick_size: float
    step_size: float

class Position(BaseModel):
    symbol: str
    size: float
    entry_px: float
    pnl_unrealized: float = 0.0
    mark_price: float = 0.0

    @property
    def liquidation_price(self) -> float:
        # Simplified placeholder; replace with exchange-specific margin model
        notional = abs(self.size) * max(self.mark_price, 1e-9)
        leverage = max(notional / 1000.0, 1.0)  # assume $1k margin for placeholder
        if self.size > 0:
            return self.entry_px * (1 - 1/leverage)
        elif self.size < 0:
            return self.entry_px * (1 + 1/leverage)
        return 0.0

    @property
    def risk_score(self) -> float:
        if self.size == 0 or self.mark_price == 0:
            return 0.0
        distance = abs(self.mark_price - self.liquidation_price) / self.mark_price
        # 1.0 = high risk, 0.0 = low risk
        return min(1.0, max(0.0, 1 - distance * 10))

class Fill(BaseModel):
    symbol: str
    size: float
    price: float
    ts: int
