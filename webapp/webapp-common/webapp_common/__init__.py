import os
import time
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, WebSocket


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
