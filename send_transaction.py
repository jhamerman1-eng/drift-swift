#!/usr/bin/env python3
"""
Send Transaction to Solana Devnet
Replace the encoded_transaction variable with your base64-encoded transaction
"""

from solana.rpc.api import Client
import base64

# Solana devnet RPC endpoint
RPC_URL = "https://thrumming-omniscient-moon.solana-devnet.quiknode.pro/ea7a129663c942e13ce1c9b414c3a8da9ab7d1d9/"

def send_transaction(encoded_transaction: str):
    """
    Send a transaction to Solana devnet

    Args:
        encoded_transaction: Base64-encoded transaction string
    """
    try:
        # Initialize client
        solana_client = Client(RPC_URL)

        # Send transaction
        response = solana_client.send_transaction(
            tx_sig=encoded_transaction,
            opts={"skip_preflight": False, "preflight_commitment": "confirmed"}
        )

        print(f"✅ Transaction sent successfully!")
        print(f"Transaction Signature: {response}")

        return response

    except Exception as e:
        print(f"❌ Error sending transaction: {e}")
        return None

if __name__ == "__main__":
    # Example usage - replace with your actual encoded transaction
    encoded_transaction = "ENTER_ENCODED_TRANSACTION_ID"

    if encoded_transaction != "ENTER_ENCODED_TRANSACTION_ID":
        send_transaction(encoded_transaction)
    else:
        print("Please replace 'ENTER_ENCODED_TRANSACTION_ID' with your actual base64-encoded transaction")
        print("\nExample format:")
        print("base64_encoded_string_here...")

