"""
Unit tests for JIT Client - US-JIT-005 testing requirement
Tests all JIT client functionality including error handling and feature flags
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

# Import the JIT client and related classes
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from libs.jit.client import (
    JITClient, JITPlaceResult, JITCancelReplaceResult, JITHealthStatus,
    JITClientError, JITTimeoutError, JITServiceUnavailableError, JITValidationError,
    build_jit_client_from_config, load_jit_config_from_file
)

class TestJITClient:
    """Test JIT client functionality"""
    
    @pytest.fixture
    def jit_client(self):
        """Create JIT client for testing"""
        return JITClient(
            base_url="http://localhost:8787",
            timeout=1.0,
            retries=2
        )
    
    @pytest.fixture
    def mock_http_client(self):
        """Mock HTTP client for testing"""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_response.headers = {"content-type": "application/json"}
        mock_client.get.return_value = mock_response
        mock_client.post.return_value = mock_response
        return mock_client, mock_response
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, jit_client, mock_http_client):
        """Test successful health check"""
        mock_client, mock_response = mock_http_client
        
        with patch.object(jit_client, '_get_client', return_value=mock_client):
            result = await jit_client.health()
        
        assert result is True
        mock_client.get.assert_called_once_with("http://localhost:8787/health")
        assert jit_client._health_status is not None
        assert jit_client._health_status.ok is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, jit_client, mock_http_client):
        """Test failed health check"""
        mock_client, mock_response = mock_http_client
        mock_response.status_code = 503
        
        with patch.object(jit_client, '_get_client', return_value=mock_client):
            result = await jit_client.health()
        
        assert result is False
        assert jit_client._consecutive_failures == 1
    
    @pytest.mark.asyncio
    async def test_health_check_caching(self, jit_client, mock_http_client):
        """Test health check caching mechanism"""
        mock_client, mock_response = mock_http_client
        
        # Set up healthy response
        mock_response.json.return_value = {"ok": True, "subscribers": {}}
        
        with patch.object(jit_client, '_get_client', return_value=mock_client):
            # First call
            result1 = await jit_client.health()
            # Second call (should use cache)
            result2 = await jit_client.health()
        
        assert result1 is True
        assert result2 is True
        # Should only call HTTP client once due to caching
        assert mock_client.get.call_count == 1
    
    @pytest.mark.asyncio 
    async def test_place_and_make_success(self, jit_client, mock_http_client):
        """Test successful place_and_make operation"""
        mock_client, mock_response = mock_http_client
        mock_response.json.return_value = {
            "txSig": "test_signature_123",
            "makerOrderId": "order_456",
            "duration": 150
        }
        
        order_message_raw = {
            "taker_authority": "11111111111111111111111111111111",
            "order_message": "deadbeef",
            "order_signature": "dGVzdA==",
            "uuid": "test-uuid"
        }
        
        signed_message = {
            "signedMsgOrderParams": {
                "marketIndex": 0,
                "direction": {"long": True},
                "baseAssetAmount": "1000000000"
            }
        }
        
        maker = {
            "price": 100.5,
            "size": 0.1,
            "postOnly": True
        }
        
        with patch.object(jit_client, '_get_client', return_value=mock_client):
            result = await jit_client.place_and_make(
                order_message_raw, signed_message, maker
            )
        
        assert isinstance(result, JITPlaceResult)
        assert result.success is True
        assert result.tx_sig == "test_signature_123"
        assert result.maker_order_id == "order_456"
        assert result.error is None
        
        # Verify the request was made correctly
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/jit/place_and_make" in call_args[0][0]
        
        payload = call_args[1]["json"]
        assert payload["orderMessageRaw"] == order_message_raw
        assert payload["signedMessage"] == signed_message
        assert payload["maker"] == maker
    
    @pytest.mark.asyncio
    async def test_place_and_make_slot_skew_error(self, jit_client, mock_http_client):
        """Test place_and_make with slot skew error"""
        mock_client, mock_response = mock_http_client
        mock_response.status_code = 409
        mock_response.json.return_value = {
            "error": "stale_signed_slot",
            "detail": {"currentSlot": 100, "signedSlot": 50}
        }
        
        order_message_raw = {
            "taker_authority": "11111111111111111111111111111111",
            "order_message": "deadbeef", 
            "order_signature": "dGVzdA==",
            "uuid": "test-uuid"
        }
        
        signed_message = {"signedMsgOrderParams": {"marketIndex": 0}}
        maker = {"price": 100.0, "size": 0.1}
        
        with patch.object(jit_client, '_get_client', return_value=mock_client):
            with pytest.raises(JITValidationError, match="Slot skew error"):
                await jit_client.place_and_make(order_message_raw, signed_message, maker)
    
    @pytest.mark.asyncio
    async def test_place_and_make_validation_error(self, jit_client):
        """Test place_and_make with invalid input parameters"""
        # Missing required fields
        with pytest.raises(JITValidationError, match="Missing required field"):
            await jit_client.place_and_make({}, {}, {})
        
        # Invalid maker parameters
        order_message_raw = {
            "taker_authority": "11111111111111111111111111111111",
            "order_message": "deadbeef",
            "order_signature": "dGVzdA==",
            "uuid": "test-uuid"
        }
        
        signed_message = {"signedMsgOrderParams": {"marketIndex": 0}}
        
        with pytest.raises(JITValidationError, match="Missing required field"):
            await jit_client.place_and_make(
                order_message_raw, signed_message, {"price": "invalid"}
            )
    
    @pytest.mark.asyncio
    async def test_place_and_make_retry_logic(self, jit_client, mock_http_client):
        """Test retry logic for transient failures"""
        mock_client, mock_response = mock_http_client
        
        # First two attempts fail with 500, third succeeds
        responses = [
            Mock(status_code=500, json=lambda: {"error": "server_error"}),
            Mock(status_code=500, json=lambda: {"error": "server_error"}),
            Mock(status_code=200, json=lambda: {"txSig": "success_sig", "duration": 100})
        ]
        responses[0].headers = {"content-type": "application/json"}
        responses[1].headers = {"content-type": "application/json"} 
        responses[2].headers = {"content-type": "application/json"}
        
        mock_client.post.side_effect = responses
        
        order_message_raw = {
            "taker_authority": "11111111111111111111111111111111",
            "order_message": "deadbeef",
            "order_signature": "dGVzdA==", 
            "uuid": "test-uuid"
        }
        
        signed_message = {"signedMsgOrderParams": {"marketIndex": 0}}
        maker = {"price": 100.0, "size": 0.1}
        
        with patch.object(jit_client, '_get_client', return_value=mock_client):
            result = await jit_client.place_and_make(
                order_message_raw, signed_message, maker
            )
        
        assert result.success is True
        assert result.tx_sig == "success_sig"
        assert mock_client.post.call_count == 3  # Two retries + success
    
    @pytest.mark.asyncio
    async def test_cancel_replace_success(self, jit_client, mock_http_client):
        """Test successful cancel_replace operation"""
        mock_client, mock_response = mock_http_client
        mock_response.json.return_value = {
            "newOrderId": "new_order_123",
            "tombstoneSet": True
        }
        
        with patch.object(jit_client, '_get_client', return_value=mock_client):
            result = await jit_client.cancel_replace(
                "old_order_456",
                {"price": 101.0, "size": 0.2}
            )
        
        assert isinstance(result, JITCancelReplaceResult)
        assert result.success is True
        assert result.new_order_id == "new_order_123"
        assert result.tombstone_set is True
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_cancel_replace_error(self, jit_client, mock_http_client):
        """Test cancel_replace with error response"""
        mock_client, mock_response = mock_http_client
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "invalid_order_id"}
        
        with patch.object(jit_client, '_get_client', return_value=mock_client):
            result = await jit_client.cancel_replace("invalid_id", {})
        
        assert result.success is False
        assert result.error is not None
        assert "HTTP 400" in result.error
    
    def test_get_health_details(self, jit_client):
        """Test get_health_details method"""
        # No health status yet
        details = jit_client.get_health_details()
        assert details["status"] == "unknown"
        assert details["last_check"] is None
        
        # Set health status
        jit_client._health_status = JITHealthStatus(
            ok=True,
            subscribers={"swift": True, "auction": True},
            last_check=time.time(),
            consecutive_failures=0
        )
        
        details = jit_client.get_health_details()
        assert details["status"] == "healthy"
        assert "subscribers" in details
        assert details["consecutive_failures"] == 0
    
    @pytest.mark.asyncio
    async def test_close_client(self, jit_client):
        """Test proper client cleanup"""
        # Mock the internal client
        mock_client = AsyncMock()
        jit_client._client = mock_client
        
        await jit_client.close()
        
        mock_client.aclose.assert_called_once()
        assert jit_client._client is None


class TestJITClientBuilding:
    """Test JIT client building and configuration"""
    
    def test_build_jit_client_from_config_enabled(self):
        """Test building JIT client when enabled"""
        config = {
            "feature": {"jit": {"enabled": True}},
            "jit": {
                "base_url": "http://test:9999",
                "timeout_seconds": 2.0,
                "retries": 5
            }
        }
        
        with patch.object(JITClient, 'health', return_value=True):
            client = build_jit_client_from_config(config)
        
        assert client is not None
        assert isinstance(client, JITClient)
        assert client.base_url == "http://test:9999"
        assert client.timeout == 2.0
        assert client.retries == 5
    
    def test_build_jit_client_from_config_disabled(self):
        """Test building JIT client when disabled"""
        config = {
            "feature": {"jit": {"enabled": False}}
        }
        
        client = build_jit_client_from_config(config)
        assert client is None
    
    def test_build_jit_client_from_config_unhealthy(self):
        """Test building JIT client when service is unhealthy"""
        config = {
            "feature": {"jit": {"enabled": True}},
            "jit": {"base_url": "http://unhealthy:8787"}
        }
        
        with patch.object(JITClient, 'health', return_value=False):
            client = build_jit_client_from_config(config)
        
        assert client is None
    
    def test_load_jit_config_from_file_exists(self):
        """Test loading JIT config from existing file"""
        mock_config = {
            "feature": {"jit": {"enabled": True}},
            "jit": {"base_url": "http://loaded:8787"}
        }
        
        with patch("builtins.open", mock_open_yaml(mock_config)):
            with patch("pathlib.Path.exists", return_value=True):
                config = load_jit_config_from_file("test.yaml")
        
        assert config == mock_config
    
    def test_load_jit_config_from_file_missing(self):
        """Test loading JIT config from missing file"""
        with patch("pathlib.Path.exists", return_value=False):
            config = load_jit_config_from_file("missing.yaml")
        
        assert config == {"feature": {"jit": {"enabled": False}}}
    
    def test_load_jit_config_from_file_error(self):
        """Test loading JIT config with file error"""
        with patch("builtins.open", side_effect=IOError("File error")):
            with patch("pathlib.Path.exists", return_value=True):
                config = load_jit_config_from_file("error.yaml")
        
        assert config == {"feature": {"jit": {"enabled": False}}}


class TestJITExceptions:
    """Test JIT exception handling"""
    
    def test_jit_client_error_hierarchy(self):
        """Test exception hierarchy"""
        base_error = JITClientError("base error")
        timeout_error = JITTimeoutError("timeout") 
        service_error = JITServiceUnavailableError("service down")
        validation_error = JITValidationError("invalid input")
        
        assert isinstance(timeout_error, JITClientError)
        assert isinstance(service_error, JITClientError)
        assert isinstance(validation_error, JITClientError)
        
        assert str(base_error) == "base error"
        assert str(timeout_error) == "timeout"


class TestJITDataClasses:
    """Test JIT data classes"""
    
    def test_jit_place_result_success(self):
        """Test JITPlaceResult for successful operation"""
        result = JITPlaceResult(
            tx_sig="signature123",
            maker_order_id="order456", 
            duration=150.5,
            success=True
        )
        
        assert result.tx_sig == "signature123"
        assert result.maker_order_id == "order456"
        assert result.duration == 150.5
        assert result.success is True
        assert result.error is None
    
    def test_jit_place_result_failure(self):
        """Test JITPlaceResult for failed operation"""
        result = JITPlaceResult(
            tx_sig="",
            maker_order_id=None,
            duration=50.0,
            success=False,
            error="Request timeout"
        )
        
        assert result.tx_sig == ""
        assert result.maker_order_id is None
        assert result.success is False
        assert result.error == "Request timeout"
    
    def test_jit_cancel_replace_result(self):
        """Test JITCancelReplaceResult"""
        result = JITCancelReplaceResult(
            new_order_id="new123",
            tombstone_set=True,
            success=True
        )
        
        assert result.new_order_id == "new123"
        assert result.tombstone_set is True
        assert result.success is True
        assert result.error is None
    
    def test_jit_health_status(self):
        """Test JITHealthStatus"""
        status = JITHealthStatus(
            ok=True,
            subscribers={"swift": True, "auction": False},
            last_check=1234567890.0,
            consecutive_failures=2
        )
        
        assert status.ok is True
        assert status.subscribers["swift"] is True
        assert status.subscribers["auction"] is False
        assert status.last_check == 1234567890.0
        assert status.consecutive_failures == 2


# Helper function for mocking YAML file reading
def mock_open_yaml(content):
    """Mock file opening for YAML content"""
    import yaml
    yaml_content = yaml.dump(content)
    
    from unittest.mock import mock_open
    return mock_open(read_data=yaml_content)


# Performance tests
class TestJITClientPerformance:
    """Test JIT client performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, jit_client):
        """Test handling multiple concurrent requests"""
        mock_client = AsyncMock()
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"txSig": "test_sig", "duration": 100}
        mock_client.post.return_value = mock_response
        
        order_message_raw = {
            "taker_authority": "11111111111111111111111111111111",
            "order_message": "deadbeef",
            "order_signature": "dGVzdA==",
            "uuid": "test-uuid"
        }
        
        signed_message = {"signedMsgOrderParams": {"marketIndex": 0}}
        maker = {"price": 100.0, "size": 0.1}
        
        with patch.object(jit_client, '_get_client', return_value=mock_client):
            # Run 10 concurrent requests
            tasks = [
                jit_client.place_and_make(order_message_raw, signed_message, maker)
                for _ in range(10)
            ]
            
            results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert all(result.success for result in results)
        assert mock_client.post.call_count == 10
    
    @pytest.mark.asyncio
    async def test_request_timing(self, jit_client, mock_http_client):
        """Test request timing measurement"""
        mock_client, mock_response = mock_http_client
        mock_response.json.return_value = {"txSig": "test_sig"}
        
        # Add a small delay to simulate network latency
        async def delayed_post(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms delay
            return mock_response
        
        mock_client.post = delayed_post
        
        order_message_raw = {
            "taker_authority": "11111111111111111111111111111111",
            "order_message": "deadbeef",
            "order_signature": "dGVzdA==",
            "uuid": "test-uuid"
        }
        
        signed_message = {"signedMsgOrderParams": {"marketIndex": 0}}
        maker = {"price": 100.0, "size": 0.1}
        
        with patch.object(jit_client, '_get_client', return_value=mock_client):
            start_time = time.time()
            result = await jit_client.place_and_make(
                order_message_raw, signed_message, maker
            )
            end_time = time.time()
        
        assert result.success is True
        assert result.duration > 0
        # The duration should be measured internally and be close to our external measurement
        external_duration = (end_time - start_time) * 1000  # Convert to ms
        assert abs(result.duration - external_duration) < 50  # Within 50ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



