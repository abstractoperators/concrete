from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from celery.result import AsyncResult
from concrete_core.abstract import AbstractOperator, AbstractOperatorMetaclass
from concrete_core.models.base import ConcreteModel

from .celery import app

print("Importing meta.py")


@dataclass
class Operation(ConcreteModel):
    client_name: str
    function_name: str
    arg_dict: dict[str, dict | list | str]


# Reconsider pickle for json + enforce basic types
@app.task(serializer='pickle')
# def abstract_operation(operation: Operation, clients: dict[str, OpenAIClientModel]) -> ConcreteChatCompletion:
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


# TODO Generic to operation
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
