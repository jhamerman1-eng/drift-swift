#!/usr/bin/env python3
"""
Global RPC Endpoint Update Script
Updates all environment and config files to use Helius RPC as primary devnet endpoint
"""

import os
import re
import glob
from pathlib import Path

# New Helius RPC endpoints
NEW_RPC_URL = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
NEW_WS_URL = "wss://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"

# Old endpoints to replace
OLD_RPC_URLS = [
    "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
    "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494/",
    "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
]

OLD_WS_URLS = [
    "wss://https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
    "wss://https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494/",
    "wss://https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494/ws"
]

def update_file(file_path):
    """Update a single file with new RPC endpoints"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace RPC URLs
        for old_url in OLD_RPC_URLS:
            content = content.replace(old_url, NEW_RPC_URL)
        
        # Replace WebSocket URLs
        for old_ws in OLD_WS_URLS:
            content = content.replace(old_ws, NEW_WS_URL)
        
        # Additional pattern replacements
        content = re.sub(
            r'https://api\.devnet\.solana\.com',
            NEW_RPC_URL,
            content
        )
        content = re.sub(
            r'wss://api\.devnet\.solana\.com',
            NEW_WS_URL,
            content
        )
        
        # Check if any changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
        
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Main update function"""
    print("🔄 Starting global RPC endpoint update...")
    print(f"New RPC URL: {NEW_RPC_URL}")
    print(f"New WS URL: {NEW_WS_URL}")
    print("=" * 60)
    
    # File patterns to update
    file_patterns = [
        "*.py",
        "*.yaml",
        "*.yml",
        "*.json",
        "*.md",
        "*.txt",
        "*.log",
        "*.env",
        "*.bat",
        "*.ps1",
        "*.sh"
    ]
    
    # Directories to exclude
    exclude_dirs = {
        "venv",
        "__pycache__",
        ".git",
        "node_modules",
        ".vscode",
        "backups"
    }
    
    updated_files = []
    total_files = 0
    
    # Process all matching files
    for pattern in file_patterns:
        for file_path in glob.glob(f"**/{pattern}", recursive=True):
            # Skip excluded directories
            if any(exclude in file_path for exclude in exclude_dirs):
                continue
            
            # Skip if it's a directory
            if os.path.isdir(file_path):
                continue
            
            total_files += 1
            
            if update_file(file_path):
                updated_files.append(file_path)
                print(f"✅ Updated: {file_path}")
    
    print("=" * 60)
    print(f"📊 Update Summary:")
    print(f"   Total files processed: {total_files}")
    print(f"   Files updated: {len(updated_files)}")
    print(f"   Files unchanged: {total_files - len(updated_files)}")
    
    if updated_files:
        print(f"\n📝 Updated files:")
        for file_path in updated_files:
            print(f"   - {file_path}")
    
    print(f"\n🎉 RPC endpoint update complete!")
    print(f"All devnet endpoints now use Helius RPC: {NEW_RPC_URL}")

if __name__ == "__main__":
    main()















