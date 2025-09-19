#!/usr/bin/env python3
"""
Verification script to ensure JIT implementation introduces no breaking changes
Tests existing bot functionality with and without JIT enabled
"""

import sys
import os
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "libs"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BreakingChangeVerifier:
    """Verifies that JIT implementation doesn't break existing functionality"""
    
    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.failures: List[str] = []
    
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details
        }
        self.test_results.append(result)
        
        if success:
            logger.info(f"✅ {test_name}: PASSED {details}")
        else:
            logger.error(f"❌ {test_name}: FAILED {details}")
            self.failures.append(f"{test_name}: {details}")
    
    def test_jit_client_import(self) -> bool:
        """Test that JIT client can be imported without errors"""
        try:
            from libs.jit.client import (
                JITClient, JITPlaceResult, JITCancelReplaceResult,
                build_jit_client_from_config, load_jit_config_from_file
            )
            self.log_test("JIT Client Import", True)
            return True
        except ImportError as e:
            self.log_test("JIT Client Import", False, str(e))
            return False
    
    def test_jit_config_loading(self) -> bool:
        """Test JIT configuration loading"""
        try:
            from libs.jit.client import load_jit_config_from_file
            
            # Test with non-existent file (should return default)
            config = load_jit_config_from_file("nonexistent_file.yaml")
            expected = {"feature": {"jit": {"enabled": False}}}
            
            if config == expected:
                self.log_test("JIT Config Loading", True, "Defaults correctly")
                return True
            else:
                self.log_test("JIT Config Loading", False, f"Expected {expected}, got {config}")
                return False
                
        except Exception as e:
            self.log_test("JIT Config Loading", False, str(e))
            return False
    
    def test_jit_client_creation_disabled(self) -> bool:
        """Test JIT client creation when disabled"""
        try:
            from libs.jit.client import build_jit_client_from_config
            
            config = {"feature": {"jit": {"enabled": False}}}
            client = build_jit_client_from_config(config)
            
            if client is None:
                self.log_test("JIT Client Creation (Disabled)", True, "Returns None when disabled")
                return True
            else:
                self.log_test("JIT Client Creation (Disabled)", False, f"Expected None, got {type(client)}")
                return False
                
        except Exception as e:
            self.log_test("JIT Client Creation (Disabled)", False, str(e))
            return False
    
    def test_existing_bot_import(self) -> bool:
        """Test that existing bot classes can still be imported"""
        try:
            # Test importing CompleteSwiftMMBot
            sys.path.insert(0, str(Path(__file__).parent.parent))
            
            # Import the main bot file to check for syntax errors
            import run_swift_mm_complete
            
            # Check that the CompleteSwiftMMBot class exists
            if hasattr(run_swift_mm_complete, 'CompleteSwiftMMBot'):
                self.log_test("Existing Bot Import", True, "CompleteSwiftMMBot class available")
                return True
            else:
                self.log_test("Existing Bot Import", False, "CompleteSwiftMMBot class not found")
                return False
                
        except Exception as e:
            self.log_test("Existing Bot Import", False, str(e))
            return False
    
    def test_existing_config_compatibility(self) -> bool:
        """Test that existing configuration format still works"""
        try:
            # Test with a typical existing configuration
            existing_config = {
                "env": "devnet",
                "rpc_url": "https://api.devnet.solana.com",
                "wallet_file": ".valid_wallet.json",
                "order_size": 0.01,
                "max_orders_per_side": 1,
                "spread_bps": 8,
                "swift_ws_enabled": True
            }
            
            from libs.jit.client import build_jit_client_from_config
            
            # Should not crash and should return None (no JIT feature)
            client = build_jit_client_from_config(existing_config)
            
            if client is None:
                self.log_test("Existing Config Compatibility", True, "Old config format works")
                return True
            else:
                self.log_test("Existing Config Compatibility", False, f"Expected None, got {type(client)}")
                return False
                
        except Exception as e:
            self.log_test("Existing Config Compatibility", False, str(e))
            return False
    
    def test_feature_flag_isolation(self) -> bool:
        """Test that JIT feature flag doesn't affect other features"""
        try:
            config = {
                "feature": {
                    "obi": {"enabled": True},
                    "trend": {"enabled": False},
                    "jit": {"enabled": False}  # JIT disabled
                },
                "env": "devnet"
            }
            
            from libs.jit.client import build_jit_client_from_config
            
            # JIT should be None
            jit_client = build_jit_client_from_config(config)
            
            # Other features should be preserved
            obi_enabled = config["feature"]["obi"]["enabled"]
            trend_enabled = config["feature"]["trend"]["enabled"]
            
            if (jit_client is None and 
                obi_enabled is True and 
                trend_enabled is False):
                self.log_test("Feature Flag Isolation", True, "Other features preserved")
                return True
            else:
                self.log_test("Feature Flag Isolation", False, "Feature flags affected")
                return False
                
        except Exception as e:
            self.log_test("Feature Flag Isolation", False, str(e))
            return False
    
    async def test_jit_client_graceful_failure(self) -> bool:
        """Test that JIT client fails gracefully when service unavailable"""
        try:
            from libs.jit.client import JITClient
            
            # Create client pointing to invalid URL
            client = JITClient("http://invalid-host:9999", timeout=0.1)
            
            # Health check should fail gracefully without raising exception
            health = await client.health()
            
            if health is False:
                self.log_test("JIT Client Graceful Failure", True, "Fails gracefully")
                return True
            else:
                self.log_test("JIT Client Graceful Failure", False, "Did not fail as expected")
                return False
                
        except Exception as e:
            self.log_test("JIT Client Graceful Failure", False, str(e))
            return False
    
    def test_existing_imports_unchanged(self) -> bool:
        """Test that existing import statements still work"""
        try:
            # Test imports that existing bots rely on
            from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
            from libs.drift.drivers.swift import SwiftSidecarDriver
            
            # These should still work
            if (SwiftEnvelopeCreator and SwiftOrderParams and SwiftSidecarDriver):
                self.log_test("Existing Imports", True, "All existing imports work")
                return True
            else:
                self.log_test("Existing Imports", False, "Some imports failed")
                return False
                
        except Exception as e:
            self.log_test("Existing Imports", False, str(e))
            return False
    
    def test_config_file_structure(self) -> bool:
        """Test that new config file structure is valid"""
        try:
            config_file = Path(__file__).parent.parent / "configs" / "features" / "jit.yaml"
            
            if not config_file.exists():
                self.log_test("Config File Structure", False, "JIT config file not found")
                return False
            
            import yaml
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check required structure
            required_keys = ["feature", "jit", "fallback"]
            missing_keys = [key for key in required_keys if key not in config]
            
            if not missing_keys:
                self.log_test("Config File Structure", True, "All required keys present")
                return True
            else:
                self.log_test("Config File Structure", False, f"Missing keys: {missing_keys}")
                return False
                
        except Exception as e:
            self.log_test("Config File Structure", False, str(e))
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all verification tests"""
        logger.info("🔍 Starting breaking change verification...")
        
        tests = [
            ("JIT Client Import", self.test_jit_client_import),
            ("JIT Config Loading", self.test_jit_config_loading),
            ("JIT Client Creation (Disabled)", self.test_jit_client_creation_disabled),
            ("Existing Bot Import", self.test_existing_bot_import),
            ("Existing Config Compatibility", self.test_existing_config_compatibility),
            ("Feature Flag Isolation", self.test_feature_flag_isolation),
            ("Existing Imports Unchanged", self.test_existing_imports_unchanged),
            ("Config File Structure", self.test_config_file_structure),
        ]
        
        # Run sync tests
        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.log_test(test_name, False, f"Exception: {e}")
        
        # Run async tests
        async_tests = [
            ("JIT Client Graceful Failure", self.test_jit_client_graceful_failure),
        ]
        
        for test_name, test_func in async_tests:
            try:
                await test_func()
            except Exception as e:
                self.log_test(test_name, False, f"Exception: {e}")
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"\n📊 Verification Summary:")
        logger.info(f"Total tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success rate: {passed_tests/total_tests*100:.1f}%")
        
        if self.failures:
            logger.error(f"\n❌ Failures:")
            for failure in self.failures:
                logger.error(f"  - {failure}")
        
        if failed_tests == 0:
            logger.info("\n✅ All tests passed! No breaking changes detected.")
            return True
        else:
            logger.error(f"\n❌ {failed_tests} test(s) failed. Breaking changes detected!")
            return False
    
    def save_report(self, output_file: str = "breaking_change_verification_report.json"):
        """Save detailed test report"""
        report = {
            "summary": {
                "total_tests": len(self.test_results),
                "passed": sum(1 for r in self.test_results if r["success"]),
                "failed": sum(1 for r in self.test_results if not r["success"]),
                "success_rate": sum(1 for r in self.test_results if r["success"]) / len(self.test_results) * 100
            },
            "tests": self.test_results,
            "failures": self.failures,
            "timestamp": __import__('time').time()
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📄 Detailed report saved to {output_file}")


async def main():
    """Main verification function"""
    verifier = BreakingChangeVerifier()
    
    try:
        success = await verifier.run_all_tests()
        verifier.save_report()
        
        if success:
            logger.info("\n🎉 Breaking change verification completed successfully!")
            return 0
        else:
            logger.error("\n💥 Breaking change verification failed!")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Verification failed with exception: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)



