from dataclasses import dataclass

from pydantic import Field

from .base import ConcreteModel, KombuMixin


# TODO: Make this a dataclass (needs serialization?)
# TODO: Make this a generic operation
class Operation(ConcreteModel, KombuMixin):
    client_name: str = Field(description="Name of LLM Client")
    function_name: str = Field(description="Name of function to call on LLM Client")
    arg_dict: dict[str, dict | list | str] = Field(description="Parameters to pass to function")


# TODO: Need custom serialization methods for complex datatypes.
# https://docs.celeryq.dev/en/stable/userguide/calling.html#calling-serializers
# Pickle? Could be unsafe.
@dataclass
class Operation:
    pass
