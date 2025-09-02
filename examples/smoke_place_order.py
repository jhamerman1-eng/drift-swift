from libs.drift.client import DriftClient

if __name__ == "__main__":
    c = DriftClient({"driver": "swift"})
    c.connect()
    print(c.place_order("SOL-PERP", "buy", 100.0, 0.01, post_only=True))
