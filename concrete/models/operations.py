from pydantic import Field

from .base import ConcreteBaseModel, KombuMixin


class Operation(ConcreteBaseModel, KombuMixin):
    client_name: str = Field(description='Name of LLM Client')
    function_name: str = Field(description='Name of function to call on LLM Client')
    arg_dict: dict[str, dict | list | str] = Field(description='Parameters to pass to function')
