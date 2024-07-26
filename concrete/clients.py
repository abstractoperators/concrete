import os

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.beta.assistant import Assistant
from openai.types.beta.thread import Thread


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

    def create_thread(self, prompt: str | None = None) -> Thread:
        new_thread = self.client.beta.threads.create()
        if prompt is not None:
            self.client.beta.threads.messages.create(thread_id=new_thread.id, role="user", content=prompt)
        return new_thread

    def create_assistant(self, prompt: str = "", model: str = "gpt-4o-mini") -> Assistant:
        return self.client.beta.assistants.create(
            instructions=prompt,
            model=model,
        )


class WebsocketClient(Client):
    """
    Wrapper around a websocket client
    """

    @classmethod
    def send_message(cls, content: str, websocket_id: str):
        print(content)


class CLIClient(Client):
    @classmethod
    def emit(cls, content: str):
        print(content)
