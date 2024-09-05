import hashlib
import hmac
import json
import os
from http.client import HTTPException

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


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
    return {"message": f"Received {payload['action']} event"}


def generate_JWT():
    pass


def verify_signature(payload_body, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256.

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
