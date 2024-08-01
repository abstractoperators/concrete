import json
import os
from datetime import datetime
from uuid import UUID

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from concrete import orchestrator

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.orchestrator_map: dict[UUID, WebSocket] = (
            {}
        )  # orchestrator.uuid to a websocket connection
        # self.services: dict[WebSocket, str] = {}  # websocket: service

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


@app.post("/webhook/image_push")
async def image_push_webhook(payload: dict):
    print("hiiiiiii")
    print(payload)


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    payload = {
        "agent_type": "Executive",
        "timestamp": datetime.now().isoformat(),
        "message": f"Hi! Ask me to do a simple coding task.\nI will work with a Developer agent to break down your prompt into smaller tasks before combining the work back together.\nPress `Submit` to get started!",
        "completed": False,
    }
    await manager.send_personal_message(json.dumps(payload), websocket)

    try:
        while True:
            data = await websocket.receive_text()
            payload = {
                "agent_type": "USER",
                "timestamp": datetime.now().isoformat(),
                "message": f"User (#{client_id}) requested: {data}",
                "completed": False,
            }
            await manager.send_personal_message(json.dumps(payload), websocket)

            so = orchestrator.SoftwareOrchestrator(manager)
            so.update(ws=websocket)
            so.update(client_id=client_id)
            result = await so.process_new_project(data)
            payload = {
                "agent_type": "EXECUTIVE",
                "timestamp": datetime.now().isoformat(),
                "message": f"[Final Code]\n {result} \nQuestions? Email us at hello@abstractoperators.ai\n© Abstract Operators, 2024.",
                "completed": True,
            }

            # Launch result, and host it in a task?
            # streams_docker_context(result, client_id)

            await manager.send_personal_message(json.dumps(payload), websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # await manager.broadcast(f"Client #{client_id} left the chat")
