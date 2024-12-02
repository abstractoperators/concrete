import json

from kombu.utils.json import register_type
from openai.types.chat import ChatCompletion
from pydantic import BaseModel
from pydantic.fields import Field

import concrete


class KombuMixin(BaseModel):
    """
    Represents a Mixin to allow serialization and deserialization of subclasses
    """

    def __init_subclass__(cls, **kwargs):
        register_type(
            cls,
            cls.__name__,
            lambda model: model.model_dump_json(),
            lambda model_json: cls.model_validate_json(model_json),
        )
        return super().__init_subclass__(**kwargs)


class Operation(concrete.models.base.ConcreteModel, KombuMixin):
    client_name: str
    function_name: str
    arg_dict: dict[str, list | dict]


class ConcreteChatCompletion(ChatCompletion, concrete.models.base.ConcreteModel, KombuMixin):
    message_format_name: str = Field(description="Response format to parse completion into")

    @property
    def message(self) -> concrete.models.messages.Message:
        message_format: type[concrete.models.messages.Message] = concrete.models.messages.Message.dereference(
            self.message_format_name
        )
        return message_format.model_validate(json.loads(self.choices[0].message.content or "{}"))
