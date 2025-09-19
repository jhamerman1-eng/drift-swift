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

# Test different string formats for the message field
print("Testing different string formats for Swift sidecar...\n")

# Test 1: Simple string message
payload1 = {
    "message": "simple_test_message",
    "signature": bytes(keypair.sign_message(b"simple_test_message")).hex(),
    "market_index": 0,
    "market_type": "perp",
    "taker_authority": str(keypair.pubkey()),
    "public_key": str(keypair.pubkey())
}

# Test 2: Base64 encoded message
message_bytes = b"test_order_message"
payload2 = {
    "message": base64.b64encode(message_bytes).decode('ascii'),
    "signature": bytes(keypair.sign_message(message_bytes)).hex(),
    "market_index": 0,
    "market_type": "perp",
    "taker_authority": str(keypair.pubkey()),
    "public_key": str(keypair.pubkey())
}

# Test 3: Hex encoded message
payload3 = {
    "message": message_bytes.hex(),
    "signature": bytes(keypair.sign_message(message_bytes)).hex(),
    "market_index": 0,
    "market_type": "perp",
    "taker_authority": str(keypair.pubkey()),
    "public_key": str(keypair.pubkey())
}

# Test 4: Raw bytes as string (might be what "borrowed string" means)
payload4 = {
    "message": message_bytes.decode('latin-1'),  # Raw bytes as string
    "signature": bytes(keypair.sign_message(message_bytes)).hex(),
    "market_index": 0,
    "market_type": "perp",
    "taker_authority": str(keypair.pubkey()),
    "public_key": str(keypair.pubkey())
}

# Test 5: Try the exact format from the error - maybe it wants a different field name
payload5 = {
    "signedMessage": message_bytes.hex(),  # Different field name
    "signature": bytes(keypair.sign_message(message_bytes)).hex(),
    "marketIndex": 0,
    "marketType": "perp",
    "takerAuthority": str(keypair.pubkey()),
    "publicKey": str(keypair.pubkey())
}

# Test each format
swift_url = "http://localhost:8787"
api_key = os.environ.get('SWIFT_API_KEY', '')

headers = {
    'Content-Type': 'application/json'
}
if api_key:
    headers['Authorization'] = f'Bearer {api_key}'

test_cases = [
    ("Simple string", payload1),
    ("Base64 message", payload2),
    ("Hex message", payload3),
    ("Raw bytes string", payload4),
    ("Different field names", payload5)
]

for test_name, payload in test_cases:
    print(f"\nTesting {test_name}...")
    print(f"Message type: {type(payload['message'])}")
    print(f"Message content: {repr(payload['message'][:50])}...")
    
    try:
        response = requests.post(f"{swift_url}/orders", json=payload, headers=headers, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        if response.status_code == 422:
            try:
                error_detail = response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                pass
        elif response.status_code == 200:
            print("✅ SUCCESS! This format works!")
            break
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 50)
