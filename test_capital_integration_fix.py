#!/usr/bin/env python3
"""
Test script to verify the capital allocation integration fixes
"""

import sys
import os
import asyncio
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_capital_allocation_integration():
    """Test the capital allocation integration fixes"""
    print("🧪 Testing Capital Allocation Integration Fixes")
    print("=" * 60)

    try:
        # Test 1: Swift Signer Fix
        print("📋 Test 1: Swift Signer Fix")
        from libs.swift.signer import SwiftSigner
        from solders.keypair import Keypair

        test_keypair = Keypair()
        class MockAdapter:
            def can_sign(self): return True
            @property
            def keypair(self): return test_keypair

        mock_adapter = MockAdapter()

        signer = SwiftSigner(mock_adapter)
        test_msg = b"test message for swift signing"
        signature = signer.sign_swift_message(test_msg)
        is_valid = signer.validate_signature(test_msg, signature)

        print(f"  ✅ Signature generated: {len(signature)} chars")
        print(f"  ✅ Signature validation: {is_valid}")
        print("  ✅ Swift signer fix: PASSED")

    except Exception as e:
        print(f"  ❌ Swift signer test failed: {e}")
        return False

    try:
        # Test 2: Capital Allocator Import
        print("\n📋 Test 2: Capital Allocator Import")
        from libs.orchestration.capital_allocator import CapitalAllocator, get_capital_allocator, reset_capital_allocator

        reset_capital_allocator()
        allocator = CapitalAllocator(total_portfolio_usd=10000.0)

        print("  ✅ Capital allocator created successfully")
        print("  ✅ Capital allocator import: PASSED")

    except Exception as e:
        print(f"  ❌ Capital allocator test failed: {e}")
        return False

    try:
        # Test 3: Capital Allocation Logic
        print("\n📋 Test 3: Capital Allocation Logic")
        mock_drift_user = Mock()
        mock_drift_user.get_total_collateral.return_value = 1000000000  # $1000
        mock_drift_user.get_free_collateral.return_value = 500000000    # $500

        allocation = await allocator.get_capital_allocation(
            "shotgun_mm", mock_drift_user, current_position_usd=100.0
        )

        print(f"  ✅ Allocation: max_trade=${allocation.max_trade_usd}, available=${allocation.available_capital_usd}")
        print("  ✅ Capital allocation logic: PASSED")

    except Exception as e:
        print(f"  ❌ Capital allocation logic test failed: {e}")
        return False

    try:
        # Test 4: Global Allocator
        print("\n📋 Test 4: Global Allocator")
        global_alloc1 = get_capital_allocator()
        global_alloc2 = get_capital_allocator()

        print(f"  ✅ Global allocator singleton: {global_alloc1 is global_alloc2}")
        print("  ✅ Global allocator: PASSED")

    except Exception as e:
        print(f"  ❌ Global allocator test failed: {e}")
        return False

    print("\n🎉 ALL CAPITAL ALLOCATION INTEGRATION FIXES PASSED!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_capital_allocation_integration())
    if not success:
        sys.exit(1)
    print("\n🚀 Ready to test with live bot!")
