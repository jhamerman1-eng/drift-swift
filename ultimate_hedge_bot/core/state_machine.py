"""
Ultimate Hedge Bot - State Machine
Fixed state machine architecture with proper transitions and validation.
"""

import time
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class HedgeState(Enum):
    """Hedge lifecycle states with proper validation."""
    PLANNED = "planned"           # Hedge calculated but not submitted
    SUBMITTED = "submitted"       # Hedge order submitted to venue
    FILLED = "filled"            # Hedge order fully filled
    MONITORING = "monitoring"    # Actively monitoring hedge performance
    RECONCILED = "reconciled"    # Hedge position reconciled with MM position
    CLOSED = "closed"           # Hedge lifecycle complete
    CANCELED = "canceled"       # Hedge canceled before execution
    UNWINDING = "unwinding"     # Partial fill - unwinding position


# Valid State Transitions
VALID_TRANSITIONS = {
    HedgeState.PLANNED: [HedgeState.SUBMITTED, HedgeState.CANCELED],
    HedgeState.SUBMITTED: [HedgeState.FILLED, HedgeState.CANCELED],
    HedgeState.FILLED: [HedgeState.MONITORING, HedgeState.UNWINDING],
    HedgeState.MONITORING: [HedgeState.RECONCILED],
    HedgeState.RECONCILED: [HedgeState.CLOSED],
    HedgeState.UNWINDING: [HedgeState.CLOSED],
    # CANCELED and CLOSED are terminal states - no further transitions allowed
}


@dataclass
class HedgeContext:
    """Context information for hedge state management."""
    hedge_id: str
    symbol: str
    venue: str
    side: str
    quantity: float
    price: Optional[float] = None
    order_id: Optional[str] = None
    effective_cost: Optional[float] = None
    urgency_score: Optional[float] = None
    created_at: float = None
    updated_at: float = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.updated_at is None:
            self.updated_at = time.time()
        if self.metadata is None:
            self.metadata = {}


class StateMachineError(Exception):
    """Custom exception for state machine errors."""
    pass


class TransitionError(StateMachineError):
    """Exception raised for invalid state transitions."""
    pass


class HedgeStateMachine:
    """
    Production-ready state machine for hedge lifecycle management.
    Fixed to prevent invalid state transitions (e.g., CANCELED → RECONCILED).
    """

    def __init__(self):
        self._states: Dict[str, HedgeState] = {}
        self._contexts: Dict[str, HedgeContext] = {}
        self._transition_history: Dict[str, List[Dict[str, Any]]] = {}

    def initialize_hedge(self, context: HedgeContext) -> HedgeState:
        """
        Initialize a new hedge in PLANNED state.

        Args:
            context: Hedge context information

        Returns:
            Initial state (PLANNED)

        Raises:
            StateMachineError: If hedge already exists
        """
        if context.hedge_id in self._states:
            raise StateMachineError(f"Hedge {context.hedge_id} already exists")

        initial_state = HedgeState.PLANNED
        self._states[context.hedge_id] = initial_state
        self._contexts[context.hedge_id] = context
        self._transition_history[context.hedge_id] = []

        # Log initial state
        self._log_transition(context.hedge_id, None, initial_state, "hedge_initialized")

        logger.info(f"✅ Hedge {context.hedge_id} initialized in {initial_state.value} state")
        return initial_state

    def transition(self, hedge_id: str, new_state: HedgeState,
                  reason: str = "", metadata: Optional[Dict[str, Any]] = None) -> HedgeState:
        """
        Transition hedge to new state with validation.

        Args:
            hedge_id: Unique hedge identifier
            new_state: Target state
            reason: Reason for transition
            metadata: Additional transition metadata

        Returns:
            New state after successful transition

        Raises:
            TransitionError: If transition is invalid
            StateMachineError: If hedge doesn't exist or other errors
        """
        if hedge_id not in self._states:
            raise StateMachineError(f"Hedge {hedge_id} does not exist")

        current_state = self._states[hedge_id]

        # Validate transition
        if not self._is_valid_transition(current_state, new_state):
            raise TransitionError(
                f"Invalid transition: {current_state.value} → {new_state.value}. "
                f"Valid transitions from {current_state.value}: "
                f"{[s.value for s in VALID_TRANSITIONS[current_state]]}"
            )

        # Check for terminal states
        if self._is_terminal_state(current_state):
            raise StateMachineError(
                f"Cannot transition from terminal state {current_state.value}"
            )

        # Execute transition
        old_state = current_state
        self._states[hedge_id] = new_state

        # Update context timestamp
        if hedge_id in self._contexts:
            self._contexts[hedge_id].updated_at = time.time()

        # Log transition
        self._log_transition(hedge_id, old_state, new_state, reason, metadata)

        logger.info(f"🔄 Hedge {hedge_id}: {old_state.value} → {new_state.value} ({reason})")
        return new_state

    def get_state(self, hedge_id: str) -> Optional[HedgeState]:
        """Get current state of a hedge."""
        return self._states.get(hedge_id)

    def get_context(self, hedge_id: str) -> Optional[HedgeContext]:
        """Get context information for a hedge."""
        return self._contexts.get(hedge_id)

    def get_transition_history(self, hedge_id: str) -> List[Dict[str, Any]]:
        """Get transition history for a hedge."""
        return self._transition_history.get(hedge_id, [])

    def is_active(self, hedge_id: str) -> bool:
        """Check if hedge is in an active state."""
        state = self.get_state(hedge_id)
        if state is None:
            return False

        # Active states are non-terminal
        return not self._is_terminal_state(state)

    def is_terminal(self, hedge_id: str) -> bool:
        """Check if hedge is in a terminal state."""
        state = self.get_state(hedge_id)
        if state is None:
            return False

        return self._is_terminal_state(state)

    def get_active_hedges(self) -> List[str]:
        """Get list of active hedge IDs."""
        return [hedge_id for hedge_id, state in self._states.items()
                if not self._is_terminal_state(state)]

    def get_all_hedges(self) -> Dict[str, HedgeState]:
        """Get all hedge states."""
        return self._states.copy()

    def force_cancel(self, hedge_id: str, reason: str = "forced_cancel") -> bool:
        """
        Force cancel a hedge regardless of current state.
        Use with caution - bypasses normal validation.

        Args:
            hedge_id: Hedge to cancel
            reason: Reason for cancellation

        Returns:
            True if successfully canceled
        """
        if hedge_id not in self._states:
            logger.warning(f"Cannot force cancel non-existent hedge {hedge_id}")
            return False

        old_state = self._states[hedge_id]
        self._states[hedge_id] = HedgeState.CANCELED

        # Update context
        if hedge_id in self._contexts:
            self._contexts[hedge_id].updated_at = time.time()

        # Log forced cancellation
        self._log_transition(hedge_id, old_state, HedgeState.CANCELED,
                           f"FORCED_CANCEL: {reason}")

        logger.warning(f"⚠️ Hedge {hedge_id} force canceled: {old_state.value} → canceled ({reason})")
        return True

    def _is_valid_transition(self, from_state: HedgeState, to_state: HedgeState) -> bool:
        """Check if transition is valid."""
        return to_state in VALID_TRANSITIONS.get(from_state, [])

    def _is_terminal_state(self, state: HedgeState) -> bool:
        """Check if state is terminal (no further transitions allowed)."""
        return state not in VALID_TRANSITIONS

    def _log_transition(self, hedge_id: str, from_state: Optional[HedgeState],
                       to_state: HedgeState, reason: str,
                       metadata: Optional[Dict[str, Any]] = None):
        """Log state transition for audit trail."""
        transition_record = {
            'timestamp': time.time(),
            'from_state': from_state.value if from_state else None,
            'to_state': to_state.value,
            'reason': reason,
            'metadata': metadata or {}
        }

        if hedge_id not in self._transition_history:
            self._transition_history[hedge_id] = []

        self._transition_history[hedge_id].append(transition_record)

    def get_state_counts(self) -> Dict[str, int]:
        """Get count of hedges in each state for monitoring."""
        counts = {}
        for state in HedgeState:
            counts[state.value] = 0

        for state in self._states.values():
            counts[state.value] += 1

        return counts

    def validate_all_states(self) -> List[str]:
        """
        Validate all current hedge states for consistency.
        Returns list of validation errors.
        """
        errors = []

        for hedge_id, state in self._states.items():
            # Check for invalid states
            if state not in VALID_TRANSITIONS and state not in [
                HedgeState.CANCELED, HedgeState.CLOSED
            ]:
                errors.append(f"Hedge {hedge_id}: Invalid state {state.value}")

            # Check for missing context
            if hedge_id not in self._contexts:
                errors.append(f"Hedge {hedge_id}: Missing context information")

            # Check for missing transition history
            if hedge_id not in self._transition_history:
                errors.append(f"Hedge {hedge_id}: Missing transition history")

        return errors


# Global state machine instance
hedge_state_machine = HedgeStateMachine()
