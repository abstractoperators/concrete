import json
from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, cast
from uuid import UUID, uuid4

from openai.types.chat import ChatCompletion

from .celery import app
from .clients import CLIClient, OpenAIClient
from .models.messages import Message, Tool
from .tools import MetaTool
from .tools import invoke_tool as invoke_tool_func

# from .db.orm.models import MessageCreate, OperatorOptions
# from .models.clients import ConcreteChatCompletion, OpenAIClientModel


class AbstractOperatorMetaclass(type):
    OperatorRegistry: dict[str, any] = {}

    def __new__(
        cls,
        clsname,
        bases,
        classdict,
    ):
        new_class = super().__new__(cls, clsname, bases, classdict)

        AbstractOperatorMetaclass.OperatorRegistry.update({clsname: new_class})

        return new_class


# TODO mypy: figure out return types and signatures for class methods between this, the metaclass, and child classes
class AbstractOperator(metaclass=AbstractOperatorMetaclass):

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
        response_format: Message,
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
                message_format=response_format.as_response_format(),
            )
            .choices[0]
            .message
        )

        if response.refusal:
            CLIClient.emit(f"Operator refused to answer question: {query}")
            raise Exception("Operator refused to answer question")

        answer = response.content
        # TODO: This solution doesn't load nested dataclasses as their dataclass type, but as a dict
        return response_format(**json.loads(answer))

    def qna(self, question_producer: Callable[..., str]) -> Callable:
        """
        Decorate something on a child object downstream to get a response from a query

        question_producer is expected to return a request like "Create a website that does xyz"
        """

        @wraps(question_producer)
        def _send_and_await_reply(
            *args,
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
            options: dict = self._options | kwargs.pop('options', {})

            tools_addendum = ""
            if tools := (
                options.get('tools') if options.get('tools') else (self.tools if options.get('use_tools') else [])
            ):
                tools_addendum = """Here are your available tools. If invoking a tool will help you answer the question, fill in the exact values for tool_name, tool_method, and tool_parameters. Leave these fields empty if no tool is needed."""  # noqa

                for tool in tools:
                    tools_addendum += str(tool)

            # Fetch underlying prompt, post string interpolation
            query = question_producer(*args, **kwargs)
            query += tools_addendum

            # Only add a tools field to message format if there are tools
            if tools:
                response_format = options.get('response_format')
                response_format = dataclass(
                    type(
                        f'{response_format.__name__}WithTools',
                        (response_format, Tool),
                        {},
                    )
                )
            else:
                response_format = options.get('response_format')

            # Process the finalized query
            instructions = options.get('instructions')
            answer = self._qna(
                query,
                response_format=response_format,
                instructions=instructions,
            )

            # TODO Reconsider where this occurs.
            # This will be blocking, and the intermediate tool call will not be returned.
            # It also makes it difficult to do a manual invocation of the tool.
            # However, it aligns with goals of wanting Operators to be able to use tools
            if issubclass(type(answer), Tool) and answer.tool_name and answer.tool_method:
                resp = self.invoke_tool(cast(Tool, answer))
                if resp is not None and hasattr(resp, '__str__'):
                    # Update the query to include the tool call results.
                    tool_preface = f'You called the tool: {answer.tool_name}.{answer.tool_method}\n'
                    tool_preface += f'with the following parameters: {answer.tool_parameters}\n'
                    tool_preface += f'The tool returned: {str(resp)}\n'
                    tool_preface += 'Use these results to answer the following query:\n'
                    query = tool_preface + question_producer(*args, **kwargs)
                    answer = self._qna(
                        query,
                        response_format=options.response_format,
                        instructions=options.instructions,
                    )

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

    # TODO: Do not re-build function every time on access but
    # still allow properties to be overridden after instantiation
    def __getattribute__(self, name: str) -> Any:
        attr = super().__getattribute__(name)
        if name.startswith("__") or name in {"qna", "_qna", "invoke_tool"} or not callable(attr):
            return attr

        def wrapped_func(*args, **kwargs):
            options = self._options | kwargs.pop('options', {})

            result = attr(*args, options=self._options, **kwargs)
            if not isinstance(result, str):
                return result

            llm_func = self.qna(attr)
            # if options.run_async:
            #     # TODO: Converts args into kwargs for this function
            #     # Return an async job if requested
            #     return llm_func._delay(self, *args, options=options, **kwargs)

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
        return invoke_tool_func(tool)
