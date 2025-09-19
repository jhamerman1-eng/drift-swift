import time

class CancelReplaceV2:
    def __init__(self, min_lifetime_ms: int, price_move_bps: float):
        self.min_lifetime_ms = min_lifetime_ms
        self.price_move_bps = price_move_bps
        self._last_price = None
        self._last_ts_ms = 0

    def record_quote(self, price: float, ts_ms: int):
        self._last_price = price
        self._last_ts_ms = ts_ms

    def should_refresh(self, new_price: float, now_ms: int):
        if self._last_price is None:
            return True, "init"
        age_ms = now_ms - self._last_ts_ms
        if age_ms < self.min_lifetime_ms:
            return False, "min_lifetime"
        move = abs(new_price - self._last_price)
        bps = (move / max(1e-9, self._last_price)) * 10000.0
        if bps >= self.price_move_bps:
            return True, f"price_move_{bps:.2f}bps"
        return False, "stable"
