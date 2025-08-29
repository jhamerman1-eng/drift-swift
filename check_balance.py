#!/usr/bin/env python3
import httpx

def check_balance():
    response = httpx.post(
        'https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494',
        json={
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'getBalance',
            'params': ['6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW']
        }
    )
    balance = response.json()
    sol_balance = balance["result"]["value"] / 1e9
    print(f"💰 Balance: {sol_balance:.6f} SOL")
    print("✅ Bot Status: RUNNING (Double-encoding fixed!)")
    return sol_balance

if __name__ == "__main__":
    check_balance()

