"""Hedge execution router.

Handles HedgeDecision execution by dispatching orders to appropriate venues.
Supports both IOC and passive execution modes.
"""
import logging
from bots.hedge.decide import HedgeDecision

logger = logging.getLogger(__name__)

def execute_hedge(decision: HedgeDecision, venues: list = None) -> str:
    """Execute a hedge decision by dispatching to appropriate venues.

    Args:
        decision: HedgeDecision containing action and quantity
        venues: List of venue strings (optional)

    Returns:
        Execution result string
    """
    if decision.action != "HEDGE":
        return f"SKIP: {decision.reason}"

    if venues is None:
        venues = ["DEX_DRIFT"]

    # Determine execution mode based on urgency
    urgency = 0.0
    if "urgency=" in decision.reason:
        try:
            urgency = float(decision.reason.split("=")[1])
        except (ValueError, IndexError):
            urgency = 0.0

    # High urgency = IOC, Low urgency = Passive
    ioc_mode = urgency > 1.0

    if ioc_mode:
        result = f"IOC_SENT: {','.join(venues)}"
    else:
        result = f"PASSIVE_SENT: {','.join(venues)}"

    logger.info(f"[EXECUTE] {result} - Qty: {decision.qty:.4f}, Urgency: {urgency:.2f}")
    return result
