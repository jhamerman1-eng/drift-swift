"""
Integration tests for JIT functionality
Tests the complete JIT integration with existing bot architecture
Ensures no breaking changes to existing functionality
"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Import test utilities
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from libs.jit.client import JITClient, build_jit_client_from_config, load_jit_config_from_file

class TestJITIntegration:
    """Test JIT integration with existing system"""
    
    @pytest.fixture
    def mock_config_with_jit_enabled(self):
        """Mock configuration with JIT enabled"""
        return {
            "feature": {
                "jit": {
                    "enabled": True
                }
            },
            "jit": {
                "base_url": "http://localhost:8787",
                "timeout_seconds": 1.5,
                "retries": 3,
                "slot_skew_max": 30
            },
            "env": "devnet",
            "rpc_url": "https://api.devnet.solana.com",
            "market_index": 0,
            "order_size": 0.01
        }
    
    @pytest.fixture
    def mock_config_with_jit_disabled(self):
        """Mock configuration with JIT disabled"""
        return {
            "feature": {
                "jit": {
                    "enabled": False
                }
            },
            "env": "devnet",
            "rpc_url": "https://api.devnet.solana.com",
            "market_index": 0,
            "order_size": 0.01
        }
    
    def test_jit_client_creation_when_enabled(self, mock_config_with_jit_enabled):
        """Test JIT client is created when feature is enabled"""
        with patch.object(JITClient, 'health', return_value=True):
            client = build_jit_client_from_config(mock_config_with_jit_enabled)
        
        assert client is not None
        assert isinstance(client, JITClient)
        assert client.base_url == "http://localhost:8787"
    
    def test_jit_client_not_created_when_disabled(self, mock_config_with_jit_disabled):
        """Test JIT client is not created when feature is disabled"""
        client = build_jit_client_from_config(mock_config_with_jit_disabled)
        assert client is None
    
    def test_config_loading_from_file(self):
        """Test configuration loading from YAML file"""
        config_content = """
feature:
  jit:
    enabled: true
    base_url: "http://test:9999"
    timeout_seconds: 2.0

jit:
  slot_skew_max: 50
  retries: 5
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            config = load_jit_config_from_file(temp_path)
            
            assert config["feature"]["jit"]["enabled"] is True
            assert config["feature"]["jit"]["base_url"] == "http://test:9999"
            assert config["feature"]["jit"]["timeout_seconds"] == 2.0
            assert config["jit"]["slot_skew_max"] == 50
            assert config["jit"]["retries"] == 5
        
        finally:
            os.unlink(temp_path)
    
    def test_config_fallback_on_missing_file(self):
        """Test configuration fallback when file is missing"""
        config = load_jit_config_from_file("nonexistent_file.yaml")
        
        assert config == {"feature": {"jit": {"enabled": False}}}
    
    @pytest.mark.asyncio
    async def test_jit_client_health_check_integration(self):
        """Test JIT client health check integration"""
        client = JITClient("http://test:8787", timeout=1.0)
        
        # Mock successful health response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "subscribers": {
                "swift": True,
                "auction": True,
                "drift": True,
                "slot": True
            }
        }
        
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response
        
        with patch.object(client, '_get_client', return_value=mock_http_client):
            health = await client.health()
            details = client.get_health_details()
        
        assert health is True
        assert details["status"] == "healthy"
        assert "subscribers" in details
        assert details["consecutive_failures"] == 0


class TestExistingSystemCompatibility:
    """Ensure JIT integration doesn't break existing functionality"""
    
    def test_existing_config_structure_preserved(self):
        """Test that existing configuration structure is preserved"""
        # This would be a typical existing configuration
        existing_config = {
            "env": "devnet",
            "rpc_url": "https://api.devnet.solana.com",
            "wallet_file": ".valid_wallet.json",
            "order_size": 0.01,
            "max_orders_per_side": 1,
            "spread_bps": 8,
            "swift_ws_enabled": True
        }
        
        # JIT should not interfere with existing config when disabled
        client = build_jit_client_from_config(existing_config)
        assert client is None  # Should be None when no JIT feature flag
        
        # Original config should be unchanged
        assert existing_config["env"] == "devnet"
        assert existing_config["order_size"] == 0.01
    
    def test_feature_flag_isolation(self):
        """Test that JIT feature flag doesn't affect other features"""
        config_with_multiple_features = {
            "feature": {
                "obi": {"enabled": True},
                "trend": {"enabled": False},
                "hedge": {"enabled": True},
                "jit": {"enabled": True}
            },
            "jit": {"base_url": "http://localhost:8787"}
        }
        
        with patch.object(JITClient, 'health', return_value=True):
            jit_client = build_jit_client_from_config(config_with_multiple_features)
        
        # JIT should be enabled
        assert jit_client is not None
        
        # Other feature flags should be preserved
        assert config_with_multiple_features["feature"]["obi"]["enabled"] is True
        assert config_with_multiple_features["feature"]["trend"]["enabled"] is False
        assert config_with_multiple_features["feature"]["hedge"]["enabled"] is True
    
    def test_configuration_backward_compatibility(self):
        """Test that old configuration format still works"""
        # Old style config without feature flags
        old_config = {
            "env": "devnet",
            "rpc_url": "https://api.devnet.solana.com",
            "order_size": 0.01
        }
        
        # Should not crash and should return None for JIT client
        client = build_jit_client_from_config(old_config)
        assert client is None
    
    def test_partial_jit_config(self):
        """Test handling of partial JIT configuration"""
        partial_config = {
            "feature": {"jit": {"enabled": True}},
            # Missing jit section - should use defaults
        }
        
        with patch.object(JITClient, 'health', return_value=True):
            client = build_jit_client_from_config(partial_config)
        
        assert client is not None
        assert client.base_url == "http://localhost:8787"  # Default value
        assert client.timeout == 1.5  # Default value


class TestCompleteSwiftMMBotIntegration:
    """Test JIT integration with CompleteSwiftMMBot"""
    
    @pytest.fixture
    def mock_bot_config(self):
        """Mock configuration for CompleteSwiftMMBot"""
        return {
            "env": "devnet",
            "rpc_url": "https://api.devnet.solana.com",
            "wallet_file": ".valid_wallet.json",
            "order_size": 0.01,
            "feature": {
                "jit": {"enabled": True}
            },
            "jit": {
                "base_url": "http://localhost:8787",
                "timeout_seconds": 1.5
            }
        }
    
    def test_bot_initialization_with_jit_enabled(self, mock_bot_config):
        """Test that bot initializes correctly with JIT enabled"""
        # This would test the actual bot initialization but we need to mock
        # many dependencies. For now, test the configuration loading part.
        
        with patch.object(JITClient, 'health', return_value=True):
            jit_client = build_jit_client_from_config(mock_bot_config)
        
        assert jit_client is not None
        
        # Verify the client has expected configuration
        assert jit_client.base_url == "http://localhost:8787"
        assert jit_client.timeout == 1.5
    
    def test_bot_initialization_with_jit_disabled(self, mock_bot_config):
        """Test that bot initializes correctly with JIT disabled"""
        mock_bot_config["feature"]["jit"]["enabled"] = False
        
        jit_client = build_jit_client_from_config(mock_bot_config)
        assert jit_client is None
        
        # Bot should still function normally without JIT
        # (This would need actual bot testing to verify completely)
    
    def test_fallback_behavior_when_jit_unhealthy(self, mock_bot_config):
        """Test fallback behavior when JIT service is unhealthy"""
        with patch.object(JITClient, 'health', return_value=False):
            jit_client = build_jit_client_from_config(mock_bot_config)
        
        # Should return None when JIT service is unhealthy
        assert jit_client is None
        
        # Bot should continue with Swift/DriftPy fallback


class TestJITServiceHealthIntegration:
    """Test integration with JIT service health monitoring"""
    
    @pytest.mark.asyncio
    async def test_service_health_monitoring(self):
        """Test comprehensive service health monitoring"""
        client = JITClient("http://localhost:8787")
        
        # Mock comprehensive health response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "timestamp": 1234567890,
            "uptime": 3600,
            "subscribers": {
                "swift": True,
                "auction": True,
                "drift": True,
                "slot": True
            },
            "lastActivity": {
                "swift": 1234567880,
                "auction": 1234567885,
                "slot": 1234567890
            }
        }
        
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response
        
        with patch.object(client, '_get_client', return_value=mock_http_client):
            health = await client.health()
            details = client.get_health_details()
        
        assert health is True
        assert details["status"] == "healthy"
        assert len(details["subscribers"]) == 4
        assert all(details["subscribers"].values())
    
    @pytest.mark.asyncio
    async def test_service_degraded_health(self):
        """Test handling of degraded service health"""
        client = JITClient("http://localhost:8787")
        
        # Mock degraded health response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": False,
            "subscribers": {
                "swift": True,
                "auction": False,  # Auction subscriber is down
                "drift": True,
                "slot": True
            }
        }
        
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response
        
        with patch.object(client, '_get_client', return_value=mock_http_client):
            health = await client.health()
            details = client.get_health_details()
        
        assert health is False
        assert details["status"] == "unhealthy"
        assert details["subscribers"]["auction"] is False


class TestMetricsIntegration:
    """Test integration with existing metrics system"""
    
    def test_metrics_compatibility(self):
        """Test that JIT metrics don't interfere with existing metrics"""
        # This would test integration with existing metrics collection
        # For now, verify that JIT client can be created without affecting
        # existing systems
        
        config = {
            "feature": {"jit": {"enabled": True}},
            "jit": {"base_url": "http://localhost:8787"}
        }
        
        with patch.object(JITClient, 'health', return_value=True):
            client = build_jit_client_from_config(config)
        
        assert client is not None
        
        # Verify JIT client doesn't interfere with creation
        assert hasattr(client, 'get_health_details')


class TestErrorHandlingIntegration:
    """Test error handling integration"""
    
    @pytest.mark.asyncio
    async def test_jit_client_error_isolation(self):
        """Test that JIT client errors don't crash the main system"""
        client = JITClient("http://invalid:8787", timeout=0.1)
        
        # Health check should fail gracefully
        health = await client.health()
        assert health is False
        
        # Should track consecutive failures
        assert client._consecutive_failures > 0
        
        # Should not raise unhandled exceptions
        details = client.get_health_details()
        assert details["status"] == "unknown"
    
    @pytest.mark.asyncio 
    async def test_jit_placement_error_handling(self):
        """Test JIT placement error handling"""
        client = JITClient("http://localhost:8787")
        
        # Mock failed HTTP response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "internal_server_error"}
        mock_response.headers = {"content-type": "application/json"}
        
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        
        order_message_raw = {
            "taker_authority": "11111111111111111111111111111111",
            "order_message": "deadbeef",
            "order_signature": "dGVzdA==",
            "uuid": "test-uuid"
        }
        
        signed_message = {"signedMsgOrderParams": {"marketIndex": 0}}
        maker = {"price": 100.0, "size": 0.1}
        
        with patch.object(client, '_get_client', return_value=mock_http_client):
            result = await client.place_and_make(
                order_message_raw, signed_message, maker
            )
        
        # Should return failure result instead of raising exception
        assert result.success is False
        assert result.error is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



