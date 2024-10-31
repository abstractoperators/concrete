import json
import pickle
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


# Reconsider pickle for json + enforce basic types
# def abstract_operation(operation: Operation, clients: dict[str, OpenAIClientModel]) -> ConcreteChatCompletion:
@app.task
def abstract_operation(operation: Operation, caller: Any) -> Any:
    """
    An operation that's able to execute arbitrary methods on operators/agents
    """

    func: Callable[..., Any] = getattr(caller, operation.function_name)

    # client = OpenAIClient(**clients[operation.client_name].model_dump())
    # func = e.g. OpenAIClient.complete
    # func: Callable[..., ChatCompletion] = getattr(client, operation.function_name)
    # res = e.g. OpenAIClient.complete(
    #   messages=[{"role": "system", ...}, {"role": "user", ...}]
    #   message_format=response_format
    # )

    res = func(**operation.arg_dict).model_dump()
    return res

    message_format_name = cast(dict, operation.arg_dict["message_format"])["json_schema"]["name"]
    res["message_format_name"] = message_format_name

    return ConcreteChatCompletion(**res)


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

    register_type(
        operator,
        operator.__name__,
        lambda model: model.__repr__(),
        lambda model_json: operator(**json.loads(model_json)),
    )

for message_name, message in MESSAGE_REGISTRY.items():
    register_type(  # Register the message type for Kombu serialization
        message,
        message.__name__,
        lambda model: model.__repr__(),
        lambda model_json: message(**json.loads(model_json)),
    )  # Should reconsider adding Pydantic back.


register_type(
    Operation,
    Operation.__name__,
    lambda model: model.__repr__(),
    lambda model_json: Operation(**json.loads(model_json)),
)

# Doing it with python standard library: Loading/Packing into a dataclass is going to lose type information.
#
