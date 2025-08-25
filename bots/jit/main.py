#!/usr/bin/env python3
"""STUB: JIT Maker Bot entrypoint.
TODO: wire to Drift/Swift client; implement skew adapter + cancel/replace v2.
"""
import time, os
def main():
    print("[JIT] starting (STUB)")
    print("env:", os.getenv("ENV"), "market:", os.getenv("MARKET","SOL-PERP"))
    for i in range(3):
        print(f"[JIT] heartbeat {i}"); time.sleep(0.5)
    print("[JIT] exit (STUB)")
if __name__ == "__main__": main()
