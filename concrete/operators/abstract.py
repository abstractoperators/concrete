from collections.abc import Callable
from functools import cache, partial, wraps
from typing import Any, TypeVar

from celery.result import AsyncResult
from openai.types.chat import ChatCompletion

from ..celery import app
from ..clients import CLIClient, OpenAIClient
from ..models.clients import ConcreteChatCompletion, OpenAIClientModel
from ..models.operations import Operation
from ..models.responses import Response, TextResponse


# TODO replace OpenAIClientModel with GenericClientModel
@app.task
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
            'response_format': {
              'type': 'json_schema',
              'json_schema': {
                'name': TextResponse.__name__,
                'schema': TextResponse.model_json_schema(),
              },
              'strict': True,
            }
          }
        )
    """
    client = OpenAIClient(**clients[operation.client_name].model_dump())
    func: Callable[..., ChatCompletion] = getattr(client, operation.function_name)
    return ConcreteChatCompletion(**func(**operation.arg_dict).model_dump())


class MetaAbstractOperator(type):
    def __new__(cls, clsname, bases, attrs):
        # identify methods and add delay functionality
        def _delay_factory(func: Callable[..., str]) -> Callable[..., AsyncResult]:

            def _delay(
                self: AbstractOperator,
                *args,
                clients: dict[str, OpenAIClient] | None = None,
                client_name: str | None = None,
                client_function: str | None = None,
                response_format: type[Response] = TextResponse,
                **kwargs,
            ) -> AsyncResult:

                operation = Operation(
                    client_name=client_name or self.llm_client,
                    function_name=client_function or self.llm_client_function,
                    arg_dict={
                        'messages': [{'role': 'user', 'content': func(self, **kwargs)}],
                        'response_format': OpenAIClient.model_to_schema(response_format),
                    },
                )
                # TODO unhardcode client conversion
                client_models = {
                    name: OpenAIClientModel(
                        model=client.model,
                        temperature=client.default_temperature,
                    )
                    for name, client in (clients or self.clients).items()
                }
                return abstract_operation.delay(operation=operation, clients=client_models)

            return _delay

        for attr in attrs:
            if attr.startswith("__") or attr in {'_qna', 'qna'} or not callable(attrs[attr]):
                continue

            attrs[attr]._delay = _delay_factory(attrs[attr])

        return super().__new__(cls, clsname, bases, attrs)


# TODO mypy: figure out return types and signatures for class methods between this, the metaclass, and child classes
class AbstractOperator(metaclass=MetaAbstractOperator):
    INSTRUCTIONS = (
        "You are a software developer." "You will answer software development questions as concisely as possible."
    )

    def __init__(self, clients: dict[str, OpenAIClient]):
        self.clients = clients
        self.llm_client = 'openai'
        self.llm_client_function = 'complete'

    def _qna(
        self,
        query: str,
        instructions: str | None = None,
        response_format: type[Response] = TextResponse,
    ) -> Response:
        """
        "Question and Answer", given a query, return an answer.
        Basically just a wrapper for OpenAI's chat completion API.

        Synchronous.
        """
        instructions = instructions or self.INSTRUCTIONS
        messages = [
            {'role': 'system', 'content': instructions},
            {'role': 'user', 'content': query},
        ]

        CLIClient.emit(f'response_format: {response_format}')

        response = (
            self.clients['openai']
            .complete(
                messages=messages,
                response_format=response_format,
            )
            .choices[0]
            .message
        )

        if response.refusal:
            CLIClient.emit(f"Operator refused to answer question: {query}")
            raise Exception("Operator refused to answer question")

        CLIClient.emit(f'{type(response)}: {response}')
        answer = response.parsed
        return answer

    def qna(self, question_producer: Callable) -> Callable:
        """
        Decorate something on a child object downstream to get a response from a query

        question_producer is expected to return a request like "Create a website that does xyz"
        """

        @wraps(question_producer)
        def _send_and_await_reply(
            *args,
            instructions: str | None = None,
            response_format: type[Response] = TextResponse,
            **kwargs,
        ):
            query = question_producer(*args, **kwargs)
            CLIClient.emit(f"[prompt]: {query}")
            return self._qna(query, instructions=instructions, response_format=response_format)

        return _send_and_await_reply

    @cache
    def __getattribute__(self, name: str) -> Any:
        attr = super().__getattribute__(name)
        if name.startswith("__") or name in {'qna', '_qna'} or not callable(attr):
            return attr

        CLIClient.emit(f"[operator]: {self.__class__.__name__}")

        prepped_func = self.qna(attr)
        prepped_func.delay = partial(prepped_func._delay, self)
        return prepped_func


# Define a shmexy type var
# Covariance: If A is a subclass of B, then SomeClass[A] is considered a subclass of SomeClass[B].
AbstractOperator_co = TypeVar('AbstractOperator_co', bound=AbstractOperator, covariant=True)
