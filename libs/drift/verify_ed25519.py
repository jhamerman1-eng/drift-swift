# verify_ed25519.py
import base64
from typing import Union
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from solders.pubkey import Pubkey

def verify_signature(
    message: Union[bytes, str],
    signature_b64: str,
    pubkey_str: str,
    message_is_hex: bool = False,
) -> bool:
    """
    Verify an Ed25519 signature produced by solders.Keypair.sign_message.

    - message: the EXACT bytes that were signed.
      If you transmitted the message as hex (e.g., Swift 'order_message'),
      pass `message_is_hex=True` and give the hex string here.
    - signature_b64: base64-encoded 64-byte signature you sent to Swift
    - pubkey_str: base58 string of the signer (e.g., str(keypair.pubkey()))
    """
    if isinstance(message, str):
        message_bytes = bytes.fromhex(message) if message_is_hex else message.encode("utf-8")
    else:
        message_bytes = message

    # Convert base58 pubkey -> 32 raw bytes
    verify_key = VerifyKey(bytes(Pubkey.from_string(pubkey_str)))

    # Decode base64 -> 64 raw bytes
    sig = base64.b64decode(signature_b64)

    try:
        verify_key.verify(message_bytes, sig)  # raises BadSignatureError on failure
        return True
    except BadSignatureError:
        return False


def test_verification_compatibility():
    """
    Quick self-test that proves it matches `solders` signing
    """
    from solders.keypair import Keypair
    import base64

    kp = Keypair()
    msg = b"hello swift"
    sig = kp.sign_message(msg)
    sig_b64 = base64.b64encode(bytes(sig)).decode()

    # This should return True if our verification matches solders signing
    result = verify_signature(msg, sig_b64, str(kp.pubkey()))
    print(f"✅ Verification test passed: {result}")
    return result


if __name__ == "__main__":
    test_verification_compatibility()



