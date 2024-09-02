import os
from typing import TypeVar

import requests
import requests.adapters
from openai import OpenAI
from openai.types.chat import ChatCompletion
from requests.adapters import HTTPAdapter, Retry

from .models.base import ConcreteBaseModel
from .models.responses import Response, TextResponse


class Client:
    pass


Client_con = TypeVar('Client_con', bound=Client, contravariant=True)


class OpenAIClient(Client):
    """
    Thin wrapper around open AI client
    """

    def __init__(self, model: str | None = None, temperature: float | None = 0):
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.default_temperature = temperature or float(str(os.getenv("OPENAI_TEMPERATURE")))
        self.model = model or "gpt-4o-mini"

    def complete(
        self,
        messages: list[dict[str, str]],
        response_format: type[Response] | dict = TextResponse,
        temperature: float | None = None,
        **kwargs,
    ) -> ChatCompletion:

        request_params = {
            "messages": messages,
            "model": self.model,
            "temperature": temperature or self.default_temperature,
            "response_format": response_format,
            **kwargs,
        }

        # Pydantic Model
        if isinstance(response_format, type(Response)):
            return self.client.beta.chat.completions.parse(**request_params)
        # JSON Schema
        return self.client.chat.completions.create(**request_params)

    @staticmethod
    def model_to_schema(model: type[ConcreteBaseModel]) -> dict[str, str | dict]:
        return {
            'type': 'json_schema',
            'json_schema': {
                'name': model.__name__,
                'schema': model.model_json_schema(),
            },
        }


class CLIClient(Client):
    @classmethod
    def emit(cls, content: str):
        if os.environ.get("ENV") != "PROD":
            print(content)


class RestApiClient(Client, requests.Session):
    """
    Set up requests.session to access
    """

    def __init__(self):
        # Setup retry logic for restful web http requests
        super().__init__()
        jitter_retry = Retry(
            total=5, backoff_factor=0.1, backoff_jitter=1.25, status_forcelist=[400, 403, 404, 500, 502, 503, 504]
        )
        self.mount("http://", HTTPAdapter(max_retries=jitter_retry))
        self.mount("https://", HTTPAdapter(max_retries=jitter_retry))
