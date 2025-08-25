from dataclasses import dataclass, field
from typing import Dict, List
import time

@dataclass
class ClientMetrics:
    orders_placed: int = 0
    orders_failed: int = 0
    ws_reconnects: int = 0
    http_retries: int = 0
    latency_ms: Dict[str, List[float]] = field(default_factory=dict)

    def record_latency(self, operation: str, duration_ms: float):
        buf = self.latency_ms.setdefault(operation, [])
        buf.append(duration_ms)
        if len(buf) > 1000:
            del buf[:len(buf) - 1000]

    def p99_latency(self, operation: str) -> float:
        samples = self.latency_ms.get(operation, [])
        if not samples:
            return 0.0
        s = sorted(samples)
        idx = int(len(s) * 0.99)
        idx = min(max(idx, 0), len(s) - 1)
        return s[idx]
