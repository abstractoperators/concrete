from abc import abstractmethod
from collections.abc import Callable
from functools import cache, wraps
from typing import Any, cast
from uuid import UUID, uuid4

from celery.result import AsyncResult
from openai.types.chat import ChatCompletion

from .celery import app
from .clients import CLIClient, OpenAIClient
from .db import crud
from .db.orm import Session
from .db.orm.models import MessageCreate, OperatorOptions
from .models.clients import ConcreteChatCompletion, OpenAIClientModel
from .models.messages import Message, Tool
from .models.operations import Operation
from .tools import TOOLS_REGISTRY, MetaTool

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


class MetaAbstractOperator(type):
    """
    This metaclass automatically creates a '_delay' version for each method in the class, allowing these methods to be executed asynchronously using Celery workers.

    Classes that use this metaclass can call the asynchronous variant of a method like `some_instance.some_method.delay()`.

    Note that .delay() returns a Celery AsyncResult object, which can be retrieved using .get() to get a ConcreteChatCompletion object.
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

        for attr in attrs:
            if attr.startswith("__") or attr in {"_qna", "qna"} or not callable(attrs[attr]):
                continue

            attrs[attr]._delay = _delay_factory(attrs[attr])

        return super().__new__(cls, clsname, bases, attrs)


# TODO mypy: figure out return types and signatures for class methods between this, the metaclass, and child classes
class AbstractOperator(metaclass=MetaAbstractOperator):

    # TODO replace OpenAIClient with GenericClient
    def __init__(
        self,
        clients: dict[str, OpenAIClient] | None = None,
        tools: list[MetaTool] | None = None,
        operator_id: UUID = uuid4(),  # TODO: Don't set a default
        project_id: UUID = uuid4(),  # TODO: Don't set a default
        starting_prompt: str | None = None,
        store_messages: bool = False,
    ):
        """
        store_messages (bool): Whether or not to save the messages in db
        """
        self._clients = clients if clients is not None else {'openai': OpenAIClient()}
        self.llm_client = "openai"
        self.llm_client_function = "complete"
        self.tools = tools

        self.operator_id = operator_id
        self.project_id = project_id
        self.starting_prompt = starting_prompt
        self.store_messages = store_messages

    def _qna(
        self,
        query: str,
        response_format: type[Message],
        instructions: str | None = None,
    ) -> Message:
        """
        "Question and Answer", given a query, return an answer.
        Basically just a wrapper for OpenAI's chat completion API.
        """
        instructions = cast(str, instructions or self.instructions)
        messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": query},
        ]
        response = (
            self.clients["openai"]
            .complete(
                messages=messages,
                message_format=response_format,
            )
            .choices[0]
            .message
        )

        if response.refusal:
            CLIClient.emit(f"Operator refused to answer question: {query}")
            raise Exception("Operator refused to answer question")

        answer = response.parsed

        if self.store_messages:
            with Session() as session:
                crud.create_message(
                    session,
                    MessageCreate(
                        type_name=response_format.__name__,
                        content=repr(answer),
                        prompt=self.starting_prompt,
                        project_id=self.project_id,
                        operator_id=self.operator_id,
                    ),
                )

        # TODO Invoke tool here? Or manual invocation?
        return answer

    def qna(self, question_producer: Callable[..., str]) -> Callable:
        """
        Decorate something on a child object downstream to get a response from a query

        question_producer is expected to return a request like "Create a website that does xyz"
        """

        @wraps(question_producer)
        def _send_and_await_reply(
            *args,
            options: OperatorOptions,
            **kwargs,
        ):
            """
            options (dict): can contain extra options:
                response_format ([PydanticModel, ConcreteModel]): something json-like
                run_async (bool): whether to use the celery .delay function
                use_tools (bool):  whether to use tools set on the operator

                # Clobbers the Operator instance attributes
                instructions (str): override system prompt
                tools (list[concrete.models.MetaTool]): list of tools available for the operator
            """
            # Pop extra kwargs and set defaults
            tools_addendum = ""
            if tools := (
                options.tools
                if options.tools
                # TODO Have a multi-select drop down in the SaaS
                else (self.tools if options.use_tools else [])
            ):
                # LLMs don't really know what should go in what field even if output struct
                # is guaranteed
                tools_addendum = """Here are your available tools:\
    Either call the tool with the specified syntax, or leave its field blank.\n"""

                for tool in tools:
                    tools_addendum += str(tool)

            # Fetch underlying prompt, post string interpolation
            query = question_producer(*args, **kwargs)
            query += tools_addendum

            # Only add a tools field to message format if there are tools
            if tools:
                response_format = type(
                    f'{options.response_format.__name__}WithTools',
                    (options.response_format, Tool),
                    {},
                )
            else:
                response_format = options.response_format

            # Process the finalized query
            answer = self._qna(
                query,
                response_format=response_format,
                instructions=options.instructions,
            )

            # Potentially invoke tools here
            return answer

        return _send_and_await_reply

    @property
    def clients(self):
        """
        Clients on an operator shouldn't be altered directly in normal operations.
        """
        return self._clients

    @property
    @abstractmethod
    def instructions(self) -> str:
        """
        Define the operators base (system) instructions
        Used in qna
        """
        pass

    @cache
    def __getattribute__(self, name: str) -> Any:
        attr = super().__getattribute__(name)
        if name.startswith("__") or name in {"qna", "_qna"} or not callable(attr):
            return attr

        def wrapped_func(*args, **kwargs):
            options = OperatorOptions(**(self._options | kwargs.pop("options", {})))

            result = attr(*args, options=options.model_dump(), **kwargs)
            if not isinstance(result, str):
                return result

            llm_func = self.qna(attr)
            if options.run_async:
                # TODO: Converts args into kwargs for this function
                # Return an async job if requested
                return llm_func._delay(self, *args, options=options, **kwargs)

            return llm_func(*args, options=options, **kwargs)

        return wrapped_func

    @property
    def _options(self) -> dict[str, Any]:
        return {'instructions': self.instructions}

    def chat(self, message: str, options: dict[str, Any] = {}) -> str:
        """
        Chat with the operator with a direct message.
        """
        return message

    def invoke_tool(self, tool: Tool):
        """
        Invokes a tool on a message.
        Throws KeyError if the tool doesn't exist.
        Throws AttributeError if the function on the tool doesn't exist.
        Throws TypeError if the parameters are wrong.
        """
        tool_name = tool.tool_name
        tool_function = tool.tool_method
        tool_parameters = tool.tool_parameters
        func = getattr(TOOLS_REGISTRY[tool_name], tool_function)

        kwargs = {param.name: param.value for param in tool_parameters}

        return func(**kwargs)
