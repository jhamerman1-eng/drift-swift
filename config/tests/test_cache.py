"""
Tests for Configuration Cache

Tests thread safety, mtime guards, and reload capability.
"""

import pytest
import threading
import time
import tempfile
from pathlib import Path
import yaml
from unittest.mock import patch

from ..core import cache
from ..core.settings import CoreSettings


class TestCacheBasics:
    """Test basic cache functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Clear cache before each test
        cache.clear_cache()
    
    def test_get_core_first_time(self):
        """Test getting core configuration for the first time"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_config(config_dir)
            
            # First call should load from files
            core = cache.get_core(config_dir)
            
            assert isinstance(core, CoreSettings)
            assert core.network == "testnet"
            assert cache.get_generation() == 0
    
    def test_get_core_cached(self):
        """Test getting core configuration from cache"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_config(config_dir)
            
            # First call
            core1 = cache.get_core(config_dir)
            
            # Second call should return same object from cache
            core2 = cache.get_core(config_dir)
            
            assert core1 is core2  # Same object reference
            assert cache.get_generation() == 0
    
    def test_clear_cache(self):
        """Test clearing cache"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_config(config_dir)
            
            # Load config
            core1 = cache.get_core(config_dir)
            
            # Clear cache
            cache.clear_cache()
            
            # Load again - should be new object
            core2 = cache.get_core(config_dir)
            
            assert core1 is not core2  # Different objects
            assert cache.get_generation() == 0  # Generation reset
    
    def test_get_cache_info(self):
        """Test getting cache information"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_config(config_dir)
            
            # Before loading
            info = cache.get_cache_info()
            assert not info["loaded"]
            assert info["generation"] == 0
            
            # After loading
            core = cache.get_core(config_dir)
            info = cache.get_cache_info()
            
            assert info["loaded"]
            assert info["generation"] == 0
            assert info["contract_version"] == core.contract_version
            assert info["schema_checksum"] == core.get_schema_checksum()
            assert len(info["tracked_files"]) > 0
    
    def _create_test_config(self, config_dir: Path):
        """Helper to create test configuration files"""
        defaults_dir = config_dir / "data" / "defaults"
        defaults_dir.mkdir(parents=True)
        
        defaults_file = defaults_dir / "core.yaml"
        with open(defaults_file, 'w') as f:
            yaml.dump({
                "network": "testnet",
                "environment": "testing"
            }, f)


class TestCacheReloading:
    """Test cache reloading functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        cache.clear_cache()
    
    def test_reload_if_changed_no_changes(self):
        """Test reload when no files have changed"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_config(config_dir)
            
            # Initial load
            core1 = cache.get_core(config_dir)
            generation1 = cache.get_generation()
            
            # Try reload - no changes
            was_reloaded = cache.reload_if_changed(config_dir)
            
            assert not was_reloaded
            assert cache.get_generation() == generation1
            
            # Should still be same object
            core2 = cache.get_core(config_dir)
            assert core1 is core2
    
    def test_reload_if_changed_with_changes(self):
        """Test reload when files have changed"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_config(config_dir)
            
            # Initial load
            core1 = cache.get_core(config_dir)
            generation1 = cache.get_generation()
            
            # Wait a bit to ensure mtime difference
            time.sleep(0.1)
            
            # Modify config file
            defaults_file = config_dir / "data" / "defaults" / "core.yaml"
            with open(defaults_file, 'w') as f:
                yaml.dump({
                    "network": "devnet",  # Changed
                    "environment": "development"  # Changed
                }, f)
            
            # Try reload - should detect changes
            was_reloaded = cache.reload_if_changed(config_dir)
            
            assert was_reloaded
            assert cache.get_generation() == generation1 + 1
            
            # Should be new config object
            core2 = cache.get_core(config_dir)
            assert core1 is not core2
            assert core2.network == "devnet"
            assert core2.environment == "development"
    
    def test_force_reload(self):
        """Test force reload regardless of file changes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_config(config_dir)
            
            # Initial load
            core1 = cache.get_core(config_dir)
            generation1 = cache.get_generation()
            
            # Force reload without file changes
            was_reloaded = cache.force_reload(config_dir)
            
            assert was_reloaded
            assert cache.get_generation() == generation1 + 1
            
            # Should be new object (even though config is same)
            core2 = cache.get_core(config_dir)
            assert core1 is not core2
    
    def test_is_cache_stale(self):
        """Test cache staleness detection"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_config(config_dir)
            
            # Before loading - should be stale
            assert cache.is_cache_stale(config_dir)
            
            # After loading - should not be stale
            cache.get_core(config_dir)
            assert not cache.is_cache_stale(config_dir)
            
            # After file change - should be stale
            time.sleep(0.1)
            defaults_file = config_dir / "data" / "defaults" / "core.yaml"
            defaults_file.touch()  # Update mtime
            
            assert cache.is_cache_stale(config_dir)
    
    def test_auto_reload_if_stale(self):
        """Test automatic reload if cache is stale"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_config(config_dir)
            
            # Initial load
            core1 = cache.get_core(config_dir)
            
            # Modify file
            time.sleep(0.1)
            defaults_file = config_dir / "data" / "defaults" / "core.yaml"
            with open(defaults_file, 'w') as f:
                yaml.dump({
                    "network": "mainnet-beta",
                    "environment": "production"
                }, f)
            
            # Auto reload
            core2, was_reloaded = cache.auto_reload_if_stale(config_dir)
            
            assert was_reloaded
            assert core1 is not core2
            assert core2.network == "mainnet-beta"
            assert core2.environment == "production"
    
    def _create_test_config(self, config_dir: Path):
        """Helper to create test configuration files"""
        defaults_dir = config_dir / "data" / "defaults"
        defaults_dir.mkdir(parents=True)
        
        defaults_file = defaults_dir / "core.yaml"
        with open(defaults_file, 'w') as f:
            yaml.dump({
                "network": "testnet",
                "environment": "testing"
            }, f)


class TestCacheThreadSafety:
    """Test cache thread safety"""
    
    def setup_method(self):
        """Setup for each test method"""
        cache.clear_cache()
    
    def test_concurrent_get_core(self):
        """Test concurrent get_core calls"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_config(config_dir)
            
            results = []
            errors = []
            
            def load_config():
                try:
                    core = cache.get_core(config_dir)
                    results.append(core)
                except Exception as e:
                    errors.append(e)
            
            # Start multiple threads
            threads = []
            for _ in range(10):
                thread = threading.Thread(target=load_config)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Check results
            assert len(errors) == 0  # No errors
            assert len(results) == 10  # All threads got result
            
            # All should be same object (from cache)
            first_core = results[0]
            for core in results[1:]:
                assert core is first_core
    
    def test_concurrent_reload(self):
        """Test concurrent reload operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_config(config_dir)
            
            # Initial load
            cache.get_core(config_dir)
            
            # Modify file to trigger reload
            time.sleep(0.1)
            defaults_file = config_dir / "data" / "defaults" / "core.yaml"
            with open(defaults_file, 'w') as f:
                yaml.dump({
                    "network": "devnet",
                    "environment": "development"
                }, f)
            
            reload_results = []
            get_results = []
            errors = []
            
            def reload_config():
                try:
                    result = cache.reload_if_changed(config_dir)
                    reload_results.append(result)
                except Exception as e:
                    errors.append(e)
            
            def get_config():
                try:
                    core = cache.get_core(config_dir)
                    get_results.append(core)
                except Exception as e:
                    errors.append(e)
            
            # Start mixed threads
            threads = []
            for i in range(5):
                if i % 2 == 0:
                    thread = threading.Thread(target=reload_config)
                else:
                    thread = threading.Thread(target=get_config)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Check results
            assert len(errors) == 0  # No errors
            assert len(reload_results) >= 1  # At least one reload attempt
            assert len(get_results) >= 1  # At least one get attempt
            
            # At least one reload should have succeeded
            assert any(reload_results)
    
    def test_generation_counter_thread_safe(self):
        """Test generation counter is thread-safe"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_config(config_dir)
            
            # Initial load
            cache.get_core(config_dir)
            
            generations = []
            errors = []
            
            def force_reload_and_check():
                try:
                    cache.force_reload(config_dir)
                    gen = cache.get_generation()
                    generations.append(gen)
                except Exception as e:
                    errors.append(e)
            
            # Start multiple threads doing force reload
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=force_reload_and_check)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Check results
            assert len(errors) == 0  # No errors
            assert len(generations) == 5  # All threads got a generation
            
            # All generations should be positive and unique
            assert all(gen > 0 for gen in generations)
            assert len(set(generations)) == len(generations)  # All unique
    
    def _create_test_config(self, config_dir: Path):
        """Helper to create test configuration files"""
        defaults_dir = config_dir / "data" / "defaults"
        defaults_dir.mkdir(parents=True)
        
        defaults_file = defaults_dir / "core.yaml"
        with open(defaults_file, 'w') as f:
            yaml.dump({
                "network": "testnet",
                "environment": "testing"
            }, f)


class TestCacheErrorHandling:
    """Test cache error handling"""
    
    def setup_method(self):
        """Setup for each test method"""
        cache.clear_cache()
    
    def test_reload_with_invalid_config(self):
        """Test reload behavior with invalid configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_config(config_dir)
            
            # Initial load
            core1 = cache.get_core(config_dir)
            generation1 = cache.get_generation()
            
            # Corrupt config file
            time.sleep(0.1)
            defaults_file = config_dir / "data" / "defaults" / "core.yaml"
            with open(defaults_file, 'w') as f:
                f.write("invalid: yaml: content: [unclosed")
            
            # Try reload - should fail but keep old config
            was_reloaded = cache.reload_if_changed(config_dir)
            
            assert not was_reloaded
            assert cache.get_generation() == generation1  # Generation not incremented
            
            # Should still have old config
            core2 = cache.get_core(config_dir)
            assert core1 is core2
    
    def test_force_reload_with_invalid_config(self):
        """Test force reload with invalid configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_config(config_dir)
            
            # Initial load
            core1 = cache.get_core(config_dir)
            generation1 = cache.get_generation()
            
            # Corrupt config file
            defaults_file = config_dir / "data" / "defaults" / "core.yaml"
            with open(defaults_file, 'w') as f:
                f.write("invalid: yaml: content: [unclosed")
            
            # Force reload - should fail
            was_reloaded = cache.force_reload(config_dir)
            
            assert not was_reloaded
            assert cache.get_generation() == generation1  # Generation not incremented
            
            # Should still have old config
            core2 = cache.get_core(config_dir)
            assert core1 is core2
    
    def _create_test_config(self, config_dir: Path):
        """Helper to create test configuration files"""
        defaults_dir = config_dir / "data" / "defaults"
        defaults_dir.mkdir(parents=True)
        
        defaults_file = defaults_dir / "core.yaml"
        with open(defaults_file, 'w') as f:
            yaml.dump({
                "network": "testnet",
                "environment": "testing"
            }, f)
