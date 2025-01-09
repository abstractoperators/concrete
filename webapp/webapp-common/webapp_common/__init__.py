import json
import logging
import os
import time
import traceback
import uuid
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, WebSocket
from pydantic import BaseModel
from starlette.concurrency import iterate_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_text(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def send_json(self, message: Any, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


class OrchestratorConnectionManager(ConnectionManager):
    def __init__(self) -> None:
        super().__init__()
        self.orchestrator_map: dict[UUID, WebSocket] = {}


def replace_html_entities(html_text: str) -> str:
    """
    Replaces <, >, and & in an HTML string for text usage in HTML.
    """
    return html_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def get_user_id_from_request(request: Request) -> UUID:
    """
    Retrieves user id from fastAPI Request object,
    assuming user has successfully logged in and has a stored session
    """
    return UUID(request.session["user"]["uuid"])


async def get_user_id_from_ws(websocket: WebSocket) -> UUID:
    """
    Retrieves user id from fastAPI Request object,
    assuming user has successfully logged in and has a stored session
    """
    return UUID(websocket.session["user"]["uuid"])


async def get_user_email_from_request(request: Request) -> str:
    """
    Retrieves user email from fastAPI Request object,
    assuming user has successfully logged in and has a stored session
    """
    return request.session["user"]["email"]


UserIdDep = Annotated[UUID, Depends(get_user_id_from_request)]
UserIdDepWS = Annotated[UUID, Depends(get_user_id_from_ws)]
UserEmailDep = Annotated[str, Depends(get_user_email_from_request)]


class JwtToken:
    """
    Represents a JWT token.
    Manages token expiry and generation.
    """

    def __init__(
        self,
        key_name: str,
        alg: str = "RS256",
        expiry_offset: int = 600,
        iss: str | None = None,
        aud: str | None = None,
        nbf: int | None = None,
        additional_headers: dict = {},
    ):
        """
        additional_headers (dict): Headers additional to {typ: 'JWT', alg: alg}
        """
        self.iat = None
        self.exp = None
        self.alg = alg
        self.expiry_offset = expiry_offset
        self.iss = iss
        self.aud = aud
        self.nbf = nbf
        self.additional_headers = additional_headers
        self.key_value = os.getenv(key_name)
        if not self.key_value:
            raise HTTPException(status_code=500, detail=f"{key_name} is not set")

        self._token: str | None = None

    @property
    def token(self):
        if not self._token or self._is_expired():
            self._generate_jwt()
        return self._token

    def _is_expired(self):
        return self.exp is None or time.time() >= self.exp

    def _generate_jwt(self):
        self.iat = time.time()
        self.exp = self.iat + self.expiry_offset
        payload = {
            'exp': self.iat + self.expiry_offset,
            'iat': self.iat,
            'iss': self.iss,
            'aud': self.aud,
            'nbf': self.nbf,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        self._token = jwt.encode(payload, self.key_value, algorithm=self.alg, headers=self.additional_headers)


# region Logger Middleware
class RequestInfo:
    def __init__(self, request) -> None:
        self.request = request

    @property
    def method(self) -> str:
        return str(self.request.method)

    @property
    def route(self) -> str:
        return self.request["path"]

    @property
    def ip(self) -> str:
        return str(self.request.client.host)

    @property
    def url(self) -> str:
        return str(self.request.url)

    @property
    def host(self) -> str:
        return str(self.request.url.hostname)

    @property
    def headers(self) -> dict:
        return {key: value for key, value in self.request.headers.items()}

    @property
    def body(self) -> dict:
        return self.request.state.body


class RequestLog(BaseModel):
    req_id: str
    method: str
    route: str
    ip: str
    url: str
    host: str
    body: dict
    headers: dict


class ErrorLog(BaseModel):
    req_id: str
    error_message: str


class LoggerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        req_id = str(uuid.uuid4())
        try:
            request.state.req_id = req_id
            request.state.body = json.loads(await request.body() or "{}")
            log_request(request, self.logger)

            response = await call_next(request)
            if response.headers.get("content-type") == "application/json":
                response_body = [chunk async for chunk in response.body_iterator]
                response.body_iterator = iterate_in_threadpool(iter(response_body))
            return response
        except Exception as e:
            log_error(req_id, {"error_message": "ERR_UNEXPECTED" + str(e)}, self.logger)
            return HTTPException(status_code=500, detail="ERR_UNEXPECTED" + str(e))


def log_request(request: Request, logger: logging.Logger):
    request_info = RequestInfo(request)
    request_log = RequestLog(
        req_id=request.state.req_id,
        method=request_info.method,
        route=request_info.route,
        ip=request_info.ip,
        url=request_info.url,
        host=request_info.host,
        body=request_info.body,
        headers=request_info.headers,
    )
    logger.info(request_log.dict())


def log_error(uuid: str, response_body: dict, logger: logging.Logger):
    error_log = ErrorLog(
        req_id=uuid,
        error_message=response_body["error_message"],
    )
    logger.error(error_log.dict())
    logger.error(traceback.format_exc())


# endregion Logger Middleware
