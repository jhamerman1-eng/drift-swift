#!/usr/bin/env python3
"""
Trade Orchestrator: Centralized trade sizing and position logic
Handles all context-aware decision making for incoming Swift orders
"""

import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)

@dataclass
class TradeContext:
    """Complete context for a trade decision"""
    # Order details
    requested_amount: float
    direction: str  # "Long" or "Short"
    price_usd: float
    start_price_usd: float
    end_price_usd: float
    market_index: int
    
    # Financial state
    total_collateral_usd: float
    free_collateral_usd: float
    current_position_sol: float
    
    # Market conditions
    effective_price: float
    order_type: str  # "Oracle" or "Market"
    
    # Risk parameters - DEVNET TRADING LIMITS
    max_position_sol: float = 5.0  # 5x leverage position limits
    max_trade_percent: float = 0.30  # Can use more capital with leverage
    min_free_collateral_buffer: float = 50.0  # Higher buffer for leverage
    absolute_max_trade_usd: float = 500.0  # 2 SOL @ ~$250 = $500 max
    min_trade_usd: float = 25.0  # 0.1 SOL @ ~$250 = $25 min
    
    # DEVNET SOL LIMITS
    min_trade_sol: float = 0.1  # Minimum 0.1 SOL
    max_trade_sol: float = 2.0  # Maximum 2.0 SOL
    
    # LEVERAGE PARAMETERS
    max_leverage: float = 5.0  # 5x leverage capability
    leverage_buffer: float = 0.8  # Use 80% of max leverage for safety

@dataclass 
class TradeDecision:
    """Final trade decision with reasoning"""
    approved: bool
    final_amount_sol: float
    reasoning: str
    constraints_applied: Dict[str, float]
    risk_assessment: str

class TradeOrchestrator:
    """Centralized orchestration for all trade sizing and position logic"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.stats = {
            "total_requests": 0,
            "approved_trades": 0,
            "rejected_insufficient_collateral": 0,
            "rejected_position_limits": 0,
            "rejected_size_constraints": 0,
            "total_size_reductions": 0
        }
    
    async def evaluate_trade_request(self, drift_user, order_data: Dict) -> TradeDecision:
        """
        CENTRALIZED TRADE EVALUATION
        Single point of truth for all trade sizing decisions
        """
        self.stats["total_requests"] += 1
        
        try:
            # 1. BUILD COMPLETE CONTEXT
            context = await self._build_trade_context(drift_user, order_data)
            if not context:
                return TradeDecision(
                    approved=False,
                    final_amount_sol=0.0,
                    reasoning="Failed to build trade context",
                    constraints_applied={},
                    risk_assessment="HIGH - Context unavailable"
                )
            
            # 2. APPLY ORCHESTRATED DECISION LOGIC
            decision = await self._make_trade_decision(context)
            
            # 3. UPDATE STATISTICS
            if decision.approved:
                self.stats["approved_trades"] += 1
                if decision.final_amount_sol < context.requested_amount:
                    self.stats["total_size_reductions"] += 1
            
            # 4. LOG DECISION
            await self._log_decision(context, decision)
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ Trade orchestration failed: {e}")
            return TradeDecision(
                approved=False,
                final_amount_sol=0.0,
                reasoning=f"Orchestration error: {e}",
                constraints_applied={},
                risk_assessment="HIGH - System error"
            )
    
    async def _build_trade_context(self, drift_user, order_data: Dict) -> Optional[TradeContext]:
        """Build complete context for trade decision"""
        try:
            # Extract order data
            requested_amount = order_data.get("amount_sol", 0.0)
            direction = order_data.get("direction", "")
            price_usd = order_data.get("price_usd", 0.0)
            start_price_usd = order_data.get("start_price_usd", 0.0)
            end_price_usd = order_data.get("end_price_usd", 0.0)
            market_index = order_data.get("market_index", 0)
            
            # Get financial state
            total_collateral = drift_user.get_total_collateral()
            free_collateral = drift_user.get_free_collateral()
            
            QUOTE_PRECISION = 1e6
            total_collateral_usd = (total_collateral / QUOTE_PRECISION) if total_collateral else 0
            free_collateral_usd = (free_collateral / QUOTE_PRECISION) if free_collateral else 0
            
            # Get current position
            current_position_sol = 0.0
            try:
                positions = drift_user.get_perp_positions()
                for pos in positions:
                    if pos.market_index == market_index:
                        current_position_sol = pos.base_asset_amount / 1e9
                        break
            except Exception as e:
                logger.warning(f"Could not get position: {e}")
            
            # Calculate effective price
            if start_price_usd > 0 and end_price_usd > 0:
                effective_price = (start_price_usd + end_price_usd) / 2
                order_type = "Oracle"
            elif price_usd > 0:
                effective_price = price_usd
                order_type = "Market"
            else:
                logger.warning("No valid price for context")
                return None
            
            return TradeContext(
                requested_amount=requested_amount,
                direction=direction,
                price_usd=price_usd,
                start_price_usd=start_price_usd,
                end_price_usd=end_price_usd,
                market_index=market_index,
                total_collateral_usd=total_collateral_usd,
                free_collateral_usd=free_collateral_usd,
                current_position_sol=current_position_sol,
                effective_price=effective_price,
                order_type=order_type
            )
            
        except Exception as e:
            logger.error(f"Failed to build trade context: {e}")
            return None
    
    async def _make_trade_decision(self, context: TradeContext) -> TradeDecision:
        """ORCHESTRATED DECISION LOGIC - Single point of truth"""
        
        constraints_applied = {}
        
        # CONSTRAINT 1: Minimum collateral buffer
        usable_collateral = max(0, context.free_collateral_usd - context.min_free_collateral_buffer)
        if usable_collateral <= 0:
            self.stats["rejected_insufficient_collateral"] += 1
            return TradeDecision(
                approved=False,
                final_amount_sol=0.0,
                reasoning=f"Insufficient free collateral: ${context.free_collateral_usd:.2f} (need ${context.min_free_collateral_buffer} buffer)",
                constraints_applied={"free_collateral": context.free_collateral_usd},
                risk_assessment="HIGH - Insufficient funds"
            )
        
        # CONSTRAINT 2: Leverage-aware position sizing
        # With 5x leverage, we can effectively use more capital
        effective_buying_power = usable_collateral * context.max_leverage * context.leverage_buffer
        max_trade_value = min(
            usable_collateral * context.max_trade_percent,  # Direct collateral limit
            effective_buying_power * 0.20  # 20% of leveraged buying power per trade
        )
        constraints_applied["max_trade_percent"] = max_trade_value
        constraints_applied["leveraged_buying_power"] = effective_buying_power
        
        # CONSTRAINT 3: Absolute maximum trade value (2 SOL limit)
        max_trade_value = min(max_trade_value, context.absolute_max_trade_usd)
        constraints_applied["absolute_max"] = context.absolute_max_trade_usd
        
        # CONSTRAINT 4: SOL-based limits (hard devnet limits)
        max_trade_sol_value = context.max_trade_sol * context.effective_price
        max_trade_value = min(max_trade_value, max_trade_sol_value)
        constraints_applied["max_sol_limit"] = f"{context.max_trade_sol} SOL"
        
        # CONSTRAINT 5: Minimum trade value (0.1 SOL limit)
        min_trade_sol_value = context.min_trade_sol * context.effective_price
        if max_trade_value < min_trade_sol_value:
            self.stats["rejected_size_constraints"] += 1
            return TradeDecision(
                approved=False,
                final_amount_sol=0.0,
                reasoning=f"Max trade value ${max_trade_value:.2f} below minimum {context.min_trade_sol} SOL (${min_trade_sol_value:.2f})",
                constraints_applied=constraints_applied,
                risk_assessment="MEDIUM - Below minimum SOL limit"
            )
        
        # CONSTRAINT 5: Position size limits
        max_position_check = await self._check_position_limits(context)
        if not max_position_check["allowed"]:
            self.stats["rejected_position_limits"] += 1
            return TradeDecision(
                approved=False,
                final_amount_sol=0.0,
                reasoning=max_position_check["reason"],
                constraints_applied=constraints_applied,
                risk_assessment="HIGH - Position limits"
            )
        
        # DETERMINE FINAL SIZE
        requested_value = context.requested_amount * context.effective_price
        
        if requested_value <= max_trade_value:
            # Original size is within all constraints
            final_amount = context.requested_amount
            available_position = max_position_check["available_size"]
            if final_amount > available_position:
                final_amount = available_position
                
            reasoning = "Original size approved"
            risk_assessment = "LOW - All constraints satisfied"
            
        else:
            # Need to scale down
            final_amount = max_trade_value / context.effective_price
            available_position = max_position_check["available_size"]
            if final_amount > available_position:
                final_amount = available_position
                
            reasoning = f"Scaled down from ${requested_value:.2f} to ${max_trade_value:.2f}"
            risk_assessment = "MEDIUM - Size reduced"
        
        # DEVNET SOL LIMITS - Hard enforcement
        if final_amount > context.max_trade_sol:
            final_amount = context.max_trade_sol
            reasoning += f" (capped at {context.max_trade_sol} SOL devnet limit)"
            
        if final_amount < context.min_trade_sol:
            self.stats["rejected_size_constraints"] += 1
            return TradeDecision(
                approved=False,
                final_amount_sol=0.0,
                reasoning=f"Final size {final_amount:.4f} SOL below devnet minimum {context.min_trade_sol} SOL",
                constraints_applied=constraints_applied,
                risk_assessment="MEDIUM - Below devnet minimum"
            )
        
        return TradeDecision(
            approved=True,
            final_amount_sol=round(final_amount, 4),
            reasoning=reasoning,
            constraints_applied=constraints_applied,
            risk_assessment=risk_assessment
        )
    
    async def _check_position_limits(self, context: TradeContext) -> Dict:
        """Check position size constraints with 5x leverage awareness"""
        try:
            # With 5x leverage, we can hold larger positions relative to collateral
            # max_position_sol (5.0) represents the maximum leveraged position size
            
            if context.direction == "Long":
                available_size = context.max_position_sol - context.current_position_sol
                if available_size <= 0:
                    return {
                        "allowed": False,
                        "reason": f"At max long position: {context.current_position_sol:.4f}/{context.max_position_sol} SOL (5x leverage)",
                        "available_size": 0.0
                    }
                
            elif context.direction == "Short":
                available_size = context.max_position_sol + context.current_position_sol  # current_position is negative for shorts
                if available_size <= 0:
                    return {
                        "allowed": False,
                        "reason": f"At max short position: {context.current_position_sol:.4f}/{-context.max_position_sol} SOL (5x leverage)",
                        "available_size": 0.0
                    }
            else:
                return {
                    "allowed": False,
                    "reason": f"Invalid direction: {context.direction}",
                    "available_size": 0.0
                }
            
            return {
                "allowed": True,
                "reason": f"Position limits OK ({available_size:.2f} SOL available)",
                "available_size": available_size
            }
            
        except Exception as e:
            logger.error(f"Position limit check failed: {e}")
            return {
                "allowed": False,
                "reason": f"Position check error: {e}",
                "available_size": 0.0
            }
    
    async def _log_decision(self, context: TradeContext, decision: TradeDecision):
        """Log the orchestrated decision"""
        logger.info(f"🏛️ TRADE ORCHESTRATION DECISION:")
        logger.info(f"   📊 Request: {context.requested_amount:.4f} SOL {context.direction} @ ${context.effective_price:.2f}")
        logger.info(f"   💰 Collateral: Total=${context.total_collateral_usd:.2f}, Free=${context.free_collateral_usd:.2f}")
        logger.info(f"   📈 Position: {context.current_position_sol:.4f} SOL")
        logger.info(f"   ✅ Decision: {'APPROVED' if decision.approved else 'REJECTED'}")
        logger.info(f"   📏 Final Size: {decision.final_amount_sol:.4f} SOL")
        logger.info(f"   🧠 Reasoning: {decision.reasoning}")
        logger.info(f"   🛡️ Risk: {decision.risk_assessment}")
        
        if decision.constraints_applied:
            logger.info(f"   🔒 Constraints: {decision.constraints_applied}")
    
    def get_stats(self) -> Dict:
        """Get orchestration statistics"""
        if self.stats["total_requests"] > 0:
            approval_rate = (self.stats["approved_trades"] / self.stats["total_requests"]) * 100
        else:
            approval_rate = 0.0
            
        return {
            **self.stats,
            "approval_rate_percent": round(approval_rate, 1)
        }
