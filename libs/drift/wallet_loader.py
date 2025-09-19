# libs/drift/wallet_loader.py
import json, base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey

class WalletFormatError(Exception): ...

def load_keypair_from_file(path: str) -> Keypair:
    """
    Supports:
    1) Solana JSON secret key: [64 int bytes]
    2) Base58-encoded 64-byte secret key string
    """
    with open(path, "r") as f:
        raw = f.read().strip()

    try:
        # First try JSON format
        kp = Keypair.from_json(raw)
    except Exception:
        try:
            # Fall back to base58 format
            kp = Keypair.from_base58_string(raw)
        except Exception as e:
            raise WalletFormatError(f"Unable to parse wallet: {e}")

    # Validate public key
    try:
        pubkey = kp.pubkey()
        # Just ensure we can access the pubkey (validation is implicit in the keypair creation)
        assert len(bytes(pubkey)) == 32
    except Exception as e:
        raise WalletFormatError(f"Pubkey validation failed: {e}")

    return kp
