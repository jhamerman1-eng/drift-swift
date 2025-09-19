#!/usr/bin/env python3
"""
Create the correct wallet file from the provided private key
"""

from solders.keypair import Keypair
import json
import base58

def create_correct_wallet():
    """Create wallet file from the provided private key"""
    
    # Your provided private key
    private_key_b58 = '61UGhmDPFesjFp7Mz2MWqaPmgp9jGm1HqnsMFyB2s2GFy1dwxuWQbTnkrCysZuccJyd1X2UFm7AknkPWJv7X1uMx'
    target_pubkey = 'A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW'

    print(f'🔑 Creating wallet from your private key...')
    print(f'🎯 Expected public key: {target_pubkey}')

    try:
        # Decode the base58 private key
        private_key_bytes = base58.b58decode(private_key_b58)
        print(f'📏 Private key length: {len(private_key_bytes)} bytes')
        
        # Create keypair from private key
        keypair = Keypair.from_bytes(private_key_bytes)
        actual_pubkey = str(keypair.pubkey())
        
        print(f'✅ Generated public key: {actual_pubkey}')
        print(f'🔍 Match check: {actual_pubkey == target_pubkey}')
        
        if actual_pubkey == target_pubkey:
            # Save as correct wallet file
            wallet_data = list(private_key_bytes)
            
            with open('.correct_wallet.json', 'w') as f:
                json.dump(wallet_data, f)
            
            print(f'💾 Saved correct wallet to: .correct_wallet.json')
            print(f'✅ Wallet verification complete!')
            
            # Also update the main devnet wallet
            with open('.devnet_wallet.json', 'w') as f:
                json.dump(wallet_data, f)
            print(f'💾 Updated .devnet_wallet.json with correct wallet')
            
            return True
        else:
            print(f'❌ ERROR: Public keys do not match!')
            print(f'   Expected: {target_pubkey}')
            print(f'   Generated: {actual_pubkey}')
            return False
            
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

if __name__ == "__main__":
    create_correct_wallet()





