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

# Test the CORRECT format based on error analysis
print("Testing CORRECT Swift sidecar format...\n")

# The correct format: message as string, signature as bytes
payload_correct = {
    "message": message_bytes.decode('utf-8'),  # String, not JSON object
    "signature": bytes(signature).hex(),  # Hex string (64 bytes)
    "market_index": 0,
    "market_type": "perp",
    "taker_authority": str(keypair.pubkey()),
    "public_key": str(keypair.pubkey())
}

print("Correct Format:")
print(json.dumps(payload_correct, indent=2))
print()

# Test the format
swift_url = "http://localhost:8787"
api_key = os.environ.get('SWIFT_API_KEY', '')

headers = {
    'Content-Type': 'application/json'
}
if api_key:
    headers['Authorization'] = f'Bearer {api_key}'

print("Testing correct format...")
try:
    response = requests.post(f"{swift_url}/orders", json=payload_correct, headers=headers, timeout=5)
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

# Also test with base64 signature
print("\n" + "="*50)
print("Testing with base64 signature...")

payload_base64_sig = {
    "message": message_bytes.decode('utf-8'),  # String
    "signature": base64.b64encode(bytes(signature)).decode('ascii'),  # Base64
    "market_index": 0,
    "market_type": "perp",
    "taker_authority": str(keypair.pubkey()),
    "public_key": str(keypair.pubkey())
}

print("Base64 Signature Format:")
print(json.dumps(payload_base64_sig, indent=2))
print()

try:
    response = requests.post(f"{swift_url}/orders", json=payload_base64_sig, headers=headers, timeout=5)
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
