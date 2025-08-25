from typing import Callable, Dict, List, Any

class InProcBus:
    def __init__(self):
        self._subs: Dict[str, List[Callable[[dict], None]]] = {}

    def publish(self, topic: str, payload: dict):
        for cb in self._subs.get(topic, []):
            cb(payload)

    def subscribe(self, topic: str, cb: Callable[[dict], None]):
        self._subs.setdefault(topic, []).append(cb)
