import json
import logging
import traceback
import uuid

from fastapi import HTTPException, Request
from pydantic import BaseModel
from starlette.concurrency import iterate_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware


class RequestInfo:

    def __init__(self, request) -> None:
        self.request = request

    @property
    def method(self) -> str:
        return str(self.request.method)

    @property
    def route(self) -> str:
        return self.request["path"]

    @property
    def ip(self) -> str:
        return str(self.request.client.host)

    @property
    def url(self) -> str:
        return str(self.request.url)

    @property
    def host(self) -> str:
        return str(self.request.url.hostname)

    @property
    def headers(self) -> dict:
        return {key: value for key, value in self.request.headers.items()}

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

    async def dispatch(self, request: Request, call_next):
        req_id = str(uuid.uuid4())
        try:
            request.state.req_id = req_id
            request.state.body = json.loads(await request.body() or "{}")
            log_request(request, self.logger)

            response = await call_next(request)
            if response.headers.get("content-type") == "application/json":
                response_body = [chunk async for chunk in response.body_iterator]
                response.body_iterator = iterate_in_threadpool(iter(response_body))
            return response
        except Exception as e:
            log_error(req_id, {"error_message": "ERR_UNEXPECTED" + str(e)}, self.logger)
            return HTTPException(status_code=500, detail="ERR_UNEXPECTED" + str(e))


def log_request(request: Request, logger: logging.Logger):
    request_info = RequestInfo(request)
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
