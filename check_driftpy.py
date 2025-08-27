try:
    import driftpy
    print("driftpy is available")
except ImportError as e:
    print(f"driftpy is NOT available: {e}")
