from openai.types.chat import ChatCompletion
from pydantic import Field

from .base import ConcreteBaseModel, KombuMixin


class OpenAIClientModel(ConcreteBaseModel, KombuMixin):
    model: str = Field(default='gpt-4o-mini', description='Name of LLM Model')
    temperature: float = Field(default=0, description='Temperature of LLM Model')


class ConcreteChatCompletion(ChatCompletion, KombuMixin):
    def get_message_content(self) -> dict:
        return self.choices[0].message.content
