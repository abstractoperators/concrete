import os

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.beta.assistant import Assistant
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

    def create_assistant(self, prompt: str = "", model: str = "gpt-4o-mini") -> Assistant:
        temperature = float(os.getenv("OPENAI_TEMPERATURE", 1))
        return self.client.beta.assistants.create(instructions=prompt, model=model, temperature=temperature)


class CLIClient(Client):
    @classmethod
    def emit(cls, content: str):
        # TODO: right now, make this a config setting
        if os.environ.get("ENV") != "PROD":
            print(content)
