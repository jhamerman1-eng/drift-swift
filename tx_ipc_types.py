from enum import Enum
from typing import Dict, List, Optional, Union, Any, TypedDict
from dataclasses import dataclass
import time


class WrappedIpcMessage(TypedDict):
    """Wrapper for IPC messages with type and data."""
    type: str
    data: 'IpcMessage'


class IpcMessageTypes(Enum):
    """Types of IPC messages for transaction processing."""
    COMMAND = 'command'
    NOTIFICATION = 'notification'
    NEW_SIGNER = 'new_signer'
    NEW_ADDRESS_LOOKUP_TABLE = 'new_address_lookup_table'
    TRANSACTION = 'transaction'
    CONFIRM_TRANSACTION = 'confirm_transaction'
    SET_TRANSACTIONS_ENABLED = 'set_transactions_enabled'
    METRICS = 'metrics'


# Type for serializable data (equivalent to TypeScript Serializable)
Serializable = Union[
    str, int, float, bool, None,
    List['Serializable'],
    Dict[str, 'Serializable']
]


class CommandMessage(TypedDict):
    """Command IPC message."""
    command: str


class NotificationMessage(TypedDict):
    """Notification IPC message."""
    message: str


class NewSignerMessage(TypedDict):
    """New signer registration message."""
    signerKey: str
    signerInfo: str


class NewAddressLookupTableMessage(TypedDict):
    """New address lookup table registration message."""
    address: str


class TransactionMessage(TypedDict):
    """Transaction IPC message with full transaction details."""
    ixsSerialized: List[Dict[str, Any]]  # serialized instructions
    ixs: List[Dict[str, Any]]  # deserialized instructions (simplified for Python)
    simOnRetry: bool  # true to simulate the tx before retrying
    simulateCUs: bool  # true to simulate the tx with CUs
    retryUntilConfirmed: bool  # retry with new blockhash until confirmed
    signerKeys: List[str]  # IDs of signers (must be registered first)
    addressLookupTables: List[str]  # pubkeys of address lookup tables
    newSigners: List[Dict[str, str]]  # new signers: [{key: string, info: string}]


class ConfirmTransactionMessage(TypedDict):
    """Transaction confirmation message."""
    confirmTxSig: str  # transaction signature to confirm
    newSigners: List[Dict[str, str]]  # new signers: [{key: string, info: string}]


class SetTransactionsEnabledMessage(TypedDict):
    """Enable/disable transactions message."""
    txEnabled: bool


class TxSenderMetrics(TypedDict):
    """Metrics for transaction sender performance tracking."""
    txLanded: int  # successfully confirmed transactions
    txAttempted: int  # total transactions attempted
    txDroppedTimeout: int  # dropped due to timeout
    txDroppedBlockhashExpired: int  # dropped due to expired blockhash
    txFailedSimulation: int  # failed simulation
    txRetried: int  # transactions retried
    lruEvictedTxs: int  # transactions evicted from LRU cache
    pendingQueueSize: int  # size of pending queue
    confirmQueueSize: int  # size of confirmation queue
    txConfirmRateLimited: int  # rate limited confirmations
    txEnabled: int  # transactions enabled (0 or 1)
    txConfirmedFromWs: int  # confirmed via websocket


# Union type for all IPC messages
IpcMessage = Union[
    CommandMessage,
    NotificationMessage,
    NewSignerMessage,
    NewAddressLookupTableMessage,
    TransactionMessage,
    ConfirmTransactionMessage,
    SetTransactionsEnabledMessage,
    TxSenderMetrics,
]


class TxState(Enum):
    """States for transactions in the processing pipeline."""
    QUEUED = 'queued'      # tx is queued and has not been sent yet
    RETRYING = 'retrying'  # tx has been sent at least once
    FAILED = 'failed'      # tx has failed (blockhash expired)
    LANDED = 'landed'      # tx has landed (confirmed)


@dataclass
class TransactionPayload:
    """Complete transaction payload with processing state."""
    instruction: TransactionMessage
    retries: Optional[int] = None
    blockhashUsed: Optional[str] = None
    blockhashExpiryHeight: Optional[int] = None
    lastSentTxSig: Optional[str] = None
    lastSentTx: Optional[Any] = None  # VersionedTransaction equivalent
    lastSentRawTx: Optional[bytes] = None
    lastSendTs: Optional[float] = None
    addressLookupTables: Optional[List[Any]] = None  # AddressLookupTableAccount equivalents


@dataclass
class AccountMeta:
    """Account metadata for transaction instructions."""
    pubkey: str
    isSigner: bool
    isWritable: bool


@dataclass
class TransactionInstruction:
    """Solana transaction instruction."""
    keys: List[AccountMeta]
    programId: str
    data: bytes


def deserialize_ix(ix: Dict[str, Any]) -> TransactionInstruction:
    """
    Deserialize a transaction instruction from dictionary format.

    Args:
        ix: Dictionary containing serialized instruction data

    Returns:
        TransactionInstruction: Deserialized instruction
    """
    keys = ix.get('keys', [])
    account_metas = []

    if keys:
        for key_data in keys:
            account_metas.append(AccountMeta(
                pubkey=key_data['pubkey'],
                isSigner=key_data['isSigner'],
                isWritable=key_data['isWritable']
            ))

    return TransactionInstruction(
        keys=account_metas,
        programId=ix['programId'],
        data=bytes.fromhex(ix['data']) if isinstance(ix['data'], str) else bytes(ix['data'])
    )


class IpcMessageFactory:
    """Factory for creating IPC messages."""

    @staticmethod
    def create_command(command: str) -> WrappedIpcMessage:
        """Create a command message."""
        return {
            'type': IpcMessageTypes.COMMAND.value,
            'data': {'command': command}
        }

    @staticmethod
    def create_notification(message: str) -> WrappedIpcMessage:
        """Create a notification message."""
        return {
            'type': IpcMessageTypes.NOTIFICATION.value,
            'data': {'message': message}
        }

    @staticmethod
    def create_new_signer(signer_key: str, signer_info: str) -> WrappedIpcMessage:
        """Create a new signer message."""
        return {
            'type': IpcMessageTypes.NEW_SIGNER.value,
            'data': {'signerKey': signer_key, 'signerInfo': signer_info}
        }

    @staticmethod
    def create_transaction(
        ixs_serialized: List[Dict[str, Any]],
        ixs: List[Dict[str, Any]],
        sim_on_retry: bool = False,
        simulate_cus: bool = False,
        retry_until_confirmed: bool = False,
        signer_keys: Optional[List[str]] = None,
        address_lookup_tables: Optional[List[str]] = None,
        new_signers: Optional[List[Dict[str, str]]] = None
    ) -> WrappedIpcMessage:
        """Create a transaction message."""
        return {
            'type': IpcMessageTypes.TRANSACTION.value,
            'data': {
                'ixsSerialized': ixs_serialized,
                'ixs': ixs,
                'simOnRetry': sim_on_retry,
                'simulateCUs': simulate_cus,
                'retryUntilConfirmed': retry_until_confirmed,
                'signerKeys': signer_keys or [],
                'addressLookupTables': address_lookup_tables or [],
                'newSigners': new_signers or []
            }
        }

    @staticmethod
    def create_metrics(metrics: TxSenderMetrics) -> WrappedIpcMessage:
        """Create a metrics message."""
        return {
            'type': IpcMessageTypes.METRICS.value,
            'data': metrics
        }


# Example usage and type checking
if __name__ == "__main__":
    # Create a sample transaction message
    tx_msg = IpcMessageFactory.create_transaction(
        ixs_serialized=[{"programId": "11111111111111111111111111111112", "keys": [], "data": "00"}],
        ixs=[{"programId": "11111111111111111111111111111112", "keys": [], "data": "00"}],
        sim_on_retry=True,
        retry_until_confirmed=True
    )

    print("Sample IPC Message:")
    print(f"Type: {tx_msg['type']}")
    print(f"Data keys: {list(tx_msg['data'].keys())}")

    # Create metrics message
    metrics: TxSenderMetrics = {
        'txLanded': 100,
        'txAttempted': 120,
        'txDroppedTimeout': 5,
        'txDroppedBlockhashExpired': 3,
        'txFailedSimulation': 2,
        'txRetried': 10,
        'lruEvictedTxs': 1,
        'pendingQueueSize': 5,
        'confirmQueueSize': 3,
        'txConfirmRateLimited': 0,
        'txEnabled': 1,
        'txConfirmedFromWs': 95
    }

    metrics_msg = IpcMessageFactory.create_metrics(metrics)
    print(f"\nMetrics message type: {metrics_msg['type']}")
    print(f"Transactions landed: {metrics_msg['data']['txLanded']}")

