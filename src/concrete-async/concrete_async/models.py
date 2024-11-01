from typing import Any

import concrete_core
from kombu.utils.json import register_type
from pydantic import BaseModel


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


class Operation(concrete_core.models.base.ConcreteModel, KombuMixin):
    client_name: str
    function_name: str
    arg_dict: dict[str, list | dict]
