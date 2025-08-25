from __future__ import annotations
from dataclasses import dataclass
import os, json, http.client, typing as t

@dataclass
class ClientConfig:
    cluster: str
    rpc_url: str
    ws_url: str
    driver: str = "swift"

class ClientFactory:
    @staticmethod
    def from_env() -> "Client":
        cluster = os.getenv("SOLANA_CLUSTER", "devnet")
        rpc = os.getenv("RPC_URL", "")
        ws = os.getenv("WS_URL", "")
        driver = os.getenv("DRIVER", os.getenv("DRIFT_DRIVER", "swift"))
        cfg = ClientConfig(cluster=cluster, rpc_url=rpc, ws_url=ws, driver=driver)
        return Client(cfg)

class Client:
    def __init__(self, cfg: ClientConfig):
        self.cfg = cfg
        if cfg.driver == "swift":
            self.impl = SwiftSidecarClient()
        else:
            # Fallback path could wire driftpy here if desired
            self.impl = SwiftSidecarClient()

    def health(self) -> dict:
        return self.impl.health()

    def place_order(self, **kwargs) -> dict:
        return self.impl.place_order(kwargs)

    def cancel_replace(self, **kwargs) -> dict:
        return self.impl.cancel_replace(kwargs)

class SwiftSidecarClient:
    def __init__(self):
        self.host = os.getenv("SWIFT_SIDECAR_HOST", "127.0.0.1")
        self.port = int(os.getenv("SWIFT_SIDECAR_PORT", "8787"))
        self.api_key = os.getenv("SWIFT_API_KEY")

    def _post(self, path: str, body: dict) -> dict:
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            payload = json.dumps(body)
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            conn.request("POST", path, payload, headers)
            resp = conn.getresponse()
            data = resp.read().decode()
            return json.loads(data) if data else {"ok": resp.status == 200}
        finally:
            conn.close()

    def health(self) -> dict:
        return self._post("/health", {})

    def place_order(self, params: dict) -> dict:
        return self._post("/place", params)

    def cancel_replace(self, params: dict) -> dict:
        return self._post("/cancelReplace", params)
