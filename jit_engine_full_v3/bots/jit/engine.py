import time, logging
from typing import Dict, Any, Optional, Tuple
from .metrics import JITMetrics, JIT_REFRESH_TOTAL, JIT_TICK_TO_QUOTE
from .components.types import MarketData, QuoteDecision, VolatilityRegime
from .components.regime import RegimeDetector
from .components.microprice import MicropriceCalculator
from .components.spoof import SpoofFilter
from .components.toxicity import ToxicityCalculator
from .components.spread import SpreadManager
from .cancel_replace import CancelReplaceV2
from .attribution import select_arm

logger = logging.getLogger("jit.engine")

class JITEngine:
    def __init__(self, client, cfg: Dict[str, Any], market: str, max_errors: int = 5):
        self.client = client
        self.config = cfg or {}
        self.market = market
        self._max_errors = max_errors
        self._error_count = 0

        # Components
        self._regime_detector = RegimeDetector()
        self._microprice_calc = MicropriceCalculator(self.config.get("obi_weights", None))
        self._spoof_filter = SpoofFilter()
        self._toxicity_calc = ToxicityCalculator()
        self._spread_manager = SpreadManager(
            min_spread_bps=self.config.get("min_spread_bps", 1.0),
            max_spread_bps=self.config.get("max_spread_bps", 50.0),
            tox_thr=self.config.get("skew", {}).get("toxicity_threshold", 0.7),
            tox_mult=self.config.get("skew", {}).get("skew_multiplier", 1.5),
        )
        cr_cfg = self.config.get("cancel_replace_v2", {})
        self._cancel_replace = CancelReplaceV2(
            min_lifetime_ms=int(cr_cfg.get("min_lifetime_ms", 250)),
            price_move_bps=float(cr_cfg.get("price_move_bps", 1.5)),
        )

        self.arm = select_arm(self.config)
        self._metrics = JITMetrics(market=market, arm=self.arm.name)

    async def step(self) -> Optional[QuoteDecision]:
        """
        Execute one JIT engine step with comprehensive error handling
        
        Returns:
            QuoteDecision if successful, None if should skip
        """
        step_start = time.time()
        try:
            # 1. Gather market data with validation
            market_data = await self._gather_market_data()
            if not market_data or not market_data.is_valid:
                self._metrics.record_skip("invalid_market_data")
                return None
            
            # 2. Detect regime and select microprice weights
            regime = await self._regime_detector.detect(market_data)
            
            # 3. Calculate reference price with profit validation
            ref_price = await self._calculate_reference_price(market_data, regime)
            if ref_price <= 0:
                self._metrics.record_skip("invalid_ref_price")
                return None
            
            # 4. Apply spoof filter to market data
            filtered_data = await self._spoof_filter.apply(market_data, regime.value)
            
            # 5. Calculate toxicity score
            toxicity = await self._toxicity_calc.calculate(filtered_data)
            
            # 6. Determine spread with toxicity adjustment
            spread_bps = await self._spread_manager.calculate(
                filtered_data, toxicity, regime
            )
            
            # 7. Check cancel/replace timing
            now_ms = int(time.time() * 1000)
            should_refresh, cr_reason = self._cancel_replace.should_refresh(
                ref_price, now_ms
            )
            
            if not should_refresh:
                self._metrics.record_skip(f"cr_{cr_reason}")
                return None
            else:
                JIT_REFRESH_TOTAL.labels(reason=cr_reason).inc()
            
            # 8. Get rails size multiplier (from orchestrator/external)
            size_multiplier = await self._get_rails_size_multiplier()
            if size_multiplier <= 0:
                self._metrics.record_skip("rails_halt")
                return None
            
            # 9. Calculate order sizes
            position = await self.client.get_position()
            bid_size, ask_size = self._calculate_order_sizes(
                market_data, position, size_multiplier
            )
            
            # 10. Create decision
            decision = QuoteDecision(
                should_quote=True,
                ref_price=ref_price,
                spread_bps=spread_bps,
                bid_size=bid_size,
                ask_size=ask_size,
                size_multiplier=size_multiplier,
                reason=f"regime_{regime.value}_tox_{toxicity:.3f}",
                toxicity_score=toxicity,
                regime=regime
            )
            
            # 11. Record successful step
            self._cancel_replace.record_quote(ref_price, now_ms)
            self._metrics.record_decision(decision, time.time() - step_start)
            self._error_count = 0  # Reset error count on success
            
            return decision
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"JIT engine step failed: {e}", exc_info=True)
            self._metrics.record_error(str(e))
            
            if self._error_count >= self._max_errors:
                logger.critical(f"JIT engine exceeded max errors ({self._max_errors}), halting")
                return None
            
            return None

    async def _gather_market_data(self) -> Optional[MarketData]:
        """Gather and validate market data from trading client"""
        try:
            orderbook = await self.client.get_orderbook()
            
            # Accept both {'best_bid','best_ask'} or level arrays {'bids','asks'}
            bids = orderbook.get('bids')
            asks = orderbook.get('asks')
            if bids is not None and asks is not None and len(bids)>0 and len(asks)>0:
                best_bid, bid_volume = bids[0]
                best_ask, ask_volume = asks[0]
            else:
                best_bid = orderbook.get('best_bid')
                best_ask = orderbook.get('best_ask')
                # volumes optional in this mode
                bid_volume = orderbook.get('bid_vol', 1.0)
                ask_volume = orderbook.get('ask_vol', 1.0)
            
            if best_bid is None or best_ask is None:
                return None
            if best_bid <= 0 or best_ask <= 0 or best_ask <= best_bid:
                # invalid or crossed book
                return None
            
            mid_price = (best_bid + best_ask) / 2.0
            spread_bps = ((best_ask - best_bid) / mid_price) * 10000.0 if mid_price>0 else 0.0
            
            return MarketData(
                best_bid=best_bid,
                best_ask=best_ask,
                bid_volume=bid_volume,
                ask_volume=ask_volume,
                mid_price=mid_price,
                spread_bps=spread_bps,
                timestamp=time.time(),
                levels=len(bids) if bids is not None else 1,
                is_valid=True
            )
            
        except Exception as e:
            logger.error(f"Failed to gather market data: {e}")
            return None

    async def _calculate_reference_price(self, market_data: MarketData, regime: VolatilityRegime) -> float:
        """Calculate reference price using regime-aware microprice"""
        mp_cfg = self.config.get("microprice", {"enabled": True})
        if not mp_cfg.get("enabled", True):
            return market_data.mid_price
        
        return await self._microprice_calc.calculate(market_data, regime)
    
    async def _get_rails_size_multiplier(self) -> float:
        """Get size multiplier from rails/orchestrator"""
        # In production, this would query orchestrator for current rails state
        return float(self.config.get("size_mult", 1.0))
    
    def _calculate_order_sizes(self, market_data: MarketData, position: float, size_multiplier: float) -> Tuple[float, float]:
        """Calculate bid/ask order sizes with inventory management"""
        base_size = float(self.config.get("base_size", 0.1))  # Base size in asset units
        
        # Apply size multiplier from rails
        adjusted_size = base_size * max(0.0, size_multiplier)
        
        # Adjust for inventory (reduce size when skewed)
        max_position = float(self.config.get("max_position", 5.0))  # Max position in asset units
        inventory_skew = (position / max_position) if max_position > 0 else 0.0
        
        # Reduce size when inventory is skewed
        skew_adjustment = 1.0 - min(1.0, abs(inventory_skew)) * 0.3
        final_size = adjusted_size * max(0.1, skew_adjustment)
        
        # Asymmetric sizing based on inventory
        if inventory_skew > 0.1:  # Long position - prefer selling
            bid_size = final_size * 0.7
            ask_size = final_size * 1.3
        elif inventory_skew < -0.1:  # Short position - prefer buying
            bid_size = final_size * 1.3
            ask_size = final_size * 0.7
        else:
            bid_size = ask_size = final_size
        
        return max(0.01, bid_size), max(0.01, ask_size)
