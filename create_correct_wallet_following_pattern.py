#!/usr/bin/env python3
"""
Create correct wallet following established pattern from WALLET_FIX_SUMMARY.md
Using the proven method that worked before
"""

import json
from nacl.signing import SigningKey

def create_wallet_following_established_pattern():
    """Create wallet using the proven pattern from previous fixes"""
    
    # Your provided keys
    target_pubkey = 'A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW'
    private_key_b58 = '61UGhmDPFesjFp7Mz2MWqaPmgp9jGm1HqnsMFyB2s2GFy1dwxuWQbTnkrCysZuccJyd1X2UFm7AknkPWJv7X1uMx'
    
    print('🔧 Creating wallet following established pattern...')
    print(f'🎯 Target public key: {target_pubkey}')
    
    try:
        # Step 1: Decode base58 private key (following previous pattern)
        alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        
        # Convert base58 to integer
        decoded = 0
        multi = 1
        for char in reversed(private_key_b58):
            if char not in alphabet:
                raise ValueError(f'Invalid base58 character: {char}')
            decoded += multi * alphabet.index(char)
            multi *= 58
        
        # Convert to hex
        hex_str = hex(decoded)[2:].rstrip('L')
        if len(hex_str) % 2:
            hex_str = '0' + hex_str
        
        # Convert to bytes
        private_key_bytes = bytes.fromhex(hex_str)
        
        # Handle leading zeros (base58 padding)
        pad = 0
        for c in private_key_b58:
            if c == '1':
                pad += 1
            else:
                break
        
        private_key_bytes = b'\x00' * pad + private_key_bytes
        
        print(f'📏 Decoded private key length: {len(private_key_bytes)} bytes')
        
        # Step 2: Follow the established pattern from WALLET_FIX_SUMMARY.md
        # Extract secret key (first 32 bytes)
        sk = private_key_bytes[:32]
        print(f'🔑 Secret key length: {len(sk)} bytes')
        
        # Derive correct public key from secret key using nacl (proven method)
        signing_key = SigningKey(sk)
        pub = signing_key.verify_key.encode()
        print(f'🔑 Derived public key length: {len(pub)} bytes')
        
        # Rebuild the 64-byte keypair (following established pattern)
        fixed_keypair = sk + pub
        print(f'🔧 Rebuilt keypair length: {len(fixed_keypair)} bytes')
        
        # Step 3: Verify with solders (following previous pattern)
        from solders.keypair import Keypair
        keypair = Keypair.from_bytes(fixed_keypair)
        actual_pubkey = str(keypair.pubkey())
        
        print(f'✅ Generated public key: {actual_pubkey}')
        print(f'🔍 Match check: {actual_pubkey == target_pubkey}')
        
        if actual_pubkey == target_pubkey:
            print('🎉 SUCCESS: Public keys match!')
            
            # Step 4: Save wallet following established pattern
            wallet_data = list(fixed_keypair)
            
            with open('.devnet_wallet.json', 'w') as f:
                json.dump(wallet_data, f)
            
            print('💾 Updated .devnet_wallet.json with correct wallet')
            print('✅ Wallet creation complete following established pattern!')
            
            # Step 5: Update bug registry (following previous pattern)
            try:
                with open('logs/bug_registry_active.json', 'r') as f:
                    bug_registry = json.load(f)
            except:
                bug_registry = {}
            
            bug_registry['WALLET_CORRECTED'] = {
                'status': 'resolved',
                'date': '2025-09-16',
                'description': 'Updated wallet to correct public key A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW',
                'method': 'Following established pattern from WALLET_FIX_SUMMARY.md'
            }
            
            with open('logs/bug_registry_active.json', 'w') as f:
                json.dump(bug_registry, f, indent=2)
            
            print('📝 Updated bug registry')
            return True
            
        else:
            print('❌ ERROR: Public key mismatch!')
            print(f'   Expected: {target_pubkey}')
            print(f'   Generated: {actual_pubkey}')
            return False
            
    except Exception as e:
        print(f'❌ Error following established pattern: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_wallet_following_established_pattern()
    if success:
        print('\n🚀 Ready to run bot with correct wallet!')
        print('✅ Following the same proven pattern from previous fixes')
    else:
        print('\n❌ Wallet creation failed')
