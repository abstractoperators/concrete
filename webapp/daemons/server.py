import hashlib
import hmac
import json
import os
import time

import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from concrete.tools import RestApiTool

# TODO: Manage key expiry instead of generating a new JWT and Installation Access token every time.

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


class Jwt_Token:
    """
    Represents a JWT token for GitHub App authentication.
    Manages token expiry and generation.
    """

    def __init__(self):
        self._token = ""  # nosec
        self._expiry = 0
        self.PRIVATE_KEY_PATH = 'concretedaemon.2024-09-04.private-key.pem'
        try:
            with open(self.PRIVATE_KEY_PATH, 'rb') as pem_file:
                self.signing_key = pem_file.read()
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Failed to read private key")

        self.GH_APP_CLIENT_ID = os.getenv("GH_CLIENT_ID")
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


class Installation_Token:
    """
    Represents an Installation Access Token for GitHub App authentication.
    """

    def __init__(self, jwt_token: Jwt_Token):
        self._token = ""  # nosec
        self._expiry = 0
        self.jwt_token = jwt_token

    def _is_expired(self):
        return not self._expiry or self._expiry < time.time()

    def _generate_installation_token(self, installation_id: str):
        """
        installation_id (str): GitHub App installation ID. Can be found in webhook payload, or from GitHub API.
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.jwt_token.token}",
            "X-GitHub-Version": "2022-11-28",
        }
        url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'

        self._expiry = int(time.time() + 3600)
        token = RestApiTool.post(url=url, headers=headers).get('token', '')
        self._token = token

    def get_token(self, installation_id: str) -> str:
        if not self._token or self._is_expired():
            self._generate_installation_token(installation_id)
        return self._token


jwt_token = Jwt_Token()
installation_token = Installation_Token(jwt_token)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/github/webhook")
async def github_webhook(request: Request):
    """Receive GitHub webhook events."""
    raw_payload = await request.body()
    signature = request.headers.get("x-hub-signature-256")

    try:
        verify_signature(raw_payload, signature)
    except HTTPException as e:
        return {"error": str(e.detail)}, e.status_code

    payload = json.loads(raw_payload)
    installation_id = payload['installation']['id']

    global installation_token
    token = installation_token.get_token(installation_id)
    print(token)
    return {"message": f"Received {payload['action']} event"}


def verify_signature(payload_body, signature_header):
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
