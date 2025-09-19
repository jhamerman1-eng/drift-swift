"""
Drift Sub-Account Manager

Utilities for creating and managing Drift sub-accounts for specialized trading strategies.
Provides functionality for hedge accounts, MM accounts, and other specialized use cases.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal

from .client import DriftpyClient
from driftpy.types import UserAccount

logger = logging.getLogger(__name__)

class SubAccountManager:
    """
    Manages Drift sub-accounts for specialized trading strategies.

    Handles creation, initialization, and management of sub-accounts
    for hedging, market making, and other specialized use cases.
    """

    def __init__(self, client: DriftpyClient):
        self.client = client
        self.sub_accounts: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def create_hedge_sub_account(
        self,
        account_name: str = "hedge_account",
        market_index: int = 0,
        initial_collateral_usd: float = 1000.0
    ) -> Dict[str, Any]:
        """
        Create a specialized sub-account for hedging operations.

        Args:
            account_name: Name identifier for the sub-account
            market_index: Primary market index for hedging
            initial_collateral_usd: Initial collateral to deposit

        Returns:
            Dictionary containing sub-account information
        """
        try:
            self.logger.info(f"🔧 Creating hedge sub-account: {account_name}")

            # Check if account already exists
            existing_accounts = await self.get_user_accounts()
            for account in existing_accounts:
                if hasattr(account, 'name') and account.name == account_name:
                    self.logger.info(f"✅ Sub-account {account_name} already exists")
                    sub_account_info = {
                        "name": account_name,
                        "account": account,
                        "pubkey": account.pubkey,
                        "market_index": market_index,
                        "status": "existing"
                    }
                    self.sub_accounts[account_name] = sub_account_info
                    return sub_account_info

            # Create new sub-account
            new_account = await self.client.create_sub_account(
                name=account_name,
                market_index=market_index
            )

            # Deposit initial collateral if specified
            if initial_collateral_usd > 0:
                await self._deposit_initial_collateral(
                    new_account, initial_collateral_usd
                )

            sub_account_info = {
                "name": account_name,
                "account": new_account,
                "pubkey": new_account.pubkey,
                "market_index": market_index,
                "status": "created",
                "initial_collateral": initial_collateral_usd
            }

            self.sub_accounts[account_name] = sub_account_info
            self.logger.info(f"✅ Created hedge sub-account: {account_name}")
            return sub_account_info

        except Exception as e:
            self.logger.error(f"❌ Failed to create hedge sub-account: {e}")
            raise

    async def get_or_create_sub_account(
        self,
        account_name: str,
        account_type: str = "hedge",
        market_index: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get existing sub-account or create new one.

        Args:
            account_name: Name identifier for the sub-account
            account_type: Type of sub-account (hedge, mm, etc.)
            market_index: Primary market index
            **kwargs: Additional parameters for account creation

        Returns:
            Dictionary containing sub-account information
        """
        if account_name in self.sub_accounts:
            return self.sub_accounts[account_name]

        if account_type == "hedge":
            return await self.create_hedge_sub_account(
                account_name=account_name,
                market_index=market_index,
                **kwargs
            )
        else:
            raise ValueError(f"Unsupported account type: {account_type}")

    async def get_user_accounts(self) -> List[UserAccount]:
        """Get all user accounts for the current user."""
        try:
            accounts = await self.client.get_user_accounts()
            return accounts
        except Exception as e:
            self.logger.error(f"❌ Failed to get user accounts: {e}")
            return []

    async def switch_to_sub_account(self, account_name: str) -> bool:
        """
        Switch the client to use a specific sub-account.

        Args:
            account_name: Name of the sub-account to switch to

        Returns:
            True if switch successful, False otherwise
        """
        try:
            if account_name not in self.sub_accounts:
                self.logger.error(f"❌ Sub-account {account_name} not found")
                return False

            sub_account = self.sub_accounts[account_name]
            await self.client.switch_sub_account(sub_account["account"])
            self.logger.info(f"✅ Switched to sub-account: {account_name}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to switch to sub-account {account_name}: {e}")
            return False

    async def get_sub_account_balance(self, account_name: str) -> Optional[Decimal]:
        """Get the balance of a specific sub-account."""
        try:
            if account_name not in self.sub_accounts:
                return None

            sub_account = self.sub_accounts[account_name]
            balance = await self.client.get_account_balance(sub_account["account"])
            return Decimal(str(balance))

        except Exception as e:
            self.logger.error(f"❌ Failed to get balance for {account_name}: {e}")
            return None

    async def transfer_between_accounts(
        self,
        from_account: str,
        to_account: str,
        amount_usd: float
    ) -> bool:
        """
        Transfer funds between sub-accounts.

        Args:
            from_account: Source account name
            to_account: Destination account name
            amount_usd: Amount to transfer in USD

        Returns:
            True if transfer successful, False otherwise
        """
        try:
            if from_account not in self.sub_accounts or to_account not in self.sub_accounts:
                self.logger.error("❌ One or both accounts not found")
                return False

            from_sub = self.sub_accounts[from_account]
            to_sub = self.sub_accounts[to_account]

            await self.client.transfer_between_accounts(
                from_sub["account"],
                to_sub["account"],
                amount_usd
            )

            self.logger.info(f"✅ Transferred ${amount_usd} from {from_account} to {to_account}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to transfer between accounts: {e}")
            return False

    async def _deposit_initial_collateral(
        self,
        account: UserAccount,
        amount_usd: float
    ) -> None:
        """Deposit initial collateral into a new sub-account."""
        try:
            # Switch to the new account
            await self.client.switch_sub_account(account)

            # Deposit collateral (assuming USDC)
            await self.client.deposit_collateral(amount_usd)

            self.logger.info(f"✅ Deposited ${amount_usd} initial collateral")

        except Exception as e:
            self.logger.error(f"❌ Failed to deposit initial collateral: {e}")
            raise

    def get_sub_account_info(self, account_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific sub-account."""
        return self.sub_accounts.get(account_name)

    def list_sub_accounts(self) -> Dict[str, Dict[str, Any]]:
        """List all managed sub-accounts."""
        return self.sub_accounts.copy()

    async def cleanup_sub_accounts(self) -> None:
        """Clean up and close all managed sub-accounts."""
        for account_name, account_info in self.sub_accounts.items():
            try:
                self.logger.info(f"🧹 Cleaning up sub-account: {account_name}")
                # Close account if needed
                # await self.client.close_sub_account(account_info["account"])
            except Exception as e:
                self.logger.error(f"❌ Failed to cleanup {account_name}: {e}")

        self.sub_accounts.clear()
        self.logger.info("✅ All sub-accounts cleaned up")


# Convenience functions
async def create_hedge_sub_account(
    client: DriftpyClient,
    account_name: str = "hedge_account",
    market_index: int = 0,
    initial_collateral_usd: float = 1000.0
) -> Dict[str, Any]:
    """
    Convenience function to create a hedge sub-account.

    Args:
        client: Drift client instance
        account_name: Name for the hedge account
        market_index: Primary market index
        initial_collateral_usd: Initial collateral amount

    Returns:
        Dictionary containing sub-account information
    """
    manager = SubAccountManager(client)
    return await manager.create_hedge_sub_account(
        account_name=account_name,
        market_index=market_index,
        initial_collateral_usd=initial_collateral_usd
    )


def get_sub_account_manager(client: DriftpyClient) -> SubAccountManager:
    """Get a SubAccountManager instance for the given client."""
    return SubAccountManager(client)
