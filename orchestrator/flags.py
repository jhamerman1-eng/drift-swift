class FeatureFlags:
    def __init__(self, defaults: dict[str, bool] | None = None):
        self._f = dict(defaults or {})

    def enabled(self, key: str) -> bool:
        return self._f.get(key, False)

    def set(self, key: str, val: bool) -> None:
        self._f[key] = val
