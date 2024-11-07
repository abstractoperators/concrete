import os
from typing import TYPE_CHECKING

try:
    from openai import OpenAI  # noqa
except ImportError as e:
    raise ImportError("Install openai to use OpenAIClient.") from e

from concrete.clients import CLIClient, LMClient
from concrete.models.messages import Message, TextMessage

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion


class OpenAIClient(LMClient):
    """
    Thin wrapper around open AI client.
    """

    def __init__(self, model: str | None = None, temperature: float | None = None):
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
            "temperature": (temperature if temperature is not None else self.default_temperature),
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
