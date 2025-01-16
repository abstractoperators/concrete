import json
import logging
import traceback
import uuid

from fastapi import HTTPException, Request
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware


class RequestInfo:

    def __init__(self, request: Request) -> None:
        self.request: Request = request

    @property
    def method(self) -> str:
        return str(self.request.method)

    @property
    def route(self) -> str:
        return self.request["path"]

    @property
    def ip(self) -> str:
        if self.request.client is None:
            return "UNKNOWN"
        return str(self.request.client.host)

    @property
    def url(self) -> str:
        return str(self.request.url)

    @property
    def host(self) -> str:
        return str(self.request.url.hostname)

    @property
    def headers(self) -> dict:
        # I asked chatgpt for headers that are safe and useful to log
        safe_headers = {
            'accept': self.request.headers.get('accept'),
            'accept-encoding': self.request.headers.get('accept-encoding'),
            'host': self.request.headers.get('host'),
            'content-type': self.request.headers.get('content-type'),
            'content-length': self.request.headers.get('content-length'),
            'connection': self.request.headers.get('connection'),
            'x-request-id': self.request.headers.get('x-request-id'),
            'x-correlation-id': self.request.headers.get('x-correlation-id'),
        }
        return {k: v for k, v in safe_headers.items() if v is not None}

    @property
    def body(self) -> dict:
        return self.request.state.body


class RequestLog(BaseModel):
    req_id: str
    method: str
    route: str
    ip: str
    url: str
    host: str
    body: dict
    headers: dict


class ErrorLog(BaseModel):
    req_id: str
    error_message: str


class LoggerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger

    async def set_body(self, request: Request):
        receive_ = await request._receive()

        async def receive():
            return receive_

        request._receive = receive

    async def dispatch(self, request: Request, call_next):
        req_id = str(uuid.uuid4())
        try:
            await self.set_body(request)
            request.state.req_id = req_id

            body = await request.body()
            try:
                json_body = await request.json()
            except json.decoder.JSONDecodeError:
                json_body = None
            try:
                form_body = await request.form()
            except Exception:
                form_body = None

            parsed_body = json_body or form_body or body
            request.state.body = {'body': parsed_body}

            log_request(request, self.logger)

            return await call_next(request)
        except Exception as e:
            log_error(req_id, {"error_message": "ERR_UNEXPECTED" + str(e)}, self.logger)
            return HTTPException(status_code=500, detail="ERR_UNEXPECTED" + str(e))


def log_request(request: Request, logger: logging.Logger):
    request_info: RequestInfo = RequestInfo(request)
    request_log = RequestLog(
        req_id=request.state.req_id,
        method=request_info.method,
        route=request_info.route,
        ip=request_info.ip,
        url=request_info.url,
        host=request_info.host,
        body=request_info.body,
        headers=request_info.headers,
    )
    logger.info(request_log.model_dump())


def log_error(uuid: str, response_body: dict, logger: logging.Logger):
    error_log = ErrorLog(
        req_id=uuid,
        error_message=response_body["error_message"],
    )
    logger.error(error_log.model_dump())
    logger.error(traceback.format_exc())


# endregion Log Database Handler
