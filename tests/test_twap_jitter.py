"""
Unit tests for TWAP Jitter execution engine.

This module tests the advanced TWAP execution capabilities, including
regime-aware execution, slice management, and integration with the
ExecutionRouter framework.
"""

import pytest
import asyncio
import time
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from libs.execution.twap_jitter import (
    TwapJitter,
    TwapIntent,
    TwapExecutionMode,
    TwapRegime,
    TwapExecutionState,
    TwapMetrics
)
from libs.execution.router import ExecIntent, OrderResult, ErrorType
from libs.execution.twap_execution import TwapExecutionConfig, PositionDirection

class TestTwapJitterInitialization:
    """Test suite for TwapJitter initialization and configuration"""
    
    def test_twap_jitter_initialization(self):
        """Test basic TwapJitter initialization"""
        mock_drift = Mock()
        mock_swift = Mock()
        
        twap_jitter = TwapJitter(
            drift_client=mock_drift,
            swift_client=mock_swift,
            swift_enabled=True
        )
        
        assert twap_jitter.drift == mock_drift
        assert twap_jitter.swift == mock_swift
        assert twap_jitter.swift_enabled == True
        assert len(twap_jitter.active_twaps) == 0
        assert isinstance(twap_jitter.twap_metrics, TwapMetrics)
        assert len(twap_jitter.regime_configs) == 3  # CALM, VOLATILE, TOXIC
    
    def test_regime_configurations(self):
        """Test regime-specific configurations are properly set"""
        mock_drift = Mock()
        twap_jitter = TwapJitter(drift_client=mock_drift)
        
        # Test CALM regime config
        calm_config = twap_jitter.regime_configs[TwapRegime.CALM]
        assert calm_config['slice_multiplier'] == 1.0
        assert calm_config['preferred_intent'] == TwapIntent.TWAP_MAKER
        assert calm_config['compute_priority'] == 'medium'
        
        # Test VOLATILE regime config  
        volatile_config = twap_jitter.regime_configs[TwapRegime.VOLATILE]
        assert volatile_config['slice_multiplier'] == 0.6
        assert volatile_config['preferred_intent'] == TwapIntent.TWAP_MIXED
        assert volatile_config['compute_priority'] == 'high'
        
        # Test TOXIC regime config
        toxic_config = twap_jitter.regime_configs[TwapRegime.TOXIC]
        assert toxic_config['slice_multiplier'] == 0.3
        assert toxic_config['preferred_intent'] == TwapIntent.TWAP_TAKER
        assert toxic_config['compute_priority'] == 'critical'
    
    def test_custom_regime_classifier(self):
        """Test custom regime classifier integration"""
        mock_drift = Mock()
        
        def custom_classifier():
            return TwapRegime.VOLATILE
        
        twap_jitter = TwapJitter(
            drift_client=mock_drift,
            regime_classifier=custom_classifier
        )
        
        assert twap_jitter.regime_classifier() == TwapRegime.VOLATILE
    
    def test_custom_toxicity_filter(self):
        """Test custom toxicity filter integration"""
        mock_drift = Mock()
        
        def custom_toxicity_filter():
            return True  # Market is toxic
        
        twap_jitter = TwapJitter(
            drift_client=mock_drift,
            toxicity_filter=custom_toxicity_filter
        )
        
        assert twap_jitter.toxicity_filter() == True

class TestTwapExecutionLifecycle:
    """Test suite for TWAP execution lifecycle management"""
    
    @pytest.fixture
    def twap_jitter(self):
        """Create a TwapJitter instance for testing"""
        mock_drift = Mock()
        mock_swift = Mock()
        
        return TwapJitter(
            drift_client=mock_drift,
            swift_client=mock_swift,
            swift_enabled=True
        )
    
    @pytest.mark.asyncio
    async def test_start_twap_execution(self, twap_jitter):
        """Test starting a new TWAP execution"""
        execution_id = "test_twap_1"
        current_position = Decimal('0')
        target_position = Decimal('1000')
        duration_sec = 600  # 10 minutes
        
        result = await twap_jitter.start_twap_execution(
            execution_id=execution_id,
            current_position=current_position,
            target_position=target_position,
            duration_sec=duration_sec
        )
        
        assert result == True
        assert execution_id in twap_jitter.active_twaps
        
        execution_state = twap_jitter.active_twaps[execution_id]
        assert execution_state.execution_id == execution_id
        assert execution_state.progress.current_position == current_position
        assert execution_state.progress.amount_target == target_position
        assert execution_state.progress.overall_duration_sec == duration_sec
        assert execution_state.active == True
        assert execution_state.paused == False
    
    @pytest.mark.asyncio
    async def test_start_duplicate_twap_execution(self, twap_jitter):
        """Test starting a TWAP execution with duplicate ID"""
        execution_id = "test_twap_duplicate"
        
        # Start first TWAP
        result1 = await twap_jitter.start_twap_execution(
            execution_id=execution_id,
            current_position=Decimal('0'),
            target_position=Decimal('500'),
            duration_sec=300
        )
        
        # Try to start duplicate TWAP
        result2 = await twap_jitter.start_twap_execution(
            execution_id=execution_id,
            current_position=Decimal('0'),
            target_position=Decimal('1000'),
            duration_sec=600
        )
        
        assert result1 == True
        assert result2 == False  # Should fail due to duplicate ID
        assert len(twap_jitter.active_twaps) == 1
    
    @pytest.mark.asyncio
    async def test_stop_twap_execution(self, twap_jitter):
        """Test stopping a TWAP execution"""
        execution_id = "test_twap_stop"
        
        # Start TWAP
        await twap_jitter.start_twap_execution(
            execution_id=execution_id,
            current_position=Decimal('0'),
            target_position=Decimal('500'),
            duration_sec=300
        )
        
        assert execution_id in twap_jitter.active_twaps
        
        # Stop TWAP
        result = await twap_jitter.stop_twap(execution_id)
        
        assert result == True
        assert execution_id not in twap_jitter.active_twaps
    
    @pytest.mark.asyncio
    async def test_pause_and_resume_twap(self, twap_jitter):
        """Test pausing and resuming TWAP execution"""
        execution_id = "test_twap_pause"
        
        # Start TWAP
        await twap_jitter.start_twap_execution(
            execution_id=execution_id,
            current_position=Decimal('0'),
            target_position=Decimal('500'),
            duration_sec=300
        )
        
        execution_state = twap_jitter.active_twaps[execution_id]
        assert execution_state.paused == False
        
        # Pause TWAP
        pause_result = await twap_jitter.pause_twap(execution_id)
        assert pause_result == True
        assert execution_state.paused == True
        
        # Resume TWAP
        resume_result = await twap_jitter.resume_twap(execution_id)
        assert resume_result == True
        assert execution_state.paused == False
    
    @pytest.mark.asyncio
    async def test_update_twap_target(self, twap_jitter):
        """Test updating TWAP target position"""
        execution_id = "test_twap_update"
        initial_target = Decimal('500')
        new_target = Decimal('750')
        
        # Start TWAP
        await twap_jitter.start_twap_execution(
            execution_id=execution_id,
            current_position=Decimal('0'),
            target_position=initial_target,
            duration_sec=300
        )
        
        execution_state = twap_jitter.active_twaps[execution_id]
        assert execution_state.progress.amount_target == initial_target
        
        # Update target
        update_result = await twap_jitter.update_twap_target(execution_id, new_target)
        assert update_result == True
        assert execution_state.progress.amount_target == new_target

class TestTwapSliceExecution:
    """Test suite for TWAP slice execution logic"""
    
    @pytest.fixture
    def twap_jitter_with_mocks(self):
        """Create TwapJitter with mocked clients"""
        mock_drift = Mock()
        mock_swift = Mock()
        
        # Mock the place method from ExecutionRouter
        twap_jitter = TwapJitter(
            drift_client=mock_drift,
            swift_client=mock_swift,
            swift_enabled=True
        )
        
        return twap_jitter, mock_drift, mock_swift
    
    @pytest.mark.asyncio
    async def test_execute_twap_slice_success(self, twap_jitter_with_mocks):
        """Test successful TWAP slice execution"""
        twap_jitter, mock_drift, mock_swift = twap_jitter_with_mocks
        
        execution_id = "test_slice"
        market_index = 0
        
        # Start TWAP
        await twap_jitter.start_twap_execution(
            execution_id=execution_id,
            current_position=Decimal('0'),
            target_position=Decimal('1000'),
            duration_sec=600
        )
        
        # Mock successful order placement
        with patch.object(twap_jitter, 'place', new_callable=AsyncMock) as mock_place:
            mock_place.return_value = OrderResult(
                success=True,
                order_id="test_order_123",
                driver="swift"
            )
            
            # Execute slice
            result = await twap_jitter.execute_twap_slice(execution_id, market_index)
            
            assert result.success == True
            assert result.order_id == "test_order_123"
            assert result.driver == "swift"
            
            # Verify place was called with correct parameters
            mock_place.assert_called_once()
            call_args = mock_place.call_args
            assert call_args[1]['context'] == f"twap_slice_{execution_id}"
            
            # Verify execution state was updated
            execution_state = twap_jitter.active_twaps[execution_id]
            assert execution_state.slice_count == 1
            assert execution_state.total_executed > 0
    
    @pytest.mark.asyncio
    async def test_execute_twap_slice_with_toxicity(self, twap_jitter_with_mocks):
        """Test TWAP slice execution when market is toxic"""
        twap_jitter, _, _ = twap_jitter_with_mocks
        
        # Set toxicity filter to return True (toxic market)
        twap_jitter.toxicity_filter = lambda: True
        
        execution_id = "test_toxic_slice"
        market_index = 0
        
        # Start TWAP
        await twap_jitter.start_twap_execution(
            execution_id=execution_id,
            current_position=Decimal('0'),
            target_position=Decimal('1000'),
            duration_sec=600
        )
        
        # Execute slice (should be paused due to toxicity)
        result = await twap_jitter.execute_twap_slice(execution_id, market_index)
        
        assert result.success == False
        assert "market toxicity" in result.error
        assert result.error_type == ErrorType.TRANSIENT
        
        # Verify TWAP was paused
        execution_state = twap_jitter.active_twaps[execution_id]
        assert execution_state.paused == True
    
    @pytest.mark.asyncio
    async def test_execute_twap_slice_nonexistent(self, twap_jitter_with_mocks):
        """Test executing slice for non-existent TWAP"""
        twap_jitter, _, _ = twap_jitter_with_mocks
        
        result = await twap_jitter.execute_twap_slice("nonexistent_twap", 0)
        
        assert result.success == False
        assert "not found" in result.error
        assert result.error_type == ErrorType.PERMANENT
    
    @pytest.mark.asyncio
    async def test_execute_twap_slice_complete(self, twap_jitter_with_mocks):
        """Test executing slice when TWAP is complete"""
        twap_jitter, _, _ = twap_jitter_with_mocks
        
        execution_id = "test_complete_slice"
        
        # Start TWAP with same current and target position (already complete)
        await twap_jitter.start_twap_execution(
            execution_id=execution_id,
            current_position=Decimal('1000'),
            target_position=Decimal('1000'),
            duration_sec=600
        )
        
        # Execute slice (should indicate completion)
        result = await twap_jitter.execute_twap_slice(execution_id, 0)
        
        assert result.success == True
        assert result.driver == "twap_complete"
        
        # Verify TWAP was marked inactive
        execution_state = twap_jitter.active_twaps[execution_id]
        assert execution_state.active == False

class TestTwapIntentDetermination:
    """Test suite for TWAP intent determination logic"""
    
    @pytest.fixture
    def twap_jitter(self):
        """Create TwapJitter for testing"""
        mock_drift = Mock()
        return TwapJitter(drift_client=mock_drift)
    
    def test_determine_execution_intent_maker(self, twap_jitter):
        """Test intent determination for TWAP_MAKER"""
        execution_state = Mock()
        execution_state.intent = TwapIntent.TWAP_MAKER
        
        intent = twap_jitter._determine_execution_intent(execution_state)
        assert intent == ExecIntent.MAKER
    
    def test_determine_execution_intent_taker(self, twap_jitter):
        """Test intent determination for TWAP_TAKER"""
        execution_state = Mock()
        execution_state.intent = TwapIntent.TWAP_TAKER
        
        intent = twap_jitter._determine_execution_intent(execution_state)
        assert intent == ExecIntent.TAKER
    
    def test_determine_execution_intent_mixed_calm_early(self, twap_jitter):
        """Test intent determination for TWAP_MIXED in calm market, early slices"""
        execution_state = Mock()
        execution_state.intent = TwapIntent.TWAP_MIXED
        execution_state.regime = TwapRegime.CALM
        execution_state.slice_count = 1  # Early slice
        
        intent = twap_jitter._determine_execution_intent(execution_state)
        assert intent == ExecIntent.MAKER  # Should use maker for early calm slices
    
    def test_determine_execution_intent_mixed_volatile_late(self, twap_jitter):
        """Test intent determination for TWAP_MIXED in volatile market, late slices"""
        execution_state = Mock()
        execution_state.intent = TwapIntent.TWAP_MIXED
        execution_state.regime = TwapRegime.VOLATILE
        execution_state.slice_count = 5  # Late slice
        
        intent = twap_jitter._determine_execution_intent(execution_state)
        assert intent == ExecIntent.TAKER  # Should use taker for late/urgent slices

class TestTwapMetricsAndStatus:
    """Test suite for TWAP metrics and status reporting"""
    
    @pytest.fixture
    def twap_jitter(self):
        """Create TwapJitter for testing"""
        mock_drift = Mock()
        return TwapJitter(drift_client=mock_drift)
    
    @pytest.mark.asyncio
    async def test_get_twap_status(self, twap_jitter):
        """Test getting status of a specific TWAP execution"""
        execution_id = "test_status"
        
        # Start TWAP
        await twap_jitter.start_twap_execution(
            execution_id=execution_id,
            current_position=Decimal('100'),
            target_position=Decimal('500'),
            duration_sec=300,
            mode=TwapExecutionMode.AGGRESSIVE,
            intent=TwapIntent.TWAP_TAKER
        )
        
        status = twap_jitter.get_twap_status(execution_id)
        
        assert status is not None
        assert status['execution_id'] == execution_id
        assert status['active'] == True
        assert status['paused'] == False
        assert status['mode'] == TwapExecutionMode.AGGRESSIVE.value
        assert status['intent'] == TwapIntent.TWAP_TAKER.value
        assert status['slice_count'] == 0
        assert status['error_count'] == 0
        assert 'progress_percentage' in status
        assert 'amount_remaining' in status
    
    def test_get_twap_status_nonexistent(self, twap_jitter):
        """Test getting status of non-existent TWAP"""
        status = twap_jitter.get_twap_status("nonexistent")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_get_all_twap_status(self, twap_jitter):
        """Test getting status of all TWAP executions"""
        # Start multiple TWAPs
        await twap_jitter.start_twap_execution("twap1", Decimal('0'), Decimal('100'), 300)
        await twap_jitter.start_twap_execution("twap2", Decimal('50'), Decimal('150'), 600)
        
        all_status = twap_jitter.get_all_twap_status()
        
        assert len(all_status) == 2
        execution_ids = [status['execution_id'] for status in all_status]
        assert "twap1" in execution_ids
        assert "twap2" in execution_ids
    
    def test_get_twap_metrics(self, twap_jitter):
        """Test getting comprehensive TWAP metrics"""
        metrics = twap_jitter.get_twap_metrics()
        
        assert 'twap_metrics' in metrics
        assert 'regime_configs' in metrics
        assert 'execution_stats' in metrics  # From parent ExecutionRouter
        
        twap_metrics = metrics['twap_metrics']
        assert 'total_executions' in twap_metrics
        assert 'total_volume' in twap_metrics
        assert 'success_rate' in twap_metrics
        assert 'active_twaps' in twap_metrics
        assert 'slices_per_regime' in twap_metrics
        
        regime_configs = metrics['regime_configs']
        assert TwapRegime.CALM.value in regime_configs
        assert TwapRegime.VOLATILE.value in regime_configs
        assert TwapRegime.TOXIC.value in regime_configs

class TestTwapHealthCheck:
    """Test suite for TWAP health monitoring"""
    
    @pytest.fixture
    def twap_jitter(self):
        """Create TwapJitter for testing"""
        mock_drift = Mock()
        return TwapJitter(drift_client=mock_drift)
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, twap_jitter):
        """Test health check with healthy TWAP executions"""
        # Start a recent TWAP
        await twap_jitter.start_twap_execution(
            "healthy_twap",
            Decimal('0'),
            Decimal('100'),
            300
        )
        
        health = await twap_jitter.health_check()
        assert health == True
    
    @pytest.mark.asyncio
    async def test_health_check_stuck_twap(self, twap_jitter):
        """Test health check with stuck TWAP execution"""
        # Start TWAP and simulate it being stuck
        await twap_jitter.start_twap_execution(
            "stuck_twap",
            Decimal('0'),
            Decimal('100'),
            300
        )
        
        execution_state = twap_jitter.active_twaps["stuck_twap"]
        
        # Simulate stuck execution (last slice was > 10 minutes ago)
        execution_state.last_slice_time = time.time() - 700  # 11+ minutes ago
        
        health = await twap_jitter.health_check()
        assert health == False
    
    @pytest.mark.asyncio
    async def test_health_check_high_error_rate(self, twap_jitter):
        """Test health check with high error rate"""
        # Start TWAP and simulate high error rate
        await twap_jitter.start_twap_execution(
            "error_twap",
            Decimal('0'),
            Decimal('100'),
            300
        )
        
        execution_state = twap_jitter.active_twaps["error_twap"]
        
        # Simulate high error rate (15% error rate)
        execution_state.slice_count = 20
        execution_state.error_count = 3  # 15% error rate
        
        health = await twap_jitter.health_check()
        assert health == False

class TestTwapComputeBudgetIntegration:
    """Test suite for TWAP compute budget optimization"""
    
    @pytest.fixture
    def twap_jitter(self):
        """Create TwapJitter for testing"""
        mock_drift = Mock()
        return TwapJitter(drift_client=mock_drift)
    
    def test_get_compute_budget_params_calm(self, twap_jitter):
        """Test compute budget parameters for calm regime"""
        execution_state = Mock()
        execution_state.regime = TwapRegime.CALM
        
        params = twap_jitter._get_compute_budget_params(execution_state)
        
        assert 'compute_unit_limit' in params
        assert 'compute_unit_price' in params
        assert params['compute_unit_limit'] > 0
        assert params['compute_unit_price'] > 0
    
    def test_get_compute_budget_params_volatile(self, twap_jitter):
        """Test compute budget parameters for volatile regime"""
        execution_state = Mock()
        execution_state.regime = TwapRegime.VOLATILE
        
        params = twap_jitter._get_compute_budget_params(execution_state)
        
        # Volatile regime should have higher priority (higher price)
        calm_state = Mock()
        calm_state.regime = TwapRegime.CALM
        calm_params = twap_jitter._get_compute_budget_params(calm_state)
        
        assert params['compute_unit_price'] > calm_params['compute_unit_price']
    
    def test_get_compute_budget_params_toxic(self, twap_jitter):
        """Test compute budget parameters for toxic regime"""
        execution_state = Mock()
        execution_state.regime = TwapRegime.TOXIC
        
        params = twap_jitter._get_compute_budget_params(execution_state)
        
        # Toxic regime should have highest priority (highest price)
        volatile_state = Mock()
        volatile_state.regime = TwapRegime.VOLATILE
        volatile_params = twap_jitter._get_compute_budget_params(volatile_state)
        
        assert params['compute_unit_price'] > volatile_params['compute_unit_price']

# Integration test
class TestTwapJitterIntegration:
    """Integration tests for complete TWAP execution workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_twap_workflow(self):
        """Test complete TWAP execution workflow from start to finish"""
        mock_drift = Mock()
        mock_swift = Mock()
        
        twap_jitter = TwapJitter(
            drift_client=mock_drift,
            swift_client=mock_swift,
            swift_enabled=True
        )
        
        execution_id = "integration_test"
        
        # 1. Start TWAP execution
        start_result = await twap_jitter.start_twap_execution(
            execution_id=execution_id,
            current_position=Decimal('0'),
            target_position=Decimal('1000'),
            duration_sec=300,
            mode=TwapExecutionMode.BALANCED,
            intent=TwapIntent.TWAP_MIXED
        )
        
        assert start_result == True
        assert execution_id in twap_jitter.active_twaps
        
        # 2. Check initial status
        status = twap_jitter.get_twap_status(execution_id)
        assert status['active'] == True
        assert status['progress_percentage'] == 0.0
        
        # 3. Mock successful slice execution
        with patch.object(twap_jitter, 'place', new_callable=AsyncMock) as mock_place:
            mock_place.return_value = OrderResult(
                success=True,
                order_id="slice_order_1",
                driver="swift"
            )
            
            # Execute a slice
            slice_result = await twap_jitter.execute_twap_slice(execution_id, 0)
            assert slice_result.success == True
        
        # 4. Verify state updates
        updated_status = twap_jitter.get_twap_status(execution_id)
        assert updated_status['slice_count'] == 1
        assert updated_status['total_executed'] > 0
        
        # 5. Pause and resume
        pause_result = await twap_jitter.pause_twap(execution_id)
        assert pause_result == True
        
        paused_status = twap_jitter.get_twap_status(execution_id)
        assert paused_status['paused'] == True
        
        resume_result = await twap_jitter.resume_twap(execution_id)
        assert resume_result == True
        
        # 6. Update target
        update_result = await twap_jitter.update_twap_target(execution_id, Decimal('1500'))
        assert update_result == True
        
        # 7. Stop execution
        stop_result = await twap_jitter.stop_twap(execution_id)
        assert stop_result == True
        assert execution_id not in twap_jitter.active_twaps
        
        # 8. Verify metrics were tracked
        metrics = twap_jitter.get_twap_metrics()
        assert metrics['twap_metrics']['total_executions'] > 0

# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])


