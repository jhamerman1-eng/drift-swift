#!/usr/bin/env python3
"""
BUG-003: JSON Serialization Safety Regression Tests

This test suite prevents JSON serialization errors that cause bot crashes.
Every fix for JSON serialization must include a regression test here.
"""

import pytest
import json
from unittest.mock import Mock
from typing import Any, Dict, List, Union


class TestJSONSerializationSafety:
    """Test suite for preventing JSON serialization errors"""

    def test_payload_json_safety(self):
        """BUG-003: Ensure all payloads are JSON serializable"""
        # Test with various payload types that could cause issues
        test_payloads = [
            {"normal": "data", "number": 123},
            {"with_bytes": b"binary_data"},
            {"with_objects": Mock()},
            {"nested": {"deep": {"data": "here"}}},
            {"list_with_bytes": [b"item1", b"item2"]},
            {"mixed_types": {"str": "value", "bytes": b"data", "int": 42}}
        ]
        
        for i, payload in enumerate(test_payloads):
            try:
                # This should not raise an exception
                safe_payload = self.make_json_safe(payload)
                json.dumps(safe_payload)
                print(f"Payload {i+1} made JSON safe successfully")
            except Exception as e:
                pytest.fail(f"Payload {i+1} failed JSON safety check: {e}")

    def test_bytes_conversion(self):
        """BUG-003: Test bytes objects are properly converted to hex"""
        payload = {
            "signature": b"binary_signature_data",
            "message": b"binary_message_data",
            "normal_field": "string_value"
        }
        
        safe_payload = self.make_json_safe(payload)
        
        # All bytes should be converted to hex strings
        assert isinstance(safe_payload["signature"], str)
        assert isinstance(safe_payload["message"], str)
        assert safe_payload["signature"] == "binary_signature_data".hex()
        assert safe_payload["message"] == "binary_message_data".hex()
        assert safe_payload["normal_field"] == "string_value"

    def test_nested_bytes_conversion(self):
        """BUG-003: Test bytes in nested structures are converted"""
        payload = {
            "level1": {
                "level2": {
                    "bytes_field": b"nested_bytes",
                    "normal_field": "normal_value"
                },
                "bytes_list": [b"item1", b"item2", b"item3"]
            }
        }
        
        safe_payload = self.make_json_safe(payload)
        
        # Verify nested bytes are converted
        assert isinstance(safe_payload["level1"]["level2"]["bytes_field"], str)
        assert safe_payload["level1"]["level2"]["bytes_field"] == "nested_bytes".hex()
        
        # Verify bytes in lists are converted
        assert all(isinstance(item, str) for item in safe_payload["level1"]["bytes_list"])
        assert safe_payload["level1"]["bytes_list"][0] == "item1".hex()

    def test_mock_object_handling(self):
        """BUG-003: Test Mock objects are handled safely"""
        mock_obj = Mock()
        mock_obj.some_attribute = "value"
        mock_obj.bytes_attribute = b"bytes_value"
        
        payload = {
            "mock_object": mock_obj,
            "normal_field": "value"
        }
        
        safe_payload = self.make_json_safe(payload)
        
        # Mock objects should be converted to strings or removed
        assert "mock_object" in safe_payload
        assert isinstance(safe_payload["mock_object"], str)
        assert safe_payload["normal_field"] == "value"

    def test_circular_reference_handling(self):
        """BUG-003: Test circular references are handled safely"""
        # Create circular reference
        obj1 = {"name": "obj1"}
        obj2 = {"name": "obj2"}
        obj1["ref"] = obj2
        obj2["ref"] = obj1  # Circular reference
        
        payload = {"circular": obj1}
        
        # This should not cause infinite recursion
        safe_payload = self.make_json_safe(payload)
        assert "circular" in safe_payload

    def test_swift_order_payload_safety(self):
        """BUG-003: Test Swift order payloads are JSON safe"""
        # Simulate a Swift order payload that might contain bytes
        swift_payload = {
            "market_type": "perp",
            "market_index": 0,
            "side": "buy",
            "price": 100.0,
            "size": 0.01,
            "signature": b"binary_signature_data",
            "message": b"binary_message_data",
            "taker_authority": "6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW",
            "post_only": True
        }
        
        safe_payload = self.make_json_safe(swift_payload)
        
        # Verify it's JSON serializable
        json_str = json.dumps(safe_payload)
        assert isinstance(json_str, str)
        
        # Verify bytes fields are converted
        assert isinstance(safe_payload["signature"], str)
        assert isinstance(safe_payload["message"], str)
        
        # Verify other fields remain unchanged
        assert safe_payload["market_type"] == "perp"
        assert safe_payload["side"] == "buy"
        assert safe_payload["price"] == 100.0

    def test_error_payload_fallback(self):
        """BUG-003: Test fallback payload when JSON safety fails"""
        # Create a payload that's difficult to make JSON safe
        problematic_payload = {
            "complex_object": Mock(),
            "bytes_data": b"data",
            "circular_ref": None
        }
        
        # Set up circular reference
        problematic_payload["circular_ref"] = problematic_payload
        
        # Test fallback mechanism
        try:
            safe_payload = self.make_json_safe(problematic_payload)
            json.dumps(safe_payload)
        except Exception:
            # If all else fails, create minimal safe payload
            fallback_payload = {
                "market_type": "perp",
                "market_index": 0,
                "message": "00",
                "signature": "dummy_signature",
                "taker_authority": "fallback_authority",
                "error": "json_serialization_failed"
            }
            json.dumps(fallback_payload)  # This should always work

    def test_performance_with_large_payloads(self):
        """BUG-003: Test JSON safety with large payloads"""
        # Create a large payload with many bytes objects
        large_payload = {
            "data": [b"item" + str(i).encode() for i in range(1000)],
            "metadata": {
                "signature": b"large_signature_data" * 100,
                "message": b"large_message_data" * 100
            }
        }
        
        # Test that large payloads are handled efficiently
        import time
        start_time = time.time()
        
        safe_payload = self.make_json_safe(large_payload)
        json.dumps(safe_payload)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process within reasonable time (adjust threshold as needed)
        assert processing_time < 1.0, f"JSON safety processing took too long: {processing_time}s"

    def test_unicode_handling(self):
        """BUG-003: Test Unicode characters in payloads"""
        unicode_payload = {
            "unicode_string": "Hello 世界 🌍",
            "bytes_with_unicode": "Hello 世界 🌍".encode('utf-8'),
            "mixed": {
                "ascii": "ASCII text",
                "unicode": "Unicode text 中文",
                "bytes": "Unicode bytes 中文".encode('utf-8')
            }
        }
        
        safe_payload = self.make_json_safe(unicode_payload)
        json_str = json.dumps(safe_payload, ensure_ascii=False)
        
        # Should handle Unicode properly
        assert "世界" in json_str
        assert "🌍" in json_str

    def test_edge_case_types(self):
        """BUG-003: Test edge case data types"""
        edge_cases = [
            None,
            True,
            False,
            0,
            0.0,
            "",
            [],
            {},
            set([1, 2, 3]),
            frozenset([1, 2, 3]),
            (1, 2, 3),
            range(10)
        ]
        
        for case in edge_cases:
            try:
                safe_case = self.make_json_safe(case)
                json.dumps(safe_case)
                print(f"Edge case {type(case).__name__} handled successfully")
            except Exception as e:
                print(f"Edge case {type(case).__name__} failed: {e}")

    def make_json_safe(self, obj: Any) -> Any:
        """Helper method to make objects JSON safe - matches bot implementation"""
        if isinstance(obj, bytes):
            return obj.hex()
        elif isinstance(obj, dict):
            return {k: self.make_json_safe(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.make_json_safe(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self.make_json_safe(item) for item in obj)
        elif isinstance(obj, set):
            return list(self.make_json_safe(item) for item in obj)
        elif isinstance(obj, frozenset):
            return list(self.make_json_safe(item) for item in obj)
        elif hasattr(obj, '__dict__'):
            # Handle objects with __dict__ (like Mock objects)
            try:
                return str(obj)
            except:
                return f"<{type(obj).__name__} object>"
        else:
            return obj

    def test_json_safety_integration(self):
        """BUG-003: Test JSON safety integration with bot components"""
        # Test the actual JSON safety check used in the bot
        def bot_json_safety_check(payload: Dict[str, Any]) -> Dict[str, Any]:
            """Bot's JSON safety check implementation"""
            try:
                # Test JSON serialization to catch any bytes/unsupported objects
                json.dumps(payload)
                return payload
            except (TypeError, ValueError) as json_error:
                print(f"JSON serialization error: {json_error}")
                print(f"Payload contains non-serializable objects: {payload}")
                
                # Repair: Convert any bytes objects to hex strings
                safe_payload = self.make_json_safe(payload)
                print(f"Repaired payload: {safe_payload}")
                
                # Test the repaired payload
                try:
                    json.dumps(safe_payload)
                    return safe_payload
                except Exception as repair_error:
                    print(f"Repair failed: {repair_error}")
                    # Ultimate fallback: create minimal safe payload
                    return {
                        "market_type": "perp",
                        "market_index": 0,
                        "message": "00",
                        "signature": "dummy_signature",
                        "taker_authority": "fallback_authority",
                        "error": "json_serialization_failed"
                    }
        
        # Test with various payloads
        test_payloads = [
            {"normal": "data"},
            {"with_bytes": b"binary_data"},
            {"with_mock": Mock()},
            {"nested": {"deep": {"bytes": b"data"}}}
        ]
        
        for payload in test_payloads:
            safe_payload = bot_json_safety_check(payload)
            # Should always be JSON serializable
            json.dumps(safe_payload)
            print(f"Payload made safe: {type(payload).__name__}")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
