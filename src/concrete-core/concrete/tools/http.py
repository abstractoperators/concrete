try:
    from requests import Response
except ImportError:
    raise ImportError("Install requests to use HTTPClient")

from typing import Optional

from concrete.clients import CLIClient
from concrete.clients.http import HTTPClient
from concrete.tools import MetaTool


class HTTPTool(metaclass=MetaTool):
    @classmethod
    def _process_response(cls, resp: Response, url: str) -> bytes:
        if not resp.ok:
            CLIClient.emit(f"Failed request to {url}: {resp.status_code} {resp}")
            resp.raise_for_status()

        return resp.content

    @classmethod
    def request(cls, method: str, url: str, **kwargs) -> bytes:
        """
        Make an HTTP request to the specified url
        Throws an error if the request was unsuccessful
        """
        resp = HTTPClient().request(method, url, **kwargs)
        return cls._process_response(resp, url)

    @classmethod
    def get(cls, url: str, **kwargs) -> Response:
        return cls.request("GET", url, **kwargs)

    @classmethod
    def post(cls, url: str, **kwargs) -> Response:
        return cls.request("POST", url, **kwargs)

    @classmethod
    def put(cls, url: str, **kwargs) -> Response:
        return cls.request("PUT", url, **kwargs)

    @classmethod
    def delete(cls, url: str, **kwargs) -> Response:
        return cls.request("DELETE", url, **kwargs)


class RestApiTool(HTTPTool):
    @classmethod
    def _process_response(cls, resp: Response, url: Optional[str] = None) -> bytes:
        if not resp.ok:
            CLIClient.emit(f"Failed request to {url}: {resp.status_code} {resp}")
            resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            return resp.json()
        if "text" in content_type:
            return resp.text
        return resp.content
