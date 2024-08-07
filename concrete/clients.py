import os

from dotenv import load_dotenv
from groq import Groq
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
        self._client = client

    def create_thread(self, prompt: str | None = None) -> Thread:
        new_thread = self._client.beta.threads.create()
        if prompt is not None:
            self._client.beta.threads.messages.create(thread_id=new_thread.id, role="user", content=prompt)
        return new_thread

    def create_assistant(self, prompt: str = "", model: str = "gpt-4o-mini") -> Assistant:
        temperature = float(os.getenv("OPENAI_TEMPERATURE", 1))
        return self._client.beta.assistants.create(instructions=prompt, model=model, temperature=temperature)


class GroqClient(Client):
    """
    Thin wrapper around Groq client
    """

    def __init__(self, model: str = "llama3-70b-8192") -> None:
        load_dotenv()
        self._client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.temperature = float(os.getenv("GROQ_TEMPERATURE", 1))
        self.model = model

    def chat(self, content: str, instructions: str | None = "you are a helpful assistant.") -> str:
        chat_completion = self._client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": instructions,
                },
                {
                    "role": "user",
                    "content": content,
                },
            ],
            model=self.model,
            temperature=self.temperature,
            n=1,
            stream=False,
        )

        return chat_completion.choices[0].message.content


class CLIClient(Client):
    @classmethod
    def emit(cls, content: str):
        # TODO: right now, make this a config setting
        if os.environ.get("ENV") != "PROD":
            print(content)
