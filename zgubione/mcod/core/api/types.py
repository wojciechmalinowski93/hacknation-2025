from typing import Any, Protocol, Union

from falcon import Request, Response
from typing_extensions import (
    TypeAlias,  # Python < 3.10. Please note, that above 3.10 you should import it from typing.
)


class _FalconProcessRequestProtocol(Protocol):
    def process_request(self, request: Request, response: Response) -> None:
        pass


class _FalconProcessResponseProtocol(Protocol):
    def process_response(self, req: Request, resp: Response, resource: Any, req_succeeded: bool) -> None:
        pass


class _FalconProcessResourcesProtocol(Protocol):
    def process_resource(self, req: Request, resp: Response, resource: Any, params: dict) -> None:
        pass


FalconMiddlewareProtocol: TypeAlias = Union[
    _FalconProcessRequestProtocol,
    _FalconProcessResponseProtocol,
    _FalconProcessResourcesProtocol,
]
