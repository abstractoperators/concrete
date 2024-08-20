import os
from typing import TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion

from .models.base import ConcreteBaseModel
from .models.responses import Response, TextResponse


class Client:
    pass


Client_con = TypeVar('Client_con', bound=Client, contravariant=True)


class OpenAIClient(Client):
    """
    Thin wrapper around open AI client
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float | None = None):
        load_dotenv()
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.default_temperature = temperature or float(os.getenv("OPENAI_TEMPERATURE", 0))
        self.model = model

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
        # TODO: right now, make this a config setting
        if os.environ.get("ENV") != "PROD":
            print(content)
