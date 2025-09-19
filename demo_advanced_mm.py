#!/usr/bin/env python3
"""
Advanced Market Making Demo

Demonstrates the integration of advanced market making features:
1. Funding-skewed quote adapter
2. Impact-aware inventory bands
3. Unified fair-value calculation
4. Drift Protocol PerpMarket adapter
5. L2 order book integration

This demo shows how all components work together to create sophisticated,
intelligent market making strategies.
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime

from libs.drift.drift_market_adapter import (
    PerpMarket, DriftAMMCalculator, ContractTier, HistoricalOracleData,
    PoolBalance, InsuranceClaim, AMM
)
from libs.market_making.advanced_quote_engine import (
    AdvancedQuoteEngine, calculate_advanced_quotes
)
from libs.orderbook.l2_orderbook_engine import get_drift_l2_orderbook
from libs.drift.drift_market_adapter import MarketRegime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedMMDemo:
    """Demonstration of advanced market making capabilities"""

    def __init__(self):
        self.engine = AdvancedQuoteEngine()

    async def run_comprehensive_demo(self):
        """Run comprehensive demonstration of all advanced features"""
        print("🔧 ADVANCED MARKET MAKING DEMO")
        print("=" * 60)

        # 1. Create sample Drift PerpMarket
        print("\n1. 🏗️ Creating Drift PerpMarket Adapter")
        perp_market = await self._create_sample_perp_market()
        print(f"   ✅ Created {perp_market.name} market")
        print(f"   📊 Contract Tier: {perp_market.contract_tier}")
        print(f"   🎯 Status: {perp_market.status}")

        # 2. Demonstrate margin calculations
        print("\n2. 💰 Margin Requirement Calculations")
        position_size = Decimal('1000')  # 1000 base units
        margin_req = perp_market.get_margin_requirement(position_size, "initial")
        print(f"   💰 Initial Margin: {margin_req:.4%}")
        print(f"   🎯 Maintenance: {perp_market.get_margin_requirement(position_size, 'maintenance'):.4%}")

        # 3. AMM Calculations
        print("\n3. ⚙️ AMM Mathematics")
        reserve_price = perp_market.amm.reserve_price()
        bid_price, ask_price = DriftAMMCalculator.calculate_bid_ask_prices(
            reserve_price, {'base_spread': 250, 'long_spread': 250, 'short_spread': 250}
        )
        print(f"   💰 Reserve Price: {reserve_price:.6f}")
        print(f"   📈 Bid Price: {bid_price:.6f}")
        print(f"   📉 Ask Price: {ask_price:.6f}")
        # 4. Funding Rate Impact
        print("\n4. 📈 Funding Rate Analysis")
        funding_rate = Decimal('0.0002')  # 0.02% funding rate
        calculated_funding = perp_market.calculate_funding_rate(Decimal('50000'), int(datetime.now().timestamp()))
        print(f"   📊 Funding Rate: {funding_rate:.6f}")
        print(f"   🔄 Calculated Funding: {calculated_funding:.6f}")
        # 5. L2 Order Book Integration
        print("\n5. 📊 L2 Order Book Integration")
        try:
            l2_orderbook = await get_drift_l2_orderbook("SOL-PERP", depth=10)
            if l2_orderbook:
                print("   ✅ Retrieved L2 orderbook data")
                print(f"   📊 Bids: {len(l2_orderbook.bids)}, Asks: {len(l2_orderbook.asks)}")
                if l2_orderbook.spread_bps:
                    print(f"   📏 Spread: {l2_orderbook.spread_bps:.2f} bps")
            else:
                print("   ⚠️ No L2 data available (using sample data)")
                l2_orderbook = None
        except Exception as e:
            print(f"   ⚠️ L2 data unavailable: {e}")
            l2_orderbook = None

        # 6. Advanced Quote Calculation
        print("\n6. 🎯 Advanced Quote Engine")
        current_inventory = Decimal('0.1')  # Slightly long bias
        oracle_price = Decimal('50000')
        market_regime = "volatile"

        advanced_quotes = await calculate_advanced_quotes(
            perp_market=perp_market,
            current_inventory=current_inventory,
            oracle_price=oracle_price,
            funding_rate=funding_rate,
            market_regime=market_regime
        )

        print("   📈 Final Quotes:")
        print(f"   💰 Bid Price: {advanced_quotes['quotes']['bid_price']:.6f}")
        print(f"   📈 Ask Price: {advanced_quotes['quotes']['ask_price']:.6f}")
        print(f"   🎯 Spread: {advanced_quotes['quotes']['spread_bps']:.2f} bps")
        print("   🎯 Fair Value:")
        print(f"   💎 Fair Price: {advanced_quotes['fair_value']['price']:.6f}")
        print(f"   🧠 Oracle Weight: {advanced_quotes['fair_value']['oracle_weight']:.1%}")
        print(f"   ⚙️ AMM Weight: {advanced_quotes['fair_value']['amm_weight']:.1%}")
        print(f"   🎯 Confidence: {advanced_quotes['fair_value']['confidence_score']:.2%}")
        print("   💰 Funding Adjustments:")
        print(f"   Bid Adjustment: {advanced_quotes['funding_adjustment']['bid_spread_adjustment']:.4%}")
        print(f"   Ask Adjustment: {advanced_quotes['funding_adjustment']['ask_spread_adjustment']:.4%}")
        print(f"   Reason: {advanced_quotes['funding_adjustment']['reason']}")

        # 7. Inventory Band Analysis
        print("\n7. 📏 Inventory Band Analysis")
        band_info = advanced_quotes['inventory_band']
        print(f"   🎯 Bid Edge: {band_info['bid_edge']:.6f}")
        print(f"   🎯 Ask Edge: {band_info['ask_edge']:.6f}")
        print(f"   📏 Band Width: {band_info['band_width']:.4f}")
        # 8. Market Regime Impact
        print("\n8. 🌊 Market Regime Analysis")
        print(f"   🎭 Current Regime: {market_regime.upper()}")
        print(f"   📊 Confidence Score: {advanced_quotes['fair_value']['confidence_score']:.2%}")
        print(f"   🎯 L2 Data Used: {advanced_quotes['metadata']['l2_data_used']}")

        # 9. Performance Metrics
        print("\n9. 📊 Performance Metrics")
        stats = self.engine.get_engine_statistics()

        print("   🔄 Funding Adapter:")
        funding_stats = stats['funding_adapter']
        if 'avg_bid_adjustment' in funding_stats:
            print(f"   📊 Avg Bid Adjustment: {funding_stats['avg_bid_adjustment']:.4f}")
            print(f"   📊 Avg Ask Adjustment: {funding_stats['avg_ask_adjustment']:.4f}")
        print("   📈 Inventory Bands:")
        band_stats = stats['inventory_bands']
        if 'avg_band_width' in band_stats:
            print(f"   📏 Avg Band Width: {band_stats['avg_band_width']:.4f}")
        print("   🎯 Fair Value Engine:")
        fv_stats = stats['fair_value_engine']
        if 'avg_confidence' in fv_stats:
            print(f"   🎯 Avg Confidence: {fv_stats['avg_confidence']:.2f}")
        # 10. Strategy Recommendations
        print("\n10. 💡 Strategy Recommendations")
        self._generate_strategy_recommendations(advanced_quotes)

        print("\n" + "=" * 60)
        print("✅ ADVANCED MARKET MAKING DEMO COMPLETE")
        print("🔥 All systems operational and integrated!")

    async def _create_sample_perp_market(self) -> PerpMarket:
        """Create a sample PerpMarket for demonstration"""
        # Create sample components
        historical_oracle_data = HistoricalOracleData(
            last_oracle_price=Decimal('50000000'),
            last_oracle_price_twap=Decimal('49900000'),
            last_oracle_price_twap_5min=Decimal('49950000'),
            last_oracle_price_twap_ts=int(datetime.now().timestamp()) - 3600,
            last_oracle_conf_pct=Decimal('50000'),
            last_oracle_delay=0
        )

        amm = AMM(
            oracle="11111111111111111111111111111113",
            historical_oracle_data=historical_oracle_data,
            base_asset_reserve=Decimal('1000000000000'),
            quote_asset_reserve=Decimal('50000000000000'),
            concentration_coef=Decimal('100000000'),
            min_base_asset_reserve=Decimal('500000000000'),
            max_base_asset_reserve=Decimal('2000000000000'),
            sqrt_k=Decimal('1000000000000'),
            peg_multiplier=Decimal('1000000'),
            terminal_quote_asset_reserve=Decimal('50000000000000'),
            base_asset_amount_long=Decimal('100000000000'),
            base_asset_amount_short=Decimal('-50000000000'),
            base_asset_amount_with_amm=Decimal('50000000000'),
            base_asset_amount_with_unsettled_lp=Decimal('0'),
            max_open_interest=Decimal('1000000000000'),
            quote_asset_amount=Decimal('1000000000000'),
            quote_entry_amount_long=Decimal('500000000000'),
            quote_entry_amount_short=Decimal('500000000000'),
            quote_break_even_amount_long=Decimal('500000000000'),
            quote_break_even_amount_short=Decimal('500000000000'),
            user_lp_shares=Decimal('1000000000000'),
            last_funding_rate=Decimal('20000'),
            last_funding_rate_long=Decimal('15000'),
            last_funding_rate_short=Decimal('25000'),
            last_24h_avg_funding_rate=Decimal('18000'),
            total_fee=Decimal('10000000000'),
            total_mm_fee=Decimal('5000000000'),
            total_exchange_fee=Decimal('2000000000'),
            total_fee_minus_distributions=Decimal('8000000000'),
            total_fee_withdrawn=Decimal('1000000000'),
            total_liquidation_fee=Decimal('500000000'),
            cumulative_funding_rate_long=Decimal('100000000'),
            cumulative_funding_rate_short=Decimal('-100000000'),
            total_social_loss=Decimal('100000000'),
            ask_base_asset_reserve=Decimal('1100000000000'),
            ask_quote_asset_reserve=Decimal('45000000000000'),
            bid_base_asset_reserve=Decimal('900000000000'),
            bid_quote_asset_reserve=Decimal('55000000000000'),
            last_oracle_normalised_price=Decimal('50000000'),
            last_oracle_reserve_price_spread_pct=Decimal('10000'),
            last_bid_price_twap=Decimal('49900000'),
            last_ask_price_twap=Decimal('50100000'),
            last_mark_price_twap=Decimal('50000000'),
            last_mark_price_twap_5min=Decimal('49980000'),
            last_update_slot=100000000,
            last_oracle_conf_pct=Decimal('50000'),
            net_revenue_since_last_funding=Decimal('1000000000'),
            last_funding_rate_ts=int(datetime.now().timestamp()) - 3600,
            funding_period=3600,
            order_step_size=Decimal('1000000'),
            order_tick_size=Decimal('1000'),
            min_order_size=Decimal('1000000'),
            volume_24h=Decimal('1000000000000'),
            long_intensity_volume=Decimal('600000000000'),
            short_intensity_volume=Decimal('400000000000'),
            last_trade_ts=int(datetime.now().timestamp()) - 60,
            mark_std=Decimal('500000'),
            oracle_std=Decimal('300000'),
            last_mark_price_twap_ts=int(datetime.now().timestamp()) - 300,
            base_spread=250,
            max_spread=1000,
            long_spread=250,
            short_spread=250,
            mm_oracle_price=Decimal('50000000'),
            mm_oracle_slot=100000000,
            max_fill_reserve_fraction=10,
            max_slippage_ratio=50,
            curve_update_intensity=100,
            amm_jit_intensity=0,
            oracle_source="pyth",
            last_oracle_valid=True,
            target_base_asset_amount_per_lp=Decimal('100000'),
            per_lp_base=6,
            taker_speed_bump_override=0,
            amm_spread_adjustment=0,
            oracle_slot_delay_override=0,
            mm_oracle_sequence_id=1000,
            net_unsettled_funding_pnl=Decimal('0'),
            quote_asset_amount_with_unsettled_lp=Decimal('0'),
            reference_price_offset=Decimal('0'),
            amm_inventory_spread_adjustment=0,
            last_funding_oracle_twap=Decimal('49950000')
        )

        pnl_pool = PoolBalance(
            scaled_balance=Decimal('1000000000000'),
            market_index=1
        )

        insurance_claim = InsuranceClaim(
            revenue_withdraw_since_last_settle=Decimal('0'),
            max_revenue_withdraw_per_period=Decimal('100000000000'),
            quote_max_insurance=Decimal('500000000000'),
            quote_settled_insurance=Decimal('0'),
            last_revenue_withdraw_ts=int(datetime.now().timestamp()) - 86400
        )

        # Create PerpMarket directly
        return PerpMarket(
            pubkey="11111111111111111111111111111112",
            name="SOL-PERP",
            market_index=0,
            amm=amm,
            pnl_pool=pnl_pool,
            insurance_claim=insurance_claim,
            status="active",
            contract_type="perpetual",
            contract_tier="B",
            paused_operations=0,
            quote_spot_market_index=1,
            fee_adjustment=0,
            unrealized_pnl_max_imbalance=Decimal('0'),
            expiry_ts=0,
            expiry_price=Decimal('0'),
            imf_factor=1000,
            unrealized_pnl_imf_factor=500,
            liquidator_fee=5000,
            if_liquidation_fee=2500,
            margin_ratio_initial=1000,
            margin_ratio_maintenance=500,
            unrealized_pnl_initial_asset_weight=5000,
            unrealized_pnl_maintenance_asset_weight=2000,
            number_of_users_with_base=1000,
            number_of_users=5000,
            fuel_boost_position=0,
            fuel_boost_taker=0,
            fuel_boost_maker=0,
            pool_id=0,
            high_leverage_margin_ratio_initial=200,
            high_leverage_margin_ratio_maintenance=100,
            protected_maker_limit_price_divisor=10,
            protected_maker_dynamic_divisor=20,
            last_fill_price=Decimal('50000000'),
            next_fill_record_id=1000,
            next_funding_rate_record_id=100,
            next_curve_record_id=50
        )

    def _generate_strategy_recommendations(self, advanced_quotes: dict):
        """Generate strategy recommendations based on quote analysis"""
        fair_value = advanced_quotes['fair_value']
        funding_adj = advanced_quotes['funding_adjustment']
        inventory_band = advanced_quotes['inventory_band']
        market_data = advanced_quotes['market_data']

        print("   📋 Key Insights:")

        # Confidence analysis
        if fair_value['confidence_score'] > 0.8:
            print("   ✅ High confidence in fair value signal")
        elif fair_value['confidence_score'] < 0.5:
            print("   ⚠️ Low confidence - rely more on AMM signals")

        # Funding analysis
        if "longs pay shorts" in funding_adj['reason']:
            print("   💰 Longs paying shorts - consider short positioning")
        elif "shorts pay longs" in funding_adj['reason']:
            print("   💰 Shorts paying longs - consider long positioning")

        # Inventory analysis
        band_width = inventory_band['band_width']
        if band_width > 0.02:  # > 2% band
            print("   📏 Wide bands - significant inventory management needed")
        elif band_width < 0.005:  # < 0.5% band
            print("   📏 Tight bands - aggressive quoting possible")

        # Market regime analysis
        regime = market_data['market_regime']
        if regime == "volatile":
            print("   🌊 Volatile market - use conservative parameters")
        elif regime == "calm":
            print("   🌊 Calm market - optimize for tighter spreads")

        print("   🎯 Recommended Actions:")
        print("   • Monitor funding rates for positioning signals")
        print("   • Adjust inventory bands based on market conditions")
        print("   • Use fair value confidence for quote aggressiveness")
        print("   • Consider L2 depth for optimal order sizing")

async def main():
    """Run the advanced market making demonstration"""
    demo = AdvancedMMDemo()

    try:
        await demo.run_comprehensive_demo()
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
