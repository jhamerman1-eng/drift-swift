import asyncio

from bots.jit.main_swift import SwiftExecClient
from run_mm_bot_v2 import SwiftExecClient as V2SwiftExecClient
import libs.drift.client as drift_client_module


class DummySigner:
    pass


class DummyClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.drift_client = DummySigner()

    async def close(self):
        pass


def test_ensure_signer_uses_rpc_and_wallet(monkeypatch):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return DummyClient(**kwargs)

    monkeypatch.setattr(drift_client_module, "DriftpyClient", fake_client)

    cfg = {
        "cluster": "beta",
        "market_index": 0,
        "swift": {},
        "rpc": {"http_url": "https://example-rpc"},
        "wallets": {"maker_keypair_path": "/tmp/test-wallet.json"},
    }

    client = SwiftExecClient(cfg, "SOL-PERP")
    signer = asyncio.run(client._ensure_signer())

    assert signer is not None
    assert captured["rpc_url"] == "https://example-rpc"
    assert captured["cfg"]["wallets"]["maker_keypair_path"] == "/tmp/test-wallet.json"


def test_encode_envelope_bytes_uses_encode_method():
    class Signer:
        def __init__(self):
            self.called = False

        def encode_signed_msg_order_params_message(self, envelope):
            self.called = True
            return b"\x01\x02"

    client = V2SwiftExecClient({}, "SOL-PERP")
    client._signer = Signer()
    result = asyncio.run(client._encode_envelope_bytes(object()))

    assert result == b"\x01\x02"
    assert client._signer.called
