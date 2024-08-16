from functools import wraps
from typing import Callable
from uuid import uuid1

from celery import Task, signals
from pydantic import BaseModel

from ..clients import OpenAIClient
from ..operator_responses import TextResponse


class OpenAiOperation(Task):
    """
    Represents the base Operator for further implementation
    """

    def __init__(self):
        super().__init__()
        self.uuid = uuid1()
        self._client = None
        signals.worker_init.connect(self.on_worker_init)

        # TODO: Move specific software prompting to its own SoftwareOperator class or mixin
        self.instructions = (
            "You are a software developer." "You will answer software development questions as concisely as possible."
        )

    def on_worker_init(self, *args, **kwargs):
        self._client = OpenAIClient()

    @property
    def client(self):
        if not self._client:
            self.on_worker_init()
        return self._client

    def __call__(self, *args, **kwargs):
        return self.qna(self.run)(*args, **kwargs)

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
        instructions = instructions or self.instructions
        messages = [
            {'role': 'system', 'content': instructions},
            {'role': 'user', 'content': query},
        ]

        response = (
            self.client.complete(
                messages=messages,
                response_format=response_format or TextResponse,
            ).choices[0]
        ).message

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
            return self._qna(query, instructions=instructions, response_format=response_format)

        return _send_and_await_reply
