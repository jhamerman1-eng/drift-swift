#!/usr/bin/env python3
# v1.17.0-RC RPC/WS Smoke Test
# - Validates env, key paths, and basic socket connectivity (HTTP + WS).
# - Safe to run without placing orders.
# Usage: python scripts/rpc_smoketest.py --env-file .env

import argparse, os, json, sys, socket

try:
    import websockets  # type: ignore
except Exception:
    websockets = None

REQUIRED_ENV = [
    "RPC_URL_HTTP", "RPC_URL_WS", "DRIFT_WS_URL", "SWIFT_WS_URL",
    "KEYPAIR_PATH", "JITO_KEYPAIR_PATH", "METRICS_PORT", "ENV"
]

def load_env(path):
    if not os.path.exists(path):
        print(f"[FAIL] .env file not found at {path}")
        sys.exit(2)
    with open(path, "r") as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k,v = line.split("=",1)
            os.environ.setdefault(k.strip(), v.strip())

def check_env():
    ok = True
    for key in REQUIRED_ENV:
        if not os.getenv(key):
            print(f"[FAIL] Missing env var: {key}")
            ok = False
        else:
            print(f"[OK] {key} is set")
    return ok

def check_keyfile(path_key, label):
    p = os.getenv(path_key, "")
    if not p:
        print(f"[FAIL] {label} not set")
        return False
    if not os.path.isabs(p):
        print(f"[WARN] {label} should be absolute: {p}")
    if not os.path.exists(p):
        print(f"[FAIL] {label} path does not exist: {p}")
        return False
    try:
        data = json.loads(open(p).read())
        if not isinstance(data, list) or not all(isinstance(i, int) for i in data):
            print(f"[FAIL] {label} not a valid Solana keypair JSON array")
            return False
    except Exception as e:
        print(f"[FAIL] {label} invalid JSON: {e}")
        return False
    print(f"[OK] {label} looks valid")
    return True

def tcp_probe(url, timeout=5):
    # crude host:port extraction for ws(s):// or http(s)://
    if "://" in url:
        rest = url.split("://",1)[1]
    else:
        rest = url
    hostport = rest.split("/",1)[0]
    if ":" in hostport:
        host, port = hostport.split(":",1)
        try:
            port = int(port)
        except:
            port = 443 if url.startswith(("wss://","https://")) else 80
    else:
        host = hostport
        port = 443 if url.startswith(("wss://","https://")) else 80
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True, f"{host}:{port} reachable"
    except Exception as e:
        return False, f"{host}:{port} unreachable: {e}"

async def ws_handshake(url):
    if websockets is None:
        return False, "websockets not installed (pip install websockets)"
    try:
        async with websockets.connect(url, ping_timeout=10, close_timeout=5) as ws:
            await ws.ping()
            return True, "WS handshake + ping OK"
    except Exception as e:
        return False, f"WS connect failed: {e}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-file", default=".env")
    args = ap.parse_args()

    load_env(args.env_file)
    print("=== v1.17.0-RC RPC/WS Smoke Test ===")

    ok = check_env()
    k1 = check_keyfile("KEYPAIR_PATH", "KEYPAIR_PATH")
    k2 = check_keyfile("JITO_KEYPAIR_PATH", "JITO_KEYPAIR_PATH")
    ok = ok and k1 and k2

    urls = ["RPC_URL_HTTP", "RPC_URL_WS", "DRIFT_WS_URL", "SWIFT_WS_URL"]
    for k in urls:
        url = os.getenv(k)
        if not url:
            continue
        good, msg = tcp_probe(url)
        print(f"[{'OK' if good else 'FAIL'}] TCP probe {k}: {msg}")
        ok = ok and good

    # Optional WS handshake checks (non-blocking if websockets missing)
    if websockets is not None:
        import asyncio
        for k in ["RPC_URL_WS", "DRIFT_WS_URL", "SWIFT_WS_URL"]:
            url = os.getenv(k)
            if not url:
                continue
            try:
                good, msg = asyncio.get_event_loop().run_until_complete(ws_handshake(url))
                print(f"[{'OK' if good else 'FAIL'}] WS handshake {k}: {msg}")
                ok = ok and good
            except Exception as e:
                print(f"[FAIL] WS handshake {k}: {e}")
                ok = False
    else:
        print("[WARN] websockets not installed; skipping WS handshake step.")

    print("=== RESULT ===")
    if ok:
        print("PASS: Environment looks ready ✅")
        sys.exit(0)
    else:
        print("FAIL: Please fix the above issues ❌")
        sys.exit(1)

if __name__ == "__main__":
    main()
