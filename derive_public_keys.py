#!/usr/bin/env python3
"""
Derive public keys from private keys
"""

import base58
from solders.keypair import Keypair

def derive_public_key_from_base58(private_key_b58: str) -> str:
    """Derive public key from base58-encoded private key"""
    try:
        # Decode base58 private key
        private_key_bytes = base58.b58decode(private_key_b58)
        print(f"Decoded length: {len(private_key_bytes)} bytes")

        # Handle different key formats
        if len(private_key_bytes) == 32:
            # 32-byte seed - use from_seed
            keypair = Keypair.from_seed(private_key_bytes)
        elif len(private_key_bytes) == 64:
            # 64-byte secret key - use from_bytes
            keypair = Keypair.from_bytes(private_key_bytes)
        else:
            return f"Error: Invalid key length {len(private_key_bytes)}. Expected 32 or 64 bytes."

        # Return public key as string
        return str(keypair.pubkey())

    except Exception as e:
        return f"Error: {e}"

# Your private keys
private_key_1 = "6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW"
private_key_2 = "4M7ojLUx4eRC8GtDq4rw8h77FPqXsuYQXTKhKNSKEpmD7TbZPZd9K5wK9HGcidFvGxSVryRCz38un4sgHtYn8Tzi"

print("🔑 Deriving Public Keys from Private Keys")
print("=" * 50)

print(f"Private Key 1: {private_key_1}")
public_key_1 = derive_public_key_from_base58(private_key_1)
print(f"Public Key 1:  {public_key_1}")
print()

print(f"Private Key 2: {private_key_2}")
public_key_2 = derive_public_key_from_base58(private_key_2)
print(f"Public Key 2:  {public_key_2}")

print("\n✅ Done!")
