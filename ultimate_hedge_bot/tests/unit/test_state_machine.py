"""
Unit tests for Ultimate Hedge Bot State Machine
Tests the fixed state machine with proper transition validation.
"""

import pytest
import asyncio
from unittest.mock import patch
from ultimate_hedge_bot.core.state_machine import (
    HedgeStateMachine, HedgeState, VALID_TRANSITIONS,
    StateMachineError, HedgeContext
)


class TestHedgeStateMachine:
    """Comprehensive tests for the fixed state machine."""

    def setup_method(self):
        """Setup test fixtures."""
        self.sm = HedgeStateMachine()

    def test_initialization(self):
        """Test state machine initialization."""
        assert len(self.sm.get_all_hedges()) == 0
        assert len(self.sm.get_active_hedges()) == 0

    def test_valid_state_transitions(self):
        """Test that all valid state transitions work correctly."""
        # Create a hedge
        context = HedgeContext(
            hedge_id="test_hedge_1",
            symbol="SOL-PERP",
            venue="drift",
            side="buy",
            quantity=100.0
        )

        # Test complete valid flow
        # PLANNED → SUBMITTED
        state = self.sm.initialize_hedge(context)
        assert state == HedgeState.PLANNED

        state = self.sm.transition("test_hedge_1", HedgeState.SUBMITTED)
        assert state == HedgeState.SUBMITTED

        # SUBMITTED → FILLED
        state = self.sm.transition("test_hedge_1", HedgeState.FILLED)
        assert state == HedgeState.FILLED

        # FILLED → MONITORING
        state = self.sm.transition("test_hedge_1", HedgeState.MONITORING)
        assert state == HedgeState.MONITORING

        # MONITORING → RECONCILED
        state = self.sm.transition("test_hedge_1", HedgeState.RECONCILED)
        assert state == HedgeState.RECONCILED

        # RECONCILED → CLOSED
        state = self.sm.transition("test_hedge_1", HedgeState.CLOSED)
        assert state == HedgeState.CLOSED

        # Verify final state
        assert self.sm.get_state("test_hedge_1") == HedgeState.CLOSED
        assert not self.sm.is_active("test_hedge_1")
        assert self.sm.is_terminal("test_hedge_1")

    def test_invalid_state_transitions_blocked(self):
        """Test that invalid state transitions are properly blocked."""
        # Create a hedge
        context = HedgeContext(
            hedge_id="test_hedge_2",
            symbol="SOL-PERP",
            venue="drift",
            side="buy",
            quantity=100.0
        )

        self.sm.initialize_hedge(context)

        # Try invalid transition: PLANNED → RECONCILED (should fail)
        with pytest.raises(StateMachineError, match="Invalid transition"):
            self.sm.transition("test_hedge_2", HedgeState.RECONCILED)

        # Try invalid transition: SUBMITTED → RECONCILED (should fail)
        self.sm.transition("test_hedge_2", HedgeState.SUBMITTED)
        with pytest.raises(StateMachineError, match="Invalid transition"):
            self.sm.transition("test_hedge_2", HedgeState.RECONCILED)

        # Try invalid transition: MONITORING → CLOSED (should fail)
        self.sm.transition("test_hedge_2", HedgeState.FILLED)
        self.sm.transition("test_hedge_2", HedgeState.MONITORING)
        with pytest.raises(StateMachineError, match="Invalid transition"):
            self.sm.transition("test_hedge_2", HedgeState.CLOSED)

    def test_canceled_state_termination(self):
        """Test that CANCELED state properly terminates the hedge."""
        context = HedgeContext(
            hedge_id="test_hedge_3",
            symbol="SOL-PERP",
            venue="drift",
            side="buy",
            quantity=100.0
        )

        self.sm.initialize_hedge(context)

        # Cancel from PLANNED state
        state = self.sm.transition("test_hedge_3", HedgeState.CANCELED)
        assert state == HedgeState.CANCELED
        assert self.sm.is_terminal("test_hedge_3")

        # Verify no further transitions allowed
        with pytest.raises(StateMachineError, match="Cannot transition from terminal state"):
            self.sm.transition("test_hedge_3", HedgeState.SUBMITTED)

    def test_unwinding_state_handling(self):
        """Test UNWINDING state for partial fills."""
        context = HedgeContext(
            hedge_id="test_hedge_4",
            symbol="SOL-PERP",
            venue="drift",
            side="buy",
            quantity=100.0
        )

        self.sm.initialize_hedge(context)

        # Go to FILLED state
        self.sm.transition("test_hedge_4", HedgeState.SUBMITTED)
        self.sm.transition("test_hedge_4", HedgeState.FILLED)

        # Test UNWINDING path
        state = self.sm.transition("test_hedge_4", HedgeState.UNWINDING)
        assert state == HedgeState.UNWINDING

        # UNWINDING → CLOSED (only valid transition)
        state = self.sm.transition("test_hedge_4", HedgeState.CLOSED)
        assert state == HedgeState.CLOSED

        # Verify invalid transitions from UNWINDING are blocked
        # Create another hedge to test
        context2 = HedgeContext(
            hedge_id="test_hedge_5",
            symbol="SOL-PERP",
            venue="drift",
            side="buy",
            quantity=100.0
        )
        self.sm.initialize_hedge(context2)
        self.sm.transition("test_hedge_5", HedgeState.SUBMITTED)
        self.sm.transition("test_hedge_5", HedgeState.FILLED)
        self.sm.transition("test_hedge_5", HedgeState.UNWINDING)

        # Try invalid transition from UNWINDING
        with pytest.raises(StateMachineError, match="Invalid transition"):
            self.sm.transition("test_hedge_5", HedgeState.MONITORING)

    def test_nonexistent_hedge_handling(self):
        """Test proper handling of operations on non-existent hedges."""
        # Try to get state of non-existent hedge
        assert self.sm.get_state("nonexistent") is None

        # Try to transition non-existent hedge
        with pytest.raises(StateMachineError, match="does not exist"):
            self.sm.transition("nonexistent", HedgeState.SUBMITTED)

        # Try to check if non-existent hedge is active
        assert not self.sm.is_active("nonexistent")
        assert not self.sm.is_terminal("nonexistent")

    def test_duplicate_hedge_prevention(self):
        """Test prevention of duplicate hedge creation."""
        context = HedgeContext(
            hedge_id="duplicate_test",
            symbol="SOL-PERP",
            venue="drift",
            side="buy",
            quantity=100.0
        )

        # First creation should succeed
        self.sm.initialize_hedge(context)

        # Second creation should fail
        with pytest.raises(StateMachineError, match="already exists"):
            self.sm.initialize_hedge(context)

    def test_transition_history_tracking(self):
        """Test that transition history is properly tracked."""
        context = HedgeContext(
            hedge_id="history_test",
            symbol="SOL-PERP",
            venue="drift",
            side="buy",
            quantity=100.0
        )

        # Create hedge and make several transitions
        self.sm.initialize_hedge(context)
        self.sm.transition("history_test", HedgeState.SUBMITTED)
        self.sm.transition("history_test", HedgeState.FILLED)
        self.sm.transition("history_test", HedgeState.MONITORING)

        # Check transition history
        history = self.sm.get_transition_history("history_test")
        assert len(history) == 4  # PLANNED + 3 transitions

        # Verify history structure
        assert history[0]['from_state'] is None  # Initial state
        assert history[0]['to_state'] == 'planned'

        assert history[1]['from_state'] == 'planned'
        assert history[1]['to_state'] == 'submitted'

        assert history[2]['from_state'] == 'submitted'
        assert history[2]['to_state'] == 'filled'

        assert history[3]['from_state'] == 'filled'
        assert history[3]['to_state'] == 'monitoring'

        # Verify timestamps are increasing
        timestamps = [entry['timestamp'] for entry in history]
        assert timestamps == sorted(timestamps)

    def test_force_cancel_functionality(self):
        """Test force cancel bypasses normal validation."""
        context = HedgeContext(
            hedge_id="force_cancel_test",
            symbol="SOL-PERP",
            venue="drift",
            side="buy",
            quantity=100.0
        )

        self.sm.initialize_hedge(context)
        self.sm.transition("force_cancel_test", HedgeState.SUBMITTED)
        self.sm.transition("force_cancel_test", HedgeState.FILLED)

        # Force cancel from FILLED state (bypasses normal validation)
        success = self.sm.force_cancel("force_cancel_test", "emergency_cancel")
        assert success
        assert self.sm.get_state("force_cancel_test") == HedgeState.CANCELED

    def test_state_machine_validation(self):
        """Test comprehensive state machine validation."""
        # Create multiple hedges in different states
        contexts = []
        for i in range(5):
            context = HedgeContext(
                hedge_id=f"validation_test_{i}",
                symbol="SOL-PERP",
                venue="drift",
                side="buy",
                quantity=100.0
            )
            contexts.append(context)

        # Initialize all hedges
        for context in contexts:
            self.sm.initialize_hedge(context)

        # Put them in different states
        self.sm.transition("validation_test_0", HedgeState.CANCELED)  # Terminal
        self.sm.transition("validation_test_1", HedgeState.SUBMITTED)  # Active
        self.sm.transition("validation_test_2", HedgeState.SUBMITTED)
        self.sm.transition("validation_test_2", HedgeState.FILLED)
        self.sm.transition("validation_test_2", HedgeState.MONITORING)  # Active
        self.sm.transition("validation_test_3", HedgeState.SUBMITTED)
        self.sm.transition("validation_test_3", HedgeState.FILLED)
        self.sm.transition("validation_test_3", HedgeState.UNWINDING)  # Active

        # Validate state machine
        errors = self.sm.validate_all_states()

        # Should have no validation errors
        assert len(errors) == 0

        # Check state counts
        counts = self.sm.get_state_counts()
        assert counts['planned'] == 1  # validation_test_4
        assert counts['submitted'] == 1  # validation_test_1
        assert counts['monitoring'] == 1  # validation_test_2
        assert counts['unwinding'] == 1  # validation_test_3
        assert counts['canceled'] == 1  # validation_test_0
        assert counts['closed'] == 0

        # Check active hedges
        active = self.sm.get_active_hedges()
        assert len(active) == 3  # submitted, monitoring, unwinding
        assert "validation_test_1" in active
        assert "validation_test_2" in active
        assert "validation_test_3" in active

    def test_context_preservation(self):
        """Test that hedge context is properly preserved and updated."""
        context = HedgeContext(
            hedge_id="context_test",
            symbol="SOL-PERP",
            venue="drift",
            side="buy",
            quantity=100.0
        )

        # Initialize
        self.sm.initialize_hedge(context)
        retrieved_context = self.sm.get_context("context_test")
        assert retrieved_context is not None
        assert retrieved_context.symbol == "SOL-PERP"
        assert retrieved_context.created_at is not None

        # Check timestamps are set
        import time
        assert abs(retrieved_context.created_at - time.time()) < 1  # Within 1 second
        assert retrieved_context.updated_at == retrieved_context.created_at

        # Make a transition and check updated_at changes
        import time
        time.sleep(0.01)  # Small delay to ensure timestamp difference
        self.sm.transition("context_test", HedgeState.SUBMITTED)

        updated_context = self.sm.get_context("context_test")
        assert updated_context.updated_at > updated_context.created_at

    def test_valid_transitions_comprehensive(self):
        """Test all valid state transitions comprehensively."""
        test_cases = [
            # (start_state, valid_transitions)
            (HedgeState.PLANNED, [HedgeState.SUBMITTED, HedgeState.CANCELED]),
            (HedgeState.SUBMITTED, [HedgeState.FILLED, HedgeState.CANCELED]),
            (HedgeState.FILLED, [HedgeState.MONITORING, HedgeState.UNWINDING]),
            (HedgeState.MONITORING, [HedgeState.RECONCILED]),
            (HedgeState.RECONCILED, [HedgeState.CLOSED]),
            (HedgeState.UNWINDING, [HedgeState.CLOSED]),
        ]

        for start_state, valid_targets in test_cases:
            # Test each valid transition
            for target_state in valid_targets:
                # Create fresh hedge for each test
                hedge_id = f"transition_test_{start_state.value}_to_{target_state.value}"
                context = HedgeContext(
                    hedge_id=hedge_id,
                    symbol="SOL-PERP",
                    venue="drift",
                    side="buy",
                    quantity=100.0
                )

                # Navigate to start state
                self.sm.initialize_hedge(context)
                if start_state != HedgeState.PLANNED:
                    self._navigate_to_state(hedge_id, start_state)

                # Test the transition
                result_state = self.sm.transition(hedge_id, target_state)
                assert result_state == target_state

    def _navigate_to_state(self, hedge_id: str, target_state: HedgeState):
        """Helper to navigate hedge to specific state for testing."""
        # This is a simplified navigation - in practice you'd follow the exact path
        if target_state == HedgeState.SUBMITTED:
            self.sm.transition(hedge_id, HedgeState.SUBMITTED)
        elif target_state == HedgeState.FILLED:
            self.sm.transition(hedge_id, HedgeState.SUBMITTED)
            self.sm.transition(hedge_id, HedgeState.FILLED)
        elif target_state == HedgeState.MONITORING:
            self.sm.transition(hedge_id, HedgeState.SUBMITTED)
            self.sm.transition(hedge_id, HedgeState.FILLED)
            self.sm.transition(hedge_id, HedgeState.MONITORING)
        elif target_state == HedgeState.RECONCILED:
            self.sm.transition(hedge_id, HedgeState.SUBMITTED)
            self.sm.transition(hedge_id, HedgeState.FILLED)
            self.sm.transition(hedge_id, HedgeState.MONITORING)
            self.sm.transition(hedge_id, HedgeState.RECONCILED)
        elif target_state == HedgeState.UNWINDING:
            self.sm.transition(hedge_id, HedgeState.SUBMITTED)
            self.sm.transition(hedge_id, HedgeState.FILLED)
            self.sm.transition(hedge_id, HedgeState.UNWINDING)

    def test_terminal_state_invariants(self):
        """Test that terminal states maintain proper invariants."""
        terminal_states = [HedgeState.CANCELED, HedgeState.CLOSED]

        for terminal_state in terminal_states:
            hedge_id = f"terminal_test_{terminal_state.value}"
            context = HedgeContext(
                hedge_id=hedge_id,
                symbol="SOL-PERP",
                venue="drift",
                side="buy",
                quantity=100.0
            )

            # Create and navigate to terminal state
            self.sm.initialize_hedge(context)

            if terminal_state == HedgeState.CANCELED:
                self.sm.transition(hedge_id, HedgeState.CANCELED)
            else:  # CLOSED
                self.sm.transition(hedge_id, HedgeState.SUBMITTED)
                self.sm.transition(hedge_id, HedgeState.FILLED)
                self.sm.transition(hedge_id, HedgeState.MONITORING)
                self.sm.transition(hedge_id, HedgeState.RECONCILED)
                self.sm.transition(hedge_id, HedgeState.CLOSED)

            # Verify terminal state properties
            assert self.sm.is_terminal(hedge_id)
            assert not self.sm.is_active(hedge_id)
            assert self.sm.get_state(hedge_id) == terminal_state

            # Verify no further transitions allowed
            with pytest.raises(StateMachineError):
                self.sm.transition(hedge_id, HedgeState.PLANNED)

    def test_comprehensive_transition_validation(self):
        """Test each valid transition individually with proper error handling."""
        # Test all valid transitions systematically
        valid_transitions = [
            # (from_state, to_state, description)
            (HedgeState.PLANNED, HedgeState.SUBMITTED, "PLANNED → SUBMITTED"),
            (HedgeState.PLANNED, HedgeState.CANCELED, "PLANNED → CANCELED"),
            (HedgeState.SUBMITTED, HedgeState.FILLED, "SUBMITTED → FILLED"),
            (HedgeState.SUBMITTED, HedgeState.CANCELED, "SUBMITTED → CANCELED"),
            (HedgeState.FILLED, HedgeState.MONITORING, "FILLED → MONITORING"),
            (HedgeState.FILLED, HedgeState.UNWINDING, "FILLED → UNWINDING"),
            (HedgeState.MONITORING, HedgeState.RECONCILED, "MONITORING → RECONCILED"),
            (HedgeState.RECONCILED, HedgeState.CLOSED, "RECONCILED → CLOSED"),
            (HedgeState.UNWINDING, HedgeState.CLOSED, "UNWINDING → CLOSED"),
        ]

        for from_state, to_state, description in valid_transitions:
            # Create fresh hedge for each test
            hedge_id = f"transition_test_{from_state.value}_to_{to_state.value}"
            context = HedgeContext(
                hedge_id=hedge_id,
                symbol="SOL-PERP",
                venue="drift",
                side="buy",
                quantity=100.0
            )

            # Initialize and navigate to from_state
            self.sm.initialize_hedge(context)
            if from_state != HedgeState.PLANNED:
                self._navigate_to_state_safely(hedge_id, from_state)

            # Test valid transition
            result_state = self.sm.transition(hedge_id, to_state)
            assert result_state == to_state, f"Failed: {description}"

        # Test invalid transitions that should raise TransitionError
        invalid_transitions = [
            # (from_state, to_state, description)
            (HedgeState.PLANNED, HedgeState.RECONCILED, "PLANNED → RECONCILED (invalid)"),
            (HedgeState.SUBMITTED, HedgeState.RECONCILED, "SUBMITTED → RECONCILED (invalid)"),
            (HedgeState.FILLED, HedgeState.CLOSED, "FILLED → CLOSED (invalid)"),
            (HedgeState.MONITORING, HedgeState.SUBMITTED, "MONITORING → SUBMITTED (invalid)"),
            (HedgeState.RECONCILED, HedgeState.MONITORING, "RECONCILED → MONITORING (invalid)"),
        ]

        for from_state, to_state, description in invalid_transitions:
            hedge_id = f"invalid_test_{from_state.value}_to_{to_state.value}"
            context = HedgeContext(
                hedge_id=hedge_id,
                symbol="SOL-PERP",
                venue="drift",
                side="buy",
                quantity=100.0
            )

            # Initialize and navigate to from_state
            self.sm.initialize_hedge(context)
            if from_state != HedgeState.PLANNED:
                self._navigate_to_state_safely(hedge_id, from_state)

            # Test that invalid transition raises TransitionError
            with pytest.raises(TransitionError) as exc_info:
                self.sm.transition(hedge_id, to_state)

            # Verify error message contains expected information
            error_msg = str(exc_info.value)
            assert from_state.value in error_msg
            assert to_state.value in error_msg
            assert "Invalid transition" in error_msg

    def _navigate_to_state_safely(self, hedge_id: str, target_state: HedgeState):
        """Navigate to target state following valid transitions."""
        if target_state == HedgeState.SUBMITTED:
            self.sm.transition(hedge_id, HedgeState.SUBMITTED)
        elif target_state == HedgeState.FILLED:
            self.sm.transition(hedge_id, HedgeState.SUBMITTED)
            self.sm.transition(hedge_id, HedgeState.FILLED)
        elif target_state == HedgeState.MONITORING:
            self.sm.transition(hedge_id, HedgeState.SUBMITTED)
            self.sm.transition(hedge_id, HedgeState.FILLED)
            self.sm.transition(hedge_id, HedgeState.MONITORING)
        elif target_state == HedgeState.RECONCILED:
            self.sm.transition(hedge_id, HedgeState.SUBMITTED)
            self.sm.transition(hedge_id, HedgeState.FILLED)
            self.sm.transition(hedge_id, HedgeState.MONITORING)
            self.sm.transition(hedge_id, HedgeState.RECONCILED)
        elif target_state == HedgeState.UNWINDING:
            self.sm.transition(hedge_id, HedgeState.SUBMITTED)
            self.sm.transition(hedge_id, HedgeState.FILLED)
            self.sm.transition(hedge_id, HedgeState.UNWINDING)
        elif target_state == HedgeState.CANCELED:
            self.sm.transition(hedge_id, HedgeState.CANCELED)
        elif target_state == HedgeState.CLOSED:
            self.sm.transition(hedge_id, HedgeState.SUBMITTED)
            self.sm.transition(hedge_id, HedgeState.FILLED)
            self.sm.transition(hedge_id, HedgeState.MONITORING)
            self.sm.transition(hedge_id, HedgeState.RECONCILED)
            self.sm.transition(hedge_id, HedgeState.CLOSED)
