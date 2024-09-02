import json

from openai.types.chat import ChatCompletion
from pydantic import Field

from .base import ConcreteModel, KombuMixin
from .messages import Message


class OpenAIClientModel(ConcreteModel, KombuMixin):
    model: str = Field(default='gpt-4o-mini', description='Name of LLM Model')
    temperature: float = Field(default=0, description='Temperature of LLM Model')


class ConcreteChatCompletion(ChatCompletion, KombuMixin):
    message_format_name: str = Field(description='Response format to parse completion into')

    def get_response(self) -> Message:
        message_format: type[Message] = Message.dereference(self.message_format_name)
        return message_format.model_validate(json.loads(self.choices[0].message.content or "{}"))
