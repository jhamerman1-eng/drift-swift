"""
Type stubs for websockets library
"""

from typing import Any, Dict, Optional, Union, Coroutine, Protocol, Callable, Awaitable
import asyncio

class WebSocketServerProtocol:
    pass

class WebSocketClientProtocol:
    def ping(self, data: Optional[bytes] = None) -> Coroutine[Any, Any, None]: ...
    def pong(self, data: Optional[bytes] = None) -> Coroutine[Any, Any, None]: ...
    async def recv(self) -> Union[str, bytes]: ...
    async def send(self, message: Union[str, bytes]) -> None: ...
    async def close(self, code: int = 1000, reason: str = "") -> None: ...
    def closed(self) -> bool: ...

class Connect:
    def __init__(
        self,
        uri: str,
        *,
        extra_headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> None: ...

    async def __aenter__(self) -> WebSocketClientProtocol: ...
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...

def connect(
    uri: str,
    *,
    extra_headers: Optional[Dict[str, str]] = None,
    **kwargs: Any
) -> Connect: ...

class ConnectionClosed(Exception):
    pass

class exceptions:
    ConnectionClosed = ConnectionClosed
