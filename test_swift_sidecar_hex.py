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

# Test with proper hex message format
print("Testing with proper hex message format...\n")

# Create a test order message
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

message_dict = {
    "action": "place_order",
    "order": test_order
}
message_bytes = json.dumps(message_dict, separators=(',', ':')).encode('utf-8')

# Sign the message
signature = keypair.sign_message(message_bytes)

# Test with proper hex message (even length)
payload_hex = {
    "message": message_bytes.hex(),  # Proper hex string
    "signature": bytes(signature).hex(),  # Hex signature
    "market_index": 0,
    "market_type": "perp",
    "taker_authority": str(keypair.pubkey()),
    "public_key": str(keypair.pubkey())
}

print("Hex Message Format:")
print(json.dumps(payload_hex, indent=2))
print()

# Test the format
swift_url = "http://localhost:8787"
api_key = os.environ.get('SWIFT_API_KEY', '')

headers = {
    'Content-Type': 'application/json'
}
if api_key:
    headers['Authorization'] = f'Bearer {api_key}'

print("Testing hex message format...")
try:
    response = requests.post(f"{swift_url}/orders", json=payload_hex, headers=headers, timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    if response.status_code == 422:
        try:
            error_detail = response.json()
            print(f"Error details: {json.dumps(error_detail, indent=2)}")
        except:
            pass
    elif response.status_code == 200:
        print("✅ SUCCESS! This format works!")
except Exception as e:
    print(f"Error: {e}")

# Also test with a simple hex message
print("\n" + "="*50)
print("Testing with simple hex message...")

simple_message = b"test_order"
payload_simple = {
    "message": simple_message.hex(),  # Simple hex
    "signature": bytes(keypair.sign_message(simple_message)).hex(),
    "market_index": 0,
    "market_type": "perp",
    "taker_authority": str(keypair.pubkey()),
    "public_key": str(keypair.pubkey())
}

print("Simple Hex Format:")
print(json.dumps(payload_simple, indent=2))
print()

try:
    response = requests.post(f"{swift_url}/orders", json=payload_simple, headers=headers, timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    if response.status_code == 422:
        try:
            error_detail = response.json()
            print(f"Error details: {json.dumps(error_detail, indent=2)}")
        except:
            pass
    elif response.status_code == 200:
        print("✅ SUCCESS! This format works!")
except Exception as e:
    print(f"Error: {e}")
