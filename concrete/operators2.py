from collections.abc import Callable
from dataclasses import dataclass
from functools import cache, partial, wraps
from typing import Any, cast

from pydantic import BaseModel

from concrete.celery import app
from concrete.clients import CLIClient, Client
from concrete.operator_responses import TextResponse


@dataclass
class Operation:
    client_name: str
    function_name: str
    arg_dict: dict[str, Any]


@app.task
def abstract_operation(operation: Operation, clients: dict[str, Client]):
    """
    An operation that's able to execute arbitrary methods on operators/agents

    operation: Operation
      Reference to a function to call. e.g.
        ('openai',
          'complete',
          {
            'messages': [{'role': 'user', 'content': 'pass butter'}],
            'response_format': TextResponse.model_dump()  # returns a json
          }
        )
    """
    print("inside abstract_operation", operation, clients)
    client = clients[operation.client_name]
    func = getattr(client, operation.function_name)
    return func(**operation.arg_dict)


class MetaAbstractOperator(type):
    def __new__(cls, clsname, bases, attrs):
        # identify methods and add delay functionality

        for attr in attrs:
            if attr.startswith("__") or attr in {'_qna', 'qna'} or not callable(attrs[attr]):
                continue

            def _delay(self, *args, **kwargs):
                clients = kwargs.pop('clients')
                client_name = kwargs.pop('llm_client', None)
                client_function = kwargs.pop('llm_client_function', None)

                operation = Operation(
                    client_name=client_name or self.llm_client,
                    function_name=client_function or self.llm_client_function,
                    arg_dict={
                        'messages': [{'role': 'user', 'content': attrs[attr](self, **kwargs)}],
                        'response_format': TextResponse,
                    },
                )
                return abstract_operation(operation=operation, clients=clients)

            attrs[attr]._delay = _delay

        return super().__new__(cls, clsname, bases, attrs)


class AbstractOperator(metaclass=MetaAbstractOperator):
    def __init__(self, clients: dict[str, Client]):
        self.clients = clients
        self.llm_client = 'openai'
        self.llm_client_function = 'complete'

    def _qna(
        self,
        query: str,
        instructions: str | None = None,
        response_format: BaseModel | None = None,
    ) -> BaseModel:
        """
        "Question and Answer", given a query, return an answer.
        Basically just a wrapper for OpenAI's chat completion API.

        Synchronous.
        """
        instructions = cast(str, instructions or self.INSTRUCTIONS)
        messages = [
            {'role': 'system', 'content': instructions},
            {'role': 'user', 'content': query},
        ]

        response = cast(
            str,
            (
                self.clients['openai']
                .complete(
                    messages=messages,
                    response_format=response_format or TextResponse,
                )
                .choices[0]
            ).message,
        )

        if response.refusal:
            print(f"Operator refused to answer question: {query}")
            raise Exception("Operator refused to answer question")

        answer = response.parsed
        return answer

    def qna(self, question_producer: Callable) -> Callable:
        """
        Decorate something on a child object downstream to get a response from a query

        question_producer is expected to return a request like "Create a website that does xyz"
        """

        @wraps(question_producer)
        def _send_and_await_reply(*args, **kwargs):
            response_format = kwargs.pop("response_format", None)
            instructions = kwargs.pop("instructions", None)
            query = question_producer(*args, **kwargs)
            CLIClient.emit(f"[prompt]: {query}")
            return self._qna(query, instructions=instructions, response_format=response_format)

        return _send_and_await_reply

    @cache
    def __getattribute__(self, name: str) -> Any:
        attr = super().__getattribute__(name)
        if not name.startswith("__") and name not in {'qna', '_qna'} and callable(attr):
            CLIClient.emit(f"[operator]: {self.__class__.__name__}")

            prepped_func = self.qna(attr)
            prepped_func.delay = partial(prepped_func._delay, self)
            return prepped_func
        return attr


class Executive(AbstractOperator):
    INSTRUCTIONS = (
        "You are an expert executive software developer."
        "You will follow the instructions given to you to complete each task."
    )

    def plan_components(self, starting_prompt) -> str:
        return """from inside {name}: hello world {starting_prompt}""".format(
            starting_prompt=starting_prompt, name=self.__class__.__name__
        )
