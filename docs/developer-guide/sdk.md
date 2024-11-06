# Operators

## Abstract Operators

Abstract Operators are the base building block of Operators. They handle a lot of magic behind the scenes, enabling asynchronous LM calls, saving of messages, and tool invocations.

### Methods

#### `__init__`

- clients (dict[str, LMClient]): A dictionary of LM clients available to the operator. The key is the enumerated name of the client (e.g. `'openai'`), and the value is the client wrapper object `LMClient`.

- tools (list[MetaTool]): A list of of Tools available to the operator. These tools are made available when `options['use_tools'] = True`. Similarly, `options['tools'] = [tool1, ...]` overrides the default list of tools.

- operator_id (uuid): A unique identifier for the operator. This is used to save messages and other data.

- project_id (uuid): A unique identifier for the project. This is used to save messages and other data.

- starting_prompt (str): The starting project prompt.

- store_messages (bool): Whether to store messages in the databases. Only works when the package `concrete-db` is installed.

- response_format (type[Message]): The response format of the operator. Message is a wrapper class for Pydantic Models which are used for OpenAI Structured Outputs.

- run_async (bool): Whether to run qna calls asynchronously via Celery. Only works when the package `concrete-celery` is installed and imported in the application. Also requires that a `celery` application is started.

#### `_qna`

A wrapper function for LM chat completions.

- query (str): The query to be sent to the LM.

- response_format (type[Message]): The response format of the operator. Message is a wrapper class for Pydantic Models which are used for OpenAI Structured Outputs.

- instructions (str): System instructions for the LM overriding class level instructions.

#### `qna`

A decorator for the `_qna` function. This function handles preprocessing and tool invocations.

#### `chat`

String returning function for chat completions with no template messages.

- message (str): The message to be sent to the LM.

- options (dict): Optional options for the qna call.

#### `invoke_tool`

Helper method for invoking tools. 

#### `__getattribute__`

Handles redirection of string returning functions on Operators to the `_qna` function. Also handles calling `_delay` on asynchronous calls.

### Properties

#### `client`

Returns the LM clients available to the operator, `self._clients`

#### `instructions`

Returns default system instructions for the operator

#### `_options`

Returns default options on the operator

## Operators

Operators are defined by their instructions property and string returning functions.

### Examples

- Simple example on how to use the Operator class

```python
from concrete.operators import Operator

operator = Operator()

print(operator.instructions)
print(operator.chat('Hello, how are you?'))

class CustomOperator(Operator):
    instructions = "This is a set of custom instructions"

    def chat_combative(self, message: str, options: dict = {}) -> str:
        return f'Respond combatively to "{message}"'


custom_operator = CustomOperator()
print(custom_operator.instructions)
print(custom_operator.chat_combative('Hello, how are you?'))
```

- Example on how to use the options parameter

```python
from concrete.operators import Operator
from concrete.models.messages import ProjectDirectory

operator = Operator()
operator.chat(
    "Could you make a directory for a helloworld python project?", options={'response_format': ProjectDirectory}
)
```

# Messages

Messages are a format for structured outputs from OpenAI completions. Outputs are validated against the Message format, guaranteeing the syntax.

Define your own message format by subclassing the Message class, and defining fields.

```python
from concrete.models.messages import Message

class CustomMessage(Message):
    field1: data_type = Field(..., description="Field 1 description")
    field2: data_type = Field(..., description="Field 2 description")
```

Messages can be used in Operators by passing the `response_format` option to string returning functions. By default, the `TextMessage` format is used.


# Tools

Tools represent an Operators ability to interact with external services and the world. Tools can be invoked by hand, or automatically by the Operator via their `invoke_tool` method.

## `MetaTool`

`MetaTool` provides a string representation of the tool. It uses type hints and documentation strings to create a human-readable representation of the tool.

metaclass from `MetaTool` to create a tool.

## Examples


```python
from concrete.tools import MetaTool
from concrete.tools import invoke_tool
class Arithmetic(metaclass = MetaTool):
    @classmethod
    def sum(cls, x: int, y: int) -> int:
        """
        Returns the sum of two numbers
        """
        return x + y

print(Arithmetic)
```


Last Updated: 2024-11-06 15:55:36 UTC

Lines Changed: +37, -0