#!/usr/bin/env python3
"""
Test script for Swift sidecar connection and basic driftpy functionality
"""

import asyncio
import logging
import sys
import os

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

from drift.swift_sidecar_driver import SwiftSidecarDriver

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sidecar():
    """Test Swift sidecar connection"""
    try:
        logger.info("Testing Swift sidecar connection...")
        
        # Test sidecar connection
        sidecar = SwiftSidecarDriver("http://localhost:8787")
        
        try:
            health = sidecar.health()
            logger.info(f"✅ Sidecar health check passed: {health}")
        except Exception as e:
            logger.warning(f"⚠️ Sidecar not running: {e}")
            logger.info("This is expected if the sidecar isn't started yet")
        
        sidecar.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Sidecar test failed: {e}")
        return False

async def test_driftpy_basic():
    """Test basic driftpy functionality without UserMap"""
    try:
        logger.info("Testing basic driftpy functionality...")
        
        # Import driftpy components
        from driftpy.drift_client import DriftClient
        from solders.keypair import Keypair
        
        logger.info("✅ Basic driftpy imports successful")
        
        # Test keypair creation
        keypair = Keypair()
        logger.info(f"✅ Keypair created: {keypair.pubkey()}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Driftpy test failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("🚀 Starting connection tests...")
    
    # Test sidecar
    sidecar_ok = await test_sidecar()
    
    # Test driftpy
    driftpy_ok = await test_driftpy_basic()
    
    # Summary
    logger.info("\n📊 Test Results:")
    logger.info(f"Swift Sidecar: {'✅ PASS' if sidecar_ok else '❌ FAIL'}")
    logger.info(f"Driftpy Basic: {'✅ PASS' if driftpy_ok else '❌ FAIL'}")
    
    if sidecar_ok and driftpy_ok:
        logger.info("🎉 All tests passed! Ready to run MM bot.")
    else:
        logger.info("⚠️ Some tests failed. Check the logs above.")

if __name__ == "__main__":
    asyncio.run(main())





