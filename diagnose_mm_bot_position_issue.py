#!/usr/bin/env python3
"""
Diagnostic script to identify the specific position issue in the MM bot
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

from driftpy.drift_client import DriftClient
from driftpy.keypair import load_keypair
from solana.rpc.async_api import AsyncClient
from anchorpy import Wallet
from driftpy.constants.numeric_constants import QUOTE_PRECISION, BASE_PRECISION
from driftpy.math.margin import MarginCategory

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("mm-diagnostic")

class MMBotDiagnostic:
    """Diagnostic tool for MM bot position issues"""
    
    def __init__(self):
        self.drift_client = None
        self.keypair = None
        self.drift_user = None
    
    async def initialize(self):
        """Initialize DriftPy client"""
        try:
            # Load keypair
            keypair_path = ".beta_dev_wallet.json"
            if not os.path.exists(keypair_path):
                logger.error(f"Wallet file not found: {keypair_path}")
                return False
            
            self.keypair = load_keypair(keypair_path)
            logger.info(f"Wallet loaded: {self.keypair.pubkey()}")
            
            # Initialize DriftPy client
            rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
            connection = AsyncClient(rpc_url)
            wallet = Wallet(self.keypair)
            
            self.drift_client = DriftClient(connection, wallet, "devnet")
            # Subscribe to get user data
            await self.drift_client.subscribe()
            
            # Get drift user
            self.drift_user = self.drift_client.get_user()
            
            logger.info("DriftPy client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    async def diagnose_position_issue(self):
        """Diagnose the position issue"""
        logger.info("🔍 Diagnosing MM Bot Position Issue")
        logger.info("=" * 60)
        
        try:
            # 1. Check user account
            logger.info("1️⃣ Checking User Account")
            user_account = self.drift_user.get_user_account()
            logger.info(f"User account loaded: {user_account is not None}")
            
            if user_account:
                logger.info(f"User account data: {user_account}")
                
                # Check perp positions
                if hasattr(user_account, 'perp_positions'):
                    logger.info(f"Perp positions count: {len(user_account.perp_positions)}")
                    for i, pos in enumerate(user_account.perp_positions):
                        logger.info(f"Position {i}: {pos}")
                        if hasattr(pos, 'base_asset_amount'):
                            position_sol = float(pos.base_asset_amount) / BASE_PRECISION
                            logger.info(f"  Position in SOL: {position_sol:.6f}")
            
            # 2. Check specific position methods
            logger.info("\n2️⃣ Checking Position Methods")
            
            # Try get_user_position
            try:
                position = await self.drift_client.get_user_position(0, 0)
                if position:
                    logger.info(f"get_user_position result: {position}")
                    if hasattr(position, 'base_asset_amount'):
                        position_sol = float(position.base_asset_amount) / BASE_PRECISION
                        logger.info(f"Position in SOL: {position_sol:.6f}")
                else:
                    logger.info("get_user_position returned None")
            except Exception as e:
                logger.error(f"get_user_position error: {e}")
            
            # 3. Check collateral status
            logger.info("\n3️⃣ Checking Collateral Status")
            try:
                total_collateral = self.drift_user.get_total_collateral(MarginCategory.INITIAL, strict=True)
                free_collateral = self.drift_user.get_free_collateral(MarginCategory.INITIAL)
                margin_req = self.drift_user.get_margin_requirement(MarginCategory.INITIAL, strict=True)
                
                total_usd = total_collateral / QUOTE_PRECISION
                free_usd = free_collateral / QUOTE_PRECISION
                margin_usd = margin_req / QUOTE_PRECISION
                
                logger.info(f"Total Collateral: ${total_usd:.2f}")
                logger.info(f"Free Collateral: ${free_usd:.2f}")
                logger.info(f"Margin Requirement: ${margin_usd:.2f}")
                
            except Exception as e:
                logger.error(f"Collateral check error: {e}")
            
            # 4. Check inventory manager logic
            logger.info("\n4️⃣ Checking Inventory Manager Logic")
            
            # Simulate the inventory manager logic
            test_positions = [0.0, 0.5, -0.5, 119.0, 120.0, 121.0, -119.0, -120.0]
            max_position = 120.0
            
            for pos in test_positions:
                should_trade = abs(pos) < max_position
                logger.info(f"Position: {pos:8.6f}, Should Trade: {should_trade}")
            
            # 5. Check the specific issue
            logger.info("\n5️⃣ Checking Specific Issue")
            
            # The issue might be in the position update logic
            current_position = 0.0  # This should be the actual position
            
            # Check if the bot is using the wrong position value
            logger.info(f"Current position (should be 0.0): {current_position}")
            logger.info(f"Max position: {max_position}")
            logger.info(f"Should trade: {abs(current_position) < max_position}")
            
            # Check if there's a default value issue
            logger.info("\n6️⃣ Checking Default Values")
            logger.info("Looking for where -5000.0000 might be coming from...")
            
            # Check if there's a default value in the code
            default_values = [-5000.0, 5000.0, -5000, 5000]
            for val in default_values:
                if abs(val) >= max_position:
                    logger.warning(f"Found problematic default value: {val}")
            
            return True
            
        except Exception as e:
            logger.error(f"Diagnostic error: {e}")
            return False
    
    async def test_position_update_methods(self):
        """Test different position update methods"""
        logger.info("\n🧪 Testing Position Update Methods")
        
        methods_to_test = [
            ("get_user_position", self._test_get_user_position),
            ("get_user_account", self._test_get_user_account),
            ("drift_user methods", self._test_drift_user_methods),
        ]
        
        for method_name, test_func in methods_to_test:
            logger.info(f"\nTesting {method_name}:")
            try:
                result = await test_func()
                logger.info(f"✅ {method_name}: {result}")
            except Exception as e:
                logger.error(f"❌ {method_name}: {e}")
    
    async def _test_get_user_position(self):
        """Test get_user_position method"""
        position = await self.drift_client.get_user_position(0, 0)
        if position:
            return f"Position: {position}, Base amount: {position.base_asset_amount if hasattr(position, 'base_asset_amount') else 'N/A'}"
        return "No position found"
    
    async def _test_get_user_account(self):
        """Test get_user_account method"""
        user_account = self.drift_user.get_user_account()
        if user_account and hasattr(user_account, 'perp_positions'):
            positions = []
            for pos in user_account.perp_positions:
                if hasattr(pos, 'base_asset_amount'):
                    pos_sol = float(pos.base_asset_amount) / BASE_PRECISION
                    positions.append(f"{pos_sol:.6f}")
            return f"Positions: {positions}"
        return "No perp positions found"
    
    async def _test_drift_user_methods(self):
        """Test drift_user methods"""
        try:
            # Try to get position from drift_user
            if hasattr(self.drift_user, 'get_perp_position'):
                position = self.drift_user.get_perp_position(0)
                return f"DriftUser position: {position}"
            else:
                return "DriftUser has no get_perp_position method"
        except Exception as e:
            return f"DriftUser method error: {e}"

async def main():
    """Main diagnostic function"""
    diagnostic = MMBotDiagnostic()
    
    if not await diagnostic.initialize():
        logger.error("Failed to initialize diagnostic tool")
        return
    
    # Run diagnostics
    await diagnostic.diagnose_position_issue()
    await diagnostic.test_position_update_methods()
    
    logger.info("\n✅ Diagnostic complete!")

if __name__ == "__main__":
    asyncio.run(main())
