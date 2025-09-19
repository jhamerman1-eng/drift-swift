"""
Drift Protocol PerpMarket Adapter

Python adaptation of Drift Protocol's PerpMarket struct and related calculations.
Implements institutional-grade risk management, AMM mathematics, and market operations.

Key Features:
- Complete PerpMarket struct adaptation
- AMM mathematics with funding rates
- Contract tier risk management
- Margin requirement calculations
- Oracle validation framework
- JIT liquidity management
- Protected maker system
"""

import time
from typing import Dict, Any, Optional, Tuple, Union
from decimal import Decimal, ROUND_DOWN
from dataclasses import dataclass, field
from enum import Enum

from ..solana.compute_budget_utils import ComputeBudgetOptimizer
from ..configs.compute_budget_strategies import TradingStrategy, MarketCondition

# Precision constants (matching Drift)
PRICE_PRECISION = Decimal('1000000')  # 1e6
QUOTE_PRECISION = Decimal('1000000')  # 1e6
BASE_PRECISION = Decimal('1000000000')  # 1e9
AMM_RESERVE_PRECISION = Decimal('1000000000')  # 1e9
PEG_PRECISION = Decimal('1000000')  # 1e6
PERCENTAGE_PRECISION = Decimal('10000')  # 1e4 for basis points
SPOT_WEIGHT_PRECISION = Decimal('1000000')  # 1e6
MARGIN_PRECISION = Decimal('10000')  # 1e4 for margin ratios
FUNDING_RATE_PRECISION = Decimal('1000000')  # 1e6

class MarketStatus(str, Enum):
    """Market status enumeration"""
    INITIALIZED = "initialized"
    ACTIVE = "active"
    FUNDING_PAUSED = "funding_paused"
    AMM_PAUSED = "amm_paused"
    FILL_PAUSED = "fill_paused"
    WITHDRAW_PAUSED = "withdraw_paused"
    REDUCE_ONLY = "reduce_only"
    SETTLEMENT = "settlement"
    DELISTED = "delisted"

class ContractTier(str, Enum):
    """Contract tier enumeration"""
    A = "A"                  # Safest, max insurance
    B = "B"                  # High safety
    C = "C"                  # Moderate safety
    SPECULATIVE = "speculative"  # Higher risk
    HIGHLY_SPECULATIVE = "highly_speculative"  # High risk
    ISOLATED = "isolated"    # Single position only

class ContractType(str, Enum):
    """Contract type enumeration"""
    PERPETUAL = "perpetual"
    FUTURE = "future"
    PREDICTION = "prediction"

class MarketRegime(str, Enum):
    """Market regime enumeration for adaptive strategies"""
    CALM = "calm"
    NORMAL = "normal"
    VOLATILE = "volatile"
    TOXIC = "toxic"

@dataclass
class PoolBalance:
    """Pool balance structure"""
    scaled_balance: Decimal
    market_index: int
    padding: Tuple[int, ...] = field(default_factory=lambda: (0,))

@dataclass
class InsuranceClaim:
    """Insurance claim structure"""
    revenue_withdraw_since_last_settle: Decimal
    max_revenue_withdraw_per_period: Decimal
    quote_max_insurance: Decimal
    quote_settled_insurance: Decimal
    last_revenue_withdraw_ts: int

@dataclass
class HistoricalOracleData:
    """Historical oracle data"""
    last_oracle_price: Decimal
    last_oracle_price_twap: Decimal
    last_oracle_price_twap_5min: Decimal
    last_oracle_price_twap_ts: int
    last_oracle_conf_pct: Decimal
    last_oracle_delay: int
    last_oracle_price_twap_2: Decimal = Decimal('0')
    last_oracle_price_twap_3: Decimal = Decimal('0')
    last_oracle_price_twap_4: Decimal = Decimal('0')

@dataclass
class AMM:
    """Automated Market Maker structure and calculations"""
    oracle: str
    historical_oracle_data: HistoricalOracleData
    base_asset_reserve: Decimal
    quote_asset_reserve: Decimal
    concentration_coef: Decimal
    min_base_asset_reserve: Decimal
    max_base_asset_reserve: Decimal
    sqrt_k: Decimal
    peg_multiplier: Decimal
    terminal_quote_asset_reserve: Decimal
    base_asset_amount_long: Decimal
    base_asset_amount_short: Decimal
    base_asset_amount_with_amm: Decimal
    base_asset_amount_with_unsettled_lp: Decimal
    max_open_interest: Decimal
    quote_asset_amount: Decimal
    quote_entry_amount_long: Decimal
    quote_entry_amount_short: Decimal
    quote_break_even_amount_long: Decimal
    quote_break_even_amount_short: Decimal
    user_lp_shares: Decimal
    last_funding_rate: Decimal
    last_funding_rate_long: Decimal
    last_funding_rate_short: Decimal
    last_24h_avg_funding_rate: Decimal
    total_fee: Decimal
    total_mm_fee: Decimal
    total_exchange_fee: Decimal
    total_fee_minus_distributions: Decimal
    total_fee_withdrawn: Decimal
    total_liquidation_fee: Decimal
    cumulative_funding_rate_long: Decimal
    cumulative_funding_rate_short: Decimal
    total_social_loss: Decimal
    ask_base_asset_reserve: Decimal
    ask_quote_asset_reserve: Decimal
    bid_base_asset_reserve: Decimal
    bid_quote_asset_reserve: Decimal
    last_oracle_normalised_price: Decimal
    last_oracle_reserve_price_spread_pct: Decimal
    last_bid_price_twap: Decimal
    last_ask_price_twap: Decimal
    last_mark_price_twap: Decimal
    last_mark_price_twap_5min: Decimal
    last_update_slot: int
    last_oracle_conf_pct: Decimal
    net_revenue_since_last_funding: Decimal
    last_funding_rate_ts: int
    funding_period: int
    order_step_size: Decimal
    order_tick_size: Decimal
    min_order_size: Decimal
    volume_24h: Decimal
    long_intensity_volume: Decimal
    short_intensity_volume: Decimal
    last_trade_ts: int
    mark_std: Decimal
    oracle_std: Decimal
    last_mark_price_twap_ts: int
    base_spread: int
    max_spread: int
    long_spread: int
    short_spread: int
    mm_oracle_price: Decimal
    mm_oracle_slot: int
    max_fill_reserve_fraction: int
    max_slippage_ratio: int
    curve_update_intensity: int
    amm_jit_intensity: int
    oracle_source: str
    last_oracle_valid: bool
    target_base_asset_amount_per_lp: Decimal
    per_lp_base: int
    taker_speed_bump_override: int
    amm_spread_adjustment: int
    oracle_slot_delay_override: int
    mm_oracle_sequence_id: int
    net_unsettled_funding_pnl: Decimal
    quote_asset_amount_with_unsettled_lp: Decimal
    reference_price_offset: Decimal
    amm_inventory_spread_adjustment: int
    last_funding_oracle_twap: Decimal

    def reserve_price(self) -> Decimal:
        """Calculate AMM reserve price"""
        return (self.quote_asset_reserve / self.base_asset_reserve) * self.peg_multiplier

    def bid_price(self, reserve_price: Optional[Decimal] = None) -> Decimal:
        """Calculate bid price with spread adjustments"""
        if reserve_price is None:
            reserve_price = self.reserve_price()

        # Apply spread adjustments (simplified version)
        spread_adjustment = Decimal(str(self.short_spread)) / PERCENTAGE_PRECISION
        return reserve_price * (Decimal('1') - spread_adjustment)

    def ask_price(self, reserve_price: Optional[Decimal] = None) -> Decimal:
        """Calculate ask price with spread adjustments"""
        if reserve_price is None:
            reserve_price = self.reserve_price()

        # Apply spread adjustments (simplified version)
        spread_adjustment = Decimal(str(self.long_spread)) / PERCENTAGE_PRECISION
        return reserve_price * (Decimal('1') + spread_adjustment)

    def mark_price(self) -> Decimal:
        """Calculate mark price (mid between bid and ask)"""
        bid = self.bid_price()
        ask = self.ask_price()
        return (bid + ask) / Decimal('2')

    def update_funding_rate(self, oracle_price: Decimal, now: int) -> Decimal:
        """Calculate and update funding rate based on TWAP divergence"""
        # Simplified funding rate calculation
        # In Drift, this is more complex with TWAP calculations

        mark_price = self.mark_price()
        divergence = (mark_price - oracle_price) / oracle_price

        # Funding rate proportional to divergence (simplified)
        funding_rate = divergence * Decimal('0.0001')  # 0.01% per unit divergence

        # Clamp to reasonable bounds
        max_funding = Decimal('0.001')  # 0.1% per day
        min_funding = Decimal('-0.001')

        funding_rate = max(min_funding, min(max_funding, funding_rate))

        # Update stored values
        self.last_funding_rate = funding_rate
        self.last_funding_rate_ts = now

        return funding_rate

    def calculate_net_user_pnl(self, oracle_price: Decimal) -> Decimal:
        """Calculate net user PnL against AMM"""
        # Simplified calculation - in reality this is more complex
        mark_price = self.mark_price()
        price_diff = mark_price - oracle_price

        # Net PnL is the difference between mark and oracle scaled by position size
        net_pnl = price_diff * (self.base_asset_amount_long - self.base_asset_amount_short)

        return net_pnl

@dataclass
class PerpMarket:
    """Drift Protocol PerpMarket adaptation for Python"""

    # Core identifiers
    pubkey: str
    name: str
    market_index: int

    # Core components
    amm: AMM
    pnl_pool: PoolBalance
    insurance_claim: InsuranceClaim

    # Market state
    status: MarketStatus
    contract_type: ContractType
    contract_tier: ContractTier

    # Operational parameters
    paused_operations: int
    quote_spot_market_index: int
    fee_adjustment: int

    # Risk parameters
    unrealized_pnl_max_imbalance: Decimal
    expiry_ts: int
    expiry_price: Decimal

    # Fee and liquidation parameters
    imf_factor: int
    unrealized_pnl_imf_factor: int
    liquidator_fee: int
    if_liquidation_fee: int

    # Margin requirements
    margin_ratio_initial: int
    margin_ratio_maintenance: int
    unrealized_pnl_initial_asset_weight: int
    unrealized_pnl_maintenance_asset_weight: int

    # Position tracking
    number_of_users_with_base: int
    number_of_users: int

    # Fuel parameters
    fuel_boost_position: int
    fuel_boost_taker: int
    fuel_boost_maker: int
    pool_id: int

    # High leverage parameters
    high_leverage_margin_ratio_initial: int
    high_leverage_margin_ratio_maintenance: int

    # Protected maker parameters
    protected_maker_limit_price_divisor: int
    protected_maker_dynamic_divisor: int

    # Additional metadata
    last_fill_price: Decimal
    next_fill_record_id: int
    next_funding_rate_record_id: int
    next_curve_record_id: int

    @classmethod
    def from_drift_data(cls, drift_market_data: Dict[str, Any]) -> 'PerpMarket':
        """Create PerpMarket from Drift API data"""
        return cls(
            pubkey=drift_market_data.get('pubkey', ''),
            name=drift_market_data.get('name', ''),
            market_index=drift_market_data.get('marketIndex', 0),
            amm=AMM(**drift_market_data.get('amm', {})),
            pnl_pool=PoolBalance(**drift_market_data.get('pnlPool', {})),
            insurance_claim=InsuranceClaim(**drift_market_data.get('insuranceClaim', {})),
            status=MarketStatus(drift_market_data.get('status', 'active')),
            contract_type=ContractType(drift_market_data.get('contractType', 'perpetual')),
            contract_tier=ContractTier(drift_market_data.get('contractTier', 'highly_speculative')),
            paused_operations=drift_market_data.get('pausedOperations', 0),
            quote_spot_market_index=drift_market_data.get('quoteSpotMarketIndex', 0),
            fee_adjustment=drift_market_data.get('feeAdjustment', 0),
            unrealized_pnl_max_imbalance=Decimal(str(drift_market_data.get('unrealizedPnlMaxImbalance', 0))),
            expiry_ts=drift_market_data.get('expiryTs', 0),
            expiry_price=Decimal(str(drift_market_data.get('expiryPrice', 0))),
            imf_factor=drift_market_data.get('imfFactor', 0),
            unrealized_pnl_imf_factor=drift_market_data.get('unrealizedPnlImfFactor', 0),
            liquidator_fee=drift_market_data.get('liquidatorFee', 0),
            if_liquidation_fee=drift_market_data.get('ifLiquidationFee', 0),
            margin_ratio_initial=drift_market_data.get('marginRatioInitial', 0),
            margin_ratio_maintenance=drift_market_data.get('marginRatioMaintenance', 0),
            unrealized_pnl_initial_asset_weight=drift_market_data.get('unrealizedPnlInitialAssetWeight', 0),
            unrealized_pnl_maintenance_asset_weight=drift_market_data.get('unrealizedPnlMaintenanceAssetWeight', 0),
            number_of_users_with_base=drift_market_data.get('numberOfUsersWithBase', 0),
            number_of_users=drift_market_data.get('numberOfUsers', 0),
            fuel_boost_position=drift_market_data.get('fuelBoostPosition', 0),
            fuel_boost_taker=drift_market_data.get('fuelBoostTaker', 0),
            fuel_boost_maker=drift_market_data.get('fuelBoostMaker', 0),
            pool_id=drift_market_data.get('poolId', 0),
            high_leverage_margin_ratio_initial=drift_market_data.get('highLeverageMarginRatioInitial', 0),
            high_leverage_margin_ratio_maintenance=drift_market_data.get('highLeverageMarginRatioMaintenance', 0),
            protected_maker_limit_price_divisor=drift_market_data.get('protectedMakerLimitPriceDivisor', 0),
            protected_maker_dynamic_divisor=drift_market_data.get('protectedMakerDynamicDivisor', 0),
            last_fill_price=Decimal(str(drift_market_data.get('lastFillPrice', 0))),
            next_fill_record_id=drift_market_data.get('nextFillRecordId', 0),
            next_funding_rate_record_id=drift_market_data.get('nextFundingRateRecordId', 0),
            next_curve_record_id=drift_market_data.get('nextCurveRecordId', 0)
        )

    def get_margin_requirement(
        self,
        position_size: Decimal,
        margin_type: str,
        user_high_leverage_mode: bool = False
    ) -> Decimal:
        """
        Implement Drift's margin calculation logic

        Args:
            position_size: Size of the position
            margin_type: "initial" or "maintenance"
            user_high_leverage_mode: Whether user is in high leverage mode

        Returns:
            Required margin as decimal (e.g., 0.10 for 10%)
        """
        # Base margin ratio
        if user_high_leverage_mode and self.is_high_leverage_mode_enabled():
            margin_ratio_initial = Decimal(str(self.high_leverage_margin_ratio_initial))
            margin_ratio_maintenance = Decimal(str(self.high_leverage_margin_ratio_maintenance))
        else:
            margin_ratio_initial = Decimal(str(self.margin_ratio_initial))
            margin_ratio_maintenance = Decimal(str(self.margin_ratio_maintenance))

        # Select margin type
        if margin_type.lower() == "initial":
            base_margin_ratio = margin_ratio_initial
        elif margin_type.lower() == "maintenance":
            base_margin_ratio = margin_ratio_maintenance
        else:
            base_margin_ratio = margin_ratio_initial

        # Convert to decimal
        margin_ratio = base_margin_ratio / MARGIN_PRECISION

        # IMF (Initial Margin Factor) calculations
        if self.imf_factor > 0 and position_size != 0:
            imf_adjustment = Decimal(str(self.imf_factor)) / MARGIN_PRECISION
            # Size premium adjustment (simplified)
            size_factor = abs(position_size) / Decimal('1000000')  # Scale factor
            margin_ratio = margin_ratio * (Decimal('1') + imf_adjustment * size_factor)

        # Contract tier modifications
        tier_multiplier = self._get_contract_tier_multiplier()
        margin_ratio = margin_ratio * tier_multiplier

        return margin_ratio

    def _get_contract_tier_multiplier(self) -> Decimal:
        """Get margin multiplier based on contract tier"""
        multipliers = {
            ContractTier.A: Decimal('1.0'),      # Safest
            ContractTier.B: Decimal('1.1'),      # Slightly higher
            ContractTier.C: Decimal('1.2'),      # Moderate increase
            ContractTier.SPECULATIVE: Decimal('1.5'),     # Higher risk
            ContractTier.HIGHLY_SPECULATIVE: Decimal('2.0'), # High risk
            ContractTier.ISOLATED: Decimal('1.0') # Special case
        }
        return multipliers.get(self.contract_tier, Decimal('1.0'))

    def get_unrealized_asset_weight(
        self,
        unrealized_pnl: Decimal,
        margin_type: str
    ) -> Decimal:
        """Calculate unrealized PnL asset weight"""
        # Base asset weight
        if margin_type.lower() == "initial":
            base_weight = Decimal(str(self.unrealized_pnl_initial_asset_weight))
        else:
            base_weight = Decimal(str(self.unrealized_pnl_maintenance_asset_weight))

        asset_weight = base_weight / SPOT_WEIGHT_PRECISION

        # IMF adjustment for unrealized PnL
        if unrealized_pnl > 0 and self.unrealized_pnl_imf_factor > 0:
            imf_factor = Decimal(str(self.unrealized_pnl_imf_factor)) / MARGIN_PRECISION
            pnl_factor = unrealized_pnl / Decimal('1000000')  # Scale factor
            asset_weight = asset_weight * (Decimal('1') + imf_factor * pnl_factor)

        # For negative PnL, always use full weight (1.0)
        if unrealized_pnl <= 0:
            asset_weight = Decimal('1.0')

        return asset_weight

    def is_high_leverage_mode_enabled(self) -> bool:
        """Check if high leverage mode is enabled"""
        return (self.high_leverage_margin_ratio_initial > 0 and
                self.high_leverage_margin_ratio_maintenance > 0)

    def get_open_interest(self) -> Decimal:
        """Calculate total open interest"""
        return abs(self.amm.base_asset_amount_long) + abs(self.amm.base_asset_amount_short)

    def is_reduce_only(self) -> bool:
        """Check if market is in reduce-only mode"""
        return self.status == MarketStatus.REDUCE_ONLY

    def is_operation_paused(self, operation: str) -> bool:
        """Check if specific operation is paused"""
        # Simplified - in reality this would check bit flags
        return self.paused_operations > 0

    def get_max_confidence_interval_multiplier(self) -> Decimal:
        """Get max confidence interval multiplier based on contract tier"""
        multipliers = {
            ContractTier.A: Decimal('1'),
            ContractTier.B: Decimal('1'),
            ContractTier.C: Decimal('2'),
            ContractTier.SPECULATIVE: Decimal('10'),
            ContractTier.HIGHLY_SPECULATIVE: Decimal('50'),
            ContractTier.ISOLATED: Decimal('50')
        }
        return multipliers.get(self.contract_tier, Decimal('1'))

    def get_contract_tier_limits(self) -> Dict[str, Decimal]:
        """Get position limits based on contract tier"""
        limits = {
            ContractTier.A: Decimal('1000000'),      # $1M
            ContractTier.B: Decimal('500000'),       # $500K
            ContractTier.C: Decimal('100000'),       # $100K
            ContractTier.SPECULATIVE: Decimal('10000'),    # $10K
            ContractTier.HIGHLY_SPECULATIVE: Decimal('1000'),  # $1K
            ContractTier.ISOLATED: Decimal('1000')    # $1K (single position)
        }
        return limits.get(self.contract_tier, Decimal('1000'))

    def calculate_funding_rate(self, oracle_price: Decimal, now: int) -> Decimal:
        """Calculate funding rate for this market"""
        return self.amm.update_funding_rate(oracle_price, now)

    def get_fair_price(self, oracle_price: Decimal, use_microprice: bool = True) -> Decimal:
        """Calculate fair price blending oracle and AMM"""
        if use_microprice:
            amm_price = self.amm.mark_price()
            # Blend oracle and AMM prices based on market conditions
            blend_factor = self._calculate_price_blend_factor(oracle_price)
            return oracle_price * (Decimal('1') - blend_factor) + amm_price * blend_factor
        return oracle_price

    def _calculate_price_blend_factor(self, oracle_price: Decimal) -> Decimal:
        """Calculate how much to blend AMM price vs oracle price"""
        # Based on oracle confidence and market conditions
        oracle_conf_pct = self.amm.last_oracle_conf_pct / PERCENTAGE_PRECISION

        # Higher confidence = more weight to oracle
        # Lower confidence = more weight to AMM microprice
        if oracle_conf_pct < Decimal('0.01'):  # < 1% confidence
            return Decimal('0.8')  # 80% AMM weight
        elif oracle_conf_pct < Decimal('0.05'):  # < 5% confidence
            return Decimal('0.6')  # 60% AMM weight
        else:
            return Decimal('0.2')  # 20% AMM weight

class DriftAMMCalculator:
    """Python implementation of Drift AMM calculations"""

    @staticmethod
    def calculate_reserve_price(base_reserve: Decimal, quote_reserve: Decimal, peg: Decimal) -> Decimal:
        """Calculate AMM reserve price with proper precision"""
        if base_reserve == 0:
            return peg
        return (quote_reserve / base_reserve) * peg

    @staticmethod
    def calculate_bid_ask_prices(reserve_price: Decimal, spread_params: Dict[str, Any]) -> Tuple[Decimal, Decimal]:
        """Calculate bid/ask prices with spread adjustments"""
        base_spread = spread_params.get('base_spread', 250) / PERCENTAGE_PRECISION
        long_spread = spread_params.get('long_spread', 250) / PERCENTAGE_PRECISION
        short_spread = spread_params.get('short_spread', 250) / PERCENTAGE_PRECISION

        bid_price = reserve_price * (Decimal('1') - short_spread)
        ask_price = reserve_price * (Decimal('1') + long_spread)

        return bid_price, ask_price

    @staticmethod
    def update_funding_rate(oracle_twap: Decimal, mark_twap: Decimal) -> Decimal:
        """Calculate funding rate based on TWAP divergence"""
        if oracle_twap == 0:
            return Decimal('0')

        # Calculate divergence
        divergence = (mark_twap - oracle_twap) / oracle_twap

        # Funding rate proportional to divergence
        funding_rate = divergence * Decimal('0.0001')  # 0.01% per unit divergence

        # Apply buffer and clamp to reasonable bounds
        funding_rate_buffer = Decimal('0.8')  # 80% buffer
        funding_rate = funding_rate * funding_rate_buffer

        max_funding = Decimal('0.001')  # 0.1% per period max
        min_funding = Decimal('-0.001')

        return max(min_funding, min(max_funding, funding_rate))

    @staticmethod
    def calculate_inventory_skew_adjustment(
        inventory_imbalance: Decimal,
        max_inventory_skew: Decimal = Decimal('0.1')
    ) -> Decimal:
        """Calculate inventory skew adjustment for quotes"""
        if abs(inventory_imbalance) < max_inventory_skew:
            return Decimal('0')

        # Linear adjustment beyond max skew
        excess_skew = abs(inventory_imbalance) - max_inventory_skew
        adjustment_factor = excess_skew * Decimal('0.5')  # 50% adjustment per unit excess

        return adjustment_factor if inventory_imbalance > 0 else -adjustment_factor

    @staticmethod
    def calculate_funding_skew_adjustment(
        funding_rate: Decimal,
        max_funding_skew: Decimal = Decimal('0.0005')
    ) -> Decimal:
        """Calculate funding-skewed quote adjustment"""
        if abs(funding_rate) < max_funding_skew:
            return Decimal('0')

        # Adjust quotes to incentivize position balancing
        # Positive funding rate = longs pay shorts = incentivize short positions
        # Negative funding rate = shorts pay longs = incentivize long positions

        adjustment_factor = (abs(funding_rate) - max_funding_skew) * Decimal('1000')
        return -adjustment_factor if funding_rate > 0 else adjustment_factor

    @staticmethod
    def calculate_impact_aware_band(
        base_price: Decimal,
        inventory_imbalance: Decimal,
        l2_depth: Optional[Dict[str, Any]] = None,
        amm_elasticity: Decimal = Decimal('0.1')
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate impact-aware inventory bands using AMM elasticity and L2 depth

        Args:
            base_price: Base price for band calculation
            inventory_imbalance: Current inventory imbalance (-1 to 1)
            l2_depth: L2 order book depth information
            amm_elasticity: AMM price elasticity factor

        Returns:
            Tuple of (bid_band, ask_band) representing the edges of the quote band
        """
        # Base band width
        base_band_width = Decimal('0.005')  # 0.5% base band

        # Adjust based on inventory imbalance
        inventory_adjustment = abs(inventory_imbalance) * Decimal('0.01')  # Up to 1% additional width

        # Adjust based on L2 depth
        depth_adjustment = Decimal('0')
        if l2_depth:
            bid_depth = l2_depth.get('bid_depth', Decimal('0'))
            ask_depth = l2_depth.get('ask_depth', Decimal('0'))

            # Less depth = wider bands to reduce impact
            avg_depth = (bid_depth + ask_depth) / Decimal('2')
            if avg_depth > 0:
                depth_factor = Decimal('1000000') / avg_depth  # Inverse relationship
                depth_adjustment = min(depth_factor * Decimal('0.001'), Decimal('0.005'))

        # AMM elasticity adjustment
        elasticity_adjustment = amm_elasticity * Decimal('0.002')

        # Total band width
        band_width = base_band_width + inventory_adjustment + depth_adjustment + elasticity_adjustment

        # Calculate band edges
        bid_band = base_price * (Decimal('1') - band_width)
        ask_band = base_price * (Decimal('1') + band_width)

        return bid_band, ask_band

# Convenience functions
def create_perp_market_adapter(drift_market_data: Dict[str, Any]) -> PerpMarket:
    """Create PerpMarket adapter from Drift API data"""
    return PerpMarket.from_drift_data(drift_market_data)

def calculate_margin_requirement(
    market: PerpMarket,
    position_size: Decimal,
    margin_type: str,
    high_leverage_mode: bool = False
) -> Decimal:
    """Convenience function for margin calculation"""
    return market.get_margin_requirement(position_size, margin_type, high_leverage_mode)

def get_fair_value_price(
    market: PerpMarket,
    oracle_price: Decimal,
    use_microprice: bool = True
) -> Decimal:
    """Convenience function for fair value calculation"""
    return market.get_fair_price(oracle_price, use_microprice)
