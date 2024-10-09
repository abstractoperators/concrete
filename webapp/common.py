from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Request, WebSocket


class ConnectionManager:
    def __init__(self):
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
    def __init__(self):
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
    return UUID(request.session['user']['uuid'])


async def get_user_id_from_ws(websocket: WebSocket) -> UUID:
    """
    Retrieves user id from fastAPI Request object,
    assuming user has successfully logged in and has a stored session
    """
    return UUID(websocket.session['user']['uuid'])


UserIdDep = Annotated[UUID, Depends(get_user_id_from_request)]
UserIdDepWS = Annotated[UUID, Depends(get_user_id_from_ws)]
