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

# class AsyncOperatorMetaclass(type):
#     """
#     This metaclass automatically creates a '_delay' version for each method in the class, allowing these methods to be executed asynchronously using Celery workers.
#     """  # noqa E501

#     def __new__(cls, clsname, bases, attrs):
#         # identify methods and add delay functionality
#         def _delay_factory(string_func: Callable[..., str]) -> Callable[..., AsyncResult]:

#             def _delay(
#                 self: "AbstractOperator",
#                 *args,
#                 options: OperatorOptions,
#                 **kwargs,
#             ) -> AsyncResult:
#                 # TODO Make generic to support other delayable methods
#                 # Pop extra kwargs and set defaults
#                 operation = Operation(
#                     client_name=self.llm_client,
#                     function_name=self.llm_client_function,
#                     arg_dict={
#                         "messages": [
#                             {"role": "system", "content": options.instructions},
#                             {"role": "user", "content": string_func(self, *args, **kwargs)},
#                         ],
#                         "message_format": OpenAIClient.model_to_schema(options.response_format),
#                     },
#                 )
#                 # TODO unhardcode client conversion
#                 client_models = {
#                     name: OpenAIClientModel(
#                         model=client.model,
#                         temperature=client.default_temperature,
#                     )
#                     for name, client in (self.clients).items()
#                 }
#                 operation_result = abstract_operation.delay(
#                     operation=operation, clients=client_models
#                 )  # (celery.result.AsyncResult) - need to .get()
#                 return operation_result

#             return _delay

#         # Inspect attrs of a class at interpretation time and process methods
#         for attr in attrs:
#             if attr.startswith("__") or attr in {"_qna", "qna"} or not callable(attrs[attr]):
#                 continue

#             attrs[attr]._delay = _delay_factory(attrs[attr])

#         return super().__new__(cls, clsname, bases, attrs)


# # If async meta is imported, then this will occur?
# # What happens if you try to import meta before Operators classes are defined
# # Shouldn't be possible because async depends on core?
# # Could turn this into a function that's called in core __init__?
# AbstractOperatorMetaclass.OperatorRegistry = {
#     operator_name: type(operator_name, bases=tuple(operator, AsyncOperatorMetaclass), dict={})
#     for operator_name, operator in AbstractOperatorMetaclass.OperatorRegistry.items()
# }


# class DatabaseMetaclass(type):
#     pass


# type(name, bases, attrs, **kwargs)

# # maybe in .env or settings.py
# middleware = [
#     AsyncMetaclass,
#     DatabaseMetaclass,
# ]

# ## Inside abstract.py
