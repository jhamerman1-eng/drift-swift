"""
Type stubs for httpx library
"""

from typing import Any, Dict, Optional, Union, Iterator, Protocol
import json

# Exception classes
class HTTPError(Exception): ...
class RequestError(HTTPError): ...
class TimeoutException(RequestError): ...
class ConnectError(RequestError): ...

class Response:
    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str

    def json(self) -> Any: ...
    def raise_for_status(self) -> None: ...

class Request:
    def __init__(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        content: Optional[Union[str, bytes]] = None,
        json: Optional[Any] = None,
        **kwargs: Any
    ) -> None: ...

class Client:
    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs: Any
    ) -> None: ...

    def get(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> Response: ...

    def post(
        self,
        url: str,
        *,
        content: Optional[Union[str, bytes]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> Response: ...

    def put(
        self,
        url: str,
        *,
        content: Optional[Union[str, bytes]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> Response: ...

    def delete(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> Response: ...

    def close(self) -> None: ...

class AsyncClient:
    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs: Any
    ) -> None: ...

    async def get(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> Response: ...

    async def post(
        self,
        url: str,
        *,
        content: Optional[Union[str, bytes]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> Response: ...

    async def put(
        self,
        url: str,
        *,
        content: Optional[Union[str, bytes]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> Response: ...

    async def delete(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> Response: ...

    async def aclose(self) -> None: ...
