from typing import cast

from concrete.utils import verify_jwt
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


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
