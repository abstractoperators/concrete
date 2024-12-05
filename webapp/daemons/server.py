# import hashlib
# import hmac
# import json
# from uuid import UUID
import argparse
import os
import time

# from abc import abstractmethod
from abc import ABC
from typing import Any, Callable

# from concrete.tools.knowledge import KnowledgeGraphTool
# from concrete_db import crud
# from concrete_db.orm import Session
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# from concrete.clients.openai import OpenAIClient
# from concrete.models.messages import NodeUUID
# from concrete.operators import Executive, Operator
from concrete.clients.http import HTTPClient
from concrete.operators import Operator

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


# region GitHub Daemon
# class GitHubDaemon(Daemon):
#     """
#     Represents a GitHub PR Daemon.
#     Daemon can act on many installations, orgs/repos/branches.
#     """

#     def __init__(self, org='abstractoperators', repo='concrete', operator: Operator = Operator()):
#         super().__init__(operator=operator, route="/github/webhook")

#         # Generate Installation (Access) Token
#         gh_client_id = os.getenv('GH_CLIENT_ID')
#         if not gh_client_id:
#             raise HTTPException(status_code=500, detail="GH_CLIENT_ID is not set")
#         jwt_token: JwtToken = JwtToken(key_name='GH_PRIVATE_KEY', iss=gh_client_id)
#         self.installation_token: InstallationToken = InstallationToken(jwt_token)

#         self.org = org
#         self.repo = repo

#         self.open_revisions: dict[str, str] = {}  # {source branch: revision branch}
#         self.org = "abstractoperators"
#         self.repo = "concrete"

#     @staticmethod
#     def _verify_signature(payload_body, signature_header):
#         """Verify that the payload was sent from GitHub by validating SHA256.
#         https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
#         Raise and return 403 if not authorized.

#         Args:
#             payload_body: original request body to verify (request.body())
#             secret_token: GitHub app webhook token (WEBHOOK_SECRET)
#             signature_header: header received from GitHub (x-hub-signature-256)
#         """
#         GH_WEBHOOK_SECRET = os.environ.get("GH_WEBHOOK_SECRET")
#         if not GH_WEBHOOK_SECRET:
#             raise HTTPException(status_code=500, detail="GH_WEBHOOK_SECRET is not set")

#         if not signature_header:
#             raise HTTPException(status_code=403, detail="x-hub-signature-256 header is missing")

#         hash_object = hmac.new(
#             GH_WEBHOOK_SECRET.encode("utf-8"),
#             msg=payload_body,
#             digestmod=hashlib.sha256,
#         )

#         expected_signature = "sha256=" + hash_object.hexdigest()
#         if not hmac.compare_digest(expected_signature, signature_header):
#             raise HTTPException(status_code=403, detail="Request signatures didn't match")

#     async def webhook_handler(self, request: Request, background_tasks: BackgroundTasks):
#         """
#         Receive and respond to GH webhook events.
#         """
#         raw_payload = await request.body()
#         signature = request.headers.get("x-hub-signature-256")
#         try:
#             self._verify_signature(raw_payload, signature)
#         except HTTPException as e:
#             return {"error": str(e.detail)}, e.status_code

#         payload: dict = json.loads(raw_payload)
#         self.installation_token.set_installation_id(payload.get("installation", {}).get("id", ""))

#         if payload.get("pull_request", None):
#             action = payload.get("action", None)
#             sender = payload.get("sender", {}).get("login", "")
#             base = payload.get("pull_request", {}).get("base", {}).get("ref", "")
#             if sender != "concreteoperator[bot]":
#                 CLIClient.emit(f"Received PR event: {action}")
#                 if action == "opened" or action == "reopened":
#                     # Open and begin working on a revision branch
#                     branch_name = payload["pull_request"]["head"]["ref"]
#                     background_tasks.add_task(self._start_revision, branch_name, base)

#                 elif action == "closed":
#                     # Close and delete the revision branch
#                     branch_name = payload["pull_request"]["head"]["ref"]
#                     background_tasks.add_task(self._close_revision, branch_name)

#     def _start_revision(self, source_branch: str, source_target: str = "main"):
#         """
#         Serial execution of creating a revision branch + commits + PR.
#         """
#         revision_branch = f"ghdaemon/revision/{source_branch}"
#         self.open_revisions[source_branch] = revision_branch

#         CLIClient.emit(f"Creating revision branch: {revision_branch}")
#         GithubTool.create_branch(
#             org=self.org,
#             repo=self.repo,
#             new_branch=revision_branch,
#             base_branch=source_branch,
#             access_token=self.installation_token.token,
#         )

#         root_node_id = KnowledgeGraphTool._get_node_by_path(org=self.org, repo=self.repo, branch=revision_branch)
#         if root_node_id is None:
#             CLIClient.emit(f"Fetching revision branch contents: {revision_branch}")
#             root_path = GithubTool.fetch_branch(
#                 org=self.org,
#                 repo=self.repo,
#                 branch=revision_branch,
#                 access_token=self.installation_token.token,
#             )

#             CLIClient.emit(f"Creating knowledge graph from revision branch: {revision_branch}")
#             root_node_id = KnowledgeGraphTool._parse_to_tree(
#                 org=self.org,
#                 repo=self.repo,
#                 dir_path=root_path,
#                 rel_gitignore_path=".gitignore",
#                 branch=revision_branch,
#             )
#         else:
#             CLIClient.emit(f"Getting root node {root_node_id} file path")
#             root_path = KnowledgeGraphTool.get_node_path(root_node_id)
#             CLIClient.emit("Root node file path: " + root_path)

#         CLIClient.emit("Finding changed files in source branch/PR")
#         raw_changed_files = GithubTool.get_changed_files(
#             org=self.org,
#             repo=self.repo,
#             base=source_target,
#             head=source_branch,
#             access_token=self.installation_token.token,
#         )
#         changed_files = [file[2:] for (_, file), _ in raw_changed_files]

#         for changed_file in changed_files:
#             full_path_to_file_to_document = os.path.join(root_path, changed_file)
#             CLIClient.emit(f"Creating append-only documentation for {full_path_to_file_to_document}")
#             suggested_documentation_to_append, documentation_dest_path = self.recommend_documentation(
#                 branch=revision_branch,
#                 path=full_path_to_file_to_document,
#             )

#             if suggested_documentation_to_append == "" or documentation_dest_path == "":
#                 CLIClient.emit(f"No documentation to append for {full_path_to_file_to_document}")
#                 continue

#             CLIClient.emit(f"Appending documentation to {documentation_dest_path}. Committing to github.")
#             with open(documentation_dest_path, "a+") as f:
#                 f.write(suggested_documentation_to_append)
#                 f.seek(0)
#                 full_documentation = f.read()

#             # Need to use relpath to get path relative to local root.
#             changed_file = os.path.relpath(documentation_dest_path, root_path)
#             CLIClient.emit(f"Putting changed file {changed_file} to github.")
#             GithubTool.put_file(
#                 org=self.org,
#                 repo=self.repo,
#                 branch=revision_branch,
#                 path=changed_file,
#                 file_contents=full_documentation,
#                 access_token=self.installation_token.token,
#                 commit_message=f"Append documentation for {changed_file}",
#             )

#         CLIClient.emit(f"Creating PR for revision branch: {revision_branch}")
#         GithubTool.create_pr(
#             org=self.org,
#             repo=self.repo,
#             title=f"Revision of {source_branch}",
#             head=revision_branch,
#             base=source_branch,
#             access_token=self.installation_token.token,
#         )

#     def _close_revision(self, source_branch: str):
#         revision_branch = self.open_revisions.get(source_branch, None)
#         CLIClient.emit(f"Closing revision branch: {revision_branch}")
#         if not revision_branch:
#             return
#         GithubTool.delete_branch(
#             org=self.org,
#             repo=self.repo,
#             branch=revision_branch,
#             access_token=self.installation_token.token,
#         )
#         self.open_revisions.pop(source_branch)

#     def navigate_to_documentation(self, node_to_document_id: UUID, cur_id: UUID) -> tuple[bool, UUID]:
#         """
#         Recommends documentation location for a given path.
#         Path refers to a module to be documented (e.g. tools)
#         Returns a boolean to indicate whether an appropriate node exists.
#         Returns current's UUID, which represents the documentation destination node if the boolean is True (e.g. UUID for docs/tools.md) # noqa: E501
#         """  # noqa: E501
#         node_to_document_summary = KnowledgeGraphTool.get_node_summary(node_to_document_id)

#         cur_node_summary = KnowledgeGraphTool.get_node_summary(cur_id)
#         CLIClient.emit(f"Currently @ {cur_node_summary}")
#         cur_children_nodes = KnowledgeGraphTool.get_node_children(cur_id)

#         if not cur_children_nodes:
#             return (True, cur_id)

#         exec = Executive(clients={"openai": OpenAIClient()})
#         next_node_id = exec.chat(
#             f"""You will navigate to the best child to document the following module. Ideally, a the module will be documented in a central location. # noqa
#         Module: {node_to_document_summary}

#         The following are summaries of children you may navigate to: {cur_node_summary}

#         The following is a list of the children's UUIDs.
#         {cur_children_nodes}

#         Think about which child would be most appropriate to document the module in. Then, respond with the UUID of the child node you wish to navigate to. # noqa
#         If you do not believe any children are appropriate, respond with NA.""",  # noqa
#             options={"response_format": NodeUUID},
#         ).node_uuid

#         if next_node_id == "NA":
#             return (False, cur_id)
#         else:
#             return self.navigate_to_documentation(node_to_document_id, UUID(next_node_id))

#     def recommend_documentation(self, branch: str, path: str) -> tuple[str, str]:
#         """
#         Recommends documentation for the file at a given path.
#         Returns a tuple of the (suggested_documentation, documentation_path)
#         """
#         root_node_id = KnowledgeGraphTool._get_node_by_path(org=self.org, repo=self.repo, branch=branch)
#         node_to_document_id = KnowledgeGraphTool._get_node_by_path(
#             org=self.org, repo=self.repo, path=path, branch=branch
#         )
#         if not node_to_document_id or not root_node_id:
#             CLIClient.emit(f"Node not found for {path}")
#             return ("", "")
#         found, documentation_node_id = self.navigate_to_documentation(node_to_document_id, root_node_id)

#         if not found:
#             return ("", "")

#         with Session() as db:
#             documentation_node = crud.get_repo_node(db=db, repo_node_id=documentation_node_id)
#             if documentation_node is None:
#                 CLIClient.emit(f"Documentation node not found for {path}")
#                 return ("", "")
#             documentation_path = documentation_node.abs_path

#         if not found:
#             documentation_path = f"{documentation_path}/{path}.md"
#             with open(documentation_path, "w") as f:
#                 f.write("")

#         with open(documentation_path, "r") as f:
#             existing_documentation = f.read()
#         with open(path, "r") as f:
#             module_contents = f.read()

#         exec = Executive(clients={"openai": OpenAIClient()})
#         suggested_documentation = exec.chat(
#             f"""Your job is to document the following module.
#     Existing Documentation: {existing_documentation}
#     Module Contents: {module_contents}

#     Respond with documentation for the module to be APPENDED to the existing documentation. Meaning, you must follow the style and structure of the existing documentation. Do NOT repeat existing information, return new documentation that is structurally consistent with the existing documentation.""",  # noqa
#         ).text

#         return suggested_documentation, documentation_path
# endregion


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
        return self.operator.chat(message)

    def chat_with_memory(self, message: str) -> str:
        return self.operator.chat('\n'.join(self.memory) + message)

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


class ArgParserNoError(argparse.ArgumentParser):
    """
    Overrides error method to return a message instead of SystemExit
    """

    def error(self, message):
        raise HTTPException(status_code=400, detail=message)


class SlackDaemon(Webhook):
    def __init__(self, operator: Operator):
        super().__init__()
        self.routes['/slack/events'] = self.event_subscriptions
        self.routes['/slack/slash_commands'] = self.slash_commands

        # self.operators: dict[str, Any] = {}  # Slack workspace: Operator

        self.personas = {
            'jaime': SlackPersona(
                instructions="You are the persona of a slack chat bot. Your name is Jaime. Assist users in the workspace.",  # noqa
                icon=":robot_face:",
                username="Jaime",
            )
        }

        self.init_slashcommand_parser()

    def init_slashcommand_parser(self):
        self.arg_parser = ArgParserNoError("Jaime Bot is a slack bot that can create personas which chat with users.")

        subparsers = self.arg_parser.add_subparsers(dest="subcommand")

        new_persona_parser = subparsers.add_parser("new", help="Create a new persona")
        update_persona_parser = subparsers.add_parser("update", help="Update a persona")
        delete_persona_parser = subparsers.add_parser("delete", help="Delete a persona")
        get_persona_parser = subparsers.add_parser("get", help="Get a persona or a list of persona names")

        new_persona_parser.add_argument(
            "name",
            type=str,
            help="The name of the persona",
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
            "name",
            type=str,
            help="The name of the persona",
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
            "name",
            type=str,
            help="The name of the persona",
        )

        get_persona_parser.add_argument(
            "--name",
            type=str,
            help="The name of the persona",
            required=False,
        )

    async def slash_commands(self, request: Request, background_tasks: BackgroundTasks):
        json_data = await request.form()

        team_id = json_data.get('team_id')
        command = json_data.get('command')

        def handle_command(command):
            if command == "/jaime":
                args = self.arg_parser.parse_args(command.split(' '))

                if args.subcommand == 'new':
                    if args.name in self.personas:
                        return Response(content=f'Persona {args.name} already exists')
                    self.new_persona(persona_name=args.name, instructions=args.instructions, icon=args.icon)
                    return Response(content=f'Created persona {args.name}')

                elif args.subcommand == 'update':
                    if args.name not in self.personas:
                        return Response(content=f'Persona {args.name} does not exist')
                    persona = self.personas[args.name]
                    persona.update_instructions(args.instructions)
                    return Response(content=f'Updated instructions for persona {args.name}')

                elif args.subcommand == 'delete':
                    if args.name not in self.personas:
                        return Response(content=f'Persona {args.name} does not exist')
                    self.personas.pop(args.name)

                elif args.subcommand == 'get':
                    if args.name:
                        if args.name not in self.personas:
                            return Response(content=f'Persona {args.name} does not exist')
                        persona = self.personas[args.name]
                        return Response(content=f'Persona {args.name}:\n{persona.get_instructions()}')

                    return Response(content='\n'.join(self.personas.keys()))

        background_tasks.add_task(handle_command, command)
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
