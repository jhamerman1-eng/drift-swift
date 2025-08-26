import os
import yaml
import random
import time
import threading
from typing import Dict, List, Optional, Tuple, Protocol
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

@dataclass
class Order:
    side: OrderSide
    price: float
    size_usd: float
    order_id: Optional[str] = None

@dataclass
class Orderbook:
    bids: List[Tuple[float, float]]  # (price, size)
    asks: List[Tuple[float, float]]  # (price, size)

@dataclass
class Position:
    size: float  # positive = long, negative = short
    avg_price: float
    unrealized_pnl: float
    realized_pnl: float
    last_update: float

@dataclass
class Trade:
    order_id: str
    side: OrderSide
    price: float
    size_usd: float
    timestamp: float
    fill_id: str

class DriftClient(Protocol):
    def place_order(self, order: Order) -> str:
        ...
    def cancel_all(self) -> None:
        ...
    def get_orderbook(self) -> Orderbook:
        ...
    async def close(self) -> None:
        ...

class EnhancedMockDriftClient:
    """Enhanced mock client that simulates realistic trading with position tracking and PnL calculation."""
    
    def __init__(self, market: str = "SOL-PERP", start: float = 150.0, spread_bps: float = 6.0):
        self.market = market
        self.mid = float(start)
        self.spread = spread_bps / 1e4
        
        # Trading state
        self.positions: Dict[str, Position] = {}
        self.open_orders: Dict[str, Order] = {}
        self.trade_history: List[Trade] = []
        self.order_counter = 0
        
        # Risk metrics
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_equity = 0.0
        
        # Market simulation
        self.volatility = 0.0007  # 7 bps
        self.trend = 0.0
        self.last_update = time.time()
        
        logger.info(f"Enhanced Mock Client initialized for {market} starting at ${start:.2f}")

    def _step(self) -> None:
        """Simulate realistic market movement with trend and volatility."""
        current_time = time.time()
        dt = current_time - self.last_update
        
        # Random walk with trend
        shock = random.gauss(0, self.volatility) * self.mid
        self.trend += random.gauss(0, 0.0001)  # Slow trend changes
        self.trend = max(-0.001, min(0.001, self.trend))  # Bounded trend
        
        self.mid = max(0.01, self.mid + shock + self.trend * dt)
        self.last_update = current_time

    def get_orderbook(self) -> Orderbook:
        """Generate realistic orderbook with depth."""
        self._step()
        half = self.mid * self.spread / 2
        top_bid = self.mid - half
        top_ask = self.mid + half
        
        levels = 5
        tick = max(self.mid * 1e-5, 0.01)
        
        # Generate realistic bid/ask depth
        bids = []
        asks = []
        
        for i in range(levels):
            bid_price = round(top_bid - i * tick, 4)
            ask_price = round(top_ask + i * tick, 4)
            
            # Size decreases with distance from mid
            bid_size = max(5.0, 50.0 - i * 8.0)
            ask_size = max(5.0, 50.0 - i * 8.0)
            
            bids.append((bid_price, bid_size))
            asks.append((ask_price, ask_size))
        
        return Orderbook(bids=bids, asks=asks)

    def place_order(self, order: Order) -> str:
        """Place order and simulate realistic fill behavior."""
        self.order_counter += 1
        order_id = f"mock-{self.order_counter:06d}"
        order.order_id = order_id
        
        # Store open order
        self.open_orders[order_id] = order
        
        # Simulate order execution with realistic delays
        self._simulate_order_fill(order_id)
        
        logger.info(f"[MOCK] Order placed: {order_id} {order.side} {order.size_usd:.2f} USD @ ${order.price:.4f}")
        return order_id

    def _simulate_order_fill(self, order_id: str) -> None:
        """Simulate realistic order fills based on market conditions."""
        order = self.open_orders[order_id]
        
        # Get current market conditions
        ob = self.get_orderbook()
        current_mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
        
        # Calculate fill probability based on order placement
        if order.side == OrderSide.BUY:
            # Buy orders above mid have higher fill probability
            fill_prob = max(0.1, min(0.9, 1.0 - (order.price - current_mid) / current_mid))
        else:
            # Sell orders below mid have higher fill probability
            fill_prob = max(0.1, min(0.9, 1.0 - (current_mid - order.price) / current_mid))
        
        # Simulate fill timing (0.1 to 5 seconds)
        fill_delay = random.uniform(0.1, 5.0)
        
        # Schedule fill simulation
        def delayed_fill():
            time.sleep(fill_delay)
            if order_id in self.open_orders:  # Order still open
                self._execute_fill(order_id)
        
        threading.Thread(target=delayed_fill, daemon=True).start()

    def _execute_fill(self, order_id: str) -> None:
        """Execute order fill and update positions."""
        order = self.open_orders.pop(order_id)
        
        # Create trade record
        trade = Trade(
            order_id=order_id,
            side=order.side,
            price=order.price,
            size_usd=order.size_usd,
            timestamp=time.time(),
            fill_id=f"fill-{order_id}"
        )
        self.trade_history.append(trade)
        
        # Update positions
        self._update_position(trade)
        
        # Calculate PnL
        self._calculate_pnl()
        
        logger.info(f"[MOCK] Order filled: {order_id} {order.side} {order.size_usd:.2f} USD @ ${order.price:.4f}")

    def _update_position(self, trade: Trade) -> None:
        """Update position tracking based on trade."""
        # Convert USD size to SOL equivalent (simplified)
        sol_size = trade.size_usd / trade.price
        
        if trade.side == OrderSide.SELL:
            sol_size = -sol_size  # Short position
        
        # Update or create position
        if self.market not in self.positions:
            self.positions[self.market] = Position(
                size=sol_size,
                avg_price=trade.price,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                last_update=time.time()
            )
        else:
            pos = self.positions[self.market]
            
            # Calculate new average price
            total_value = pos.size * pos.avg_price + sol_size * trade.price
            total_size = pos.size + sol_size
            
            if total_size != 0:
                pos.avg_price = total_value / total_size
                pos.size = total_size
            else:
                # Position closed, calculate realized PnL
                if pos.size > 0:  # Was long
                    pos.realized_pnl += (trade.price - pos.avg_price) * abs(sol_size)
                else:  # Was short
                    pos.realized_pnl += (pos.avg_price - trade.price) * abs(sol_size)
                
                pos.size = 0
                pos.avg_price = 0.0
            
            pos.last_update = time.time()

    def _calculate_pnl(self) -> None:
        """Calculate unrealized PnL and update risk metrics."""
        current_mid = self.mid
        
        for market, pos in self.positions.items():
            if pos.size != 0:
                if pos.size > 0:  # Long position
                    pos.unrealized_pnl = (current_mid - pos.avg_price) * pos.size
                else:  # Short position
                    pos.unrealized_pnl = (pos.avg_price - current_mid) * abs(pos.size)
        
        # Calculate total PnL
        total_unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_realized = sum(pos.realized_pnl for pos in self.positions.values())
        self.total_pnl = total_unrealized + total_realized
        
        # Update risk metrics
        if self.total_pnl > self.peak_equity:
            self.peak_equity = self.total_pnl
        
        current_drawdown = self.peak_equity - self.total_pnl
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown

    def cancel_all(self) -> None:
        """Cancel all open orders."""
        cancelled_count = len(self.open_orders)
        self.open_orders.clear()
        logger.info(f"[MOCK] Cancelled {cancelled_count} open orders")

    def get_positions(self) -> Dict[str, Position]:
        """Get current positions."""
        return self.positions.copy()

    def get_pnl_summary(self) -> Dict[str, float]:
        """Get PnL summary."""
        return {
            "total_pnl": self.total_pnl,
            "unrealized_pnl": sum(pos.unrealized_pnl for pos in self.positions.values()),
            "realized_pnl": sum(pos.realized_pnl for pos in self.positions.values()),
            "max_drawdown": self.max_drawdown,
            "peak_equity": self.peak_equity
        }

    def get_trade_history(self) -> List[Trade]:
        """Get trade history."""
        return self.trade_history.copy()

    async def close(self) -> None:
        """Close client and log final metrics."""
        logger.info(f"[MOCK] Client closing. Final PnL: ${self.total_pnl:.2f}, Max Drawdown: ${self.max_drawdown:.2f}")

# Legacy MockDriftClient for backward compatibility
MockDriftClient = EnhancedMockDriftClient

# Optional real client (skeleton)
try:
    import driftpy  # type: ignore
except Exception:
    driftpy = None

class DriftpyClient:
    """Skeleton for real Drift integration. Fill RPC, wallet, market wiring in v0.3."""
    def __init__(self, rpc_url: str, wallet_secret_key: str, market: str = "SOL-PERP", ws_url: str | None = None):
        if driftpy is None:
            raise RuntimeError("driftpy not installed. Add to pyproject and install.")
        self.rpc_url = rpc_url
        self.ws_url = ws_url
        self.wallet_secret_key = wallet_secret_key
        self.market = market
        # TODO: initialize drift client, load market accounts, signer, etc.

    def place_order(self, order: Order) -> str:
        # TODO: translate USD size to contracts/quote size, build instruction, send TX
        return "txsig_placeholder"

    def cancel_all(self) -> None:
        # TODO
        return None

    def get_orderbook(self) -> Orderbook:
        # TODO: fetch from Drift markets/orderbook accounts
        return Orderbook(bids=[], asks=[])

    async def close(self) -> None:
        # TODO: close websockets if any
        return None

async def build_client_from_config(cfg_path: str) -> DriftClient:
    """Builder reads YAML with env‑var interpolation and returns a client."""
    text = os.path.expandvars(open(cfg_path, "r").read())
    cfg = yaml.safe_load(text)
    env = cfg.get("env", "testnet")
    market = cfg.get("market", "SOL-PERP")
    use_mock = bool(cfg.get("use_mock", True))

    if use_mock:
        logger.info(f"Using Enhanced MockDriftClient for {market} ({env})")
        return EnhancedMockDriftClient(market=market)

    rpc = cfg.get("rpc_url") or os.getenv("DRIFT_RPC_URL")
    ws = cfg.get("ws_url") or os.getenv("DRIFT_WS_URL")
    secret = cfg.get("wallet_secret_key") or os.getenv("DRIFT_KEYPAIR_PATH")
    if not rpc or not secret:
        raise RuntimeError("rpc_url and wallet_secret_key/DRIFT_KEYPAIR_PATH are required for real client")
    logger.info(f"Using DriftpyClient for {market} ({env}) via {rpc}")
    return DriftpyClient(rpc_url=rpc, wallet_secret_key=secret, market=market, ws_url=ws)

if __name__ == "__main__":
    import asyncio
    async def _smoke():
        client = await build_client_from_config(os.getenv("DRIFT_CFG", "configs/core/drift_client.yaml"))
        ob = client.get_orderbook()
        if ob.bids and ob.asks:
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
            logger.info(f"Top‑of‑book mid={mid:.4f} (b={ob.bids[0][0]:.4f} a={ob.asks[0][0]:.4f})")
    asyncio.run(_smoke())
