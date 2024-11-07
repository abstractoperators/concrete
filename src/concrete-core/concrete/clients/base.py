import os
from abc import ABC, abstractmethod
from typing import Any, Sequence, TypeVar

from pydantic import BaseModel as PydanticModel


class Client:
    pass


class LMClient(ABC):
    @abstractmethod
    def complete(self, messages: list, *args, **kwargs):
        """
        Complete a chat message (message[-1]) with history messages[0:-1]
        """
        pass


LMClient_con = TypeVar("LMClient_con", bound=LMClient, contravariant=True)


class CLIClient(Client):
    @classmethod
    def emit(cls, content: Any):
        if os.environ.get("ENV") != "PROD":
            print(str(content))

    @classmethod
    def emit_sequence(cls, content: Sequence):
        if os.environ.get("ENV") != "PROD":
            for item in content:
                print(str(item))


def model_to_schema(model: type[PydanticModel]) -> dict[str, str | dict]:
    """
    Utility for formatting a pydantic model into a json output for OpenAI.
    """
    return {
        "type": "json_schema",
        "json_schema": {
            "name": model.__name__,
            "schema": model.model_json_schema(),
        },
    }
