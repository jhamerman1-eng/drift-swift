"""STUB: Hedge execution router.
Dispatches an IOC or passive order to the best venue list.
"""
def execute_hedge(signal: dict) -> str:
    if signal.get("ioc"): return "IOC_SENT:" + ",".join(signal.get("venues",[]))
    return "PASSIVE_SENT:" + ",".join(signal.get("venues",[]))
