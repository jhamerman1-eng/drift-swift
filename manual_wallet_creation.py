#!/usr/bin/env python3
"""
Manual wallet creation without external dependencies
Convert base58 private key to wallet file
"""

import json

def base58_decode(s):
    """Simple base58 decoder"""
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    decoded = 0
    multi = 1
    
    for char in reversed(s):
        if char not in alphabet:
            raise ValueError(f'Invalid character: {char}')
        decoded += multi * alphabet.index(char)
        multi *= 58
    
    # Convert to bytes
    h = hex(decoded)[2:].rstrip('L')
    if len(h) % 2:
        h = '0' + h
    
    result = bytes.fromhex(h)
    
    # Handle leading zeros
    pad = 0
    for c in s:
        if c == alphabet[0]:
            pad += 1
        else:
            break
    
    return b'\x00' * pad + result

def create_wallet_from_private_key():
    """Create wallet file from your private key"""
    
    private_key_b58 = '61UGhmDPFesjFp7Mz2MWqaPmgp9jGm1HqnsMFyB2s2GFy1dwxuWQbTnkrCysZuccJyd1X2UFm7AknkPWJv7X1uMx'
    target_pubkey = 'A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW'
    
    print(f'🔑 Creating wallet from private key')
    print(f'🎯 Target public key: {target_pubkey}')
    
    try:
        # Decode the base58 private key
        private_key_bytes = base58_decode(private_key_b58)
        print(f'📏 Decoded private key length: {len(private_key_bytes)} bytes')
        
        # Import after we have the bytes
        from solders.keypair import Keypair
        
        # Create keypair from the private key bytes
        keypair = Keypair.from_bytes(private_key_bytes)
        actual_pubkey = str(keypair.pubkey())
        
        print(f'✅ Generated public key: {actual_pubkey}')
        
        if actual_pubkey == target_pubkey:
            print('🎉 SUCCESS: Public keys match!')
            
            # Create wallet file in the expected format
            wallet_data = list(private_key_bytes)
            
            # Save as the main devnet wallet
            with open('.devnet_wallet.json', 'w') as f:
                json.dump(wallet_data, f)
            
            print('💾 Updated .devnet_wallet.json with your correct wallet')
            print('✅ Wallet setup complete!')
            
            return True
            
        else:
            print('❌ ERROR: Public key mismatch!')
            print(f'   Expected: {target_pubkey}')
            print(f'   Got:      {actual_pubkey}')
            return False
            
    except Exception as e:
        print(f'❌ Error creating wallet: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_wallet_from_private_key()
    if success:
        print('\n🚀 Ready to run bot with correct wallet!')
    else:
        print('\n❌ Wallet creation failed')





