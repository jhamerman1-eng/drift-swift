import os, json, requests

RPC = os.getenv("RPC_URL") or "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"

def call(method, params=None, id=1):
    payload = {"jsonrpc":"2.0","id":id,"method":method,"params": params or []}
    r = requests.post(RPC, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()

def main():
    print("RPC:", RPC)
    print("→ getVersion")
    print(json.dumps(call("getVersion"), indent=2))
    print("→ getSlot")
    print(json.dumps(call("getSlot"), indent=2))
    print("→ getHealth (non-standard; some RPCs support)")
    try:
        print(json.dumps(call("getHealth"), indent=2))
    except Exception as e:
        print("getHealth not supported:", e)

if __name__ == "__main__":
    main()
