import os

import requests
import requests.adapters
from openai import OpenAI
from openai.types.chat import ChatCompletion
from pydantic import BaseModel
from requests.adapters import HTTPAdapter, Retry


class Client:
    pass


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
        response_format: BaseModel,
        temperature: float | None = None,
        **kwargs,
    ) -> ChatCompletion:

        request_params = {
            "messages": messages,
            "model": self.model,
            "temperature": temperature if temperature is not None else self.default_temperature,
            "response_format": response_format,
            **kwargs,
        }

        return self.client.beta.chat.completions.parse(**request_params)


class CLIClient(Client):
    @classmethod
    def emit(cls, content: str):
        # TODO: right now, make this a config setting
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
