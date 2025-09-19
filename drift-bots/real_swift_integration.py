#!/usr/bin/env python3
"""
Real Swift API Integration - Actually submits orders to Swift API
"""

import os
import time
import json
import httpx
from typing import Dict, Any

class RealSwiftAPI:
    """Real Swift API integration"""
    
    def __init__(self):
        self.swift_base = "https://swift.drift.trade"
        self.api_key = os.getenv("SWIFT_API_KEY")
        self.secret = os.getenv("SWIFT_SECRET")
        
        if not self.api_key or not self.secret:
            print("❌ SWIFT_API_KEY and SWIFT_SECRET environment variables required")
            print("💡 Set these to your actual Swift API credentials")
            return
        
        self.client = httpx.AsyncClient(
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
        )
        
        print(f"✅ Real Swift API initialized: {self.swift_base}")
    
    async def place_order(self, symbol: str, side: str, price: float, size: float):
        """Place real order via Swift API"""
        try:
            order_data = {
                "symbol": symbol,
                "side": side,
                "price": price,
                "size": size,
                "type": "limit",
                "postOnly": True
            }
            
            print(f"🚀 Submitting REAL order to Swift: {side} {size} @ ${price}")
            
            response = await self.client.post(
                f"{self.swift_base}/orders",
                json=order_data
            )
            
            if response.status_code == 200:
                result = response.json()
                order_id = result.get("orderId")
                print(f"✅ Order submitted successfully: {order_id}")
                return order_id
            else:
                print(f"❌ Order failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error submitting order: {e}")
            return None
    
    async def get_positions(self):
        """Get real positions from Swift"""
        try:
            response = await self.client.get(f"{self.swift_base}/positions")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get positions: {response.status_code}")
                return {}
        except Exception as e:
            print(f"❌ Error getting positions: {e}")
            return {}
    
    async def close(self):
        """Close API client"""
        await self.client.aclose()

# Usage example
async def main():
    print("🔑 To use real Swift API, set environment variables:")
    print("   export SWIFT_API_KEY=your_api_key")
    print("   export SWIFT_SECRET=your_secret")
    print()
    print("📊 Then orders will appear on Swift UI and potentially Drift UI")
    print("🌐 Swift UI: https://swift.drift.trade")
    print("🎯 Drift UI: https://beta.drift.trade")

if __name__ == "__main__":
    asyncio.run(main())
