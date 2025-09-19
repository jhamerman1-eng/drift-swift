from prometheus_client import Counter, Gauge, Summary

# Core JIT metrics
JIT_QUOTES_TOTAL = Counter("jit_quotes_total", "Total quote placement attempts", ["arm"])
JIT_REFRESH_TOTAL = Counter("jit_refresh_total", "Total cancel/replace refresh decisions", ["reason"])
JIT_TOXICITY = Gauge("jit_toxicity_score", "Current toxicity proxy (0..1)", ["market"])
JIT_SPREAD_BPS = Gauge("jit_spread_bps", "Final quoted spread (bps)", ["market","arm"])
JIT_REF_PRICE = Gauge("jit_ref_price", "Reference price used for quoting", ["market","arm"])
JIT_SIZE_MULT = Gauge("jit_size_mult", "Applied size multiplier after rails/regime", ["market","arm"])
JIT_TICK_TO_QUOTE = Summary("jit_tick_to_quote_seconds", "Latency from tick→quote placement", ["arm"])

# Additional observability
JIT_SKIPS_TOTAL = Counter("jit_skips_total", "JIT step skips by reason", ["reason"])
JIT_ERRORS_TOTAL = Counter("jit_errors_total", "JIT step errors", ["message"])

class JITMetrics:
    def __init__(self, market: str, arm: str):
        self.market = market
        self.arm = arm

    def record_skip(self, reason: str):
        JIT_SKIPS_TOTAL.labels(reason=reason).inc()

    def record_error(self, message: str):
        JIT_ERRORS_TOTAL.labels(message=message[:80]).inc()

    def record_decision(self, decision, latency_s: float):
        JIT_QUOTES_TOTAL.labels(self.arm).inc()
        JIT_REF_PRICE.labels(self.market, self.arm).set(decision.ref_price)
        JIT_SPREAD_BPS.labels(self.market, self.arm).set(decision.spread_bps)
        JIT_SIZE_MULT.labels(self.market, self.arm).set(decision.size_multiplier)
