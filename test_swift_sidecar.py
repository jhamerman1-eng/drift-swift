import requests
import json
import os
from solders.keypair import Keypair
from solders.signature import Signature
import base64
import binascii

# Load your keypair - use our working 64-byte keypair
keypair_path = '.valid_wallet.json'
with open(keypair_path, 'r') as f:
    keypair_data = json.load(f)
keypair = Keypair.from_bytes(keypair_data)

# Create a minimal test order
test_order = {
    "marketIndex": 0,
    "marketType": "perp",
    "amount": 1.0,
    "price": 100.0,
    "postOnly": True,
    "orderType": "limit",
    "direction": "long",
    "reduceOnly": False
}

# Create the message to sign
message_dict = {
    "action": "place_order",
    "order": test_order
}
message_bytes = json.dumps(message_dict, separators=(',', ':')).encode('utf-8')

# Sign the message
signature = keypair.sign_message(message_bytes)

# Test different payload formats
print("Testing different payload formats...\n")

# Format 1: Hex encoding
payload_hex = {
    "signedMessage": binascii.hexlify(message_bytes).decode('ascii'),
    "signature": bytes(signature).hex(),
    "marketIndex": 0,
    "marketType": "perp",
    "takerAuthority": str(keypair.pubkey()),
    "publicKey": str(keypair.pubkey())
}

print("Format 1 (Hex):")
print(json.dumps(payload_hex, indent=2))
print()

# Format 2: Base64 encoding
payload_base64 = {
    "message": base64.b64encode(message_bytes).decode('ascii'),
    "signature": base64.b64encode(bytes(signature)).decode('ascii'),
    "market_index": 0,
    "market_type": "perp",
    "taker": str(keypair.pubkey()),
    "public_key": str(keypair.pubkey())
}

print("Format 2 (Base64):")
print(json.dumps(payload_base64, indent=2))
print()

# Format 3: Raw JSON with signature
payload_json = {
    "order": test_order,
    "signature": bytes(signature).hex(),
    "publicKey": str(keypair.pubkey())
}

print("Format 3 (JSON with signature):")
print(json.dumps(payload_json, indent=2))
print()

# Test each format
swift_url = "http://localhost:8787"
api_key = os.environ.get('SWIFT_API_KEY', '')

headers = {
    'Content-Type': 'application/json'
}
if api_key:
    headers['Authorization'] = f'Bearer {api_key}'

for format_name, payload in [("Hex", payload_hex), ("Base64", payload_base64), ("JSON", payload_json)]:
    print(f"\nTesting {format_name} format...")
    try:
        response = requests.post(f"{swift_url}/orders", json=payload, headers=headers, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        if response.status_code == 422:
            # Try to get more details about what's wrong
            try:
                error_detail = response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                pass
    except Exception as e:
        print(f"Error: {e}")
