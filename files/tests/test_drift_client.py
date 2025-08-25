from libs.drift.client import DriftClient, DriftConfig

def test_cfg_init():
    cfg = DriftConfig(rpc_url="http://localhost:8899")
    c = DriftClient(cfg)
    assert c.cfg.rpc_url.endswith("8899")
