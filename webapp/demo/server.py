import asyncio
import json
import os
from datetime import datetime

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
from concrete.tools import AwsTool, Container, RestApiTool

from ..common import OrchestratorConnectionManager

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


manager = OrchestratorConnectionManager()


@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": {}})


def _deploy_to_prod(response_url: str):
    """
    Helper function for deploying latest registry images to prod.
    Also updates slack button (that triggered this function) with success/failure message.
    """
    if AwsTool._deploy_service(
        [
            Container(
                image_uri="008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-homepage:latest",
                container_name="webapp-homepage",
                container_port=80,
            ),
        ],
        "webapp-homepage",
        listener_rule={"field": "host-header", "value": "abop.ai"},
    ) and AwsTool._deploy_service(
        [
            Container(
                image_uri="008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest",
                container_name="webapp-demo",
                container_port=80,
            ),
        ],
        listener_rule={"field": "host-header", "value": "demo.abop.ai"},
    ):
        body = {
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "Successfully deployed `main`"},
                }
            ],
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
                    "text": {
                        "type": "mrkdwn",
                        "text": "Deploy failed. Attempt deploy `main` to production again?",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "DEPLOY"},
                            "style": "primary",
                        }
                    ],
                },
            ],
        }
    headers = {"Content-type": "application/json"}
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
    payload = json.loads(form["payload"])
    background_tasks.add_task(_deploy_to_prod, response_url=payload["response_url"])

    return payload


def _post_button():
    """
    Posts a button to #github-logs under slack bot user.
    """
    url = "https://slack.com/api/chat.postMessage"
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {slack_token}",
    }
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "Deploy `main` to production"},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "deploy"},
                    "style": "primary",
                }
            ],
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
    if json_data.get("type", None) == "url_verification":
        challenge = json_data.get("challenge")
        return Response(content=challenge, media_type="text/plain")

    elif json_data.get("type", None) == "event_callback":
        event = json_data.get("event")
        if (
            event.get("channel", None) == "C07DQNQ7L0K"
            and event.get("type", None) == "message"
            and event.get("subtype", None) == "thread_broadcast"
            and (attachments := event.get("attachments", None))
            and len(attachments) == 1
            and "merged" in attachments[0]["pretext"]
        ):
            background_tasks.add_task(_post_button())

    return Response(content="OK", media_type="text/plain")


@app.post("/ping", status_code=200)
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
        "operator_type": "Executive",
        "timestamp": datetime.now().isoformat(),
        "message": (
            "Hi! Ask me to do a simple coding task.\n"
            "I will work with a Developer Operator to break down your prompt "
            "into smaller tasks before combining the work back together.\n"
            "Press `Submit` to get started!"
        ),
        "completed": False,
    }
    await manager.send_json(payload, websocket)

    payload = {
        "operator_type": "Developer",
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
            async for operator_type, message in so.process_new_project(
                starting_prompt=data, deploy=False, use_celery=False
            ):
                result = message

                payload = {
                    "operator_type": operator_type,
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
                "operator_type": "EXECUTIVE",
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
