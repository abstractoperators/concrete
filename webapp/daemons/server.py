# import hashlib
# import hmac
# import json
# from uuid import UUID
import argparse
import json
import os
import shlex
import time

# from abc import abstractmethod
from abc import ABC
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any, Callable

import llama_index

# from concrete.tools.knowledge import KnowledgeGraphTool
# from concrete_db import crud
# from concrete_db.orm import Session
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# from concrete.clients.openai import OpenAIClient
# from concrete.models.messages import NodeUUID
# from concrete.operators import Executive, Operator
from concrete.clients.http import HTTPClient
from concrete.operators import Operator
from concrete.tools.arxiv import ArxivTool

# from concrete.tools.github import GithubTool
from concrete.tools.http import RestApiTool
from webapp.common import JwtToken

# from concrete.clients import CLIClient

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)

app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(dname, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(dname, "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/ping")
def ping():
    return {"message": "pong"}


load_dotenv('.env', override=True)


class Webhook(ABC):
    """
    Represents a Webhook.
    """

    def __init__(self):
        self.routes: dict[str, Callable] = {}

    # @abstractmethod
    # async def webhook_handler(self, request: Request, background_tasks: BackgroundTasks):
    #     pass


# class Daemon(Webhook):
#     """
#     Represents a Daemon. Daemons ~ Stance of an Operator
#     """

#     def __init__(self, operator: Operator, route: str):
#         """
#         route (str): The route the daemon listens to.
#         e.g. "/github/webhook"
#         """
#         super().__init__(route)
#         self.operator = operator


class InstallationToken:
    """
    Represents an Installation Access Token for GitHub App authentication.
    """

    def __init__(self, jwt_token: JwtToken, installation_id: str | None = None):
        self._token: str = ""  # nosec
        self.expiry_offset = 3600
        self.exp = None
        self._generated_at = 0
        self.jwt_token = jwt_token
        self.installation_id = installation_id

    def _is_expired(self):
        return self.exp is None or time.time() >= self.exp

    def _generate_installation_token(self):
        """
        installation_id (str): GitHub App installation ID. Can be found in webhook payload, or from GitHub API.
        """
        if not self.installation_id:
            raise HTTPException(status_code=500, detail="Installation ID is not set")

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.jwt_token.token}",
            "X-GitHub-Version": "2022-11-28",
        }
        url = f"https://api.github.com/app/installations/{self.installation_id}/access_tokens"

        self._expiry = int(time.time() + 3600)
        token = RestApiTool.post(url=url, headers=headers).get("token", "")
        self._token = token
        self.exp = int(time.time() + self.expiry_offset)
        self._token = RestApiTool.post(url=url, headers=headers).get('token', '')

    @property
    def token(self) -> str:
        if not self._token or self._is_expired():
            self._generate_installation_token()
        return self._token

    def set_installation_id(self, installation_id: str):
        self.installation_id = installation_id


class SlackPersona:
    """
    Represents a persona in a slack workspace
    """

    def __init__(
        self,
        instructions: str,
        icon: str,
        persona_name: str,
    ):
        self.operator = Operator()
        self.operator.instructions = instructions

        self.icon: str = icon
        self.username: str = persona_name

        self.memory: list[str] = []

    def chat_no_memory(self, message: str) -> str:
        return self.operator.chat(message).text

    def chat_with_memory(self, message: str) -> str:
        return self.operator.chat('\n'.join(self.memory) + message).text

    def append_memory(self, message: str) -> None:
        self.memory.append(message)

    def clear_memory(self) -> None:
        self.memory = []

    def update_instructions(self, instructions: str) -> None:
        self.operator.instructions = instructions

    def update_icon(self, icon: str) -> None:
        self.icon = icon

    def get_instructions(self) -> str:
        return self.operator.instructions

    def get_memory(self) -> list[str]:
        return self.memory

    def get_icon(self) -> str:
        return self.icon

    def post_message_as_persona(self, token: str, channel: str, message):
        endpoint = 'https://slack.com/api/chat.postMessage'
        headers = {
            'Content-type': 'application/json',
            'Authorization': f'Bearer {token}',
        }
        payload = {
            'channel': channel,
            'text': message,
            'icon_emoji': f':{self.icon}:',
            'username': self.username,
        }

        print(payload)
        HTTPClient().post(url=endpoint, headers=headers, json=payload)


class SlackDaemon(Webhook):
    def __init__(self, operator: Operator):
        super().__init__()
        self.routes['/slack/events'] = self.event_subscriptions
        self.routes['/slack/slash_commands'] = self.slash_commands

        self.personas = {
            'jaime': SlackPersona(
                instructions="You are the persona of a slack chat bot. Your name is Jaime. Assist users in the workspace.",  # noqa
                icon=":robot_face:",
                persona_name="Jaime",
            )
        }

        self.init_slashcommand_parser()

    def init_slashcommand_parser(self):
        self.arg_parser = argparse.ArgumentParser(
            description="Jaime Bot is a slack bot that can create personas which chat with users.",
            prog="/jaime",
        )

        subparsers = self.arg_parser.add_subparsers(dest="subcommand")
        subparsers.required = True

        new_persona_parser = subparsers.add_parser("new_persona", help="Create a new persona")
        update_persona_parser = subparsers.add_parser("update_persona", help="Update a persona")
        delete_persona_parser = subparsers.add_parser("delete_persona", help="Delete a persona")
        get_persona_parser = subparsers.add_parser("get_persona", help="Get a persona or a list of persona names")
        chat_persona_parser = subparsers.add_parser("chat", help="Chat with a persona")
        arxiv_papers_parser = subparsers.add_parser("add_arxiv_paper", "Add an arXiv paper to RAG database")

        new_persona_parser.add_argument(
            "--name",
            type=str,
            help="The name of the persona",
            required=True,
        )
        new_persona_parser.add_argument(
            "--instructions",
            type=str,
            help="The instructions for the persona",
            required=False,
        )
        new_persona_parser.add_argument(
            "--icon",
            type=str,
            help="The icon for the persona (e.g. :smiley:)",
            default=":robot_face:",
            required=False,
        )

        update_persona_parser.add_argument(
            "--name",
            type=str,
            help="The name of the persona",
            required=True,
        )
        update_persona_parser.add_argument(
            "--instructions",
            type=str,
            help="The instructions for the persona",
            required=False,
        )
        update_persona_parser.add_argument(
            "--icon",
            type=str,
            help="The icon for the persona (e.g. :smiley:)",
            required=False,
        )

        delete_persona_parser.add_argument(
            "--name",
            type=str,
            help="The name of the persona",
            required=True,
        )

        get_persona_parser.add_argument(
            "--name",
            type=str,
            help="The name of the persona",
            required=False,
        )

        chat_persona_parser.add_argument(
            "--name",
            type=str,
            help="The name of the persona",
            required=True,
        )
        chat_persona_parser.add_argument(
            "--message",
            type=str,
            help="The message to send to the persona",
            required=True,
        )

        arxiv_papers_parser.add_argument(
            "--id",
            type=str,
            help="The arXiv paper ID (e.g. 2308.08155)",
            required=True,
        )

    async def slash_commands(self, request: Request, background_tasks: BackgroundTasks):
        json_data = await request.form()

        team_id = json_data.get('team_id')
        command = json_data.get('command')
        text = json_data.get('text').strip()
        args = shlex.split(text)

        buf = StringIO()
        parsed_args = None
        try:
            # -h is stdout, parse errors go to stderr
            with redirect_stderr(buf), redirect_stdout(buf):
                parsed_args = self.arg_parser.parse_args(args)
        except SystemExit:
            message = {
                "response_type": "in_channel",
                "text": buf.getvalue(),
            }
            return JSONResponse(content=message, status_code=200)

        def handle_command(args: argparse.Namespace) -> str:
            """
            Potentially can take a long time to run.
            """
            subcommand = args.subcommand
            if subcommand == 'chat':
                if args.name not in self.personas:
                    resp = f'Persona {args.name} does not exist'
                    HTTPClient().post(
                        url=json_data.get('response_url'),
                        json={"text": resp},
                    )
                else:
                    persona = self.personas[args.name]
                    resp = persona.chat_no_memory(args.message)
                    persona.append_memory(args.message)

                    persona.post_message_as_persona(
                        token=os.getenv('SLACK_BOT_TOKEN'),
                        channel=json_data.get('channel_id'),
                        message=resp,
                    )
            else:
                if subcommand == 'new_persona':
                    if args.name in self.personas:
                        resp = f'Persona {args.name} already exists'
                    self.new_persona(persona_name=args.name, instructions=args.instructions, icon=args.icon)
                    resp = f'Persona {args.name} created'

                elif subcommand == 'update_persona':
                    if args.name not in self.personas:
                        resp = f'Persona {args.name} does not exist'
                    else:
                        persona = self.personas[args.name]
                        persona.update_instructions(args.instructions)
                        resp = f'Persona {args.name} updated'

                elif subcommand == 'delete_persona':
                    if args.name not in self.personas:
                        resp = f'Persona {args.name} does not exist'
                    else:
                        self.personas.pop(args.name)
                        resp = f'Persona {args.name} deleted'

                elif subcommand == 'get_persona':
                    if args.name:
                        if args.name not in self.personas:
                            resp = f'Persona {args.name} does not exist'
                        else:
                            persona = self.personas[args.name]
                            resp = f'Persona {args.name}:\n{persona.get_instructions()}'
                    else:
                        resp = '\n'.join(self.personas.keys())

                elif subcommand == 'add_arxiv_paper':
                    paper_documents: llama_index.core.schema.Document = ArxivTool._get_llama_documents_from_id(
                        id=args.id
                    )

                response_url = json_data.get('response_url')
                HTTPClient().post(
                    url=response_url,
                    json={"text": resp},
                )

        if parsed_args is not None:
            background_tasks.add_task(handle_command, parsed_args)

        return Response(status_code=200)

    def new_persona(self, persona_name: str, instructions: str = "", icon: str = ':robot_face:'):
        instructions = f'You are a slack bot persona named {persona_name}' + instructions
        icon = icon
        self.personas[persona_name] = SlackPersona(instructions, icon, persona_name)

    async def event_subscriptions(self, request: Request, background_tasks: BackgroundTasks):
        json_data = await request.json()
        team_id = json_data.get('team_id')

        if json_data.get('type') == 'url_verification':
            challenge = json_data.get('challenge')
            return Response(content=challenge, media_type='text/plain')

        elif json_data.get("type") == "event_callback":
            event = json_data.get("event")

            def handle_event(event):
                print(event)
                event_type = event.get('type')
                if event_type == 'app_mention':
                    text = event.get('text', '').replace('<@U07N8UE0NCV>', '').strip()  # TODO: Stop assuming bot id

                    if team_id not in self.operators:
                        self.new_operator(team_id)

                    self.append_operator_history(team_id, f'User: {text}')
                    resp = self.chat_operator(team_id, text)
                    self.append_operator_history(team_id, f'Assistant: {resp}')

                    self.post_message(channel=event.get('channel'), message=resp)

            background_tasks.add_task(handle_event, event)
            return Response(status_code=200)

    def post_message(self, channel: str, message: str):
        """
        Posts a message to a slack channel.
        """
        print(f'Posting message to {channel}: {message}')
        chat_endpoint = 'https://slack.com/api/chat.postMessage'
        headers = {
            'Content-type': 'application/json',
            'Authorization': f'Bearer {os.getenv("SLACK_BOT_TOKEN")}',  # TODO: Workspace independent token
        }

        HTTPClient().post(
            url=chat_endpoint,
            headers=headers,
            json={
                'channel': channel,  # Note, channel_id is only unique within a workspace.
                'text': message,
            },
        )


routers = [slack_daemon := SlackDaemon(Operator())]
for router in routers:
    for route, handler in router.routes.items():
        app.add_api_route(route, handler, methods=["POST"])
