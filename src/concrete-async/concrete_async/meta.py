import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from celery.result import AsyncResult
from concrete_core.abstract import AbstractOperator, AbstractOperatorMetaclass
from concrete_core.models.base import ConcreteModel
from concrete_core.models.messages import MESSAGE_REGISTRY
from kombu.utils.json import register_type

from .celery import app


@dataclass
class Operation(ConcreteModel):
    client_name: str
    function_name: str
    arg_dict: dict[str, dict | list | str]


# def abstract_operation(operation: Operation, clients: dict[str, OpenAIClientModel]) -> ConcreteChatCompletion:
# Why are we even using this? What's the difference between adding a _delay that calls abstract_operation vs. decorating tasks directly?
@app.task(name='concrete_async.meta.abstract_operation')
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

    setattr(operator, "model_dump", lambda self: self.__dict__)
    setattr(operator, "model_load", lambda self, model_dict: operator(**model_dict))

    register_type(
        operator,
        operator.__name__,
        lambda model: model.__repr__(),
        lambda model_json: operator(**json.loads(model_json)),
    )

for message_name, message in MESSAGE_REGISTRY.items():
    setattr(message, "model_dump", lambda self: self.__dict__)
    setattr(message, "model_load", lambda self, model_dict: message(**model_dict))

    register_type(  # Register the message type for Kombu serialization
        message,
        message.__name__,
        lambda model: model.model_dump(),
        lambda model_json: message.model_load(json.loads(model_json)),
    )  # Should reconsider adding Pydantic back.


register_type(
    Operation,
    Operation.__name__,
    lambda model: model.__repr__(),
    lambda model_json: Operation(**json.loads(model_json)),
)
