"""Configuration model for the Drift client."""

from pydantic import BaseModel, SecretStr


class DriftConfig(BaseModel):
    """Configuration for connecting to Drift APIs."""

    http_url: str
    ws_url: str
    api_key: SecretStr | None = None
    api_secret: SecretStr | None = None
    subaccount: str | None = None
    qps_limit: int = 10
    burst: int = 20
    timeout_sec: float = 10.0
