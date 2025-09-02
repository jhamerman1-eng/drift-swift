#!/usr/bin/env python3
"""
Live Dashboard for JIT Market Maker Bot
"""

import asyncio
import time
import json
import httpx
from datetime import datetime
from typing import Dict, Any

class LiveDashboard:
    """Live dashboard for monitoring MM bot status"""
    
    def __init__(self):
        self.rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        self.wallet_address = "MBVHQtmMxT9YRFrcdALYpQnsA6vtzBpZASm5LBXJ3VV"
        self.explorer_base = "https://explorer.solana.com"
        self.drift_ui = "https://beta.drift.trade/~devnet"
        
    async def get_wallet_balance(self) -> Dict[str, Any]:
        """Get current wallet balance"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [self.wallet_address]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.rpc_url, json=payload, timeout=10.0)
                
            if response.status_code == 200:
                result = response.json()
                if "result" in result and "value" in result["result"]:
                    balance_lamports = result["result"]["value"]
                    balance_sol = balance_lamports / 1_000_000_000
                    return {
                        'success': True,
                        'balance_sol': balance_sol,
                        'balance_lamports': balance_lamports
                    }
            
            return {'success': False, 'error': 'Failed to fetch balance'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_recent_transactions(self) -> Dict[str, Any]:
        """Get recent transactions for the wallet"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    self.wallet_address,
                    {"limit": 5}
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.rpc_url, json=payload, timeout=10.0)
                
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    return {
                        'success': True,
                        'transactions': result["result"]
                    }
            
            return {'success': False, 'error': 'Failed to fetch transactions'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def print_header(self):
        """Print dashboard header"""
        print("🚀 JIT MARKET MAKER BOT - LIVE DASHBOARD")
        print("=" * 80)
        print(f"📅 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Network: Solana Devnet")
        print(f"🔗 Drift UI: {self.drift_ui}")
        print(f"🔗 Explorer: {self.explorer_base}/address/{self.wallet_address}?cluster=devnet")
        print("=" * 80)
    
    def print_wallet_status(self, balance_data: Dict[str, Any]):
        """Print wallet status section"""
        print("💰 WALLET STATUS")
        print("-" * 40)
        
        if balance_data['success']:
            balance_sol = balance_data['balance_sol']
            print(f"   📍 Address: {self.wallet_address[:8]}...{self.wallet_address[-8:]}")
            print(f"   💎 SOL Balance: {balance_sol:.6f} SOL")
            
            if balance_sol >= 0.1:
                print(f"   ✅ Status: READY FOR TRADING")
            else:
                print(f"   ⚠️  Status: LOW BALANCE - Need at least 0.1 SOL")
        else:
            print(f"   ❌ Error: {balance_data.get('error', 'Unknown error')}")
        
        print()
    
    def print_trading_status(self):
        """Print trading status section"""
        print("🤖 TRADING STATUS")
        print("-" * 40)
        
        # Check if MM bot processes are running
        import psutil
        mm_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python' and proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'run_mm_bot' in cmdline or 'mm_bot' in cmdline:
                        mm_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if mm_processes:
            print(f"   ✅ MM Bot Status: RUNNING ({len(mm_processes)} processes)")
            for proc in mm_processes:
                print(f"      • PID {proc['pid']}: {' '.join(proc['cmdline'][:3])}...")
        else:
            print(f"   ❌ MM Bot Status: NOT RUNNING")
            print(f"      💡 Start with: python run_mm_bot_v2.py --env devnet --cfg configs/core/drift_client.yaml")
        
        print()
    
    def print_recent_activity(self, tx_data: Dict[str, Any]):
        """Print recent activity section"""
        print("📊 RECENT ACTIVITY")
        print("-" * 40)
        
        if tx_data['success'] and tx_data['transactions']:
            print(f"   📋 Recent Transactions: {len(tx_data['transactions'])} found")
            for i, tx in enumerate(tx_data['transactions'][:3]):
                signature = tx.get('signature', 'N/A')[:16] + '...'
                slot = tx.get('slot', 'N/A')
                print(f"      {i+1}. {signature} (Slot: {slot})")
        else:
            print(f"   ℹ️  No recent transactions found")
            print(f"      💡 This is normal for a new wallet")
        
        print()
    
    def print_quick_actions(self):
        """Print quick actions section"""
        print("⚡ QUICK ACTIONS")
        print("-" * 40)
        print("   1. 🚀 Start MM Bot: python run_mm_bot_v2.py --env devnet --cfg configs/core/drift_client.yaml")
        print("   2. 💰 Check Balance: python check_wallet_funds.py")
        print("   3. 🪂 Request Airdrop: python alternative_airdrop.py")
        print("   4. 🔍 View Logs: Get-Content *.log -Tail 20")
        print("   5. 🛑 Stop All Bots: Get-Process python | Stop-Process")
        print()
    
    async def update_dashboard(self):
        """Update and display the dashboard"""
        # Clear screen (Windows)
        import os
        os.system('cls')
        
        # Print header
        self.print_header()
        
        # Get wallet balance
        balance_data = await self.get_wallet_balance()
        self.print_wallet_status(balance_data)
        
        # Get recent transactions
        tx_data = await self.get_recent_transactions()
        self.print_recent_activity(tx_data)
        
        # Print trading status
        self.print_trading_status()
        
        # Print quick actions
        self.print_quick_actions()
        
        # Print footer
        print("=" * 80)
        print(f"🔄 Auto-refresh in 30 seconds... (Press Ctrl+C to stop)")
        print("=" * 80)

async def main():
    """Main dashboard loop"""
    dashboard = LiveDashboard()
    
    try:
        while True:
            await dashboard.update_dashboard()
            await asyncio.sleep(30)  # Refresh every 30 seconds
            
    except KeyboardInterrupt:
        print("\n\n🛑 Dashboard stopped by user")
        print("💡 Use the quick actions above to manage your MM bots!")

if __name__ == "__main__":
    print("🚀 Starting Live Dashboard...")
    asyncio.run(main())
