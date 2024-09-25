import hashlib
import hmac
import json
import os
import time
from abc import ABC, abstractmethod

import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from concrete.clients import CLIClient
from concrete.tools import GithubTool, KnowledgeGraphTool, RestApiTool

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


class Webhook(ABC):
    """
    Represents a Webhook.
    """

    def __init__(self, route: str):
        self.route = route

    @abstractmethod
    async def webhook_handler(self, request: Request):
        pass


class JwtToken:
    """
    Represents a JWT token for GitHub App authentication.
    Manages token expiry and generation.
    """

    def __init__(self):
        self._token: str = ""  # nosec
        self._expiry: float = 0
        self.PRIVATE_KEY_PATH: str = os.environ.get("GH_PRIVATE_KEY_PATH")
        try:
            with open(self.PRIVATE_KEY_PATH, 'rb') as pem_file:
                self.signing_key = pem_file.read()
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Failed to read private key")

        self.GH_APP_CLIENT_ID = os.environ.get("GH_CLIENT_ID")
        if not self.GH_APP_CLIENT_ID:
            raise HTTPException(status_code=500, detail="GH_CLIENT_ID is not set")

    @property
    def token(self):
        if not self._token or self._is_expired():
            self._generate_jwt()
        return self._token

    def _is_expired(self):
        return not self._expiry or self._expiry < time.time()

    def _generate_jwt(self):
        iat = int(time.time())
        exp = iat + 600
        payload = {
            'iat': iat,
            'exp': exp,
            'iss': self.GH_APP_CLIENT_ID,
        }
        self._token = jwt.encode(payload, self.signing_key, algorithm='RS256')
        self._expiry = exp

    def get_jwt(self) -> tuple[str, int]:
        return self.token


class InstallationToken:
    """
    Represents an Installation Access Token for GitHub App authentication.
    """

    def __init__(self, jwt_token: JwtToken, installation_id: str = ""):
        self._token: str = ""  # nosec
        self._expiry: float = 0
        self.jwt_token = jwt_token
        self.installation_id: str = ""

    def _is_expired(self):
        return not self._expiry or self._expiry < time.time()

    def _generate_installation_token(self):
        """
        installation_id (str): GitHub App installation ID. Can be found in webhook payload, or from GitHub API.
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.jwt_token.token}",
            "X-GitHub-Version": "2022-11-28",
        }
        url = f'https://api.github.com/app/installations/{self.installation_id}/access_tokens'

        self._expiry = int(time.time() + 3600)
        token = RestApiTool.post(url=url, headers=headers).get('token', '')
        self._token = token

    @property
    def token(self) -> str:
        if not self._token or self._is_expired():
            self._generate_installation_token()
        return self._token

    def set_installation_id(self, installation_id: str):
        self.installation_id = installation_id


class AOGitHubDaemon(Webhook):
    """
    Represents a GitHub PR Daemon.
    Daemon can act on many installations, orgs/repos/branches.
    TODO: AOGitHubDaemon -> GitHubDaemon. Should be installable on any repository, and not hardcoded to abop.
    """

    def __init__(self):
        super().__init__("/github/webhook")
        self.installation_token: InstallationToken = InstallationToken(JwtToken())
        self.open_revisions: dict[str, str] = {}  # {source branch: revision branch}
        self.org = 'abstractoperators'
        self.repo = 'concrete'

    @staticmethod
    def _verify_signature(payload_body, signature_header):
        """Verify that the payload was sent from GitHub by validating SHA256.
        https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
        Raise and return 403 if not authorized.

        Args:
            payload_body: original request body to verify (request.body())
            secret_token: GitHub app webhook token (WEBHOOK_SECRET)
            signature_header: header received from GitHub (x-hub-signature-256)
        """
        GH_WEBHOOK_SECRET = os.getenv("GH_WEBHOOK_SECRET")
        if not GH_WEBHOOK_SECRET:
            raise HTTPException(status_code=500, detail="GH_WEBHOOK_SECRET is not set")

        if not signature_header:
            raise HTTPException(status_code=403, detail="x-hub-signature-256 header is missing")

        hash_object = hmac.new(GH_WEBHOOK_SECRET.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)

        expected_signature = "sha256=" + hash_object.hexdigest()
        if not hmac.compare_digest(expected_signature, signature_header):
            raise HTTPException(status_code=403, detail="Request signatures didn't match")

    async def webhook_handler(self, request: Request):
        """
        Receive and respond to GH webhook events.
        """
        raw_payload = await request.body()
        signature = request.headers.get("x-hub-signature-256")
        try:
            self._verify_signature(raw_payload, signature)
        except HTTPException as e:
            return {"error": str(e.detail)}, e.status_code

        payload: dict = json.loads(raw_payload)
        self.installation_token.set_installation_id(payload.get('installation', {}).get('id', ''))

        if payload.get('pull_request', None):
            action = payload.get('action', None)
            sender = payload.get('sender', 
            CLIClient.emit(f"Received PR event: {action}")
            if action == 'opened' or action == 'reopened':
                # Open and begin working on a revision branch
                branch_name = payload['pull_request']['head']['ref']
                self._start_revision(branch_name)

            elif action == 'closed':
                # Close and delete the revision branch
                branch_name = payload['pull_request']['head']['ref']
                self._close_revision(branch_name)

    def _start_revision(self, source_branch: str):
        """
        Serial execution of creating a revision branch + commits + PR.
        """
        revision_branch = f'ghdaemon/revision/{source_branch}'
        self.open_revisions[source_branch] = revision_branch

        CLIClient.emit(f"Creating revision branch: {revision_branch}")
        GithubTool.create_branch(
            org=self.org,
            repo=self.repo,
            new_branch=revision_branch,
            base_branch=source_branch,
            access_token=self.installation_token.token,
        )

        CLIClient.emit(f"Creating PR for revision branch: {revision_branch}")
        GithubTool.create_pr(
            org=self.org,
            repo=self.repo,
            title=f"Revision of {source_branch}",
            branch=revision_branch,
            base=source_branch,
            access_token=self.installation_token.token,
        )

        CLIClient.emit(f"Fetching revision branch contents: {revision_branch}")
        branch_contents_path = GithubTool.fetch_branch(
            org=self.org,
            repo=self.repo,
            branch=revision_branch,
            access_token=self.installation_token.token,
        )

        CLIClient.emit(f"Creating knowledge graph from revision branch: {revision_branch}")
        root_node_id = KnowledgeGraphTool._parse_to_tree(
            org=self.org, repo=self.repo, dir_path=branch_contents_path, rel_gitignore_path='.gitignore'
        )

        CLIClient.emit(str(root_node_id))
        # GithubTool.put_file(
        #     org=self.org,
        #     repo=self.repo,
        #     branch=revision_branch,
        #     path='foobarbaz.md',
        #     file_contents="This is a revision branch.",
        #     access_token=self.installation_token.token,
        #     commit_message="Add foobarbaz.md",
        # )

    def _close_revision(self, source_branch: str):
        revision_branch = self.open_revisions.get(source_branch, None)
        if not revision_branch:
            return
        GithubTool.delete_branch(
            org=self.org,
            repo=self.repo,
            branch=revision_branch,
            access_token=self.installation_token.token,
        )
        self.open_revisions.pop(source_branch)


hooks = [gh_daemon := AOGitHubDaemon()]
for hook in hooks:
    app.add_api_route(hook.route, hook.webhook_handler, methods=["POST"])
