from openai.types.chat import ChatCompletion
from pydantic import Field

from .base import ConcreteBaseModel, KombuMixin

# TODO Port over concrete.clients.OpenAIClient


class OpenAIClientModel(ConcreteBaseModel, KombuMixin):
    model: str = Field(default='gpt-4o-mini', description='Name of LLM Model')
    temperature: float = Field(default=0, description='Temperature of LLM Model')


# What is this?
class ConcreteChatCompletion(ChatCompletion, KombuMixin):
    pass
