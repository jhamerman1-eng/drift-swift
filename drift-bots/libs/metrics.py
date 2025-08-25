from prometheus_client import Counter, Gauge, Summary, start_http_server

ORDERS_PLACED = Counter("orders_placed_total", "Total number of orders the bot attempted")
FILLS = Counter("fills_total", "Total number of fills (mock in v0.2)")
LOOP_LATENCY = Summary("loop_latency_seconds", "Per‑tick loop latency")
MIDPRICE = Gauge("mid_price", "Current mid price (mock)")
INV_USD = Gauge("inventory_usd", "Inventory notional in USD (mock)")
PNL_USD = Gauge("pnl_usd", "PnL in USD (mock)")

_started = False

def start_metrics(port: int) -> None:
    global _started
    if not _started:
        start_http_server(port)
        _started = True

def record_mid(mid: float) -> None:
    MIDPRICE.set(mid)