import asyncio
import json
from datetime import datetime
from typing import Any
from uuid import UUID

import requests
from fastapi import BackgroundTasks, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from concrete import orchestrator
from concrete.tools import DeployToAWS

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

    async def send_json(self, message: Any, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html", {'request': {}})


def deploy_images(response_url: str):
    if DeployToAWS._deploy_image(
        '008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-main:latest', 'webapp-main'
    ) and DeployToAWS._deploy_image('008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest', 'webapp-demo'):
        body = {
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Successfully deployed `main`"}}],
            "response_type": "in_channel",
            "replace_original": True,
        }
    else:
        body = {
            "text": "Deploy failed. Try again?",
            "response_type": "in_channel",
            "replace_original": True,
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "Deploy failed. Attempt deploy `main` to production again?"},
                },
                {
                    "type": "actions",
                    "elements": [
                        {"type": "button", "text": {"type": "plain_text", "text": "DEPLOY"}, "style": "primary"}
                    ],
                },
            ],
        }
    headers = {'Content-type': 'application/json'}
    requests.post(response_url, headers=headers, data=json.dumps(body), timeout=3)


@app.post("/slack", status_code=200)
async def slack_endpoint(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    payload = json.loads(form['payload'])
    print(payload)
    background_tasks.add_task(deploy_images, response_url=payload['response_url'])

    return payload


@app.post('/ping', status_code=200)
async def ping(request: Request):
    form = await request.form()
    payload = form['payload']
    return payload


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
    await manager.send_json(payload, websocket)

    payload = {
        "agent_type": "Developer",
        "timestamp": datetime.now().isoformat(),
        "message": ("Hi! I'm the Developer!\n"),
        "completed": False,
    }
    await manager.send_json(payload, websocket)
    try:
        while True:
            data = await websocket.receive_text()

            so = orchestrator.SoftwareOrchestrator()
            so.update(ws=websocket, manager=manager)
            result = ""
            async for agent_type, message in so.process_new_project(data, False):
                result = message

                payload = {
                    "agent_type": agent_type,
                    "timestamp": datetime.now().isoformat(),
                    "message": (message),
                    "completed": False,
                }
                await manager.send_json(payload, websocket)
                await asyncio.sleep(0)
                # this is also valid:
                # await asyncio.create_task(manager.send_json(payload, websocket))
                # the problem here is websocket.send* does not properly function without
                # the asyncio.sleep or asyncio.create_task, for whatever reason
                # websocket.receive_text also "flushes" the stack of messages passed to websocket.send*

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
            await manager.send_json(payload, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
