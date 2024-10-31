import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from celery.result import AsyncResult
from concrete_core.abstract import AbstractOperator, AbstractOperatorMetaclass
from concrete_core.models.base import ConcreteModel
from concrete_core.models.messages import MESSAGE_REGISTRY
from kombu.utils.json import register_type
from pydantic import BaseModel

from .celery import app


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


# @dataclass
class Operation(ConcreteModel, KombuMixin):
    client_name: str
    function_name: str
    arg_dict: dict[str, Any]


# def abstract_operation(operation: Operation, clients: dict[str, OpenAIClientModel]) -> ConcreteChatCompletion:
# Why are we even using this? What's the difference between adding a _delay that calls abstract_operation vs. decorating tasks directly?
@app.task
def abstract_operation(operation: Operation, caller: Any) -> Any:
    """
    An operation that's able to execute arbitrary methods on operators/agents
    """

    func: Callable[..., Any] = getattr(caller, operation.function_name)

    print('func', func)
    res = func(**operation.arg_dict).model_dump()
    return res


def _delay_factory(string_func: Callable[..., str]) -> Callable[..., AsyncResult]:
    def _delay(
        self: AbstractOperator,
        *args,
        options: dict,
        **kwargs,
    ) -> AsyncResult:
        print(f'{self.llm_client=}')
        print(f'{self.llm_client_function=}')
        print(string_func(self, *args, **kwargs))
        print(options["response_format"])
        arg_dict = {
            "messages": [
                {"role": "system", "content": options["instructions"]},
                {"role": "user", "content": string_func(self, *args, **kwargs)},
            ],
            "message_format": options["response_format"],
        }
        print(f'{arg_dict=}')
        operation = Operation(
            client_name=self.llm_client,
            function_name=self.llm_client_function,
            arg_dict={
                "messages": [
                    {"role": "system", "content": options["instructions"]},
                    {"role": "user", "content": string_func(self, *args, **kwargs)},
                ],
                "message_format": options["response_format"],
            },
        )
        operation_result = abstract_operation.delay(operation=operation, caller=self)
        return operation_result

    return _delay


for operator_name, operator in AbstractOperatorMetaclass.OperatorRegistry.items():
    for attr, method in operator.__dict__.items():
        if attr.startswith("__") or attr in {"_qna", "qna"} or not callable(method):
            continue
        print(f'Setting delay for {operator_name}.{attr}')
        setattr(method, "_delay", _delay_factory(method))


for message_name, message in MESSAGE_REGISTRY.items():
    message = type(message_name, (KombuMixin, message), {})
