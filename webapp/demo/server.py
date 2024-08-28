import asyncio
import json
import os
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import (
    BackgroundTasks,
    FastAPI,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from concrete import orchestrator
from concrete.tools import AwsTool, RestApiTool

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


def _deploy_to_prod(response_url: str):
    """
    Helper function for deploying latest registry images to prod.
    Also updates slack button (that triggered this function) with success/failure message.
    """
    if AwsTool._deploy_image(
        '008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-homepage:latest',
        'webapp-homepage',
        listener_rule={'field': 'host-header', 'value': 'abop.ai'},
    ) and AwsTool._deploy_image(
        '008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest',
        'webapp-demo',
        listener_rule={'field': 'host-header', 'value': 'demo.abop.ai'},
    ):
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
    RestApiTool.post(response_url, headers=headers, json=body)


@app.post("/slack/interactions", status_code=200)
async def slack_interactions(request: Request, background_tasks: BackgroundTasks):
    """
    A slack endpoint that listens for Slack interactions https://api.slack.com/apps/A07JF384C05/interactive-messages?
    Deploys to prod on interaction (button click).
    """
    # TODO Figure out somewhere smarter to put this? Currently Slack posts to webapp-demo-staging, which will deploy
    # to prod. It's also weird to have Slack post to webapp-demo (prod), because then prod is responsible for deploying
    # to prod.
    form = await request.form()
    payload = json.loads(form['payload'])
    background_tasks.add_task(_deploy_to_prod, response_url=payload['response_url'])

    return payload


def _post_button():
    """
    Posts a button to #github-logs under slack bot user.
    """
    url = "https://slack.com/api/chat.postMessage"
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    headers = {'Content-type': 'application/json', "Authorization": f"Bearer {slack_token}"}
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": "Deploy `main` to production"}},
        {
            "type": "actions",
            "elements": [{"type": "button", "text": {"type": "plain_text", "text": "deploy"}, "style": "primary"}],
        },
    ]

    data = {"channel": "github-logs", "blocks": blocks}

    response = RestApiTool.post(url, headers=headers, data=json.dumps(data))
    return response


@app.post("/slack/events", status_code=200)
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """
    Listens to slack events.
    Handles the event where a message is posted to #github-logs, and the message contains 'merged'.
    When this happens, a button is posted to the channel.
    """
    # TODO Separate event handling into separate functions
    json_data = await request.json()
    if json_data.get('type', None) == 'url_verification':
        challenge = json_data.get('challenge')
        return Response(content=challenge, media_type="text/plain")
    elif json_data.get('type', None) == 'event_callback':
        # Add a button to #github-logs
        event = json_data.get('event')
        if event.get('type', None) == 'message' and event.get('channel', None) == 'C07DQNQ7L0K':  # #github-logs
            text = event.get('text')
            if 'merged' in text:
                background_tasks.add_task(_post_button())

    return Response(content="OK", media_type="text/plain")


@app.post('/ping', status_code=200)
async def ping(request: Request):
    """
    A simple endpoint to test if the server is running.
    """
    json_data = await request.json()
    return json_data


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
