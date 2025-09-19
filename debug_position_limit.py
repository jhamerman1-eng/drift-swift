#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
import asyncio
from unittest.mock import Mock
from libs.orchestration.capital_allocator import CapitalAllocator, reset_capital_allocator

reset_capital_allocator()
allocator = CapitalAllocator(total_portfolio_usd=1000.0)
drift_user = Mock()

async def debug_position_limit():
    print('🔍 Debugging position limit logic...')

    # Test position limit exceeded (98% utilization)
    allocation = await allocator.get_capital_allocation(
        'shotgun_mm', drift_user, current_position_usd=490.0
    )

    print(f'Position: {allocation.current_position_usd}')
    print(f'Max position: 500.0')
    print(f'Available capital: {allocation.available_capital_usd}')
    print(f'Risk limit: {allocation.risk_limit_usd}')
    print(f'Can trade: {allocation.can_trade}')
    print(f'Reason: "{allocation.reason}"')

    position_utilization = abs(allocation.current_position_usd) / 500.0
    print(f'Position utilization: {position_utilization:.3f}')
    print(f'Should trigger position limit: {position_utilization > 0.95}')

asyncio.run(debug_position_limit())
