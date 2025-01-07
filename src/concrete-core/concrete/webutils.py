import hmac
import time
from typing import cast

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from concrete.utils import verify_jwt


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exclude_paths: set[str] | None = None):
        super().__init__(app)
        self.exclude_paths: set[str] = cast(set[str], (exclude_paths or set()))

    @classmethod
    def check_auth(cls, request: Request) -> dict[str, str] | None:
        access_token = request.session.get("access_token")
        id_token = request.session.get("id_token")
        if not access_token or not id_token:
            request.session.clear()
            return None

        try:
            payload = verify_jwt(id_token, access_token)
        except AssertionError:
            request.session.clear()
            return None
        return payload

    async def dispatch(self, request: Request, call_next):
        if request.url.path not in self.exclude_paths:
            user_data = AuthMiddleware.check_auth(request)
            if user_data is None:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Missing or invalid authentication credentials"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
        return await call_next(request)


async def verify_slack_request(slack_signing_secret: str, request: Request) -> bool:
    """
    Verify the request is coming from Slack by checking the request signature.
    https://api.slack.com/authentication/verifying-requests-from-slack

    TODO: Pass in timestamp/signature as arguments instead of reading from request headers.
    Maybe pass in basestring as well.
    """

    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")

    if not timestamp or not signature:
        return False

    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    sig_basestring = f'v0:{timestamp}:{body.decode("utf-8")}'

    my_signature = (
        'v0='
        + hmac.new(
            slack_signing_secret.encode(),
            sig_basestring.encode(),
            'sha256',
        ).hexdigest()
    )

    return hmac.compare_digest(my_signature, signature)
