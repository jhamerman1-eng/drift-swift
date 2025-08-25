#!/usr/bin/env python3
# v1.17.0-RC RPC/WS Smoke Test (no orders)
import argparse, os, json, sys, socket
try:
    import websockets  # type: ignore
except Exception:
    websockets = None
REQ = ["RPC_URL_HTTP","RPC_URL_WS","DRIFT_WS_URL","SWIFT_WS_URL","KEYPAIR_PATH","JITO_KEYPAIR_PATH","METRICS_PORT","ENV"]
def load_env(p):
    if not os.path.exists(p):
        print(f"[FAIL] missing {p}"); sys.exit(2)
    for line in open(p):
        line=line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k,v=line.split("=",1); os.environ.setdefault(k.strip(), v.strip())
def check_env():
    ok=True
    for k in REQ:
        if not os.getenv(k): print(f"[FAIL] {k}"); ok=False
        else: print(f"[OK] {k}")
    return ok
def check_key(k):
    p=os.getenv(k,"")
    if not p: print(f"[FAIL] {k} not set"); return False
    if not os.path.isabs(p): print(f"[WARN] {k} should be absolute: {p}")
    if not os.path.exists(p): print(f"[FAIL] {k} missing: {p}"); return False
    try:
        data=json.loads(open(p).read())
        assert isinstance(data,list) and all(isinstance(i,int) for i in data)
    except Exception as e:
        print(f"[FAIL] {k} invalid json: {e}"); return False
    print(f"[OK] {k} looks valid"); return True
def tcp_probe(url,timeout=5):
    rest=url.split("://",1)[1] if "://" in url else url
    hostport=rest.split("/",1)[0]
    if ":" in hostport:
        host,port=hostport.split(":",1); port=int(port) if port.isdigit() else (443 if url.startswith(("wss://","https://")) else 80)
    else:
        host=hostport; port=443 if url.startswith(("wss://","https://")) else 80
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM); s.settimeout(timeout)
    try: s.connect((host,port)); s.close(); return True,f"{host}:{port} reachable"
    except Exception as e: return False,f"{host}:{port} unreachable: {e}"
async def ws_handshake(u):
    if websockets is None: return False,"websockets not installed"
    try:
        async with websockets.connect(u,ping_timeout=10,close_timeout=5) as ws:
            await ws.ping(); return True,"WS handshake + ping OK"
    except Exception as e:
        return False,f"WS connect failed: {e}"
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--env-file",default=".env"); args=ap.parse_args()
    load_env(args.env_file); print("=== v1.17.0-RC Smoke Test ===")
    ok=check_env(); ok=ok and check_key("KEYPAIR_PATH") and check_key("JITO_KEYPAIR_PATH")
    for k in ["RPC_URL_HTTP","RPC_URL_WS","DRIFT_WS_URL","SWIFT_WS_URL"]:
        u=os.getenv(k); 
        if not u: continue
        good,msg=tcp_probe(u); print(f"[{'OK' if good else 'FAIL'}] {k}: {msg}"); ok=ok and good
    if websockets is not None:
        import asyncio
        for k in ["RPC_URL_WS","DRIFT_WS_URL","SWIFT_WS_URL"]:
            u=os.getenv(k); 
            if not u: continue
            good,msg=asyncio.get_event_loop().run_until_complete(ws_handshake(u))
            print(f"[{'OK' if good else 'FAIL'}] WS {k}: {msg}"); ok=ok and good
    print("PASS ✅" if ok else "FAIL ❌"); sys.exit(0 if ok else 1)
if __name__=="__main__": main()
