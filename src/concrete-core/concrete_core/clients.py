import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Sequence, TypeVar

import requests
import requests.adapters

# from openai import OpenAI, RateLimitError
# from openai.types.chat import ChatCompletion
from pydantic import BaseModel as PydanticModel
from requests.adapters import HTTPAdapter, Retry

from .models.messages import Message, TextMessage

# https://stackoverflow.com/questions/61384752/how-to-type-hint-with-an-optional-import
if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion


class Client:
    pass


class LMClient(ABC):
    @abstractmethod
    def complete(self, messages: list, *args, **kwargs):
        """
        Complete a chat message (message[-1]) with history messages[0:-1]
        """
        pass


LMClient_con = TypeVar("LMClient_con", bound=LMClient, contravariant=True)


class OpenAIClient(LMClient):
    """
    Thin wrapper around open AI client.
    """

    def __init__(self, model: str | None = None, temperature: float | None = None):
        try:
            from openai import OpenAI  # noqa
        except ImportError as e:
            raise ImportError("OpenAI must be installed to use this client.") from e

        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.default_temperature = temperature if temperature is not None else float(os.getenv("OPENAI_TEMPERATURE", 0))
        self.model = model or "gpt-4o-mini"

    def complete(
        self,
        messages: list[dict[str, str]],
        message_format: type[Message] = TextMessage,
        temperature: float | None = None,
        **kwargs,
    ) -> "ChatCompletion":
        from openai import RateLimitError

        request_params = {
            "messages": messages,
            "model": self.model,
            "temperature": temperature if temperature is not None else self.default_temperature,
            "response_format": message_format,
            **kwargs,
        }

        try:
            if isinstance(message_format, type(Message)):
                # Turn Message into a json_schema
                # https://platform.openai.com/docs/guides/structured-outputs/supported-schemas

                return self.client.beta.chat.completions.parse(**request_params)
            return self.client.chat.completions.create(**request_params)
        except RateLimitError as e:
            CLIClient.emit(f"Rate limit error: {e}")
            raise e  # retry decorator

    # TODO: Rename to structure output api or similar
    @staticmethod
    def model_to_schema(model: type[PydanticModel]) -> dict[str, str | dict]:
        """
        Utility for formatting a pydantic model into a json output for OpenAI.
        """
        return {
            "type": "json_schema",
            "json_schema": {
                "name": model.__name__,
                "schema": model.model_json_schema(),
            },
        }


class CLIClient(Client):
    @classmethod
    def emit(cls, content: Any):
        if os.environ.get("ENV") != "PROD":
            print(str(content))

    @classmethod
    def emit_sequence(cls, content: Sequence):
        if os.environ.get("ENV") != "PROD":
            for item in content:
                print(str(item))


class HTTPClient(Client, requests.Session):
    """
    Set up requests.session to access
    """

    def __init__(self):
        # Setup retry logic for restful web http requests
        super().__init__()
        jitter_retry = Retry(
            total=5,
            backoff_factor=0.1,
            backoff_jitter=1.25,
            status_forcelist=[400, 403, 404, 500, 502, 503, 504],
            raise_on_status=False,
        )
        self.mount("http://", HTTPAdapter(max_retries=jitter_retry))
        self.mount("https://", HTTPAdapter(max_retries=jitter_retry))
