import argparse
import logging
import os
import shlex
import time
from abc import ABC
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Callable
from uuid import UUID, uuid4

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from webapp_common import JwtToken, LoggerMiddleware

from concrete.clients.http import HTTPClient
from concrete.operators import Operator
from concrete.tools.arxiv import ArxivTool
from concrete.tools.document import DocumentTool
from concrete.tools.http import RestApiTool
from concrete.webutils import AuthMiddleware, verify_slack_request

abspath = os.path.abspath(__file__)

dname = os.path.dirname(abspath)

logging.basicConfig(
    level=logging.DEBUG,
    filename=os.path.join(dname, "server.log"),
    filemode="w",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# slack commands are authenticated by Slack signing secret.
UNAUTHENTICATED_PATHS = {
    "/",
    "/logs",
    "/docs",
    "/ping",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/slack/slash_commands",
}

# Setup App with Middleware
middleware = [
    Middleware(
        SessionMiddleware,
        secret_key=os.getenv("HTTP_SESSION_SECRET"),
        domain=os.getenv("HTTP_SESSION_DOMAIN"),
    ),
    Middleware(AuthMiddleware, exclude_paths=UNAUTHENTICATED_PATHS),
    Middleware(LoggerMiddleware, logger=logger),
]


app = FastAPI(title="Agent Server", middleware=middleware)

templates = Jinja2Templates(directory=os.path.join(dname, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(dname, "static")), name="static")

# TODO: Stateful Operators using concrete-db. Remove from memory.
operators: dict[UUID, Operator] = {}


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/logs")
def get_logs():
    with open(dname + "/server.log", "r") as f:
        return f.read()


@app.get("/ping")
def ping():
    return {"message": "pong"}


load_dotenv('.env', override=True)


@app.get("/operators")
def list_operators() -> dict:
    """
    List all operators.
    """
    return {"operators": list(operators.keys())}


@app.get("/operators/{operator_id}")
def get_operator(operator_id: UUID) -> dict:
    """
    Get details for an Operator.

    Returns:
    TODO: More detailed response
    """

    if operator_id not in operators:
        raise HTTPException(status_code=404, detail="Operator not found")

    return {
        'instructions': operators[operator_id].instructions,
        'operator_id': operator_id,
        "tools": [
            tool.__name__ for tool in operators[operator_id].tools
        ],  # TODO: Structured tool response (sqlmodel maybe?)
    }


@app.post("/chat/{operator_id}")
async def chat_with_operator(operator_id: UUID, request: Request) -> str:
    """
    Chat with an operator.
    """
    data = await request.json()
    message = data.get('message', '')
    if operator_id not in operators:
        raise HTTPException(status_code=404, detail="Operator not found")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    operator = operators[operator_id]
    return operator.chat(message).text


@app.delete("/operators/{operator_id}")
def delete_operator(operator_id: UUID) -> dict:
    """
    Delete an operator.
    """
    if operator_id not in operators:

        raise HTTPException(status_code=404, detail="Operator not found")
    operators.pop(operator_id)
    return {"message": "Operator deleted", "operator_id": operator_id}


@app.post("/operators/{operator_id}")
def create_operator(instructions: str) -> dict:
    """
    Create an operator.
    """
    operator_id = uuid4()
    operator = Operator(
        tools=[ArxivTool, DocumentTool],
        use_tools=True,
        operator_id=operator_id,
    )
    operator.instructions = instructions
    operators[operator_id] = operator

    return get_operator(operator_id)


@app.patch("/operators/{operator_id}")
def update_operator(operator_id: UUID, instructions: str) -> dict:
    if operator_id not in operators:
        raise HTTPException(status_code=404, detail="Operator not found")
    operators[operator_id].instructions = instructions
    return {"message": "Operator updated", "operator_id": operator_id}


class Webhook(ABC):
    """
    Represents a Webhook.
    """

    def __init__(self):
        self.routes: dict[str, Callable] = {}


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
        persona_name: str,
        instructions: str = "",
        icon: str = "smiley",
        uuid: UUID | None = None,
    ):
        # New Operator
        if not uuid or uuid not in operators:
            self.operator_id = create_operator(instructions)['operator_id']
        else:
            self.operator_id = uuid

        self.icon: str = icon
        self.username = persona_name
        self.memory: list[str] = []

    @property
    def operator(self) -> Operator | None:
        return operators.get(self.operator_id)

    def chat_no_memory(self, message: str) -> str:
        if not self.operator:
            raise ValueError("Operator not found")
        return self.operator.chat(message).text

    def chat_with_memory(self, message: str) -> str:
        if not self.operator:
            raise ValueError("Operator not found")
        return self.operator.chat('\n'.join(self.memory) + message).text

    def append_memory(self, message: str) -> None:
        self.memory.append(message)

    def clear_memory(self) -> None:
        self.memory = []

    def update_instructions(self, instructions: str) -> None:
        if not self.operator:
            raise ValueError("Operator not found")
        self.operator.instructions = instructions

    def update_icon(self, icon: str) -> None:
        self.icon = icon

    def get_instructions(self) -> str:
        if not self.operator:
            raise ValueError("Operator not found")
        return self.operator.instructions

    def get_memory(self) -> list[str]:
        return self.memory

    def get_icon(self) -> str:
        return self.icon

    def post_message(self, token: str, channel: str, message):
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

        HTTPClient().post(url=endpoint, headers=headers, json=payload)


class SlackDaemon(Webhook):
    def __init__(self):
        super().__init__()
        self.routes['/slack/slash_commands'] = self.slash_commands

        self.personas = {
            'jaime': SlackPersona(
                instructions="You are the persona of a slack chat bot. Your name is Jaime. Assist users in the workspace.",  # noqa
                icon="robot_face",
                persona_name="Jaime",
            )
        }

        self.http_client = HTTPClient()
        self.signing_secret = os.getenv('SLACK_SIGNING_SECRET')
        if not self.signing_secret:
            raise Exception("Slack signing secret not found")

        def init_slashcommand_parser():
            self.arg_parser = argparse.ArgumentParser(
                description="Jaime Bot is a slack bot that can create personas which chat with users.",
                prog="/jaime",
            )

            subparsers = self.arg_parser.add_subparsers(dest="subcommand")
            subparsers.required = True

            new_persona_parser = subparsers.add_parser("new-persona", help="Create a new persona")
            update_persona_parser = subparsers.add_parser("update-persona", help="Update a persona")
            delete_persona_parser = subparsers.add_parser("delete-persona", help="Delete a persona")
            get_persona_parser = subparsers.add_parser(
                "get-persona",
                help=(
                    "Get a persona or a list of persona names. Provide a name to get a specific persona."
                    "Leave blank to get a list of persona names."
                ),
            )
            chat_persona_parser = subparsers.add_parser("chat", help="Chat with a persona")
            arxiv_papers_parser = subparsers.add_parser("add-arxiv-paper", help="Add an arXiv paper to RAG database")

            new_persona_parser.add_argument("name", type=str, help="The name of the persona to create.")
            new_persona_parser.add_argument(
                "--instructions",
                type=str,
                help="The instructions for the persona.",
                default="You are a slack bot persona.",
                required=False,
            )
            new_persona_parser.add_argument(
                "--icon", type=str, help="The icon for the persona (e.g. smiley)", default="smiley", required=False
            )
            new_persona_parser.add_argument(
                "--uuid",
                type=UUID,
                help="The existing operator uuid for the persona to be created from",
                required=False,
            )

            update_persona_parser.add_argument("name", type=str, help="The name of the persona to update.")
            update_persona_parser.add_argument(
                "--instructions", type=str, help="The instructions for the persona.", required=False
            )
            update_persona_parser.add_argument(
                "--icon", type=str, help="The icon for the persona (e.g. smiley)", required=False
            )
            update_persona_parser.add_argument(
                "--clear-memory", action="store_true", help="Clear the memory of the persona", required=False
            )

            delete_persona_parser.add_argument("name", type=str, help="The name of the persona to delete")

            get_persona_parser.add_argument(
                "name", type=str, help="The name of the persona to get", nargs="?", default=None
            )

            chat_persona_parser.add_argument("name", type=str, help="The name of the persona to chat with")
            chat_persona_parser.add_argument("message", type=str, help="The message to send to the persona")

            arxiv_papers_parser.add_argument("id", type=str, help="The arXiv paper ID to add (e.g. 2308.08155)")

        init_slashcommand_parser()

    def respond(self, response_url: str, text: str, response_type: str = 'in_channel'):
        """
        Responds to a slack slash command with a message.
        response_url: URL provided with the original slash command payload
        text: Message to send
        response_type: in_channel or ephemeral
        """
        logger.info(f'Responding to slack {response_url} with {text}')
        self.http_client.post(
            url=response_url,
            json={
                'text': text,
                'response_type': response_type,
                'icon_emoji': ':robot_face:',
            },
        )

    async def slash_commands(self, request: Request, background_tasks: BackgroundTasks):
        def handle_command(args: argparse.Namespace) -> None:
            """
            Potentially can take a long time to run.
            """
            subcommand = args.subcommand
            response_url = json_data.get('response_url')

            if subcommand == 'chat':
                if args.name not in self.personas:
                    self.respond(
                        response_url=response_url,
                        text=f'Persona {args.name} does not exist',
                    )
                else:
                    persona = self.personas[args.name]
                    resp = persona.chat_with_memory(args.message)
                    persona.append_memory(f'User {json_data.get("user_id")}: {args.message}')
                    persona.append_memory(f'Assistant {args.name}: {resp}')

                    persona.post_message(
                        token=os.getenv('SLACK_BOT_TOKEN'),
                        channel=json_data.get('channel_id'),
                        message=resp,
                    )
            else:
                if subcommand == 'new-persona':
                    self.new_persona(
                        persona_name=args.name,
                        response_url=response_url,
                        instructions=args.instructions,
                        icon=args.icon,
                        uuid=args.uuid,
                    )

                elif subcommand == 'update-persona':
                    self.update_persona(
                        persona_name=args.name,
                        response_url=response_url,
                        instructions=args.instructions,
                        icon=args.icon,
                        clear_memory=args.clear_memory,
                    )

                elif subcommand == 'delete-persona':
                    self.delete_persona(
                        persona_name=args.name,
                        response_url=response_url,
                    )

                elif subcommand == 'get-persona':
                    self.get_persona_uuid(
                        persona_name=args.name,
                        response_url=response_url,
                    )

                elif subcommand == 'add-arxiv-paper':
                    self.respond(
                        response_url=response_url,
                        text=f'Adding ArXiv paper {args.id} to RAG database...',
                    )
                    documents = ArxivTool.get_arxiv_paper_as_llama_document(id=args.id)
                    self.respond(
                        response_url=response_url,
                        text=f'ArXiv paper {args.id} retrieved. Chunked into {len(documents)} documents',
                    )
                    for i, document in enumerate(documents):
                        self.respond(
                            response_url=response_url,
                            text=f'Adding document {i + 1} of {len(documents)} to RAG database...',
                        )
                        DocumentTool.index.insert(document)

                    self.respond(
                        response_url=response_url,
                        text=f'ArXiv paper {args.id} added to RAG database',
                    )

        if not await verify_slack_request(slack_signing_secret=self.signing_secret, request=request):
            return JSONResponse(
                content={"error": "Request not from Slack"},
                status_code=401,
            )

        json_data = await request.form()

        text = json_data.get('text').strip()
        args = shlex.split(text)

        # argparse is designed to be CLI, so we need to redirect stdout and stderr to capture help messages
        buf = StringIO()
        parsed_args = None
        try:
            with redirect_stderr(buf), redirect_stdout(buf):  # -h goes to stdout, parse errors go to stderr
                parsed_args = self.arg_parser.parse_args(args)
            background_tasks.add_task(handle_command, parsed_args)
            return JSONResponse(
                content={
                    "response_type": "in_channel",
                    "text": f'Processing command from {json_data.get("user_id")}: {text}',
                },
            )
        except SystemExit:  # Immediately return a help message if the command is invalid
            return JSONResponse(
                content={
                    "response_type": "in_channel",
                    "text": buf.getvalue(),
                },
                status_code=200,
            )

    def update_persona(
        self,
        persona_name: str,
        response_url: str,
        instructions: str | None = None,
        icon: str | None = None,
        clear_memory: bool = False,
    ):
        persona = self.get_persona(persona_name)
        if not persona:
            logger.info(f'Failed to get persona {persona_name}. Does not exist')
            self.respond(
                response_url=response_url,
                text=f'Persona {persona_name} does not exist',
            )
        else:
            if instructions:
                persona.update_instructions(instructions)
            if icon:
                persona.update_icon(icon)
            if clear_memory:
                persona.clear_memory()
            logger.info(f'Persona {persona_name} updated')
            self.respond(
                response_url=response_url,
                text=f'Persona {persona_name} updated',
            )

    def delete_persona(self, persona_name: str, response_url: str):
        persona = self.get_persona(persona_name)
        if not persona:
            logger.info(f'Failed to get persona {persona_name} to delete. Does not exist')
            self.respond(
                response_url=response_url,
                text=f'Persona {persona_name} does not exist',
            )
        else:
            self.personas.pop(persona_name)
            logger.info(f'Persona {persona_name} deleted')
            self.respond(
                response_url=response_url, text=f'Persona {persona_name} deleted'
            ),  # Doesn't delete the operator

    def new_persona(
        self,
        persona_name: str,
        response_url: str,
        instructions: str = "",
        icon: str = 'robot_face',
        uuid: UUID | None = None,
    ):
        """
        Creates a new persona.
        Responds with a message to the user.
        """
        if self.get_persona(persona_name):
            logger.info(f'Failed to create persona {persona_name}. Already exists')
            self.respond(
                response_url=response_url,
                text=f'Persona {persona_name} already exists',
            )
        else:
            persona = SlackPersona(persona_name=persona_name, instructions=instructions, icon=icon, uuid=uuid)
            self.personas[persona_name] = persona
            logger.info(f'Persona {persona_name} created')
            self.respond(
                response_url=response_url,
                text=f'Persona {persona_name} with operator uuid {persona.operator_id} created',
            )

    def get_persona(
        self,
        persona_name: str,
    ) -> SlackPersona | None:
        """
        Gets a SlackPersona.
        Deletes the persona if the operator no longer exists
        Returns None if the Persona does not exist, or if the Operator does not exist.
        """

        persona = self.personas.get(persona_name)
        if not persona:
            return None
        if not persona.operator:
            self.personas.pop(persona_name)
            return None
        return persona

    def get_persona_uuid(
        self,
        persona_name: str | None,
        response_url: str,
    ):
        """
        Gets a persona or personas
        Responds with a message of the persona or list of personas to the user.
        """
        if persona_name:
            if not self.get_persona(persona_name):
                logger.info(f'Failed to get persona {persona_name}. Does not exist')
                self.respond(
                    response_url=response_url,
                    text=f'Persona {persona_name} does not exist',
                )
            else:
                persona = self.personas[persona_name]
                text = (
                    f'Persona: {persona_name}\n'
                    f'Instructions: {persona.get_instructions()}\n'
                    f'UUID: {persona.operator_id}'
                )
                logger.info(f'Got persona {persona_name} {text}')
                self.respond(
                    response_url=response_url,
                    text=text,
                )

        else:
            text_list: list[str] = []
            for name in self.personas:
                if persona := self.get_persona(name):
                    text_list.append(
                        f'Persona: {name}\n'
                        f'Instructions: {persona.get_instructions()}\n'
                        f'UUID: {persona.operator_id}'
                    )
            text = '\n'.join(text_list)

            logger.info(f'Got list of personas {text}')
            self.respond(
                response_url=response_url,
                text=text,
            )


routers = [slack_daemon := SlackDaemon()]
for router in routers:
    for route, handler in router.routes.items():
        app.add_api_route(route, handler, methods=["POST"])
