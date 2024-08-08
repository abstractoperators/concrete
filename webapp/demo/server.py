import json
from datetime import datetime
from uuid import UUID

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from concrete import orchestrator

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.orchestrator_map: dict[UUID, WebSocket] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    payload = {
        "agent_type": "Executive",
        "timestamp": datetime.now().isoformat(),
        "message": (
            "Hi! Ask me to do a simple coding task.\n"
            "I will work with a Developer agent to break down your prompt "
            "into smaller tasks before combining the work back together.\n"
            "Press `Submit` to get started!"
        ),
        "completed": False,
    }

    await manager.send_personal_message(json.dumps(payload), websocket)

    payload = {
        "agent_type": "Developer",
        "timestamp": datetime.now().isoformat(),
        "message": ("Hi! I'm the Developer!\n"),
        "completed": False,
    }

    await manager.send_personal_message(json.dumps(payload), websocket)
    try:
        while True:
            data = await websocket.receive_text()

            so = orchestrator.SoftwareOrchestrator()
            so.update(ws=websocket)
            so.update(manager=manager)
            result = so.process_new_project(data, True)
            payload = {
                "agent_type": "EXECUTIVE",
                "timestamp": datetime.now().isoformat(),
                "message": (
                    f"[Final Code]\n"
                    f"{result}\n"
                    f"Questions? Email us at hello@abstractoperators.ai\n"
                    f"© Abstract Operators, 2024."
                ),
                "completed": True,
            }

            await manager.send_personal_message(json.dumps(payload), websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
