import os
from typing import List

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion
from pydantic import BaseModel


class ProjectFile(BaseModel):
    name: str  # eg app.py
    content: str  # eg "print('hello world')\nprint('goodbye world')"


class Project(BaseModel):
    files: list[ProjectFile]


class Client:
    pass


class OpenAIClient(Client):
    """
    Thin wrapper around open AI client
    """

    def __init__(self):
        load_dotenv()
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=OPENAI_API_KEY)
        self.client = client

    def complete(self, messages: List[str], **kwargs) -> ChatCompletion:
        return self.client.chat.completions.create(messages=messages, **kwargs)


class CLIClient(Client):
    @classmethod
    def emit(cls, content: str):
        # TODO: right now, make this a config setting
        if os.environ.get("ENV") != "PROD":
            print(content)
