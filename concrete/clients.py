import os
from typing import List

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion


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
        self.OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE"))

    def complete(self, messages: List[str], model: str = "gpt-4o-mini", **kwargs) -> ChatCompletion:
        return self.client.beta.chat.completions.parse(
            messages=messages, model=model, temperature=self.OPENAI_TEMPERATURE, **kwargs
        )


class CLIClient(Client):
    @classmethod
    def emit(cls, content: str):
        # TODO: right now, make this a config setting
        if os.environ.get("ENV") != "PROD":
            print(content)
