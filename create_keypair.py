#!/usr/bin/env python3
"""
Script to convert a base58 private key to a Solana keypair file
"""
import base58
import json
import sys

def create_keypair_file(private_key_base58, output_path):
    """Convert base58 private key to Solana keypair file"""
    try:
        # Decode the base58 private key
        private_key_bytes = base58.b58decode(private_key_base58)
        
        # Create the keypair structure
        keypair_data = list(private_key_bytes)
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(keypair_data, f)
        
        print(f"✅ Keypair file created successfully: {output_path}")
        print(f"📁 File contains {len(keypair_data)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating keypair file: {e}")
        return False

if __name__ == "__main__":
    # Your private key and desired output path
    PRIVATE_KEY = "61UGhmDPFesjFp7Mz2MWqaPmgp9jGm1HqnsMFyB2s2GFy1dwxuWQbTnkrCysZuccJyd1X2UFm7AknkPWJv7X1uMx"
    OUTPUT_PATH = r"C:\Users\genuw\.config\solana\id_devnet_custom.json"
    
    print("🔑 Creating Solana keypair file...")
    print(f"📝 Private key: {PRIVATE_KEY[:10]}...{PRIVATE_KEY[-10:]}")
    print(f"📁 Output path: {OUTPUT_PATH}")
    
    success = create_keypair_file(PRIVATE_KEY, OUTPUT_PATH)
    
    if success:
        print("\n🎉 Keypair file created successfully!")
        print("You can now use this file with: solana config set --keypair " + OUTPUT_PATH)
    else:
        print("\n💥 Failed to create keypair file")
        sys.exit(1)
