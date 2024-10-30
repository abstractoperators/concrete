from collections.abc import Callable

from celery.result import AsyncResult

from concrete.abstract import AbstractOperator, AbstractOperatorMetaclass
from concrete.clients import Client  # noqa
from concrete.db.orm.models import OperatorOptions


# TODO: Make this a dataclass (needs serialization?)
# TODO: Make this a generic operation
class Operation(ConcreteModel):
    client_name: str = Field(description="Name of LLM Client")
    function_name: str = Field(description="Name of function to call on LLM Client")
    arg_dict: dict[str, dict | list | str] = Field(description="Parameters to pass to function")


# TODO: Make abstract_operation a true generic function that can do things besides chat completions
# TODO Separate clients
@app.task(serializer='pickle')
def abstract_operation(operation: Operation, clients: dict[str, OpenAIClientModel]) -> ConcreteChatCompletion:
    """
    An operation that's able to execute arbitrary methods on operators/agents

    operation: Operation
      Reference to a function to call. e.g.
        (
          'openai',
          'complete',
          {
            'messages': [{'role': 'user', 'content': 'pass butter'}],
            'message_format': {
              'type': 'json_schema',
              'json_schema': {
                'name': TextMessage.__name__,
                'schema': TextMessage.model_json_schema(),
              },
              'strict': True,
            }
          }
        )
    """

    client = OpenAIClient(**clients[operation.client_name].model_dump())
    # func = e.g. OpenAIClient.complete
    func: Callable[..., ChatCompletion] = getattr(client, operation.function_name)
    # res = e.g. OpenAIClient.complete(
    #   messages=[{"role": "system", ...}, {"role": "user", ...}]
    #   message_format=response_format
    # )
    res = func(**operation.arg_dict).model_dump()

    message_format_name = cast(dict, operation.arg_dict["message_format"])["json_schema"]["name"]
    res["message_format_name"] = message_format_name

    return ConcreteChatCompletion(**res)


class AsyncOperatorMetaclass(type):
    """
    This metaclass automatically creates a '_delay' version for each method in the class, allowing these methods to be executed asynchronously using Celery workers.
    """  # noqa E501

    def __new__(cls, clsname, bases, attrs):
        # identify methods and add delay functionality
        def _delay_factory(string_func: Callable[..., str]) -> Callable[..., AsyncResult]:

            def _delay(
                self: "AbstractOperator",
                *args,
                options: OperatorOptions,
                **kwargs,
            ) -> AsyncResult:
                # TODO Make generic to support other delayable methods
                # Pop extra kwargs and set defaults
                operation = Operation(
                    client_name=self.llm_client,
                    function_name=self.llm_client_function,
                    arg_dict={
                        "messages": [
                            {"role": "system", "content": options.instructions},
                            {"role": "user", "content": string_func(self, *args, **kwargs)},
                        ],
                        "message_format": OpenAIClient.model_to_schema(options.response_format),
                    },
                )
                # TODO unhardcode client conversion
                client_models = {
                    name: OpenAIClientModel(
                        model=client.model,
                        temperature=client.default_temperature,
                    )
                    for name, client in (self.clients).items()
                }
                operation_result = abstract_operation.delay(
                    operation=operation, clients=client_models
                )  # (celery.result.AsyncResult) - need to .get()
                return operation_result

            return _delay

        # Inspect attrs of a class at interpretation time and process methods
        for attr in attrs:
            if attr.startswith("__") or attr in {"_qna", "qna"} or not callable(attrs[attr]):
                continue

            attrs[attr]._delay = _delay_factory(attrs[attr])

        return super().__new__(cls, clsname, bases, attrs)


# If async meta is imported, then this will occur?
# What happens if you try to import meta before Operators classes are defined
# Shouldn't be possible because async depends on core?
# Could turn this into a function that's called in core __init__?
AbstractOperatorMetaclass.OperatorRegistry = {
    operator_name: type(operator_name, bases=tuple(operator, AsyncOperatorMetaclass), dict={})
    for operator_name, operator in AbstractOperatorMetaclass.OperatorRegistry.items()
}


class DatabaseMetaclass(type):
    pass


type(name, bases, attrs, **kwargs)

# maybe in .env or settings.py
middleware = [
    AsyncMetaclass,
    DatabaseMetaclass,
]

## Inside abstract.py
