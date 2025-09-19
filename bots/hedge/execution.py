"""
Hedge Execution Router for Drift Protocol

Handles execution of hedge orders through Drift Protocol instead of external exchanges.
Supports IOC and passive order types with sub-account management.
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal

from libs.drift.client import DriftpyClient, Order
from libs.drift.sub_account_manager import SubAccountManager

logger = logging.getLogger(__name__)

class DriftHedgeExecutor:
    """
    Executes hedge orders through Drift Protocol using specialized sub-accounts.

    Handles the routing and execution of hedge orders with proper sub-account
    management and risk controls.
    """

    def __init__(self, client: DriftpyClient):
        self.client = client
        self.sub_account_manager = SubAccountManager(client)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def initialize_hedge_account(self, config: Dict[str, Any]) -> bool:
        """
        Initialize or verify hedge sub-account exists.

        Args:
            config: Hedge configuration dictionary

        Returns:
            True if account is ready, False otherwise
        """
        try:
            sub_account_config = config.get("sub_account", {})
            account_name = sub_account_config.get("name", "hedge_account")
            market_index = sub_account_config.get("market_index", 0)
            create_if_missing = sub_account_config.get("create_if_missing", True)

            if create_if_missing:
                self.logger.info(f"🔧 Ensuring hedge sub-account exists: {account_name}")
                sub_account_info = await self.sub_account_manager.create_hedge_sub_account(
                    account_name=account_name,
                    market_index=market_index,
                    initial_collateral_usd=1000.0  # Default collateral
                )
                self.logger.info(f"✅ Hedge sub-account ready: {account_name}")
                return True
            else:
                # Just verify it exists
                account_info = self.sub_account_manager.get_sub_account_info(account_name)
                if account_info:
                    self.logger.info(f"✅ Hedge sub-account verified: {account_name}")
                    return True
                else:
                    self.logger.error(f"❌ Hedge sub-account not found: {account_name}")
                    return False

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize hedge account: {e}")
            return False

    async def execute_hedge_order(
        self,
        side: str,
        price: float,
        size_usd: float,
        order_type: str = "ioc",
        sub_account_name: str = "hedge_account"
    ) -> Optional[str]:
        """
        Execute a hedge order through Drift.

        Args:
            side: "buy" or "sell"
            price: Limit price for the order
            size_usd: Size in USD
            order_type: "ioc" or "passive"
            sub_account_name: Name of sub-account to use

        Returns:
            Order ID if successful, None if failed
        """
        try:
            # Switch to the specified sub-account
            success = await self.sub_account_manager.switch_to_sub_account(sub_account_name)
            if not success:
                self.logger.error(f"❌ Failed to switch to sub-account: {sub_account_name}")
                return None

            # Create the order
            order = Order(
                side=side,
                price=Decimal(str(price)),
                size_usd=Decimal(str(size_usd))
            )

            # Set order type parameters
            if order_type.lower() == "ioc":
                order.immediate_or_cancel = True
                order.post_only = False
            elif order_type.lower() == "passive":
                order.immediate_or_cancel = False
                order.post_only = True
            else:
                self.logger.warning(f"Unknown order type: {order_type}, defaulting to IOC")
                order.immediate_or_cancel = True
                order.post_only = False

            # Execute the order
            self.logger.info(f"📤 Executing {order_type.upper()} hedge order: {side} ${size_usd} at ${price}")
            order_id = await self.client.place_order(order)

            self.logger.info(f"✅ Hedge order executed: {order_id}")
            return str(order_id)

        except Exception as e:
            self.logger.error(f"❌ Failed to execute hedge order: {e}")
            return None

    async def execute_signal(self, signal: Dict[str, Any]) -> str:
        """
        Execute a hedge signal through Drift.

        Args:
            signal: Hedge signal dictionary containing order details

        Returns:
            Execution result string
        """
        try:
            # Extract signal parameters
            side = signal.get("side", "sell")  # Default to sell (hedge long)
            price = signal.get("price", 0.0)
            size_usd = signal.get("size_usd", 0.0)
            order_type = signal.get("order_type", "ioc")
            sub_account = signal.get("sub_account", "hedge_account")
            venues = signal.get("venues", ["drift"])

            if price <= 0 or size_usd <= 0:
                return "ERROR: Invalid price or size"

            # Execute the order
            order_id = await self.execute_hedge_order(
                side=side,
                price=price,
                size_usd=size_usd,
                order_type=order_type,
                sub_account_name=sub_account
            )

            if order_id:
                return f"DRIFT_{order_type.upper()}_EXECUTED:{order_id}"
            else:
                return f"DRIFT_{order_type.upper()}_FAILED"

        except Exception as e:
            self.logger.error(f"❌ Signal execution failed: {e}")
            return f"ERROR: {str(e)}"

    async def cancel_hedge_orders(self, sub_account_name: str = "hedge_account") -> bool:
        """
        Cancel all open hedge orders in the specified sub-account.

        Args:
            sub_account_name: Name of sub-account to cancel orders in

        Returns:
            True if successful, False otherwise
        """
        try:
            # Switch to the sub-account
            success = await self.sub_account_manager.switch_to_sub_account(sub_account_name)
            if not success:
                return False

            # Cancel all orders
            await self.client.cancel_all_orders()
            self.logger.info(f"✅ Cancelled all hedge orders in {sub_account_name}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to cancel hedge orders: {e}")
            return False

    def get_sub_account_info(self, account_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a hedge sub-account."""
        return self.sub_account_manager.get_sub_account_info(account_name)

    async def get_hedge_account_balance(self, account_name: str = "hedge_account") -> Optional[Decimal]:
        """Get the balance of the hedge sub-account."""
        return await self.sub_account_manager.get_sub_account_balance(account_name)


# Global executor instance (to be initialized)
_hedge_executor: Optional[DriftHedgeExecutor] = None

def get_hedge_executor(client: DriftpyClient) -> DriftHedgeExecutor:
    """Get or create the global hedge executor instance."""
    global _hedge_executor
    if _hedge_executor is None:
        _hedge_executor = DriftHedgeExecutor(client)
    return _hedge_executor

async def execute_hedge(signal: Dict[str, Any], client: Optional[DriftpyClient] = None) -> str:
    """
    Execute a hedge order through Drift Protocol.

    This is the main entry point for hedge execution. If no client is provided,
    it will attempt to use the global executor (which must be initialized first).

    Args:
        signal: Hedge signal dictionary
        client: Drift client (optional, will use global if not provided)

    Returns:
        Execution result string
    """
    global _hedge_executor

    try:
        if client:
            executor = DriftHedgeExecutor(client)
        elif _hedge_executor:
            executor = _hedge_executor
        else:
            return "ERROR: No Drift client available"

        return await executor.execute_signal(signal)

    except Exception as e:
        logger.error(f"❌ Hedge execution failed: {e}")
        return f"ERROR: {str(e)}"

def initialize_hedge_executor(client: DriftpyClient) -> None:
    """Initialize the global hedge executor with a Drift client."""
    global _hedge_executor
    _hedge_executor = DriftHedgeExecutor(client)
    logger.info("✅ Hedge executor initialized with Drift client")
