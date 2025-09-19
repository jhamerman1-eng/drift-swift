from libs.drift.client import DriftClient

def test_stub_client():
    c = DriftClient({"driver": "swift"})
    c.connect()
    ob = c.get_orderbook("SOL-PERP")
    assert ob["symbol"] == "SOL-PERP"
    assert "bids" in ob and "asks" in ob
