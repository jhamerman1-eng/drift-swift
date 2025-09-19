"""
Transaction Sender - Python implementation of high-throughput Solana transaction processing engine.

This module provides a comprehensive transaction sender that handles:
- Transaction queuing and processing
- Retry logic with configurable intervals
- Transaction confirmation via websockets and polling
- Blockhash management and expiry handling
- Address lookup table support
- Comprehensive metrics and monitoring
- Multiple RPC connection support
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import base64

# Placeholder imports - would need actual implementations
# from solana.rpc.async_api import AsyncClient
# from solana.transaction import Transaction, VersionedTransaction
# from solana.system_program import PublicKey
# from solana.rpc.commitment import Commitment, Confirmed
# from driftpy.drift_client import DriftClient
# from driftpy.subscribers import BlockhashSubscriber, SlotSubscriber

from tx_ipc_types import (
    TransactionMessage,
    TxSenderMetrics,
    TransactionPayload,
    TransactionInstruction,
    deserialize_ix
)

logger = logging.getLogger(__name__)

CONFIRM_TX_INTERVAL_MS = 15_000
CONFIRM_TX_RATE_LIMIT_BACKOFF_MS = 5_000
TX_CONFIRMATION_BATCH_SIZE = 50
TX_TIMEOUT_THRESHOLD_MS = 1000 * 60 * 10  # 10 minutes
LOG_PREFIX = '[TxSender]'


class Commitment(Enum):
    """Transaction commitment levels."""
    PROCESSED = "processed"
    CONFIRMED = "confirmed"
    FINALIZED = "finalized"


@dataclass
class ConfirmOptions:
    """Options for transaction confirmation."""
    commitment: Commitment = Commitment.CONFIRMED
    max_retries: int = 0
    skip_preflight: bool = True


@dataclass
class TxSenderConfig:
    """Configuration for TxSender."""
    connection: Any  # AsyncClient placeholder
    blockhash_subscriber: Any  # BlockhashSubscriber placeholder
    slot_subscriber: Any  # SlotSubscriber placeholder
    resend_interval: int = 2000
    send_tx_enabled: bool = False


@dataclass
class PendingTxInfo:
    """Information about a pending transaction."""
    ts: float
    slot: int
    sim_slot: Optional[int] = None


@dataclass
class SimulateAndGetTxWithCUsResponse:
    """Response from transaction simulation with CU estimation."""
    tx: Any  # VersionedTransaction placeholder
    sim_error: Optional[Dict[str, Any]] = None
    sim_tx_logs: Optional[List[str]] = None
    cu_estimate: Optional[int] = None
    sim_slot: Optional[int] = None


class TxSender:
    """
    High-throughput transaction sender for Solana.

    Features:
    - Transaction queuing and processing with retry logic
    - WebSocket-based transaction confirmation
    - Batch confirmation polling with rate limiting
    - Blockhash expiry handling and renewal
    - Address lookup table caching
    - Comprehensive metrics collection
    - Multiple RPC connection support
    - LRU cache for pending transaction tracking
    """

    def __init__(self, config: TxSenderConfig):
        self.connection = config.connection
        self.tx_confirmation_connection = None  # Would be AsyncClient("https://api.mainnet-beta.solana.com")
        self.blockhash_subscriber = config.blockhash_subscriber
        self.slot_subscriber = config.slot_subscriber
        self.resend_interval = config.resend_interval
        self.additional_send_tx_connections: List[Any] = []  # Additional AsyncClient connections

        self.send_tx_opts = ConfirmOptions()
        self.running = False
        self.send_tx_enabled = config.send_tx_enabled

        # Transaction processing
        self.tx_to_send_payload: List[TransactionPayload] = []
        self.pending_tx_sigs_to_confirm: Dict[str, PendingTxInfo] = {}

        # Control flags
        self.confirm_loop_running = False
        self.last_confirm_loop_run_ts = time.time() * 1000 - CONFIRM_TX_RATE_LIMIT_BACKOFF_MS

        # Background tasks
        self.confirm_task: Optional[asyncio.Task] = None
        self.sender_task: Optional[asyncio.Task] = None

        # Signers and lookup tables
        self.signers: Dict[str, Any] = {}  # signer_key -> wallet
        self.address_lookup_tables: Dict[str, Any] = {}  # address -> lookup_table

        # Metrics
        self.metrics = TxSenderMetrics(
            txEnabled=1 if self.send_tx_enabled else 0,
            txLanded=0,
            txAttempted=0,
            txDroppedTimeout=0,
            txDroppedBlockhashExpired=0,
            txFailedSimulation=0,
            pendingQueueSize=0,
            lruEvictedTxs=0,
            confirmQueueSize=0,
            txRetried=0,
            txConfirmRateLimited=0,
            txConfirmedFromWs=0
        )

        logger.info(
            f"{LOG_PREFIX} TxSender initialized, send_tx_enabled: {self.send_tx_enabled}"
        )

    def set_transactions_enabled(self, state: bool) -> None:
        """Enable or disable transaction sending."""
        self.send_tx_enabled = state
        logger.info(f"{LOG_PREFIX} Transaction sending {'enabled' if state else 'disabled'}")

    async def subscribe(self) -> None:
        """Initialize and start the transaction sender."""
        # Wait for blockhash subscriber to be ready
        blockhash = None
        while not blockhash:
            logger.info(f"{LOG_PREFIX} Waiting for blockhash subscriber to update...")
            await asyncio.sleep(1)
            # blockhash = self.blockhash_subscriber.getLatestBlockhash(5)

        self.running = True

        # Start background tasks
        self.sender_task = asyncio.create_task(self._start_tx_sender_loop())
        self.confirm_task = asyncio.create_task(self._confirm_pending_tx_sigs_loop())

        logger.info(f"{LOG_PREFIX} TxSender subscribed and running")

    async def unsubscribe(self) -> None:
        """Stop the transaction sender and cleanup."""
        logger.info(f"{LOG_PREFIX} Unsubscribing TxSender...")
        self.running = False

        # Cancel background tasks
        if self.sender_task:
            self.sender_task.cancel()
            try:
                await self.sender_task
            except asyncio.CancelledError:
                pass

        if self.confirm_task:
            self.confirm_task.cancel()
            try:
                await self.confirm_task
            except asyncio.CancelledError:
                pass

        logger.info(f"{LOG_PREFIX} TxSender unsubscribed")

    def get_metrics(self) -> TxSenderMetrics:
        """Get current metrics."""
        self.metrics.confirmQueueSize = len(self.pending_tx_sigs_to_confirm)
        self.metrics.pendingQueueSize = len(self.tx_to_send_payload)
        self.metrics.txEnabled = 1 if self.send_tx_enabled else 0
        return self.metrics

    async def _listen_to_tx_logs(self, account_pubkey: str) -> None:
        """
        Listen to transaction logs for a specific account.

        This would typically use websockets to listen for transaction confirmations.
        """
        # Placeholder - would implement websocket log listening
        logger.info(f"{LOG_PREFIX} Listening to tx logs for {account_pubkey}")
        # In real implementation:
        # async for log in self.connection.logs_subscribe(account_pubkey, commitment="confirmed"):
        #     await self._handle_tx_log(log)

    async def _handle_tx_log(self, log: Dict[str, Any]) -> None:
        """Handle a transaction log from websocket."""
        # Skip simulation results
        if log.get('signature') == '1111111111111111111111111111111111111111111111111111111111111111':
            return

        signature = log.get('signature')
        if signature in self.pending_tx_sigs_to_confirm:
            # Remove from pending
            tx_info = self.pending_tx_sigs_to_confirm.pop(signature)

            # Update metrics
            self.metrics.txConfirmedFromWs += 1
            self.metrics.txLanded += 1

            # Calculate timing
            confirmed_age = time.time() * 1000 - tx_info.ts
            current_slot = self.slot_subscriber.get_slot() if self.slot_subscriber else 0
            slot_age = current_slot - tx_info.slot

            logger.info(
                f"{LOG_PREFIX} Tx confirmed from ws: {signature} "
                f"({confirmed_age:.0f}ms elapsed, slots elapsed: {slot_age}, "
                f"current slot: {current_slot}, txSlot: {tx_info.slot}, "
                f"txSimSlot: {tx_info.sim_slot})"
            )

    async def _confirm_pending_tx_sigs_loop(self) -> None:
        """Background loop for confirming pending transactions."""
        while self.running:
            try:
                await self._confirm_pending_tx_sigs()
                await asyncio.sleep(CONFIRM_TX_INTERVAL_MS / 1000)
            except Exception as e:
                logger.error(f"{LOG_PREFIX} Error in confirm loop: {e}")
                await asyncio.sleep(5)

    async def _confirm_pending_tx_sigs(self) -> None:
        """Confirm pending transactions via batch RPC calls."""
        current_time = time.time() * 1000
        next_time_can_run = self.last_confirm_loop_run_ts + CONFIRM_TX_RATE_LIMIT_BACKOFF_MS

        if current_time < next_time_can_run:
            logger.warning(
                f"Skipping confirm loop due to rate limit, next run in "
                f"{next_time_can_run - current_time:.0f} ms"
            )
            self.metrics.txConfirmRateLimited += 1
            return

        if self.confirm_loop_running:
            return

        self.confirm_loop_running = True
        if not self.running:
            return

        try:
            # Get all pending transactions
            tx_entries = list(self.pending_tx_sigs_to_confirm.items())

            # Process in batches
            for i in range(0, len(tx_entries), TX_CONFIRMATION_BATCH_SIZE):
                batch = tx_entries[i:i + TX_CONFIRMATION_BATCH_SIZE]
                tx_sigs = [sig for sig, _ in batch]

                # Get transaction details (placeholder)
                # txs = await self.tx_confirmation_connection.get_transactions(
                #     tx_sigs, commitment="confirmed", max_supported_transaction_version=0
                # )

                # For now, simulate getting transactions
                txs = [None] * len(tx_sigs)  # Placeholder

                for j, tx_resp in enumerate(txs):
                    tx_sig, tx_info = batch[j]
                    current_time = time.time() * 1000
                    tx_age = tx_info.ts - current_time

                    # Skip if already processed
                    if tx_sig not in self.pending_tx_sigs_to_confirm:
                        continue

                    if tx_resp is None:
                        # Check for timeout
                        if abs(tx_age) > TX_TIMEOUT_THRESHOLD_MS:
                            logger.info(
                                f"{LOG_PREFIX} Tx not found after {tx_age / 1000:.1f}s, "
                                f"untracking: {tx_sig}"
                            )
                            self.pending_tx_sigs_to_confirm.pop(tx_sig, None)
                            self.metrics.txDroppedTimeout += 1
                    else:
                        # Transaction confirmed
                        confirmed_age = tx_info.ts / 1000 - (tx_resp.get('blockTime', current_time / 1000))
                        logger.info(
                            f"{LOG_PREFIX} Tx landed: {tx_sig}, confirmed tx age: {confirmed_age:.1f}s, "
                            f"slot: {tx_resp.get('slot', 'unknown')}"
                        )
                        self.pending_tx_sigs_to_confirm.pop(tx_sig, None)
                        self.metrics.txLanded += 1

                    await asyncio.sleep(0.5)  # Rate limiting

        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg:
                logger.info(f"{LOG_PREFIX} Confirming tx loop rate limited: {error_msg}")
                self.last_confirm_loop_run_ts = time.time() * 1000 + CONFIRM_TX_RATE_LIMIT_BACKOFF_MS
            else:
                logger.error(f"{LOG_PREFIX} Other error confirming tx sigs: {error_msg}")
        finally:
            self.confirm_loop_running = False

    async def add_tx_payload(self, tx_payload: TransactionMessage) -> None:
        """Add a transaction payload to the processing queue."""
        # Resolve address lookup tables
        address_lookup_tables = []
        for lut_address in tx_payload.get('addressLookupTables', []):
            lookup_table = await self._must_get_address_lookup_table(lut_address)
            address_lookup_tables.append(lookup_table)

        payload = TransactionPayload(
            instruction=tx_payload,
            addressLookupTables=address_lookup_tables
        )

        self.tx_to_send_payload.append(payload)

    async def add_tx_to_confirm(self, tx_payload: Dict[str, Any]) -> None:
        """Add a transaction to the confirmation tracking."""
        confirm_tx_sig = tx_payload.get('confirmTxSig')
        if confirm_tx_sig:
            slot = self.slot_subscriber.get_slot() if self.slot_subscriber else 0
            self.pending_tx_sigs_to_confirm[confirm_tx_sig] = PendingTxInfo(
                ts=time.time() * 1000,
                slot=slot
            )
            self.metrics.txAttempted += 1

    def add_signer(self, signer_key: str, signer_info: str) -> None:
        """Add a signer for transaction signing."""
        # Placeholder - would load keypair from signer_info
        # keypair = load_keypair(signer_info)
        # wallet = AnchorWallet(keypair)

        logger.info(
            f"{LOG_PREFIX} Adding new signer: {signer_key}: "
            f"info: {signer_info[:10]}... ({len(signer_info)} len)"
        )

        # Store signer (placeholder)
        self.signers[signer_key] = signer_info

        # Start listening to logs for this signer (placeholder)
        # if keypair:
        #     asyncio.create_task(self._listen_to_tx_logs(keypair.public_key))

    async def add_address_lookup_table(self, address: str) -> None:
        """Add an address lookup table."""
        if address not in self.address_lookup_tables:
            logger.info(f"{LOG_PREFIX} Adding new address lookup table: {address}")

            # Fetch address lookup table (placeholder)
            # resp = await self.connection.get_address_lookup_table(PublicKey(address))
            # if resp.value:
            #     self.address_lookup_tables[address] = resp.value

            # Placeholder storage
            self.address_lookup_tables[address] = f"lookup_table_{address}"

    async def _must_get_address_lookup_table(self, address: str) -> Any:
        """Get an address lookup table, fetching it if necessary."""
        if address not in self.address_lookup_tables:
            logger.error(
                f"{LOG_PREFIX} Address lookup table not found for {address}, adding it..."
            )
            await self.add_address_lookup_table(address)

        return self.address_lookup_tables.get(address)

    async def _build_transaction_to_send(
        self,
        ixs: List[TransactionInstruction],
        lookup_table_accounts: Optional[List[Any]],
        payer_public_key: str,
        simulate_for_cus: bool = True
    ) -> Tuple[SimulateAndGetTxWithCUsResponse, Dict[str, Any]]:
        """Build a transaction for sending with simulation."""
        # Get latest blockhash (placeholder)
        # blockhash = self.blockhash_subscriber.getLatestBlockhash(5)

        # Simulate transaction (placeholder)
        sim_result = SimulateAndGetTxWithCUsResponse(
            tx="versioned_transaction_placeholder",
            sim_error=None,
            sim_tx_logs=[],
            cu_estimate=50000,
            sim_slot=12345
        )

        blockhash = {
            'blockhash': 'blockhash_placeholder',
            'lastValidBlockHeight': 100000
        }

        return sim_result, blockhash

    async def _send_versioned_transaction(
        self,
        tx: Any,
        signers: List[Any],
        opts: Optional[ConfirmOptions] = None
    ) -> Tuple[bytes, str]:
        """Send a versioned transaction and return raw tx and signature."""
        # Sign transaction (placeholder)
        # tx.sign(signers)
        # tx_raw = tx.serialize()

        # Send transaction (placeholder)
        await self._send_raw_transaction(b"tx_raw_placeholder", opts)

        # Generate signature (placeholder)
        tx_sig = "signature_placeholder"

        return b"tx_raw_placeholder", tx_sig

    async def _send_to_additional_connections(
        self,
        raw_tx: bytes,
        opts: Optional[ConfirmOptions] = None
    ) -> None:
        """Send transaction to additional RPC connections."""
        for connection in self.additional_send_tx_connections:
            try:
                # await connection.send_raw_transaction(raw_tx, opts)
                pass
            except Exception as e:
                logger.error(f"{LOG_PREFIX} Error sending to additional connection: {e}")

    async def _send_raw_transaction(
        self,
        raw_transaction: bytes,
        opts: Optional[ConfirmOptions] = None
    ) -> None:
        """Send raw transaction to primary connection."""
        # await self.connection.send_raw_transaction(raw_transaction, opts)
        await self._send_to_additional_connections(raw_transaction, opts)

    async def _run_tx_sender_loop(self) -> None:
        """Main transaction processing loop."""
        work = None
        if self.tx_to_send_payload:
            work = self.tx_to_send_payload.pop(0)

        if not work:
            return

        current_time = time.time() * 1000

        # 1) Handle expired transactions
        tx_expired = False
        if work.blockhashExpiryHeight:
            # block_height = self.blockhash_subscriber.getLatestBlockHeight()
            block_height = 100000  # Placeholder
            if block_height > work.blockhashExpiryHeight:
                logger.info(
                    f"{LOG_PREFIX} Blockhash expired for tx: {work.lastSentTxSig}, "
                    f"retrying: {work.instruction.get('retryUntilConfirmed', False)}"
                )
                if work.instruction.get('retryUntilConfirmed', False):
                    tx_expired = True
                else:
                    if work.lastSentTxSig:
                        self.pending_tx_sigs_to_confirm.pop(work.lastSentTxSig, None)
                    self.metrics.txDroppedBlockhashExpired += 1
                    return

        # Check retry timing
        tx_ready_to_retry = current_time > (work.lastSendTs or 0) + self.resend_interval
        first_time_sending_tx = work.lastSendTs is None
        tx_previously_sent = work.lastSentRawTx is not None

        # 2) Check if transaction has been confirmed
        if not first_time_sending_tx and work.lastSentTxSig:
            if work.lastSentTxSig not in self.pending_tx_sigs_to_confirm:
                return

        # 3) Send transaction if first time or ready to retry
        if tx_expired or first_time_sending_tx:
            # Get signers
            signers = []
            for signer_key in work.instruction.get('signerKeys', []):
                signer = self.signers.get(signer_key)
                if not signer:
                    raise ValueError(f"{LOG_PREFIX} Signer not found for {signer_key}")
                signers.append(signer)

            if not signers:
                raise ValueError(f"{LOG_PREFIX} No signers found for tx")

            # Build transaction
            sim_result, blockhash = await self._build_transaction_to_send(
                work.instruction.get('ixs', []),
                work.addressLookupTables,
                "payer_public_key_placeholder",  # signers[0].public_key
                work.instruction.get('simulateCUs', True)
            )

            if sim_result.sim_error is None:
                work.lastSendTs = current_time

                if self.send_tx_enabled:
                    # Send transaction
                    tx_raw, tx_sig = await self._send_versioned_transaction(
                        sim_result.tx,
                        signers,  # signers would be signer objects
                        self.send_tx_opts
                    )

                    work.lastSentTxSig = tx_sig
                    work.lastSentTx = sim_result.tx
                    work.lastSentRawTx = tx_raw
                    work.blockhashExpiryHeight = blockhash['lastValidBlockHeight']
                    work.blockhashUsed = blockhash['blockhash']

                    # Track for confirmation
                    slot = self.slot_subscriber.get_slot() if self.slot_subscriber else 0
                    self.pending_tx_sigs_to_confirm[tx_sig] = PendingTxInfo(
                        ts=current_time,
                        slot=slot,
                        sim_slot=sim_result.sim_slot
                    )

                    # Re-queue for potential retry
                    self.tx_to_send_payload.append(work)
                else:
                    logger.info(
                        f"{LOG_PREFIX} sendTxEnabled=false, cuEst: {sim_result.cu_estimate} "
                        f"simError: {sim_result.sim_error}, sim tx logs: {sim_result.sim_tx_logs}"
                    )

                self.metrics.txAttempted += 1
            else:
                self.metrics.txFailedSimulation += 1
                logger.error(
                    f"{LOG_PREFIX} TxSimulationFailed: {sim_result.sim_error}: "
                    f"simLogs: {sim_result.sim_tx_logs}"
                )

        elif tx_previously_sent and tx_ready_to_retry:
            # Retry existing transaction
            if (work.instruction.get('simOnRetry', False) and work.lastSentTx):
                # Re-simulate before retry (placeholder)
                # sim_resp = await self.connection.simulateTransaction(work.lastSentTx, ...)
                sim_error = None  # Placeholder

                if sim_error is not None:
                    logger.error(f"{LOG_PREFIX} TxSimulationFailed on retry: {sim_error}")
                    self.metrics.txFailedSimulation += 1
                    return

            if self.send_tx_enabled and work.lastSentRawTx:
                await self._send_raw_transaction(work.lastSentRawTx, self.send_tx_opts)
                work.lastSendTs = current_time
                self.tx_to_send_payload.append(work)
                self.metrics.txRetried += 1
            else:
                logger.info(
                    f"{LOG_PREFIX} sendTxEnabled=false, skipping retry {work.lastSentTxSig}"
                )
        else:
            # Not ready to retry, re-queue
            self.tx_to_send_payload.append(work)

    async def _start_tx_sender_loop(self) -> None:
        """Main sender loop."""
        logger.info(f"{LOG_PREFIX} TxSender started")

        while self.running:
            try:
                await self._run_tx_sender_loop()
            except Exception as e:
                logger.error(f"{LOG_PREFIX} Error in txSenderLoop: {e}")

            # Allow event loop to run
            await asyncio.sleep(0.01)

        logger.info(f"{LOG_PREFIX} TxSender stopped")


# Example usage and testing
async def example_usage():
    """Example of how to use the TxSender."""
    # This would need actual implementations of the placeholder classes
    logger.info("TxSender example - would need actual Drift SDK implementations")

    # Example configuration (placeholders)
    config = TxSenderConfig(
        connection=None,  # AsyncClient(...)
        blockhash_subscriber=None,  # BlockhashSubscriber(...)
        slot_subscriber=None,  # SlotSubscriber(...)
        resend_interval=2000,
        send_tx_enabled=False
    )

    # tx_sender = TxSender(config)
    # await tx_sender.subscribe()

    # Add a transaction (example)
    # tx_payload = IpcMessageFactory.create_transaction(...)
    # await tx_sender.add_tx_payload(tx_payload)

    # Get metrics
    # metrics = tx_sender.get_metrics()

    # await tx_sender.unsubscribe()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(example_usage())

