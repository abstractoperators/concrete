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

jwt_token = None


class Jwt_Token:
    token = None
    expiry = None

    def __init__(self):
        self.PRIVATE_KEY_PATH = 'concretedaemon.2024-09-04.private-key.pem'


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
    print(installation_id := payload['installation']['id'])  # noqa

    encoded_jwt = generate_JWT()
    installation_token = generate_installation_access_token(installation_id, encoded_jwt)
    print(installation_token)
    return {"message": f"Received {payload['action']} event"}


def generate_JWT() -> str:
    global jwt_token
    if not jwt_token or jwt_token.jwt_expiry < time.time():
        jwt_token = 1  # new token

    PRIVATE_KEY_PATH = 'concretedaemon.2024-09-04.private-key.pem'
    with open(PRIVATE_KEY_PATH, 'rb') as pem_file:
        signing_key = pem_file.read()

    GH_APP_CLIENT_ID = os.getenv("GH_CLIENT_ID")
    if not GH_APP_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GH_CLIENT_ID is not set")

    payload = {
        'iat': int(time.time()),
        'exp': int(time.time()) + 600,
        'iss': GH_APP_CLIENT_ID,
    }

    encoded_jwt = jwt.encode(payload, signing_key, algorithm='RS256')
    return encoded_jwt


def generate_installation_access_token(installation_id: int, encoded_jwt: str):
    """
    installation_id (int): GitHub App installation ID. Can be found in webhook payload body.
    encoded_jwt (str): JWT token generated by generate_JWT() function.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {encoded_jwt}",
        "X-GitHub-Version": "2022-11-28",
    }
    url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
    token = RestApiTool.post(url=url, headers=headers)
    token = token['token']
    return token


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
