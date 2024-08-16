import os

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion
from pydantic import BaseModel


class Client:
    pass


class OpenAIClient(Client):
    """
    Thin wrapper around open AI client
    """

    def __init__(self):
        load_dotenv()
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.default_temperature = float(os.getenv("OPENAI_TEMPERATURE"))
        self.model = "gpt-4o-mini"

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
